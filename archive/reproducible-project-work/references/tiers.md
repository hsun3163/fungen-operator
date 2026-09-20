# Proportional tiers

Use run cost × rerun frequency × lifespan × number of readers × cost of failure to select the evidence bar. State the factors, selected tier, and any user override; the domains below are reference profiles, not technology branches.

| Concern | Tier 1: small standalone script | Tier 2: HPC or scientific workflow | Tier 3: continuously running service |
|---|---|---|---|
| Profile | Cheap runs, infrequent reuse, short lifespan, one or few readers, low failure cost | Costly or repeated runs, shared use, meaningful lifespan, or material failure cost | Persistent operation, repeated change, multiple operators, high interruption or failure cost |
| Environment | Machine-readable direct dependency declarations with versions and one build command | Locked transitive environment with validation platform recorded; transferable artifact plus producing spec when the target has no network | Locked, deployable environment artifact with producing spec and recorded validation platform |
| Canonical path | One program or existing conventional entrypoint | One workflow or program entrypoint supporting narrow and scaled configurations | One deployment and operation entrypoint using the project's existing service convention |
| Run evidence | Execution-produced command, commit, configuration, input, output, time, and status record | Tier 1 fields plus scheduler or platform identifiers, unit-level completion, and cheap checksums | Tier 2 fields plus deployed artifact identity, lifecycle event, and service health evidence produced by the platform |
| Smoke verification | Small real-shaped input through the full entrypoint | Small real-shaped input through the same execution route used at scale | Small real-shaped request or workload through the same deployed route |
| Input provenance | Origin, integrity identity, parameters, and exclusions | Tier 1 plus generated-input code identities and transferable input declarations | Tier 2 plus external service and durable-state compatibility declarations |
| Configuration | One separated layer for machine-, user-, and site-specific values | Same, with scaled resource and execution settings declared | Same, with deployment-site and operating-policy values declared |
| Observability | Declared outputs, logs, and failure context | Step-and-input failures, unit status, isolated-step execution | Lifecycle, request or work-unit failure context, and platform-produced operating evidence |
| Resume | Required only when interruption cost matters under the five factors | Resume completed units without corruption or duplication | Resume or restart from durable state without duplicating effects |
| Runbook | Setup, smoke, run, outputs, debug | Setup, smoke, run, monitor, resume, one step, scale, debug | Setup, smoke, deploy or start, monitor, restart or resume, isolate work, scale, debug |
| External requirements | Declare omitted data, secrets, services, and hardware | Same, with acquisition and integrity procedures | Same, with availability and compatibility assumptions |
| History | One logical change per immutable commit | Same | Same |

Escalate when any factor materially raises the cost of rediscovery or failure. Do not add a mechanism merely because it appears in a higher tier; satisfy the evidence meaning with the project's existing convention, or the lightest conventional mechanism when none exists.
