# bSmart protocol: Security Watch

## Purpose

Security Watch is a scheduled, low-noise bSmart maintenance role for checking the parts of a VPS/container setup that an AI instance can already inspect safely.

It is designed to avoid every AI container repeating the same scan. By default, only the designated admin/security instance runs it.

## Default ownership

For Erling's VPS setup:

- Default owner: `SschwAdmin`
- Default cadence: weekly lightweight script-only scan
- Default delivery: operator/home chat only when findings or check failures occur
- Default posture: read-only inspection; no deploys, restarts, deletes, chmod/chown, secret disclosure, or host mutation

Other bSmart-enabled AI containers should not run this job unless the operator explicitly opts them in during setup or later configuration.

## Setup prompt rule

During bSmart setup or re-setup, ask:

> Should this AI instance run the bSmart Security Watch job?

Recommended choices:

1. `No — another admin instance owns it` default for ordinary worker/personal containers.
2. `Yes — this is the designated admin/security instance` for SschwAdmin-style containers.
3. `Limited local-only watch` for isolated containers that should check only their own workspace/state.

Record the choice in the instance-local `bSmart_Agent.md`; do not hardcode all containers to run the job.

## Weekly lightweight scan

Use a deterministic script-only job where possible. It should be fast, bounded, and silent unless there are findings.

Recommended checks:

- expected host-facing mounts exist and have expected read/write posture;
- Docker socket is absent unless explicitly approved;
- host helper wrappers exist and shell syntax checks pass;
- Dockerfiles and Compose blueprints avoid obvious high-risk patterns;
- secret-like assignments are not introduced in image blueprints or helper scripts;
- read-only secret mounts remain read-only where visible;
- backup folders exist and obvious backup file permissions are not world-readable;
- bSmart/project roots remain writable where expected;
- high-signal blueprint/helper files changed since the previous scan.

## Findings policy

Report only:

- `CRITICAL` — likely immediate security risk or broken expected boundary.
- `WARNING` — important drift, missing expected artifact, or suspicious but not confirmed issue.
- `CHANGED` — relevant blueprint/helper files changed since last scan.
- `UNKNOWN` — important state could not be inspected from this container.

Each reported finding should include a suggested next action or a suggestion to initiate an action process. The action process is interactive: the admin instance handles findings one by one and asks the operator with buttons/choices such as `Yes`, `No`, and `Other feedback` before taking or recommending any risky next step.

Avoid weekly noise from unchanged accepted design choices, such as known `nousresearch/hermes-agent:latest` base image usage when paired with manual force-pull update helpers.

## Monthly/deeper review

A monthly LLM-assisted review may summarize posture and technical debt using the latest script snapshot. Keep it separate from the weekly script-only watchdog so weekly checks stay cheap and predictable.

## Access limitations

Without a narrow host helper or Docker/Dokploy read-only bridge, Security Watch cannot authoritatively inspect:

- live running containers;
- actual Docker image digests;
- open host ports;
- Dokploy app runtime state;
- host package vulnerability status.

If those become required, add a least-privilege read-only helper instead of mounting the raw Docker socket.
