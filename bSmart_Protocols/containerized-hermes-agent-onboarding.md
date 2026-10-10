# bSmart Protocol: containerized Hermes agent onboarding

```yaml
bsmart-protocol-summary:
  id: containerized-hermes-agent-onboarding
  title: Containerized Hermes agent onboarding
  purpose: Create and update a Hermes agent that runs in Docker under a VPS or Dokploy-style orchestrator, without treating a host blueprint as the live deployment.
  load_when:
    - containerized Hermes
    - Docker Hermes agent
    - VPS Hermes
    - Dokploy
    - orchestrator Compose
    - pull_policy never
    - Hermes image rebuild
    - Hermes redeploy
    - state.db recovery
    - agent update harness
```

```yaml
protocol:
  id: containerized-hermes-agent-onboarding
  title: Containerized Hermes agent onboarding
  purpose: Set up and update one Hermes agent whose container is defined by an orchestrator, not by a file that merely sits on the host.
  use_when:
    - the operator asks to create, update, rebuild, redeploy, or recover a Docker Hermes agent on a VPS or similar orchestrator
    - a host-built image must not be pulled from a public registry on recreate
    - live Compose, the running container, and the bSmart checkout have to be kept distinct
  scope: orchestrated Docker hosts (VPS, Dokploy-style control planes, and the same shape elsewhere)
  excludes:
    - local workstation Docker Desktop onboarding (local-agent-onboarding.md)
    - bSmart instance questions, feature setup, and content repair (bSmart_Setup.md)
    - credential material, tokens, private keys, and .env contents
  related_protocols:
    - local-agent-onboarding
    - bootstrap
    - project-storage
    - admin-container-design
    - github-ai-access
    - secret-provider-onboarding
    - operations
  reference:
    state_db: https://hermes-agent.nousresearch.com/docs/developer-guide/state-db-recovery
```

This protocol is operator-triggered. It is not part of every session startup. Instance names, host paths, image tags, service ids, and channel names below are placeholders. Replace them from the live host. Do not copy an example into an orchestrator.

## Deployment model

A host blueprint is not proof of what is deployed.

```yaml
sources_of_truth:
  host_blueprint: Dockerfile and Compose file on the host. Editing it changes nothing that is running.
  built_image: the image id produced by a build on that host. Building it does not recreate a container.
  live_compose: the service definition stored by the orchestrator. On Dokploy this is the Raw Compose document. Other orchestrators have the same role under another label. This document is what the next deploy uses.
  running_container: the container that is actually running. It can lag live Compose until a recreate.
rule: Before a redeploy, copy an approved blueprint change into live Compose. A blueprint edit that was not synced is not part of the deployment.
mutation_path: Use the host's allowlisted update harness when one exists. Do not drive builds, sync, redeploy, or restart through an unrestricted docker client or a mounted Docker socket.
```

Read the blueprint and the live Compose as two documents. Diff them. Do not assume they match because they once did.

## Host-local images

An image that exists only because this host built it must not be pulled from Docker Hub, or any other registry, when the service is recreated.

```yaml
pull_policy_rule:
  applies_to: every service whose image is host-local, not only the agent being created or updated
  required_key: pull_policy
  required_value: never
  placement: service-level sibling of image, directly under the image key in that service
  not_sufficient:
    - a comment
    - a blueprint file the orchestrator is not using
    - pull_policy nested under build or under a different service
  failure_mode: Recreate may try the registry. The running container keeps working until recreate or until the local image cache is gone, so the missing key is invisible in ordinary logs.
  audit: Before creating or updating an agent, list every service in live Compose that uses a host-local image and confirm pull_policy: never directly under its image key.
```

Example shape only. Every angle-bracket token is a placeholder:

```yaml
services:
  <agent>:
    image: <local-image-name>:<tag>
    pull_policy: never
```

A published image that the orchestrator is supposed to pull does not use `pull_policy: never`. Classify each service before editing the key. `nousresearch/hermes-agent:latest` is a moving public base, not a host-local image, until a host Dockerfile builds a local image from it.

## Image build guardrails

```yaml
base_image:
  common_base: nousresearch/hermes-agent:latest
  rule: That tag moves. Record the image id the build actually produced. Do not treat the tag string as a permanent contract.
toolchain:
  uv: The base image may not have uv on PATH. Do not add Dockerfile steps that call uv unless that image's PATH has been checked.
  package_manager: Hermes uses pm. Use the interpreter and package tool the image already provides.
optional_patches:
  rule: An optional patch looks for a target block. If that block is absent, the patch prints a warning and leaves the file unchanged. It must not apply a partial edit, and a warning is not evidence that the patch took effect.
  required_patches: A patch the image cannot run without fails the build when its target block is absent.
web_build:
  rule: Do not repeat a web asset build the base image or an earlier stage already finished.
  exdev: A rename across filesystem boundaries fails with EXDEV (invalid cross-device link). If artifacts must cross a mount, copy them. Do not rely on rename.
outcomes:
  image_build_success: The build command exited 0 and produced an image id. The container has not been proven to start.
  sanity_container: A short-lived container from that image ran its check. Host cgroup or systemd policy can block this container even when the image is usable. Read this output separately from the build log. Sanity failure is not automatically a bad image. Sanity success is not runtime health.
  runtime_success: The orchestrator recreated the service, the container is running, and the gateway is connected. Only this outcome counts as an updated agent.
runtime_only_dependencies:
  rule: After the service is up, import or probe dependencies that exist only in the running container.
  example: For local speech-to-text, confirm faster_whisper imports inside the running container. A successful build stage is not that check.
```

