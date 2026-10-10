# bSmart Protocol: Hermes runtime onboarding

```yaml
bsmart-protocol-summary:
  id: hermes-runtime-onboarding
  title: Hermes runtime onboarding
  purpose: Set up and update a Hermes runtime on any host, and keep bSmart updates separate from that runtime.
  load_when:
    - Hermes runtime
    - Hermes update
    - native Hermes
    - Docker Hermes
    - containerized Hermes
    - pull_policy never
    - state.db corruption
  applies_everywhere:
    - bSmart system and instance updates do not change the Hermes runtime
    - verify runtime-only dependencies after the agent is running
    - state.db corruption is incident-only
  orchestrated_docker_only:
    - live Compose
    - pull_policy
    - image build
    - s6
    - Dokploy-style redeploy
```

```yaml
protocol:
  id: hermes-runtime-onboarding
  title: Hermes runtime onboarding
  purpose: Update a Hermes agent without confusing a bSmart checkout change with a runtime change, and deploy orchestrated Docker agents without treating a host blueprint as live.
  use_when:
    - the operator asks to set up or update Hermes on Windows, Linux, macOS, WSL, Docker Desktop, or an orchestrated host
    - a host-built image must not be pulled from a public registry on recreate
    - state.db reports corruption
  scope: every Hermes runtime. Compose, image-build, pull_policy, and s6 rules apply only to orchestrated Docker.
  excludes:
    - provisioning named local workstation agents (local-agent-onboarding.md)
    - bSmart instance questions and content repair (bSmart_Setup.md)
    - credential material, tokens, private keys, and .env contents
  related_protocols:
    - local-agent-onboarding
    - bootstrap
    - project-storage
    - admin-container-design
    - github-ai-access
    - secret-provider-onboarding
    - operations
```

This protocol is operator-triggered. It is not part of every session startup. Placeholders such as `<agent>` and `<host-data-path>` are not real paths. Do not copy an example into an orchestrator.

## Where it applies

```yaml
everywhere:
  hosts:
    - Windows native
    - Linux native
    - macOS native
    - WSL
    - Docker Desktop or another workstation container
    - VPS or Dokploy-style orchestrated Docker
  rules:
    - a bSmart system pull or instance push does not rebuild an image, restart Hermes, or change live Compose
    - after the agent is running, import dependencies that exist only at runtime
    - if state.db reports corruption, use the incident section only
orchestrated_docker_only:
  when: a Compose document stored by an orchestrator is what the next deploy uses
  not_this_section:
    - native Windows, Linux, or macOS
    - WSL when Hermes is the native Linux process, not a Compose service
    - Docker Desktop when no orchestrator stores a live Compose document
  rules:
    - live Compose, pull_policy, image build, the update workflow, and s6
```

`local-agent-onboarding.md` still provisions a workstation's named agents. This protocol does not replace that. Its everywhere rules, and the incident section, still apply to those agents.

## Everywhere

`bSmart_Setup.md` and `bsmart-update` change bSmart files and hooks. They do not change the Hermes process. On an orchestrated host they also do not build an image or edit live Compose. When a runtime restart or redeploy is required, say so and get approval before doing it. On a native install that restart is `hermes gateway` or the Desktop app, not a container recreate.

After the agent is up, confirm a dependency this agent needs only at runtime by importing it in that running process. A successful image build or install step is not that check. Local speech-to-text is one example: `faster_whisper` must import in the running agent.

