# HermesSessionShortcuts

```yaml
name: HermesSessionShortcuts
status: bundled_optional_extension
source_root: /workspace/bSmart-System/bSmart-Extensions/HermesSessionShortcuts
install_root: /workspace/bSmart-Extensions/HermesSessionShortcuts
license: MIT
purpose: Optional Hermes plugin package for quick session listing/resume shortcuts across Telegram and CLI.
```

## What it provides

This extension packages the Hermes user plugin `session-shortcuts`.

Commands:

- `/hist` — list recent Telegram sessions by default.
- `/hist telegram` — list Telegram sessions explicitly.
- `/hist all` — intentionally list all sources; use explicitly because it can reveal CLI/local sessions.
- `/hresume <number-or-session-id>` — resume in CLI mode; in gateway mode show a compact recap, exact `/resume <id>` command, and a prepared `/queue` command to review the recap into working context.
- `/teleresume [search]` — select the latest Telegram session, optionally matching search text; in gateway mode show a compact recap, exact `/resume <id>` command, and a prepared `/queue` command to review the recap into working context.

## Why `/hist` defaults to Telegram

Telegram is a remote chat surface. A default all-source history list could reveal local CLI/admin session titles or previews in Telegram. Cross-source browsing is still available through `/hist all`, but it must be explicit.

## Install into a Hermes home

From the extension root:

```bash
scripts/install-session-shortcuts.sh /opt/data
```

Then enable inside the target Hermes container/home:

```bash
HERMES_HOME=/opt/data hermes plugins enable session-shortcuts --no-allow-tool-override
```

Restart the Hermes gateway/CLI process after enabling.

## Docker image pattern

Because `/opt/data` is normally a bind-mounted persistent Hermes home, files copied to `/opt/data` at image build time are hidden by the runtime volume. Instead:

1. Bake the plugin into the image under `/opt/hermes/bsmart-plugins/session-shortcuts`.
2. At container startup, sync that directory into `/opt/data/plugins/session-shortcuts`.
3. Run `hermes plugins enable session-shortcuts --no-allow-tool-override` idempotently.

Current AI Hermes blueprints using this pattern:

- `hermes-admin`
- `hermes-digtech`
- `hermes-hugo`
- `hermes-jenza`
- `grimne`
- `hermes-unity`

After changing this extension, sync `plugins/session-shortcuts/` into each image source context and rebuild/redeploy the affected containers.
