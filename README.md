# Rewrite Shortcut

This project builds a personal Apple Shortcut named **Rewrite in Somnath's
Voice**. From the Share Sheet it sends selected text to OpenAI, copies the
rewritten result to the clipboard, and shows a notification when it is ready.

The generated Shortcut uses `gpt-5.6-luna` with reasoning disabled for a quick,
inexpensive rewrite. Both settings can be changed in `config.toml`.

## Install

On your Mac, run:

```bash
./install.sh
```

The first run asks for your OpenAI API key with hidden input and saves it in the
git-ignored `.env` file. When Shortcuts opens, review the actions and click
**Add Shortcut**. If macOS asks whether to replace the existing shortcut during
a later install, choose **Replace**.

The following sections explain how to finish the device-specific setup after
installing the Shortcut.

## Set up on iPhone

### 1. Sync the Shortcut to the iPhone

The Shortcut should sync automatically when the Mac and iPhone use the same
Apple Account and Shortcuts iCloud sync is enabled. On the iPhone, open
**Settings → your name → iCloud → See All**, then ensure **Shortcuts** is on.

Open the **Shortcuts** app and confirm that **Rewrite in Somnath's Voice** is
present before continuing.

### 2. Enable the Share Sheet

1. In Shortcuts, tap **•••** on **Rewrite in Somnath's Voice**.
2. Tap the Shortcut name at the top, then tap **Details**.
3. Turn on **Show in Share Sheet**.
4. In the input settings, ensure at least **Text** and **Rich Text** are
   accepted.
5. Tap **Done**.

The Share Sheet is the panel that appears after tapping **Share** in another
app; the panel itself is not labelled “Share Sheet.”

### 3. Test the Share Sheet workflow

Notes is a good app for the first test:

1. Type a sentence in Notes and select it.
2. In the selection menu, tap **Share**. Tap **>** first if Share is hidden.
3. Expand the sharing panel and scroll vertically below the row of app icons.
4. If necessary, tap **View More**.
5. Tap **Rewrite in Somnath's Voice**.
6. Approve any OpenAI network or clipboard permissions requested on the first
   run.
7. Wait for the **Rewritten — paste to replace** notification.
8. Paste while the original text is selected to replace it with the rewrite.

Some apps restrict text selection or sharing. Confirm that the Shortcut works
in Notes before troubleshooting it in Slack, Gmail, Messages, or another app.

### 4. Add the Shortcut to Share Sheet Favorites

To remove the **View More** step:

1. Open the Share Sheet and tap **View More**.
2. Touch and hold **Rewrite in Somnath's Voice**.
3. Tap **Add to Favorites**.

If that option is unavailable, scroll to the bottom of the Share Sheet, tap
**Edit Actions…**, and add the Shortcut to Favorites there.

### 5. Enable the faster clipboard workflow

The optimized workflow is:

**Select text → Copy → triple-tap the back of the iPhone → Paste**

First, make the Shortcut use the clipboard when it is run without Share Sheet
input:

1. In Shortcuts, tap **•••** on **Rewrite in Somnath's Voice**.
2. At the top, find **Receive Text from Share Sheet**.
3. Tap **If There’s No Input: Continue**.
4. Change **Continue** to **Get Clipboard**.
5. Tap **Done**.

Then assign the Shortcut to Back Tap:

1. Open **Settings → Accessibility → Touch → Back Tap**.
2. Select **Triple Tap**. Triple Tap reduces the chance of accidentally sending
   clipboard content to OpenAI.
3. Scroll to **Shortcuts** and select **Rewrite in Somnath's Voice**.

To use it, select text, tap **Copy**, triple-tap the back of the iPhone, wait for
the notification, and paste. Pasting while the original text remains selected
replaces it without a separate delete step. On supported iPhones, the Action
button can be assigned to the Shortcut instead of using Back Tap.

Apple documents the relevant features in its guides for
[Share Sheet shortcuts](https://support.apple.com/guide/shortcuts/apd163eb9f95/ios),
[clipboard fallback](https://support.apple.com/guide/shortcuts/apd8195f96d6/ios),
and [Back Tap](https://support.apple.com/guide/shortcuts/apd897693606/ios).

The generated Shortcut does not currently preserve the **Get Clipboard**
fallback when it is replaced during a reinstall. Repeat step 5 after replacing
the Shortcut.

## Set up on Mac

For selected text on a Mac, the Services menu or a keyboard shortcut is more
convenient than the Share Sheet.

### 1. Enable the Services menu

1. Open the **Shortcuts** app on the Mac.
2. Double-click **Rewrite in Somnath's Voice**.
3. Click the **ⓘ Shortcut Details** button near the upper-right.
4. Enable **Use as Quick Action**.
5. Enable **Services Menu** underneath it.
6. If an input selector appears, ensure it accepts **Text** and **Rich Text**.
7. Close the details panel.

### 2. Test it in TextEdit

1. Open TextEdit and type a sentence that needs rewriting.
2. Select the sentence.
3. In the Mac menu bar, choose **TextEdit → Services → Rewrite in Somnath's
   Voice**. In some apps it is also available by Control-clicking selected text
   and opening **Services**.
4. Approve any first-run permission prompts.
5. Wait for the **Rewritten — paste to replace** notification.
6. Press **⌘V** while the original sentence is selected to replace it.

If the Shortcut is missing from the Services menu, open **System Settings →
Keyboard → Keyboard Shortcuts → Services**, find the Shortcut among the
text-related services, and enable it. Restart the app in which you are testing
if the Services menu does not refresh immediately.

### 3. Add a Mac keyboard shortcut

After the Services workflow works:

1. Open **Rewrite in Somnath's Voice** in Shortcuts.
2. Open **ⓘ Shortcut Details**.
3. Click **Add Keyboard Shortcut**.
4. Press an unused combination, such as **Control–Option–R**.

The normal Mac workflow is then **select text → press the keyboard shortcut →
wait for the notification → press ⌘V**.

See Apple's guide to
[running Shortcuts while working on a Mac](https://support.apple.com/guide/shortcuts-mac/apd163eb9f95/mac)
for the Share Sheet, Services, Quick Action, and keyboard-shortcut options.

## Tune the writing style

Edit `prompt.md`. It is the system-level writing instruction sent to OpenAI.
The starter prompt aims for fluent, concise, warm, professional English while
preserving meaning and personality. Add preferences and short before/after
examples as you learn what produces your voice best.

After every prompt or configuration change, rebuild and reinstall:

```bash
./install.sh
```

For a build without opening Shortcuts:

```bash
uv run rewrite-shortcut build
```

The signed file is written to `dist/`.

## Change or rotate the API key

Run:

```bash
uv run rewrite-shortcut setup-key
./install.sh
```

The `.env` file and `dist/` directory are ignored by Git. The signed Shortcut
still contains the API key because it calls OpenAI directly from your device.
Do not share the generated `.shortcut` file or the installed shortcut. Use a
dedicated project key with an appropriate usage budget, and rotate it if the
shortcut is ever shared accidentally.

## Project layout

- `prompt.md` — your editable writing style and rewrite rules
- `config.toml` — shortcut name, model, reasoning, and notification settings
- `.env` — your local API key (created on first install and ignored by Git)
- `src/rewrite_shortcut/` — plist generation and macOS signing code
- `dist/` — generated signed shortcut (ignored by Git)