## bSmart, instance, and deployment are different layers

Pushing or pulling bSmart does not rebuild an image and does not change live Compose.

```yaml
layers:
  bsmart_system: the reusable checkout, usually /workspace/bSmart-System inside the container. A system update changes this checkout only.
  instance_content: /workspace/bSmart and the rest of the mounted workspace. An instance push changes that content only.
  host_blueprint: files on the host such as <blueprint-path>. Not live until synced.
  built_image: <local-image-name>@<image-id>
  live_compose: orchestrator-stored Compose for <service-id>
  running_container: <container-id> started at a specific time
before_update_identify:
  - source and instance state (system revision, instance dirty/clean, content revision)
  - host blueprint path and hash
  - built image id
  - live Compose hash
  - running container id, status, and start time
paths:
  in_container_hermes_home: /opt/data
  host_data_path: <host-data-path>
  rule: /opt/data is the path inside the container. <host-data-path> is the host directory mounted there. Do not use one path as if it were the other. Recovery files, snapshots, and forensic copies are named on the path that the process doing the copy can see.
workspace:
  in_container: /workspace
  host: <host-workspace-path>
```

`bSmart_Setup.md` and `bsmart-update` finish instance files and hooks. They do not build images, edit live Compose, or recreate containers. When those deployment actions are required, continue in this protocol and get approval before each mutation.

## Allowlisted update harness

An allowlisted update harness is an optional host pattern, not a bSmart-System command and not a tool that exists on every machine.

```yaml
harness:
  pattern_name: agent-update
  meaning: a narrow host command that may build, validate, sync live Compose, and redeploy only named services
  existence: discover it on this host. If none is documented, stop and ask the operator how this host builds and redeploys. Do not invent a docker-socket workflow and do not assume a fixed install path.
  preference: when a harness exists, it is the only mutation path for build, sync, redeploy, and restart
  unrestricted_docker: not the update path. Direct docker build, compose up, or restart bypasses the allowlist and can recreate a service that still points at Docker Hub.
  read_only_inspection: prefer the orchestrator's read-only view or a read-only helper. Do not mount the Docker socket into the agent container to inspect or deploy.
```

Describe the harness by what this host allows it to do. Do not document a site-local binary path as if every deployment has that file.

## Safe update workflow

Do the steps in order. Steps 1–3 are read-only. Step 4 is approval of one concrete diff. Steps 5–6 may prepare that diff on the host blueprint. Steps 7–9 mutate the image, live Compose, or the running service and do not start until step 4 still matches the diff. If the diff changes, ask again immediately before step 7. A hash match in step 3 proves text sync only.

1. **Resolve identifiers.** Record `<agent>`, the orchestrator `<service-id>`, the container name, `<blueprint-path>`, `<host-data-path>`, `<host-workspace-path>`, and the image name. These strings are often different from each other. Do not guess one from another.
2. **Read the blueprint, the update helper, and live Compose separately.** Read the host Dockerfile and Compose, and the harness or helper definition if this host has one. Then read the orchestrator's live Compose. Do not open one and treat it as the other.
3. **Compare hashes.** Hash the blueprint Compose and the live Compose. Record both hashes and whether they match. A match is not health. A mismatch means the next edit must say which document is being changed.
4. **Get explicit approval immediately before build, sync, redeploy, or restart.** State the service, the files, the image, and the exact operation. Wait for approval of that operation. Do not batch later mutations under an earlier, broader yes.
5. **Make a narrow change.** Change only the service and the keys this task requires. Do not reformat or replace the rest of live Compose. Do not widen mounts, add a Docker socket, or change other agents in the same file.
6. **Validate Compose.** Validate the document the orchestrator will store. A valid host blueprint file is not a valid live document until it is the text that will be synced.
7. **Build through the harness.** Build the one image. Read the image-build result and the sanity-container result as separate outputs. Record the image id. If the sanity container fails, say whether the log shows a host cgroup or systemd block before calling the image bad.
8. **Sync Raw Compose.** Write the approved Compose into the orchestrator's stored definition (Dokploy Raw Compose, or that orchestrator's equivalent). Re-read it and compare hashes with the approved text.
9. **Redeploy and verify recreate.** Redeploy through the harness or orchestrator. Confirm the container id or start time changed. A command that exits 0 without a new start time did not recreate the service.
10. **Read back the running service.** Record image id, status, start time, published ports, mounts, and recent logs. Confirm the gateway process is up and the agent's channel is connected. When the agent uses Telegram, that connection is part of the check. Do not stop at a healthy-looking Compose hash.

