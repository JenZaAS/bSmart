# bSmart Protocol: admin/container design

This document records design boundaries for an admin or work container. Creating, updating, and redeploying the container is the orchestrated-Docker section of `hermes-runtime-onboarding.md`. Normal bSmart instances can ignore this file unless they are being set up as an admin or work container on a Docker or Dokploy-style VPS.

## Scope

Use this when reviewing the privilege boundary of a containerized Hermes/bSmart instance:

- an operator admin container, which may receive narrow host mounts only when that access is explicit;
- a work container, which should receive only its own data, workspace, secrets, and the project mounts selected later;
- a container that needs private GitHub access and project storage.

Creating, updating, or redeploying the container belongs to `hermes-runtime-onboarding.md`.

For the detailed GitHub credential/repo-access workflow, see `/workspace/bSmart-System/bSmart_Protocols/github-ai-access.md`.

Do not treat this as a requirement for every bSmart installation on non-container platforms.

## Container boundaries

Prefer least privilege by role.

- Admin container: may receive narrow host blueprint/helper/runtime mounts when explicitly intended.
- Work container: should normally receive only its own persistent data/workspace, its own secrets directory, optional shared read-only tools, and project/storage mounts selected through the bSmart project-storage workflow.
- Do not mount the Docker socket by default.
- Do not copy one admin instance's persona into other containers.

## Persistent paths

Recommended baseline for a work container. Host paths are placeholders. `/opt/data` is the in-container Hermes home.

```yaml
volumes:
  - <host-data-path>:/opt/data
  - <host-workspace-path>:/workspace
  - <host-secrets-path>:/run/secrets:ro
  - <host-shared-tools-path>:/host-tools/shared-tools:ro
```

For bSmart project storage, let the bSmart project-storage workflow select and verify `/projects` and `/sandboxes` instead of hard-coding a one-off exchange path.

## Runtime secrets pattern

Store per-container secrets in the container's own host secrets directory:

```text
<host-secrets-path>/
```

Mount the whole directory read-only:

```yaml
- <host-secrets-path>:/run/secrets:ro
```

Do not add separate file-level mounts below `/run/secrets` when the directory is already mounted read-only. Docker may fail because it cannot create the nested mountpoint inside a read-only mount.

For GitHub SSH access, put these files in the per-container secrets directory:

```text
<container>_container_ed25519
<container>_container_ed25519.pub
github_known_hosts
```

The private key must be readable by the container's non-root user. Confirm that uid and gid from the image. Do not assume a host default.

```bash
sudo chown <runtime-uid>:<runtime-gid> <host-secrets-path>/<container>_container_ed25519 \
  <host-secrets-path>/<container>_container_ed25519.pub \
  <host-secrets-path>/github_known_hosts
sudo chmod 600 <host-secrets-path>/<container>_container_ed25519
sudo chmod 644 <host-secrets-path>/<container>_container_ed25519.pub \
  <host-secrets-path>/github_known_hosts
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
- Project storage uses only the configured `/projects` or local `./projects` root.
- If the configured project root is unavailable, stop and report the storage problem; never substitute an unconfigured directory.

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
