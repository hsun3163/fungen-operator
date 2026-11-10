# Changelog

All notable operator changes are recorded here in Keep a Changelog style.
Operator versions follow Semantic Versioning independently of bundled Ollama
0.40.6 and Codex 0.155.1. Historical versions were assigned retrospectively;
their embedded package version remains 0.1.0. A release commit can follow the
image source commit with validation-only documentation. SHA-256 below identifies
the SIF bytes; the registry manifest digest identifies its ORAS descriptor.
GHCR repository: `ghcr.io/hsun3163/fungen-operator`.

## [1.2.0] - 2026-11-09

- Git tag: `v1.2.0`; release commit: [commit selected by v1.2.0](https://github.com/hsun3163/fungen-operator/commit/v1.2.0).
- Image source commit: [a583993]. Later release commits contain validation and delivery documentation.
- SIF SHA-256: `31cb32693ed3e0a7cd237bbb2d4e94d345b128bbe56e5a6ab25d7eee9d3c99cc`.
- GHCR manifest digest: pending publication.
- Immutable GHCR tags: `1.2.0`, `1.2.0-ollama0.40.6-codex0.155.1`.
- Moving GHCR tags at publication: `ollama0.40.6-codex0.155.1`, `latest`.

### Fixed

Each quote is from the BU SCC round-5 field report (2026-11-09).
All four cause fixes and their regression tests are in [38d6f22].

- **A, GPU capacity:** "SGE placed it on a 12 GB P100 that Ollama could not use."
  SGE/Slurm rendered only GPU count while LSF computed capacity. A shared model,
  context and GPU-count requirement now drives all renderers. Host `qconf -sc`
  discovers and validates SGE capacity complexes; SCC-like XS Q4 requests
  `gpu_memory=24G`. Explicit `none` is recorded and disclosed when a site has no
  capacity mechanism. Slurm accepts a validated site Feature plus declared
  capacity, and explicitly describes its lack of a standard VRAM request.
  LSF's existing resource output is preserved.
- **B, upgrades:** "[Errno 17] File exists" on old skill links. `exists()` misses
  dangling symlinks, and earlier live install links were refused. Setup now
  examines links first and repairs dangling or recognizable older Fungen links.
  Real directories and unrelated live links remain protected, with exact
  move-aside instructions. Regression cases cover both skill roots and reruns.
- **C, scheduler detection:** "No scheduler client detected; defaulting to local".
  Setup looked for host clients inside the image. Image setup now copies the
  installer and prints the host command; host setup detects clients and scheduler
  environment evidence, including `SGE_ROOT` without `qsub` on PATH. Downloads and
  advanced-context creation are dispatched into the image by host setup. Host
  operator execution and mount/readiness guards remain enforced.
- **D, SGE memory:** "was killed at 67 GB of virtual memory". Four fixed
  `h_vmem=16G` limits constrained CUDA virtual address reservations. Setup discovers
  physical per-slot memory resources, prefers `mem_per_core`, and scales host RAM
  with model/context. SCC-like XS Q4 now requests four slots at 16G physical RAM
  each. Virtual-only sites receive an explicit explained headroom calculation.

### Added

- One operator version source for package metadata, `fungen --version`, and the
  captured image `source.json`; semantic Git/GHCR tags and this release history.
  Implemented in [a44f8b3]; the user guide and tag scheme are in [a583993].

### Notes

- **E is not a product defect:** "the tester's .bashrc overrides HOME to a project
  folder". Restoring the shell HOME made the config visible; HOME selection is
  unchanged. Live SCC GPU allocation remains a site-native tester check.
- The prior test-isolation incident affecting an account config is documented in
  the BU evidence report. The offending test now isolates config paths; this
  release's tests and image acceptance use isolated HOME/config paths.

### Validation

753 host tests passed with zero failures/skips on 244 frozen files, unchanged
across 3,096 checks (job 281657746). Round-six native XS acceptance and real tmux
S/XS acceptance passed: health, actual file-writing answer, actual XS child,
backend round trip and SGE guide guards. Fake SGE tests verify SGE_ROOT discovery
without qsub, qconf resource requests and skill-link repair. A real prior bundle
was installed with embedded package 0.1.0, then upgraded in place to distribution
and CLI 1.2.0 successfully. All acceptance GPU services and PTYs were stopped.
Live SCC allocation remains the tester's site-native verification step.

Pull the immutable release with Apptainer (or use `singularity`):

```bash
apptainer pull fungen-operator-1.2.0.sif oras://ghcr.io/hsun3163/fungen-operator:1.2.0
```

## [1.1.0] - 2026-11-07

- Git tag: `v1.1.0`; release commit: [89f88c2].
- Embedded image source commit: [9910940].
- SIF SHA-256: `3f6ff0ee3dbd5fb8b76c25c87e5006c752c759604c5e5ade96769ddf90d4117f`.
- GHCR manifest: `sha256:d32217d97d6515307894209cdb51cdd3b59efd9d7e848d2a18bbf6851e26910f`.
- Historical delivery tags: `ollama0.40.6-codex0.155.1`, `latest` (moving).
- Retrospective immutable GHCR tag: `1.1.0`; original manifest confirmed available
  on 2026-11-09; tagging status is recorded in the release publication evidence.

### Fixed

Quotes below are from the 2026-11-07 interactive findings and Round-2 repair.

- "Host setup fails after its questions." The installer unconditionally required
  `/opt/fungen` even after copying its bundle to the host. [10ad9fb] uses and
  validates that retained bundle for host reconfiguration and prints a copy fix
  when it is incomplete.
- "Health says VERIFIED although local launch refuses the endpoint." Health and
  launch used different validation. [10ad9fb] adds the launcher's served-catalog
  identity validation to `check`; pending and failed states retain nonzero exits.
- "The SGE xQTL guide omits scheduler and project questions." The guide silently
  computed them. [10ad9fb] prompts on fresh roots and preserves explicit flags,
  saved-root contracts, and predecessor/nonempty-root guards.
- "The public S Q4 tag's reported metadata is inconsistent." The official Q4 tag
  has a mixed Q4_K/Q8_0 payload and a Q8_0 global header. Header equality could not
  identify it correctly. [10ad9fb] pins exact official manifests, model-layer
  digests/sizes and aggregate sizes; derived context manifests are verified
  against their local hash. Unknown, missing or mismatched identities refuse.
  Both health and launch apply this check; the catalog labels the mixed payload.
- "CUDA-capable device(s) is/are busy or unavailable" when XS joined S. CUDA
  exclusive-process mode blocked the second runner. [10ad9fb] uses shared compute
  mode with job-exclusive GPU allocation and honors explicit
  `OLLAMA_MAX_LOADED_MODELS=2`. GPU offload/context checks remain enforced.
- "Public-pull documentation was stale." The image was already anonymously
  accessible. [9910940] documents public pulls, normal Minerva proxy setup, and
  the distinction between public pulls and authenticated publication.

### Validation

696 frozen host tests passed with zero failures/skips. Rebuilt-image native and
real tmux interactive acceptance passed, including an answered/file-writing
prompt, both model choices, actual XS child, backend round trip and SGE prompts.
The image and both moving GHCR tags matched byte-for-byte; anonymous pull and the
single Drive replacement passed. [5a2a82b] and [89f88c2] retain delivery evidence.
Live SGE/qrsh allocation at BU was not exercised on Minerva.

## [1.0.0] - 2026-11-07

- First release in this public version history; Git tag: `v1.0.0`;
  release commit: [9848347]. The package was private at initial delivery and
  subsequently made public by its owner; visibility is unchanged by versioning.
- Embedded image source commit: [33730da].
- SIF SHA-256: `2ced4e06a33fdb0d0adf9b059402f2261b7a64594213ca257196552f69b84380`.
- GHCR manifest: `sha256:e7ca90b67f150e388ec103021eae06a9f7bb1152c2d6b2e5375fbb678ee05747`.
- Historical delivery tags: `ollama0.40.6-codex0.155.1`, `latest` (moving).
- Retrospective immutable GHCR tag: `1.0.0`; original manifest confirmed available
  on 2026-11-09; tagging status is recorded in the release publication evidence.

### Fixed

The following quoted field/audit findings were repaired before first delivery.
The field-feedback and audits F1-F6 were consolidated in [8f68729], with the
workflow lock/runtime changes in [dfa1ce5]. Historical failed candidates and
superseded claims remain in the audit evidence; they are not release acceptance.

| Reported problem or audit finding | Cause and released change | Commit |
| --- | --- | --- |
| "Expose and detect SGE"; "SGE operator handoff still renders LSF controllers" | LSF assumptions crossed scheduler boundaries. Added explicit SGE detection/selection, native controller/rule/task submit and status/accounting, scheduler-aware handoff and project defaults. Account inheritance is scheduler-specific; explicit clearing and changed-root constraints are preserved. | [8f68729] |
| "Scheduler-default fallback"; "Account/project defaults" | Saved answers could obscure fresh scheduler evidence or retain an account from another scheduler. Fresh detection and explicit choices take priority; unavailable discovery is announced, accounts inherit only within the same scheduler, and explicit clearing is preserved. | [8f68729] |
| "Non-LSF SoS task boundary" | Rule-level allocation did not establish each task's declared resources. Native SGE/Slurm SoS task hosts submit task cores, memory and walltime independently through the native adapters; actual host SoS execution is regression-tested with explicit synthetic clients. | [8f68729] |
| "Backend configuration versus readiness" | Configuration presence was presented as readiness. Local selection now validates complete models, exact catalog/client and matching serve script; backend status labels runtime and authentication unverified until checked. Persistent and one-session backend choices preserve local settings. | [8f68729] |
| "Stop writes to detected private home/install"; H5 "Unknown mount means host-visible" | Filesystem type or failed mount inspection could pass a private destination. Deepest mount identity/source and positive storage evidence now guard all installation writes and print exact bind commands. | [8f68729] |
| "PENDING becomes successful health"; "Infer failure from a log prefix"; "Empty/failed GPU observation accepted" | Missing observations and stale logs could count as readiness. Health follows the retained native launch, endpoint and selected model with positive VRAM; missing evidence is visibly unverified with nonzero exit. API/native failures remain failures. Documentation bounds this to positive offload; partial offload can pass and exclusive GPU execution is not asserted. | [8f68729] |
| H1 "Suite-wide fake host"; W2 "Required grader checks skipped" | An autouse fixture fabricated host execution and missing htslib skipped required cases. Removed that fixture/image test shipping; canonical host tests require tools and fail with actionable installation guidance. | [8f68729] |
| H6 "last-record accounting" | Earlier failed SGE records/tasks were discarded. Parse and validate every job/task accounting record; incomplete, mismatched or unsupported successful arrays remain unverified. | [8f68729] |
| H7 "a missing required model catalog silently restores fallback behavior" | Missing catalog data silently altered model instructions. Require the exact catalog and pinned host Codex 0.155.1; validate actual client schema and round trip. | [8f68729], [dfa1ce5] |
| H8 "Missing backend attribute silently defaulted" | Incomplete direct-call test objects bypassed the parser contract. Read the required backend directly and construct complete inputs. | [8f68729] |
| H9 "Broad predecessor error rewritten" | Catch-all restart messages erased root causes. Check predecessors before prompts/writes, preserve expected failure details and let unexpected errors propagate. | [8f68729] |
| "Root/software collision guards" | A fresh setup could collide with existing content or software. Reject nonempty/new-root collisions before writes and validate resumed settings. | [8f68729] |
| "SGE serve has no pending-job receipt"; "legacy receipts" | Pending launches could duplicate; old LSF receipts lacked a scheduler field. Retain strict native receipts and reuse known launches; accept only the exact validated legacy LSF schema, preserving its timestamp. Unknown state blocks resubmission. | [8f68729] |
| "Non-LSF handoff inspection STILL HIDDEN" | Real deployments used a fixture-only empty snapshot. Native lineage discovery now queries every retained controller/wrapper/task and rejects missing or ambiguous membership/accounting; journal completeness adds the positive F1 guarantee below. | [8f68729] |
| "synchronous local replay" | Completed local actions were forced through a scheduler job-ID lookup. Replay the completed synchronous result through the existing local execution contract. | [8f68729] |
| F1 "native discovery completeness" | Readable streams were treated as the complete submission set. Durable locked intents/receipts, controller/wrapper boundaries, parent identity and exact stream/journal set agreement now establish coverage; missing evidence fails visibly. | [8f68729] |
| F2 "implicit LSF discriminator" | An absent backend silently selected LSF. Require the declared validated deployment backend and reject unsupported dispatch before querying. | [8f68729] |
| F3 "local launch restart/reuse" | Endpoint failure discarded a live process observation; vanished processes were ambiguous. Preserve the observation, bind receipts to process birth/boot identity, and restart only proven terminal/vanished launches. | [8f68729] |
| F4 "guided caller" | Guided production launched without caller-owned native tracking. Submit and wait for one native controller; use its scheduler ID and profile-owned journal/log paths, preserving dry-run and native exit status. | [8f68729] |
| F5 "producer-owned guided inspection contract" | Guide work/logs lay outside its emitted run root; an earlier test substituted deployment/receipts. The producer now owns one runtime graph, registers through the normal action/notebook/executor path, and public inspection consumes its unchanged emitted deployment/receipt. Removed test substitutions. | [8f68729] |
| F6 "hidden override choices / documentation overclaim" | Hidden family metadata supplied no runnable picker IDs. Expose only exact served Q4/Q8/context IDs via validated immutable catalogs. Compare actual pinned-client requests, including every tool schema, with the asserted picker difference. | [8f68729], [dfa1ce5] |
| "complete production LSF rule/task tracking" | Production LSF rule/task branches bypassed the shared journal adapter. Route all native schedulers through common tracked rule/task submission and controller context; verify complete child membership. | [8f68729] |
| "dirty-build snapshot" | Preflight checked HEAD then copied mutable worktree bytes. Capture one commit/tree/blob set, refuse dirty or index-hidden differences, preserve modes and record transformed hashes. | [8f68729] |
| "pecotmr installation still requests locked 0.9.3" | Dependency/worker interfaces drifted. Pin pecotmr 0.9.5 and susieR 0.16.6 in the explicit lock, update the upstream patch and sample-list handling against workflow e1095f63. | [dfa1ce5] |
| "Pulse-file cause" | SoS monitor startup unlinked its published heartbeat. Apply and verify the exact runtime patch during software installation. | [dfa1ce5] |
| "Cannot verify local model override choices: 'parameters'" | Real Ollama base-model metadata omits an optional key. Accept omission only with positive loaded/configured context evidence; absent context, wrong identity and capacity still refuse. | [33730da] |

### Added

- Reviewed GHCR ORAS publication, authenticated manifest/tag and native pulled-byte
  verification in [cf8088d]; first matching-byte Drive delivery in [9848347].

### Validation

670 frozen host tests passed with zero failures/skips. Fresh guided native LSF
inspection verified all 259 controller/rule/task jobs; the frozen scientific grader
passed. Rebuilt-image clean-home host installation, local Codex connection,
selected-model GPU offload and final health verification passed. Publication and
Drive hashes match the SIF above. [7b816f4] records acceptance. Host regression
clients simulate SGE/Slurm; live site allocation remained unverified.

[1.2.0]: https://github.com/hsun3163/fungen-operator/releases/tag/v1.2.0
[1.1.0]: https://github.com/hsun3163/fungen-operator/releases/tag/v1.1.0
[1.0.0]: https://github.com/hsun3163/fungen-operator/releases/tag/v1.0.0
[38d6f22]: https://github.com/hsun3163/fungen-operator/commit/38d6f22
[89f88c2]: https://github.com/hsun3163/fungen-operator/commit/89f88c2
[9910940]: https://github.com/hsun3163/fungen-operator/commit/9910940
[10ad9fb]: https://github.com/hsun3163/fungen-operator/commit/10ad9fb
[5a2a82b]: https://github.com/hsun3163/fungen-operator/commit/5a2a82b
[9848347]: https://github.com/hsun3163/fungen-operator/commit/9848347
[33730da]: https://github.com/hsun3163/fungen-operator/commit/33730da
[8f68729]: https://github.com/hsun3163/fungen-operator/commit/8f68729
[dfa1ce5]: https://github.com/hsun3163/fungen-operator/commit/dfa1ce5
[cf8088d]: https://github.com/hsun3163/fungen-operator/commit/cf8088d
[7b816f4]: https://github.com/hsun3163/fungen-operator/commit/7b816f4

[a44f8b3]: https://github.com/hsun3163/fungen-operator/commit/a44f8b3
[a583993]: https://github.com/hsun3163/fungen-operator/commit/a583993
