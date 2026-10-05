# Agents Toward Determinism

*Hao Sun · October 2026*

This is the working philosophy behind fungen-operator, the reliability layer that lets coding agents operate the [FunGen-xQTL protocol](https://github.com/StatFunGen/xqtl-protocol). It grew out of scientific analysis and figure generation.

## Core thesis

The point of an AI agent is to make itself unnecessary.

I use AI to resolve ambiguity and discover structure. The resulting understanding becomes explicit, composable operations with intrinsic checks. Repeatable work moves to deterministic execution, and mature behavior consolidates into static code.

AI stays at the frontier, where judgment is still genuinely required. Intelligence is not eliminated. Agent behavior that has become understood simply stops being agentic.

## The construction barrier

During construction, the agent never inspects the output it is building. This is a hard rule, not a preference.

The common loop is intent → attempt → inspect → critique → modify → repeat. It works, but it makes the builder a feedback controller: each result is shaped by reactions to earlier results. In scientific analysis, that is the garden of forking paths.

The construction path I want is specification → explicit operations → executable checks → rendered result. Inspection belongs to post-review: interpretation, surprising findings, aesthetics, and whether a new analysis is warranted. A change motivated by review becomes a new explicit request, never an implicit tweak.

The rule is strict because only a closed channel can be audited. If the agent can see the output, no one can tell whether what it saw shaped what it did. So the barrier is enforced by the environment, with construction given no access to rendered output, not by instructions the agent could ignore.

The strictness is also what does the work. It acts as selection pressure: a process that silently depends on looking cannot survive it. Every visual dependency is forced into the spec (fixed canvas, sizes, label repulsion), into a computed check (text bounding boxes), or surfaces at review as a visible gap.

This is Darwinian, not Lamarckian. Inspect-and-tweak lets traits acquired during one run get baked into the artifact. The barrier works like the Weismann barrier: the spec is the germline, the rendered artifact is the soma, and nothing in the soma writes back. Variation happens in the spec, selection happens at review, and only explicit requests are inherited.

This is not epistemic blinding. The agent may know the hypothesis and the expected story; what it may not do is steer construction by watching the result.

## Explicit operations

Complex analyses should be compositions of small, explicit, meaningful transformations. The tidyverse is my reference point. What matters is not the `%>%` operator or R itself, but the shape:

```
data → filter → join → transform → group → summarize → plot
data + mappings + transformations + layers + scales → figure
```

The code itself shows how the result was constructed. Modularity that hides consequential choices inside a helper, leaving a thin notebook that calls `make_context_comparison(data)`, reduces transparency rather than adding it.

The rule: abstract implementation mechanics; keep scientific decisions explicit. The unit of decomposition is the smallest operation with understandable scientific or computational meaning.

The test for what counts as a decision: a choice is scientific if a plausible alternative could move the conclusion. NA handling, join type, and allele orientation look like mechanics and often are not.

## Intrinsic checks

The alternative to visual trial-and-error is not skipping validation. It is validation built into execution as contracts, properties, and invariants.

- A relabeling preserves observations, identifiers, and values.
- A join asserts its expected cardinality.
- Allele harmonization preserves |z| and flips the sign exactly when alleles swap.
- A transformation is tested on synthetic data with known behavior.

These checks ask whether an operation did what its specification says, not whether the result looks as expected. Passing them does not prove the science right. It narrows the ways the implementation can be wrong.

Checks also mark the frontier. Like guards in a JIT compiler, a check that fails on new data sends that path back to the agent.

## Crystallization

The underlying preference is forward causality: declared choices → deterministic execution → result. Nondeterminism is pushed to explicit decision points, and everything downstream is as deterministic as practical. This does not rule out stochastic models or human judgment; it confines them to declared places.

A task matures along one path:

```
unknown → agentic → understood → specified → deterministic → static
```

The agent works like a JIT compiler. It interprets what is still ambiguous, compiles the paths that run hot into static code, and moves on. A mature workflow contains less agentic computation, not more.

Crystallization needs an entry criterion: the agent keeps making the same choice across inputs, and the rule can be stated. It also needs an exit: when a guard fails, the path returns to the frontier.

Determinism makes errors reproducible, not correct. Checks, not determinism alone, are what make crystallized code trustworthy.

## Swarms

Twenty agents continuously inspecting and revising each other's output form a large stochastic feedback system that is hard to reason about. Mutual revision is the swarm version of inspect-and-tweak.

A better swarm attacks explicitly decomposed problems with understandable inputs and outputs. Agents may independently produce or verify the same result, but never edit each other's work; agreement between them is a check.

The goal is not 20 agents doing everything forever. It is 20 agents converting the current frontier into reliable, composable machinery, then leaving those paths.

## Where this shows up

- **Operator contract (fungen-operator).** The agent consumes the canonical workflow rather than developing it. State-changing actions are fixed-skeleton notebook cells with bounded slots, and a scientific parameter changes only with an explicit human yes. The operator notebook is both the recipe and the history.
- **Data librarian.** A privileged local model reads protected results; hosted agents work on placeholders and semantic releases. It is the construction barrier enforced by the environment: the builder never sees the result directly.
