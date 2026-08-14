from __future__ import annotations

import argparse
import getpass
import subprocess
import sys

from rewrite_shortcut.builder import (
    ConfigurationError,
    PROJECT_ROOT,
    build_signed_shortcut,
    load_api_key,
    save_api_key,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rewrite-shortcut",
        description="Build and install Somnath's personal text-rewriting Apple Shortcut.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Build and sign the Shortcut without opening it.")
    subparsers.add_parser("install", help="Build the Shortcut and open the macOS installer.")
    subparsers.add_parser("setup-key", help="Save the OpenAI API key in the local .env file.")
    return parser


def _get_or_prompt_for_key() -> str:
    api_key = load_api_key()
    if api_key:
        return api_key
    if not sys.stdin.isatty():
        raise ConfigurationError(
            "OPENAI_API_KEY is missing. Run 'uv run rewrite-shortcut setup-key' first."
        )
    api_key = getpass.getpass("OpenAI API key (input is hidden): ")
    path = save_api_key(api_key)
    print(f"Saved the key locally in {path}")
    return api_key


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "setup-key":
            api_key = getpass.getpass("OpenAI API key (input is hidden): ")
            path = save_api_key(api_key)
            print(f"Saved the key locally in {path}")
            return

        output_path = build_signed_shortcut(api_key=_get_or_prompt_for_key())
        print(f"Built {output_path}")
        print("Note: the generated Shortcut contains your API key; do not share it.")

        if args.command == "install":
            subprocess.run(["open", str(output_path)], check=True, cwd=PROJECT_ROOT)
            print("The Shortcut is open in Shortcuts. Confirm Add Shortcut to finish.")
    except (ConfigurationError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
