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

### Copy/paste installer

Run this from the Docker/VPS host. It prompts for the local container/service values.

```bash
sudo bash - <<'BASH'
set -euo pipefail

ask() {
  local prompt="$1"
  local default="$2"
  local value
  if [ ! -r /dev/tty ]; then
    echo "ERROR: this installer needs an interactive terminal for prompts." >&2
    exit 1
  fi
  if [ -n "$default" ]; then
    read -r -p "$prompt [$default]: " value < /dev/tty || value=""
    printf '%s' "${value:-$default}"
  else
    while true; do
      read -r -p "$prompt: " value < /dev/tty || value=""
      if [ -n "$value" ]; then
        printf '%s' "$value"
        return 0
      fi
      echo "This value is required." >&2
    done
  fi
}

SERVICE="$(ask 'Container/service name' '')"
AGENT_NAME="$(ask 'Agent display name' "$SERVICE")"
AGENT_ROLE="$(ask 'Short agent role/purpose' 'Constrained Hermes work assistant')"
OPERATOR="$(ask 'Operator/user name' 'operator')"
WORKSPACE_HOST_PATH="$(ask 'Host path for the persistent workspace' "/opt/docker-workspace/${SERVICE}/workspace")"
HERMES_UID="$(ask 'Hermes runtime UID' '10000')"
HERMES_GID="$(ask 'Hermes runtime GID' '10000')"

WS="$WORKSPACE_HOST_PATH"
UID_GID="${HERMES_UID}:${HERMES_GID}"

install -d -o "$HERMES_UID" -g "$HERMES_GID" "$WS"

if [ ! -d "$WS/bSmart-System/.git" ]; then
  git clone https://github.com/JenZaAS/bSmart.git "$WS/bSmart-System"
else
  git -C "$WS/bSmart-System" pull --ff-only
fi

install -d -o "$HERMES_UID" -g "$HERMES_GID" \
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
    - ask/update after setup

access_model:
  writable_paths:
    - /workspace
    - /opt/data
  readonly_paths:
    - ask/update after setup
  unavailable:
    - Docker socket unless explicitly configured
    - broad host filesystem access unless explicitly configured

operating_policy:
  default_posture: concise, practical, confidentiality-aware
  approval_thresholds:
    - ask before modifying important project files
    - ask before deleting, overwriting, or moving files
    - ask before actions involving credentials or external publication
  secret_handling: avoid exposing secrets in chat; prefer direct transfer methods for confidential files
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

- ⬜ Review and complete `/workspace/bSmart/bSmart_Agent.md` for this instance.
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
echo "Restart command, if Docker container name matches SERVICE: sudo docker restart ${SERVICE}"
BASH
```

After running the block, restart the Hermes container. Example when the container name equals the prompted service name:

```bash
sudo docker restart <service-name>
```

Then in the bot/chat for that Hermes instance:

```text
/new
Hi
```

Expected first real reply starts with the bSmart startup wording from `/workspace/bSmart-System/bSmart.md`.

### What belongs in setup vs install

The installer should only bootstrap files and ask for the minimum local values needed to create them. The generated `/workspace/bSmart/bSmart_Agent.md` is intentionally local content; review and refine it after install using `bSmart_Setup.md` or by asking the agent to complete the bSmart setup for that instance.

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
