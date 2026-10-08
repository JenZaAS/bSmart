# bProtective Hermes plugin

bProtective is a disabled-by-default Hermes `pre_tool_call` guard for terminal actions. The policy lives in `integrations/bprotective/`; this directory is the Hermes adapter.

## Behavior

- Catastrophic commands are blocked deterministically.
- Risky commands return Hermes's `approve` directive and use the existing operator approval gate.
- Missing state defaults to off.
- Invalid state fails closed for terminal commands.
- `/bprotective on` and `/bprotective off` each require a separate confirmation.
- POSIX and Windows command rules are the same rules the CLI and the other adapters use.

## Install

The adapter imports `integrations/bprotective/core.py` from the bSmart-System checkout. Copying the two plugin files does not copy the core.

```bash
mkdir -p "$HERMES_HOME/plugins/bprotective"
cp plugin.yaml __init__.py "$HERMES_HOME/plugins/bprotective/"
export BSMART_SYSTEM_ROOT=/path/to/bSmart-System
hermes plugins doctor "$HERMES_HOME/plugins/bprotective" --ci
hermes plugins enable bprotective
```

In-tree, the adapter finds `integrations/bprotective` next to `integrations/hermes`. Set `BSMART_SYSTEM_ROOT` or `BPROTECTIVE_CORE` when the plugin directory was copied elsewhere. A container checkout at `/workspace/bSmart-System` is found without the variable.

Start a new Hermes session or restart the gateway. Installation and plugin enablement do not activate the guard. Use:

```text
/bprotective status
/bprotective on
```

Then confirm the displayed request with `/bprotective yes <ID>`.

## Scope

The Hermes adapter covers Hermes terminal tools in both CLI and gateway sessions. It is defense in depth and does not replace OS, container, Docker, or host-level controls. Other clients call this same core through `scripts/bprotective` or their hook adapter.
