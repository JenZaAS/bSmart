# bProtective Hermes plugin

bProtective is a disabled-by-default Hermes `pre_tool_call` guard for terminal actions.

## Behavior

- Catastrophic commands are blocked deterministically.
- Risky commands return Hermes's `approve` directive and use the existing operator approval gate.
- Missing state defaults to off.
- Invalid state fails closed for terminal commands.
- `/bprotective on` and `/bprotective off` each require a separate confirmation.

## Install

Copy `plugin.yaml` and `__init__.py` into the active Hermes profile:

```bash
mkdir -p "$HERMES_HOME/plugins/bprotective"
cp plugin.yaml __init__.py "$HERMES_HOME/plugins/bprotective/"
hermes plugins doctor "$HERMES_HOME/plugins/bprotective" --ci
hermes plugins enable bprotective
```

Start a new Hermes session or restart the gateway. Installation and plugin enablement do not activate the guard. Use:

```text
/bprotective status
/bprotective on
```

Then confirm the displayed request with `/bprotective yes <ID>`.

## Scope

The first implementation covers Hermes terminal tools in both CLI and gateway sessions. It is defense in depth and does not replace OS, container, Docker, or host-level controls. Other client adapters should call the same policy core rather than copy this command list.