If `state.db` reports corruption, see [Incident only: state.db corruption](#incident-only-statedb-corruption). That section is not a setup or update step.

## Orchestrated Docker only

Skip this heading on a native or non-orchestrated install.

A host blueprint is not proof of what is deployed.

```yaml
sources_of_truth:
  host_blueprint: Dockerfile and Compose file on the host. Editing it changes nothing that is running.
  built_image: the image id produced by a build on that host. Building it does not recreate a container.
  live_compose: the service definition stored by the orchestrator. On Dokploy this is the Raw Compose document. Other orchestrators have the same role under another label. This document is what the next deploy uses.
  running_container: the container that is actually running. It can lag live Compose until a recreate.
rule: Before a redeploy, copy an approved blueprint change into live Compose. A blueprint edit that was not synced is not part of the deployment.
mutation_path: Use the host's allowlisted <update-harness> when one exists. Do not drive builds, sync, redeploy, or restart through an unrestricted docker client or a mounted Docker socket.
paths:
  in_container_hermes_home: /opt/data
  host_data_path: <host-data-path>
  rule: /opt/data is the path inside the container. <host-data-path> is the host directory mounted there. Do not use one path as if it were the other.
```

Read the blueprint and the live Compose as two documents. Diff them. Do not assume they match because they once did.

`<update-harness>` is an optional host pattern, not a bSmart-System command and not a tool that exists on every machine. It may build, validate, sync live Compose, and redeploy only named services. If none is documented, stop and ask how this host builds and redeploys. Do not invent a Docker-socket workflow or a fixed install path. Describe the harness by what this host allows it to do.

### Host-local images

An image that exists only because this host built it must not be pulled from a registry when the service is recreated.

```yaml
pull_policy_rule:
  applies_to: every service whose image is host-local, not only the agent being created or updated
  required_key: pull_policy
  required_value: never
  placement: service-level sibling of image. Putting the key on the line after image is a readability convention; Compose ignores key order. The key must not be nested under image, build, or another service.
  failure_mode: Recreate may try the registry. The running container keeps working until recreate or until the local image cache is gone.
  audit: Before creating or updating an agent, list every host-local image in live Compose and confirm pull_policy never beside its image key.
```

```yaml
services:
  <agent>:
    image: <local-image-name>:<tag>
    pull_policy: never
```

A published image that the orchestrator is supposed to pull does not use `pull_policy: never`. `nousresearch/hermes-agent:latest` is a moving public base until a host Dockerfile builds a local image from it.

### Image build

```yaml
base_image: Record the image id the build produced. The tag nousresearch/hermes-agent:latest moves.
toolchain: Check what the current base image provides on PATH before reusing uv or pip commands. Upstream images have built with uv pinned under /opt/hermes/tools, which does not mean uv is on PATH for every tag.
optional_patches: If the target block is absent, print a warning and leave the file unchanged. A warning is not evidence the patch took effect. A required patch fails the build when its block is absent.
web_build: Do not repeat a web build the base image or an earlier stage already finished. A rename across filesystem boundaries fails with EXDEV. Copy artifacts that must cross a mount.
outcomes:
  image_build_success: the build exited 0 and produced an image id. The container has not been proven to start.
  sanity_container: a short-lived container ran its check. Host cgroup or systemd policy can block it even when the image is usable. Read this output separately from the build log.
  runtime_success: the orchestrator recreated the service, the container is running, and the gateway is connected.
```

### Safe update workflow

Do the steps in order. Steps 1–4 only read and draft. Step 5 approves that draft before it is applied. Step 6 saves the rollback point and applies the draft to the host blueprint. Step 7 approves again immediately before any runtime write. Steps 8–10 are those writes. Step 11 reads the running service. A hash match proves text sync only. If the draft changes after either approval, stop and ask again.

1. **Resolve identifiers.** Record `<agent>`, `<service-id>`, the container name, `<blueprint-path>`, `<host-data-path>`, `<host-workspace-path>`, and the image name. Do not guess one from another.
2. **Read the blueprint, the update helper, and live Compose separately.** Do not treat one document as a copy of another.
3. **Compare hashes.** Record both Compose hashes. A match is not health.
4. **Draft a narrow change and validate it.** Do not write it to the orchestrator yet. Do not reformat the rest of the file, widen mounts, or add a Docker socket. `pull_policy: never` is a sibling of `image`. The next-line placement is for readers; Compose ignores key order.
5. **Approve the concrete planned change before applying it.** Wait for approval of that draft.
6. **Save the rollback point, then apply the draft to the host blueprint.** Copy the current live Compose and record the image id that is running now, before a build can move a tag. Do not sync yet.
7. **Approve again immediately before runtime writes.** Runtime writes are build, sync, redeploy, and restart. This approval must match the draft and the blueprint. If it does not, stop.
8. **Build through the harness.** Read the image-build result and the sanity-container result as separate outputs. Record the new image id.
9. **Sync Raw Compose.** Write the approved Compose into the orchestrator's stored definition. Re-read it and compare hashes.
10. **Redeploy and verify recreate.** Confirm the container id or start time changed. If recreate fails, or the new container is not the approved image, restore the saved live Compose and the previous image id through the same harness.
11. **Read back the running service.** Record image id, status, start time, published ports, mounts, and recent logs. Confirm the gateway is up and the agent's channel is connected. Keep the saved Compose and previous image id until this read-back matches the approval.

Creation uses the same steps. Audit `pull_policy: never` on every host-local image before step 5.

## Verification

```yaml
everywhere:
  - the Hermes process is running and its channel is connected
  - a runtime-only dependency this agent needs imports in that process
  - a bSmart update is not reported as a runtime update
orchestrated_docker_only:
  - a Compose hash match proves the texts match, not that the container is healthy
  - read container status, start time or container id, and logs after every create or update
```

If a check was not run, say it was not run.

## Open questions

Verify these on the live agent.

Everywhere:

- Which runtime-only imports does this agent need after start?
- Which channel must be connected before the update is called done?

Orchestrated Docker only:

- Which live-Compose services use a host-local image, and which already have `pull_policy: never` beside `image`?
- What are `<service-id>`, the container name, `<blueprint-path>`, `<host-data-path>`, and `<host-workspace-path>`?
- Does this host have an allowlisted `<update-harness>`, and what may it do?
- Is the running image a host-built child of `nousresearch/hermes-agent:latest`, and what image id is it?
- Can a sanity container on this host fail because of cgroup or systemd policy?

## What this protocol does not own

Design boundaries for an admin or work container stay in `admin-container-design.md`. Project and sandbox mounts stay in `project-storage.md`. GitHub credentials stay in `github-ai-access.md` and `secret-provider-onboarding.md`. Named local workstation provisioning stays in `local-agent-onboarding.md`. Instance setup questions stay in `bSmart_Setup.md`.

## Incident only: state.db corruption

Not a setup or update step. Use this only when `state.db` reports corruption. The same steps apply on every host. Upstream flags: [State DB recovery](https://hermes-agent.nousresearch.com/docs/developer-guide/state-db-recovery). Home resolution: [Session storage](https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage).

`state.db`, `state.db-wal`, and `state.db-shm` are one SQLite image. The database is `<hermes-home>/state.db`. Hermes resolves that home from `HERMES_HOME` when it is set, otherwise from the platform default. A named profile is that profile's home (`hermes gateway stop -p <profile>`), not the default home.

Where the live file is, from upstream docs:

- Linux, macOS, and WSL: `~/.hermes/state.db`, unless `HERMES_HOME` points somewhere else. [Windows (Native)](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native) says WSL data lives under `~/.hermes`.
- Windows native: the installer sets `HERMES_HOME` to `%LOCALAPPDATA%\hermes`, so the file is `%LOCALAPPDATA%\hermes\state.db`. `%USERPROFILE%\.hermes` is only the location when `HERMES_HOME` was set to that path, which is the documented way to match a Linux or WSL layout. It is not the installer default.
- Official Docker image, including Docker Desktop: `/opt/data/state.db` inside the container. [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) maps `/opt/data` from the host's `~/.hermes` in the quickstart. An orchestrated host may mount another directory. Read the mount. Do not guess it. On the host, the same three files are under that mount, `<host-data-path>`.

How to stop, and leave it stopped until the new file is in place:

- Native Windows, Linux, or macOS: `hermes gateway stop` for that profile. Quit the Desktop app and stop the dashboard or cron if they are running. On Windows this also stops the scheduled task.
- Container, including one supervised by s6: stop the container and do not start it again until promotion is finished. A container restart brings the gateway back unless `hermes gateway stop` had recorded it stopped. Do not start a second `hermes gateway` while s6 supervises one.

Then:

1. Do not rebuild `messages_fts_trigram` in place. Do not run `hermes doctor --fix` while anything still has the database open. Do not delete a sidecar, and do not copy `state.db` without the other two.
2. Copy the three files together into a writable `<recovery-workspace>` that is not the live home. Set `HERMES_HOME` to that workspace. Do not point it at the live home, and do not open the live WAL set through a read-only mount. SQLite may need to create the shm sidecar.
3. Inspect the copy, then write a different file:

```text
HERMES_HOME=<recovery-workspace> hermes sessions recover --source <recovery-workspace>/state.db --inspect-only
HERMES_HOME=<recovery-workspace> hermes sessions recover --source <recovery-workspace>/state.db --output <recovery-workspace>/recovered-state.db
```

`--output` is not the copied source and not the live `state.db`. `hermes sessions repair --check-only` on that copy is an inspection alternative. `hermes sessions repair` without `--check-only` writes and is not the first step. Restoring the newest snapshot from `state-snapshots/` is the other alternative. `repair.lock` is not a backup. A `*.malformed-backup` file is damaged; do not copy it over the live database.

4. On the recovered file, read-only, run `PRAGMA integrity_check` and count sessions and messages. Checkpoint it with `PRAGMA wal_checkpoint(TRUNCATE)` until it is one file with no wal and no shm beside it.
5. Move the live `state.db`, `state.db-wal`, and `state.db-shm` together into one forensic directory. If a sidecar is already absent, record that. Do not leave a sidecar that is present. Confirm the live directory no longer contains any of the three names. Only then place the checkpointed file as `state.db`. SQLite replays a leftover `state.db-wal` into whatever `state.db` sits beside it.
6. Start the agent the way it normally starts: one native gateway or Desktop app, or the container through its orchestrator. Then run `hermes doctor`.
