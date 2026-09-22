# Research basis and evaluation vocabulary

Updated: 2026-09-22  
Purpose: connect the Fungen Operator design to established agent-evaluation ideas without turning the repository into a literature review.

The literature does not supply a ready-made solution for this project. It does, however, provide useful concepts for understanding the failures already observed in the repository.

## 1. What this project borrows

| Research line | Useful result | Fungen Operator interpretation |
|---|---|---|
| **Agent-eval structure — Anthropic** | Anthropic's practical eval framework distinguishes task, trial, grader, transcript/trajectory, outcome, and harness; it also distinguishes capability from regression evals and code/model/human graders. [Anthropic Engineering, 2026](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Use this as the benchmark's operational object model; prefer environment outcomes over agent self-report and deterministic graders over subjective grading where possible. |
| **Failure-mode analysis — MAST** | Cemri et al., *Why Do Multi-Agent LLM Systems Fail?* derive a failure taxonomy from expert-annotated trajectories and validate scalable annotation. [NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html) | Treat failure modes as trajectory-level diagnostic categories rather than reducing everything to "bad code" or binary success. |
| **Compositional workflows — WorkArena++** | WorkArena++ evaluates realistic workflows composed from smaller knowledge-work capabilities. [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/0b82662b6c32e887bb252a74d8cb2d5e-Abstract-Datasets_and_Benchmarks_Track.html) | Mini-protocol composition is a legitimate benchmark object: success depends on selecting and sequencing existing capabilities, not merely solving isolated tasks. |
| **Stateful tool use — ToolSandbox** | ToolSandbox evaluates stateful execution, implicit dependencies between actions, and intermediate/final milestones. [NAACL Findings 2025](https://aclanthology.org/2025.findings-naacl.65/) | Source, configuration, materialized commands, scheduler state, and products must be treated as distinct state layers. |
| **Rule-constrained goal completion — τ-bench** | τ-bench evaluates whether agents reach a goal state while following domain-specific policies and introduces repeated-trial `pass^k`. [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html) | Evaluate endpoint completion and contract adherence together; repeat cases before claiming reliability. |
| **Trajectory progress — AgentBoard** | AgentBoard argues that final success alone hides useful information and introduces fine-grained progress analysis. [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/877b40688e330a0e2a3fc24084208dfa-Abstract-Datasets_and_Benchmarks_Track.html) | Retain enough trajectory evidence to tell whether an operator selected, composed, executed, recovered, and verified correctly. |
| **Cost and complexity — AI Agents That Matter** | Kapoor et al. argue that accuracy-only benchmarks can reward unnecessarily complex and costly agents and emphasize reproducible evaluation. [arXiv:2407.01502](https://arxiv.org/abs/2407.01502) | Parsimony is measurable: additional wrappers, controllers, checks, and execution paths are operational cost, not free sophistication. |
| **Scientific-task evaluation — ScienceAgentBench** | ScienceAgentBench argues for rigorous evaluation of constituent scientific tasks, uses SME validation, and evaluates programs, execution results, and cost. [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html) | Benchmark the operator on concrete scientific workflow tasks and recovery cases before claiming a general autonomous-science system. |
| **Scientific experimentation — MLAgentBench** | MLAgentBench exposes agents to multi-step experimentation with file/code execution and identifies long-horizon planning as a challenge. [ICML 2024](https://proceedings.mlr.press/v235/huang24y.html) | Long-horizon scientific operation is difficult, but Fungen Operator differs in one crucial way: it usually must preserve an already-selected scientific method rather than optimize the method itself. |

## 2. The gap Fungen Operator targets

Most neighboring benchmarks emphasize one or more of:

- solving a task;
- composing tools;
- obeying domain rules;
- handling persistent state;
- performing scientific experimentation;
- diagnosing trajectory failures.

Fungen Operator combines these under a narrower operating problem:

> **faithfully operate and recover an already-defined scientific workflow while preserving scientific semantics and the established execution path.**

The agent has substantial freedom over operational reasoning but limited authority over the scientific method.

That distinction matters. In an autonomous experimentation benchmark, changing a model or preprocessing strategy may be the intended behavior. In Fungen Operator, the same change can be a failure if the user delegated execution but not scientific redesign.

This is a working positioning statement, not a claim that no prior system has ever addressed the same combination.

## 3. Evaluation vocabulary

The canonical benchmark uses the external eval terms **task, trial, grader, transcript/trajectory, outcome, and harness** from the Anthropic framework. The terms below are Fungen-domain concepts used inside those tasks and graders; they are not replacements for the benchmark object model.

### Endpoint success

The requested scientific endpoint or explicitly valid handoff was reached.

### Contract adherence

The operator preserved the delegated scope, scientific semantics, project execution path, and authorized side effects.

### State coherence

The operator reasoned about the execution state that actually governed active work, including already-materialized commands and scheduler jobs.

### Evidence calibration

Claims such as submitted, running, failed, incomplete, valid no-result, and complete are supported by the appropriate native evidence.

### Steering burden

Number and type of corrective user interventions required to bring the operator back to the requested task.

### Operational surface

Additional maintained artifacts, execution paths, dependencies, and decision points introduced by the operator.

### Repeated reliability

Performance over repeated attempts on the same class of case, inspired by the motivation behind `pass^k`. One lucky success is not enough to establish dependable operation.

## 4. What not to copy from the literature

The research basis is not a mandate to reproduce every benchmark architecture.

Fungen Operator does **not** need:

- a multi-agent system merely because MAST studies one;
- a simulated enterprise application stack because WorkArena++ uses one;
- a new database-backed sandbox because ToolSandbox evaluates state;
- a single aggregate score because benchmarks publish leaderboards;
- a new orchestration engine to make composition explicit;
- an autonomous hypothesis-generation loop because scientific-agent benchmarks study discovery.

Use the smallest mechanism that makes the relevant property observable in the existing workflow.

## 5. Minimal benchmark implications

A compact benchmark suite should include cases that expose:

1. **composition:** choose and connect the right mini-protocols;
2. **constraint adherence:** complete the task without changing protected scientific semantics;
3. **state dependency:** recover when source and materialized execution state diverge;
4. **termination:** reach the declared endpoint rather than an intermediate checkpoint;
5. **verification:** distinguish outer success markers from actual scientific products;
6. **parsimony:** avoid unnecessary parallel infrastructure;
7. **consistency:** repeat representative cases across multiple trials.

These can be implemented with synthetic or public data. Controlled-access biological data are not necessary to test the operator behaviors themselves.

## 6. Evidence hierarchy for this repository

Published work supplies concepts and evaluation patterns. The repository's own historical record supplies the product requirements.

When they differ in specificity:

1. direct project/user requirements govern the intended behavior;
2. observed historical incidents motivate local acceptance cases;
3. published research provides vocabulary and evaluation precedent;
4. broader agent design trends remain optional context.

The research should clarify the project, not replace its empirical history.
