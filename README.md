# bSmart-System

```yaml
name: bSmart-System
status: draft-v1
purpose: Portable system layer for bSmart-enabled Hermes workspaces.
system_root: /workspace/bSmart-System
content_root: /workspace/bSmart
extensions_root: /workspace/bSmart-Extensions
license: MIT
```

## What this repo contains

```yaml
contains:
  - reusable bootstrap instructions
  - setup and update procedures
  - protocols
  - templates
  - docs
  - examples
  - version and changelog

excludes:
  - local agent identity
  - local projects
  - local TODOs
  - local workdocs
  - local logs
  - secrets
  - Hermes runtime state
```

## Standard workspace layout

```text
/workspace/
├── bSmart-System/       # this git repo; safe to update
├── bSmart/              # local content/state; not overwritten by system updates
├── bSmart-Extensions/   # optional extension packs, e.g. Fabric
└── HERMES.md            # tiny Hermes hook outside bSmart
```

## Install into a Hermes container workspace

Use this when a Hermes container already has a persistent `/workspace` mount and should start loading bSmart on new sessions.

### Generic copy/paste

Run from the VPS host. Replace `SERVICE`, `AGENT_NAME`, `AGENT_ROLE`, and `OPERATOR` before running.

```bash
sudo bash - <<'BASH'
set -euo pipefail

SERVICE="hermes-digtech"
AGENT_NAME="DigTech"
AGENT_ROLE="Constrained Hermes work assistant for Dig Technology company work."
OPERATOR="Erling H Jensen"

WS="/opt/docker-workspace/${SERVICE}/workspace"
UID_GID="10000:10000"

install -d -o 10000 -g 10000 "$WS"

if [ ! -d "$WS/bSmart-System/.git" ]; then
  git clone https://github.com/JenZaAS/bSmart.git "$WS/bSmart-System"
else
  git -C "$WS/bSmart-System" pull --ff-only
fi

install -d -o 10000 -g 10000 \
  "$WS/bSmart" \
  "$WS/bSmart/bSmart_Projects" \
  "$WS/bSmart/bSmart_Workdocs" \
  "$WS/bSmart/bSmart_Library" \
  "$WS/bSmart-Extensions"

cat > "$WS/HERMES.md" <<'EOF'
At session start, read /workspace/bSmart-System/bSmart.md and follow it.
EOF

cat > "$WS/bSmart/bSmart_Agent.md" <<EOF
# bSmart agent profile

\`\`\`yaml
agent:
  name: ${AGENT_NAME}
  role: ${AGENT_ROLE}
  operator: ${OPERATOR}
  framework: Hermes
  platforms:
    - Telegram

access_model:
  writable_paths:
    - /workspace
    - /opt/data
  readonly_paths:
    - /host-tools/shared-tools
  unavailable:
    - Docker socket
    - VPS admin mounts unless explicitly configured
    - broad host filesystem access

operating_policy:
  default_posture: concise, practical, confidentiality-aware
  approval_thresholds:
    - ask before modifying important project files
    - ask before deleting, overwriting, or moving files
    - ask before actions involving credentials or external publication
  secret_handling: avoid exposing secrets in chat; prefer direct SSH/SFTP/rsync transfer for confidential files
\`\`\`
EOF

cat > "$WS/bSmart/bSmart_State.md" <<'EOF'
# bSmart state

- Mode: `Free`
- Active project (short name): `none`

Notes:
- Projects live under `/workspace/bSmart/bSmart_Projects/`.
EOF

cat > "$WS/bSmart/bSmart_TODO.md" <<'EOF'
# bSmart TODO

## Next tasks

- ⬜ Create/select first project.
- ⬜ Confirm preferred working style.
EOF

cat > "$WS/bSmart/bSmart_Log.md" <<EOF
# bSmart log

- Initial bSmart setup for ${SERVICE}.
EOF

chown -R "$UID_GID" "$WS/HERMES.md" "$WS/bSmart-System" "$WS/bSmart" "$WS/bSmart-Extensions"

echo "bSmart installed for ${SERVICE}."
echo "Next: restart the container, send /new to the bot, then send: Hi"
BASH
```

After running the block:

```bash
sudo docker restart hermes-digtech
```

Then in the bot chat:

```text
/new
Hi
```

Expected first real reply starts with the bSmart startup wording from `/workspace/bSmart-System/bSmart.md`.

### DigTech-ready values

For `hermes-digtech`, keep these values in the generic block:

```bash
SERVICE="hermes-digtech"
AGENT_NAME="DigTech"
AGENT_ROLE="Constrained Hermes work assistant for Dig Technology company work."
OPERATOR="Erling H Jensen"
```

## Update rule

```yaml
system_update_rule:
  allowed_to_modify:
    - /workspace/bSmart-System
  must_not_modify_without_approval:
    - /workspace/bSmart
    - /workspace/bSmart-Extensions
    - /workspace/HERMES.md
    - /opt/data/SOUL.md
```

See:
- `bSmart.md` for runtime bootstrap instructions.
- `bSmart_Setup.md` for first-time setup.
- `bSmart_Version.md` for version history and migration notes.
- `bSmart_Docs/system-vs-content.md` for the separation model.
