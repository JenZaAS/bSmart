# bSmart Protocol: admin/container design

This document captures reusable SschwAdmin lessons that should apply when initializing another bSmart-aware admin or work container. It is optional system guidance: normal bSmart instances can ignore it unless they are being set up as an admin/work container on a Docker/Dokploy VPS.

## Scope

Use this when creating or reviewing a containerized Hermes/bSmart instance such as:

- VPS admin assistant containers.
- Constrained work containers like `hermes-jenza` or `hermes-digtech`.
- Future bSmart-enabled containers that need private GitHub access and project storage.

Do not treat this as a requirement for every bSmart installation on non-container platforms.

## Container boundaries

Prefer least privilege by role.

- Admin container: may receive narrow host blueprint/helper/runtime mounts when explicitly intended.
- Work container: should normally receive only its own persistent data/workspace, its own secrets directory, optional shared read-only tools, and project/storage mounts selected through the bSmart project-storage workflow.
- Do not mount the Docker socket by default.
- Do not copy the SschwAdmin persona into non-admin containers.

## Persistent paths

Recommended baseline for a work container:

```yaml
volumes:
  - /opt/docker-workspace/<scope>/data-or-hermes-data:/opt/data
  - /opt/docker-workspace/<scope>/workspace:/workspace
  - /opt/docker-workspace/<scope>/secrets:/run/secrets:ro
  - /opt/shared-tools:/host-tools/shared-tools:ro
```

For bSmart project storage, let the bSmart project-storage workflow select and verify `/projects` and `/sandboxes` instead of hard-coding a one-off exchange path.

## Runtime secrets pattern

Store per-container secrets in the container's own host secrets directory:

```text
/opt/docker-workspace/<scope>/secrets/
```

Mount the whole directory read-only:

```yaml
- /opt/docker-workspace/<scope>/secrets:/run/secrets:ro
```

Do not add separate file-level mounts below `/run/secrets` when the directory is already mounted read-only. Docker may fail because it cannot create the nested mountpoint inside a read-only mount.

For GitHub SSH access, put these files in the per-container secrets directory:

```text
<container>_container_ed25519
<container>_container_ed25519.pub
github_known_hosts
```

The private key must be readable by the non-root container user. For Hermes containers on this VPS, that is usually UID/GID `10000:10000`:

```bash
sudo chown 10000:10000 /opt/docker-workspace/<scope>/secrets/<container>_container_ed25519 \
  /opt/docker-workspace/<scope>/secrets/<container>_container_ed25519.pub \
  /opt/docker-workspace/<scope>/secrets/github_known_hosts
sudo chmod 600 /opt/docker-workspace/<scope>/secrets/<container>_container_ed25519
sudo chmod 644 /opt/docker-workspace/<scope>/secrets/<container>_container_ed25519.pub \
  /opt/docker-workspace/<scope>/secrets/github_known_hosts
```

Use strict host checking with a pinned `github_known_hosts` file:

```yaml
environment:
  GIT_SSH_COMMAND: "ssh -i /run/secrets/<container>_container_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/secrets/github_known_hosts"
```

Avoid `StrictHostKeyChecking=no` and avoid writing `known_hosts` only into ephemeral container home directories as the primary solution.

## bSmart project storage and migration

- Prefer `/projects` as canonical project root once configured.
- Prefer `/sandboxes` for VPS-local sandboxes outside Git.
- Before suggesting a project volume, create or ask the operator to create the host folder first.
- If migrating from legacy `/workspace/bSmart/Projects`, never delete or overwrite it during setup.
- Inspect old and new roots, prompt the operator, perform a dry-run/listing first, then copy only after explicit approval.
- Leave old source cleanup/archive as a separate explicit decision.

## Verification checks

Inside the container, verify:

```bash
id
ls -l /run/secrets
git ls-remote git@github.com:<owner>/<repo>.git | head
findmnt -T /workspace
findmnt -T /projects || true
findmnt -T /sandboxes || true
```

If Git reports `No ED25519 host key is known for github.com`, the private key may be fine but `github_known_hosts` is missing or `GIT_SSH_COMMAND` is not using it.
