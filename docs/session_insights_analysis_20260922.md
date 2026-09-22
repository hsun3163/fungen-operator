# Session insights analysis for fungen-operator

Date: 2026-09-22. Status: analysis and proposed priorities; no operating policy changes.

Development context: the intended outcome is a new Fungen Operator skill or plugin that replaces the old collection. This analysis supplies evidence and candidate requirements for the [development brief](fungen_operator_development_brief.md); it is not a standalone plan to keep adding rules to the old skills. The brief now provides the development sequence and acceptance cases.

The next iteration of `fungen-operator` should reduce the user corrections needed to complete authorized scientific work through the established workflow. The strongest supported priorities are clearer skill selection, faithful execution, recovery that accounts for submitted task state, and evidence-based completion reporting.

This analysis complements the [historical evidence packet](historical_evidence_extraction_20260920.md) and [failure-mode analysis](failure_mode_insights_20260920.md). It adds findings from a separate session-insights run and identifies errors in that report. Historical incidents are not current workflow-status claims, and proposed changes below have not been applied to the skills.

## Source and coverage

- Tool: [`cosformula/codex-session-insights`](https://github.com/cosformula/codex-session-insights), installed version `0.4.0`.
- Invocation: `codex-session-insights --days 60 --limit 100 --yes --no-open`.
- Report generated at: `2026-09-22T07:05:41.756Z`.
- Local report files: `/hpc/users/sunh14/.codex/usage-data/report.html` and `/hpc/users/sunh14/.codex/usage-data/report.json`.
- Report JSON SHA-256: `96a800f24bcc74ee0980cb06748aff10424deb09e1cc957a26f3c6787e5a7aaf`.
- Selection: 72 eligible substantive main threads, with 50 receiving detailed model-generated labels. The requested limit of 100 was a ceiling; the default uncached facet limit was 50.
- Of those 72 threads, 17 were from the main xQTL directory, 17 from COSI_paper, and 11 from COSI_pecotmr: 45 across these three directories.
- Among the 50 labeled threads, 25 had a positive `wrong_approach` count and 20 had a positive `misunderstood_request` count; their union was 30 threads. These are automated incident-finding labels, not validated failure rates.
- The source analysis inspected the local skill snapshot at `e032391`. Before adding this document, the checkout was fast-forwarded to `2671ff7`, which added the two existing evidence documents without changing that skill snapshot.

The report files and full session transcripts remain local. The source IDs, inspected receipt, relative repository links, and report hash below identify the evidence used in this analysis.

## Findings and project implications

| Priority | Evidence | Implication for fungen-operator |
|---|---|---|
| Preserve the requested workflow | The report's CARDIA recovery facet describes an unnecessary validation dependency. The historical packet records additional controllers and a second SuSiE fit. | State scope, scientific semantics, and the canonical execution path early. Additional diagnostics must not silently become prerequisites. |
| Use the scheduler correctly at every layer | The CARDIA facet describes a missing LSF profile that left chromosome work inside the controller. Other retained incidents concern child-job memory and constrained fan-out. | Assess the actual child execution path and resources. Preserve the existing DAG and its intended computational units. |
| Report the scientific endpoint accurately | The six-analysis MESA facet records completed controllers alongside missing required TWAS and fine-mapping outputs. | Tie completion claims to declared outputs and child results. Where failures are masked, repair propagation in the owning workflow rather than adding another completion system. |
| Make recovery reproducible | The historical packet records a source revert while materialized SoS commands retained a removed argument. | Distinguish source, configuration, runtime, and submitted task generation. A source edit does not update already-created tasks. |
| Reduce repeated steering | Retained corrections restore the intended directory, result packet, environment, or endpoint. | Resolve these from project context and state the selected target briefly. Continue ordinary authorized recovery through that endpoint. |

Evidence anchors:

- CARDIA recovery and added validation dependency: report facet `01a0bb16-1754-7d00-8caa-479f8187e568`.
- Missing LSF executor/profile and controller memory failure: report facet `01a060e3-a1e2-7643-858a-5edb622e4ada`.
- Six MESA analyses with missing scientific outputs: report facet `01a08492-da19-79a2-b1c6-cfdff65d62ab`.
- Wrong directory scope during the extended_TADB audit: report facet `01a048d8-2a0b-7d71-a77a-0ab1a7e36ab0`.
- Scientific-method change and stale materialized commands: historical packet TASK-009 and EVENT-020–024.
- Constrained fan-out: historical packet TASK-008 and EVENT-018.

Report facets summarize retained sessions; they do not independently revalidate historical jobs. The historical packet preserves whether evidence originated in a tool result, user correction, assistant admission, notebook, or handoff. That attribution remains important when using these cases.

The strengths to preserve are native command-chain debugging, scientific provenance, reuse of the established environment and workflow, scoped recovery, and explicit reporting of missing outputs. These strengths are already central to the repository's operating model.

## First concrete repository priority: resolve overlapping COSI procedures

The current active collection supplies conflicting guidance for overlapping COSI run and resume requests:

- [cosi-run](../skills/cosi-run/SKILL.md), especially “Record commands in a notebook and executable scripts” and “Gate production,” requires direct `bsub`–Snakemake invocation, production gates, a dry-run, and sometimes a smoke run.
- [cosi-runner](../skills/cosi-runner/SKILL.md), especially “Keep Commands Literal And Minimal” and “Submit The Native Run,” requires a visible `bsub` heredoc and prohibits adding a dry-run controller or separate review stage.

The README acknowledges different policy generations, but both skills remain discoverable for overlapping requests. This leaves the agent to resolve an operational policy decision during execution.

The proposed first change is to establish one authoritative default for each task family and clearly identify superseded or explicitly historical procedures. Routing should be visible in skill entrypoints as well as the README. Legitimate differences between xQTL and COSI should remain explicit. This analysis does not itself select, merge, or retire a procedure.

Many requested protections already exist in [human-runner](../skills/human-runner/SKILL.md) and [xqtl-runner](../skills/xqtl-runner/SKILL.md): native execution, preserved scientific semantics, no extra validation gates, and continuation to the authorized endpoint. The useful evaluation question is whether the agent applies the relevant instruction at the decision point. Another paragraph alone does not establish better behavior.

## Corrections and limitations of the insights report

### The historical-evidence upload was verified

The report's facet for `01a0c047-56fe-7b50-a6b0-d93d75c0181f` says the GitHub upload and exact-match verification remain unconfirmed. That statement is contradicted by the original tool result inspected during this analysis.

Original source:

`/hpc/users/sunh14/.codex/sessions/2026/09/20/rollout-2026-09-20T15-24-55-01a0c047-56fe-7b50-a6b0-d93d75c0181f.jsonl`

At line 151, the retained command uploads the packet, fetches the committed file at the returned revision, and asserts that its decoded contents equal the local bytes. Line 154, timestamp `2026-09-20T19:54:49.018Z`, records exit code zero and this receipt:

```json
{
  "commit": "01439970be706953b80ae9abdcae99fa388247c5",
  "bytes": 58466,
  "sha256": "c21cc08902c298200c72dba2ead6efc867dfde25e769546932beb0478afbf3ab",
  "verified": true
}
```

The uploaded artifact is retained at [commit 0143997](https://github.com/hsun3163/fungen-operator/blob/01439970be706953b80ae9abdcae99fa388247c5/docs/historical_evidence_extraction_20260920.md).

The compact transcript supplied to the analyzer omitted the successful verification receipt. It retained a failure labeled `gh`, although that compound inspection command's exit code came from a final `ls` for a nonexistent `AGENTS.md`. The upload itself succeeded later. The report therefore cannot support a claim that the agent fabricated this upload's completion.

### The window is based on thread updates

The installed tool selects threads using `updated_at >= cutoff` and analyzes their retained histories. The embedded previews include a thread created on `2026-04-19`, before the displayed `2026-07-24` to `2026-09-22` range. Totals are therefore not strictly activity occurring within the last 60 days.

### Some extracted instructions belong to the analyzer

The facets' `user_instructions` include statements such as “Use only transcript evidence,” “Keep keys and enum values unchanged,” and “Write free-text fields in English.” These match the analyzer's instructions, rather than establishing user preferences from the historical session. Such entries should not be promoted automatically into active skills.

### Outcome labels do not measure project reliability

The 50 labeled threads contain 29 `partially_achieved`, 17 `mostly_achieved`, and 4 `fully_achieved` labels. These are not task-level success or failure rates. Long threads contain multiple requests, legitimate running-job handoffs, later scope changes, and unresolved questions. Transcript compression can omit decisive evidence, as the upload example demonstrates.

The analysis also cannot establish whether recent skill revisions improved outcomes. The exact instructions loaded during older incidents are often unknown, and the collection contains instructions written in response to those incidents. Current rules are not proof of historical compliance or causation.

Use the report to locate candidate incidents, then check original evidence. Generic tool counts, lifetime tokens, summed active hours, and subjective labels should not become project success measures.

## Proposed next increment: consolidation and incident-based evaluation

Alongside the routing clarification, use a small set of retained cases to assess whether an agent:

1. Selects the correct skill, checkout, environment, and endpoint.
2. Preserves the scientific method and the existing execution graph.
3. Avoids adding unrequested dependencies or machinery.
4. Distinguishes submission, valid handoff, failure, and verified completion.
5. Resumes the authorized endpoint after a narrow repair.

Useful cases are an advice-only request, a COSI run with overlapping skill triggers, a missing LSF profile, successful outer markers with a missing required product, and materialized tasks that still reference a removed flag. Add the verified GitHub upload as a case for distinguishing missing evidence in a compressed summary from missing evidence in the original record.

Record the request, allowed effects, loaded skill revision, decisive action or response, evidence, and observed outcome. Start with retained or small synthetic artifacts; these decision checks do not require new live HPC jobs or a new execution framework. Evaluate actual workflow fixes through the owning project's native checks when such changes are authorized.

The project measures should be user corrections, unauthorized workflow changes, unsupported completion claims, and completed declared endpoints. Preserve a valid pending/running handoff as its own outcome when that is the requested stopping point. Keep environmental failures separate from avoidable operator deviations, and preserve uncertainty where the evidence is incomplete.
