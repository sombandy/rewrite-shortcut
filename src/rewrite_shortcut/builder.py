from __future__ import annotations

import os
import plistlib
import re
import shutil
import subprocess
import tempfile
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OBJECT_REPLACEMENT_CHARACTER = "\ufffc"
VALID_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}
VALID_SIGNING_MODES = {"anyone", "people-who-know-me"}


class ConfigurationError(RuntimeError):
    """Raised when local configuration cannot produce a safe Shortcut."""


@dataclass(frozen=True)
class ShortcutConfig:
    name: str
    model: str
    reasoning_effort: str
    api_url: str
    notification: str
    prompt_file: Path
    output_directory: Path
    signing_mode: str


def load_config(root: Path = PROJECT_ROOT) -> ShortcutConfig:
    config_path = root / "config.toml"
    try:
        with config_path.open("rb") as config_file:
            values = tomllib.load(config_file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Missing configuration file: {config_path}") from error

    required = {
        "name",
        "model",
        "reasoning_effort",
        "api_url",
        "notification",
        "prompt_file",
        "output_directory",
        "signing_mode",
    }
    missing = sorted(required.difference(values))
    if missing:
        raise ConfigurationError(f"Missing config values: {', '.join(missing)}")

    reasoning_effort = str(values["reasoning_effort"])
    if reasoning_effort not in VALID_REASONING_EFFORTS:
        allowed = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise ConfigurationError(f"reasoning_effort must be one of: {allowed}")

    signing_mode = str(values["signing_mode"])
    if signing_mode not in VALID_SIGNING_MODES:
        allowed = ", ".join(sorted(VALID_SIGNING_MODES))
        raise ConfigurationError(f"signing_mode must be one of: {allowed}")

    return ShortcutConfig(
        name=str(values["name"]),
        model=str(values["model"]),
        reasoning_effort=reasoning_effort,
        api_url=str(values["api_url"]),
        notification=str(values["notification"]),
        prompt_file=root / str(values["prompt_file"]),
        output_directory=root / str(values["output_directory"]),
        signing_mode=signing_mode,
    )


def load_api_key(root: Path = PROJECT_ROOT) -> str | None:
    environment_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if environment_key:
        return environment_key

    env_path = root / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "OPENAI_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        return value or None
    return None


def save_api_key(api_key: str, root: Path = PROJECT_ROOT) -> Path:
    key = api_key.strip()
    if not key or key == "sk-your-key-here" or not key.startswith("sk-"):
        raise ConfigurationError("That does not look like an OpenAI API key (expected sk-…).")
    if "\n" in key or "\r" in key:
        raise ConfigurationError("The API key must be a single line.")

    env_path = root / ".env"
    env_path.write_text(f"OPENAI_API_KEY={key}\n", encoding="utf-8")
    env_path.chmod(0o600)
    return env_path


def build_signed_shortcut(
    *,
    api_key: str,
    root: Path = PROJECT_ROOT,
) -> Path:
    if shutil.which("shortcuts") is None:
        raise ConfigurationError("Apple's 'shortcuts' command is required; build this on macOS.")

    key = api_key.strip()
    if not key or key == "sk-your-key-here" or not key.startswith("sk-"):
        raise ConfigurationError("Set a valid OPENAI_API_KEY before building.")

    config = load_config(root)
    try:
        prompt = config.prompt_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise ConfigurationError(f"Missing prompt file: {config.prompt_file}") from error
    if not prompt:
        raise ConfigurationError(f"Prompt file is empty: {config.prompt_file}")

    workflow = make_workflow(config=config, api_key=key, instructions=prompt)
    output_path = config.output_directory / f"{_safe_filename(config.name)}.shortcut"
    config.output_directory.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="rewrite-shortcut-") as temporary_directory:
        temporary_path = Path(temporary_directory)
        unsigned_path = temporary_path / "unsigned.shortcut"
        signed_path = temporary_path / "signed.shortcut"
        with unsigned_path.open("wb") as shortcut_file:
            plistlib.dump(workflow, shortcut_file, fmt=plistlib.FMT_BINARY, sort_keys=False)

        try:
            subprocess.run(
                [
                    "shortcuts",
                    "sign",
                    "--mode",
                    config.signing_mode,
                    "--input",
                    str(unsigned_path),
                    "--output",
                    str(signed_path),
                ],
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise ConfigurationError("macOS could not sign the generated Shortcut.") from error

        signed_path.replace(output_path)

    output_path.chmod(0o600)
    return output_path


def make_workflow(
    *,
    config: ShortcutConfig,
    api_key: str,
    instructions: str,
) -> dict[str, Any]:
    get_text_id = _uuid()
    request_id = _uuid()
    output_id = _uuid()
    first_output_id = _uuid()
    content_id = _uuid()
    first_content_id = _uuid()
    response_text_id = _uuid()

    actions = [
        _action(
            "is.workflow.actions.gettext",
            get_text_id,
            WFTextActionText=_token_string(
                OBJECT_REPLACEMENT_CHARACTER,
                {"{0, 1}": {"Type": "ExtensionInput"}},
            ),
        ),
        _action(
            "is.workflow.actions.downloadurl",
            request_id,
            ShowHeaders=True,
            WFHTTPBodyType="JSON",
            WFHTTPHeaders=_dictionary(
                [
                    _dictionary_item("Authorization", f"Bearer {api_key}"),
                    _dictionary_item("Content-Type", "application/json"),
                ]
            ),
            WFHTTPMethod="POST",
            WFJSONValues=_dictionary(
                [
                    _dictionary_item("model", config.model),
                    _dictionary_item(
                        "reasoning",
                        _dictionary([_dictionary_item("effort", config.reasoning_effort)]),
                        item_type=1,
                    ),
                    _dictionary_item("instructions", instructions),
                    _dictionary_item(
                        "input",
                        _token_string(
                            OBJECT_REPLACEMENT_CHARACTER,
                            {
                                "{0, 1}": _action_output(
                                    output_uuid=get_text_id,
                                    output_name="Text",
                                )
                            },
                        ),
                    ),
                ]
            ),
            WFURL=config.api_url,
        ),
        _get_dictionary_value_action(
            action_uuid=output_id,
            key="output",
            input_uuid=request_id,
            input_name="Contents of URL",
        ),
        _list_item_action(
            action_uuid=first_output_id,
            input_uuid=output_id,
            input_name="Dictionary Value",
        ),
        _get_dictionary_value_action(
            action_uuid=content_id,
            key="content",
            input_uuid=first_output_id,
            input_name="Item from List",
        ),
        _list_item_action(
            action_uuid=first_content_id,
            input_uuid=content_id,
            input_name="Dictionary Value",
        ),
        _get_dictionary_value_action(
            action_uuid=response_text_id,
            key="text",
            input_uuid=first_content_id,
            input_name="Item from List",
        ),
        _action(
            "is.workflow.actions.setclipboard",
            _uuid(),
            WFInput=_token_attachment(
                output_uuid=response_text_id,
                output_name="Dictionary Value",
            ),
        ),
        _action(
            "is.workflow.actions.notification",
            _uuid(),
            WFNotificationActionBody=config.notification,
        ),
    ]

    return {
        "WFQuickActionSurfaces": [],
        "WFWorkflowActions": actions,
        "WFWorkflowClientVersion": "4711",
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 61440,
            "WFWorkflowIconStartColor": 431817727,
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowInputContentItemClasses": [
            "WFAppContentItem",
            "WFArticleContentItem",
            "WFSafariWebPageContentItem",
            "WFStringContentItem",
            "WFURLContentItem",
            "WFRichTextContentItem",
        ],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowTypes": ["ActionExtension", "WFWorkflowTypeShowInSearch"],
    }


