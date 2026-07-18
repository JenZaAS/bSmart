# bSmart Protocol: GitHub access for AI containers

This protocol defines the standard way bSmart/Hermes AI containers get access to GitHub repositories owned by JenZaAS or related organizations.

Use this for containers such as SschwAdmin, DigTech, JenZa, Hugo, and future bSmart-aware work containers.

## Goals

- Use the shared AI GitHub machine user: [JenZaAI](https://github.com/JenZaAI).
- Grant repository access case-by-case, not globally.
- Keep credentials outside Docker images, Git repositories, and `/workspace`.
- Make every AI container use the same secrets/mount/runtime pattern.
- Prefer branches and PRs for updates; avoid direct pushes to `main` unless explicitly approved.

## Identity and attribution

GitHub identity:

```text
JenZaAI — https://github.com/JenZaAI
```

Public GitHub comments/posts must be shown to Erling in full before posting. Approval is for the exact text, not just the idea of posting.

Default public comment signature:

```markdown
—
Posted by [JenZaAI](https://github.com/JenZaAI) via [bSmart AI workflow](https://github.com/JenZaAS/bSmart), approved by [JenZAAS](https://github.com/JenZaAS).
```

## Credentials: SSH vs token

Use both, for different jobs:

| Credential | Used for | Notes |
|---|---|---|
| SSH key | `git clone`, `git pull`, `git push` | Required/preferred for private repo git transport. |
| GitHub token via `GH_TOKEN` | `gh` API actions: PR comments, issue comments, PR metadata, releases | SSH alone is not enough for GitHub API comments. |

The current shared `public_repo` token is suitable for public-repo comments only. It does not grant private repo contents access.

For private repository API operations, create/use a token with the minimum private-repo permissions required, or use SSH for git and limit token use to public comments.

## Host secrets layout

Each container gets its own host-side secrets directory mounted read-only as `/run/secrets`.

Examples:

```text
/opt/docker-workspace/hermes-admin/secrets
/opt/docker-workspace/hermes-digtech/secrets
/opt/docker-workspace/ai/jenza/secrets
/opt/docker-workspace/hermes-hugo/secrets
```

Expected files when GitHub access is enabled:

```text
/run/secrets/jenzai_container_ed25519       # private SSH key; never print
/run/secrets/jenzai_container_ed25519.pub   # public SSH key; safe to show
/run/secrets/github_known_hosts             # pinned GitHub host keys
/run/secrets/github_token                   # optional token for gh/API; never print
```

Host permissions for Hermes containers using UID/GID `10000`:

```bash
sudo chown root:10000 /opt/docker-workspace/<container>/secrets
sudo chmod 750 /opt/docker-workspace/<container>/secrets
sudo chown root:10000 /opt/docker-workspace/<container>/secrets/jenzai_container_ed25519 /opt/docker-workspace/<container>/secrets/github_token 2>/dev/null || true
sudo chmod 640 /opt/docker-workspace/<container>/secrets/jenzai_container_ed25519 /opt/docker-workspace/<container>/secrets/github_token 2>/dev/null || true
sudo chown root:10000 /opt/docker-workspace/<container>/secrets/jenzai_container_ed25519.pub /opt/docker-workspace/<container>/secrets/github_known_hosts 2>/dev/null || true
sudo chmod 644 /opt/docker-workspace/<container>/secrets/jenzai_container_ed25519.pub /opt/docker-workspace/<container>/secrets/github_known_hosts 2>/dev/null || true
```

## Compose/runtime pattern

Mount the whole secrets directory, not individual secret files inside an already read-only `/run/secrets` mount:

```yaml
volumes:
  - /opt/docker-workspace/<container>/secrets:/run/secrets:ro
```

Set SSH command for git operations:

```yaml
environment:
  GIT_SSH_COMMAND: "ssh -i /run/secrets/jenzai_container_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/secrets/github_known_hosts"
```

Do not set `StrictHostKeyChecking=no`.

## GitHub-side repo access workflow

For each private repo:

1. In GitHub, add [JenZaAI](https://github.com/JenZaAI) to the repo or an appropriate team.
2. Grant the least permission needed:
   - `Read` for inspect-only work.
   - `Write` for branch pushes and PRs.
   - Avoid admin unless truly required.
3. Protect `main` where possible:
   - require PR before merge,
   - avoid direct pushes by AI containers unless explicitly approved.
4. Add the container's public SSH key to the JenZaAI GitHub account if it is not already present.

## Container-side verification

Inside the target container:

```bash
id
ls -l /run/secrets
ssh-keygen -lf /run/secrets/jenzai_container_ed25519.pub
GIT_SSH_COMMAND="ssh -i /run/secrets/jenzai_container_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/secrets/github_known_hosts" \
  git ls-remote git@github.com:JenZaAS/<repo>.git HEAD
```

If `gh` is needed and `/run/secrets/github_token` exists:

```bash
GH_TOKEN="$(cat /run/secrets/github_token)" gh auth status
GH_TOKEN="$(cat /run/secrets/github_token)" gh api user --jq '.login + " " + .html_url'
```

Expected user:

```text
JenZaAI https://github.com/JenZaAI
```

## Clone/update workflow

Clone private repos into that container's project storage, usually `/projects`:

```bash
git clone git@github.com:JenZaAS/<repo>.git /projects/<repo>
```

For updates:

```bash
cd /projects/<repo>
git status
git switch -c ai/<short-task-name>
# edit/test
git add <files>
git commit -m "<concise message>"
git push -u origin ai/<short-task-name>
```

Then create a PR with `gh` if token/API auth exists, or ask Erling to open the PR manually.

## Example: DigTech access to `DIG_MATLAB`

GitHub side:

1. Add [JenZaAI](https://github.com/JenZaAI) to `JenZaAS/DIG_MATLAB` with `Write` permission.
2. Confirm the DigTech public SSH key is added to the JenZaAI account, labelled for DigTech.

VPS host secrets:

```text
/opt/docker-workspace/hermes-digtech/secrets/jenzai_container_ed25519
/opt/docker-workspace/hermes-digtech/secrets/jenzai_container_ed25519.pub
/opt/docker-workspace/hermes-digtech/secrets/github_known_hosts
/opt/docker-workspace/hermes-digtech/secrets/github_token        # optional for gh/API
```

After redeploying DigTech, verify inside DigTech:

```bash
git ls-remote git@github.com:JenZaAS/DIG_MATLAB.git HEAD
```

Clone:

```bash
git clone git@github.com:JenZaAS/DIG_MATLAB.git /projects/DIG_MATLAB
```

## Guardrails

- Never print or paste private keys/tokens into chats, logs, docs, or commits.
- Never bake credentials into images.
- Never commit credentials to bSmart or project repositories.
- Prefer per-container SSH keys even when using the same JenZaAI account.
- If a shared token is used, treat rotation as affecting every container that received it.
- Public GitHub comments require full-text approval by Erling before posting.