Creation of a new agent uses the same ten steps. The audit of `pull_policy: never` on every host-local image in live Compose happens before step 4.

## state.db recovery

Hermes keeps the profile database at `/opt/data/state.db` inside the container, which is `<host-data-path>/state.db` on the host. `state.db`, `state.db-wal`, and `state.db-shm` are one SQLite image. Sidecar files are not optional copies.

Upstream mechanics: [State DB recovery](https://hermes-agent.nousresearch.com/docs/developer-guide/state-db-recovery). The rules below are the operating guardrails. They do not replace that guide.

```yaml
do_not_start_with:
  - an in-place rebuild of messages_fts_trigram
  - hermes doctor --fix while any process still has the database open
  - deleting state.db-wal or state.db-shm
  - copying state.db without its wal and shm
  - writing a recovered database onto the live state.db path
stop_first:
  - stop the agent container through the orchestrator or allowlisted harness
  - keep it stopped for the whole recovery and verification window
  - a second writer, including a supervisor restart, invalidates the copy
preserve_together:
  - state.db
  - state.db-wal
  - state.db-shm
look_for_existing_copies:
  backups:
    - state-snapshots/
    - files named *.malformed-backup
    - other backup files already beside the database
  not_a_backup:
    - repair.lock is a lock or marker, not a database backup, and must not be restored over state.db
  restore_caution: malformed-backup files and corrupt bak files are often the damaged bytes. Do not copy them onto the live database because they exist.
inspect_first: hermes sessions recover --source <state.db> --inspect-only
write_recovery_to: a new database path that is not the live state.db
recovery_container:
  writable_workspace: a separate host directory mounted for the recovered file
  live_data: mounted read-only
  never: mount <host-data-path> read-write as /opt/data on a recovery container
verify_readonly:
  - PRAGMA integrity_check on the recovered database, read-only
  - session and message counts
  - counts must not be treated as healthy if integrity_check is not ok
promote:
  - keep the damaged original under a forensic name on the host data path
  - put the verified database in place only after that forensic copy exists
  - start the agent through the orchestrator after promotion
  - then run hermes doctor
gateway:
  rule: If s6, or another process supervisor inside the image, already runs the gateway, do not start a second gateway. hermes gateway start inside that container is a second writer. Use the supervisor or the orchestrator restart path.
```

Run `hermes` with `HERMES_HOME` set to the Hermes home visible in that environment: `/opt/data` in the agent container, or `<host-data-path>` when the command runs on the host against that directory. `--inspect-only` must not modify the source file. Recovery output goes to a separate path, for example a file under the recovery workspace, never to the live `state.db`.

After promotion, runtime success still includes container status, logs, and the gateway channel. `hermes doctor` is the post-start check, not the first repair action.

## Verification

```yaml
verification:
  hash_match: proves the compared texts are the same. It does not prove the container is running, the image is the one you built, the mounts are right, or the gateway is connected.
  always_read:
    - container status
    - start time or container id, to see whether recreate happened
    - logs
  runtime_examples:
    - faster_whisper imports when this agent uses local speech-to-text
    - gateway process is the supervised one, not a second process
    - channel connection, including Telegram when that is the agent's channel
  bsmart_layer: a successful bsmart-update or instance push does not count as a container update
```

If a check was not run, say it was not run. Do not fill it in from a previous agent.

## Open questions

Verify these on the live agent. This protocol does not know the answers.

- Which services in live Compose use a host-local image, and which of them already have `pull_policy: never` directly under `image:`?
- What are this agent's `<service-id>`, container name, `<blueprint-path>`, `<host-data-path>`, and `<host-workspace-path>`?
- Does this host have an allowlisted update harness, and which operations is it allowed to perform?
- Is the image still `nousresearch/hermes-agent:latest` or a host-built child, and what image id is running?
- Does a sanity container on this host fail because of cgroup or systemd policy?
- Which runtime-only imports does this agent need after start?
- Is the gateway supervised by s6 or by another process supervisor?
- Where are `state-snapshots/`, malformed backups, and any real backup files for this profile?
- Which channel (Telegram or another) must be connected before the update is called done?

## What this protocol does not own

Design boundaries for an admin or work container stay in `admin-container-design.md`. Project and sandbox mounts stay in `project-storage.md`. GitHub credentials stay in `github-ai-access.md` and `secret-provider-onboarding.md`. Local workstation agents stay in `local-agent-onboarding.md`. Instance setup questions stay in `bSmart_Setup.md`.
