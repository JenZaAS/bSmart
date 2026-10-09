# bSmart Codex plugin

Codex does not load the Hermes `bsmart-project` plugin, and current Codex builds do not reliably register custom slash commands. This plugin uses skills plus a SessionStart hook. The skills call `integrations/bsmart_client_adapter.py`, which calls the shared `/project` engine. `$bsmart-role` only prints a deprecation notice. Chat text cannot supply paths.

Invoke `$bsmart-project`, or ask for `/project`. `$bsmart-role` and `/role` do not select a project. The startup hook runs `bStart.py`. Codex does not run plugin hooks until the hook definition is reviewed and trusted. A web install does not deploy the hook script; the script has to exist on the machine.

## Local marketplace

This workspace lists the plugin in `.agents/plugins/marketplace.json`. Add that marketplace in Codex, install `bsmart`, trust the startup hook, and start a new session.

Node.js must be available. The hook command tries `python3`, then `python`, then `py -3`.