def _uuid() -> str:
    return str(uuid.uuid4()).upper()


def _safe_filename(name: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9._ -]+", "", name).strip().rstrip(".")
    return filename or "Rewrite Shortcut"


def _action(identifier: str, action_uuid: str, **parameters: Any) -> dict[str, Any]:
    return {
        "WFWorkflowActionIdentifier": identifier,
        "WFWorkflowActionParameters": {"UUID": action_uuid, **parameters},
    }


def _text(value: str) -> dict[str, Any]:
    return {
        "Value": {"string": value},
        "WFSerializationType": "WFTextTokenString",
    }


def _token_string(value: str, attachments: dict[str, Any]) -> dict[str, Any]:
    return {
        "Value": {
            "attachmentsByRange": attachments,
            "string": value,
        },
        "WFSerializationType": "WFTextTokenString",
    }


def _dictionary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "Value": {"WFDictionaryFieldValueItems": items},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def _dictionary_item(
    key: str,
    value: str | dict[str, Any],
    *,
    item_type: int = 0,
) -> dict[str, Any]:
    serialized_value = _text(value) if isinstance(value, str) else value
    if item_type == 1:
        serialized_value = {
            "Value": serialized_value,
            "WFSerializationType": "WFDictionaryFieldValue",
        }
    return {
        "WFItemType": item_type,
        "WFKey": _text(key),
        "WFValue": serialized_value,
    }


def _action_output(*, output_uuid: str, output_name: str) -> dict[str, str]:
    return {
        "OutputName": output_name,
        "OutputUUID": output_uuid,
        "Type": "ActionOutput",
    }


def _token_attachment(*, output_uuid: str, output_name: str) -> dict[str, Any]:
    return {
        "Value": _action_output(output_uuid=output_uuid, output_name=output_name),
        "WFSerializationType": "WFTextTokenAttachment",
    }


def _get_dictionary_value_action(
    *,
    action_uuid: str,
    key: str,
    input_uuid: str,
    input_name: str,
) -> dict[str, Any]:
    return _action(
        "is.workflow.actions.getvalueforkey",
        action_uuid,
        WFDictionaryKey=key,
        WFInput=_token_attachment(output_uuid=input_uuid, output_name=input_name),
    )


def _list_item_action(
    *,
    action_uuid: str,
    input_uuid: str,
    input_name: str,
) -> dict[str, Any]:
    return _action(
        "is.workflow.actions.getitemfromlist",
        action_uuid,
        WFInput=_token_attachment(output_uuid=input_uuid, output_name=input_name),
    )
