# Agents Toward Determinism

*Hao Sun · October 2026*

This is the working philosophy behind fungen-operator, the reliability layer that lets coding agents operate the [FunGen-xQTL protocol](https://github.com/StatFunGen/xqtl-protocol). It grew out of scientific analysis and figure generation.

## Core thesis

The world is uncertain. To build certainty out of it, I try to make everything certain. Where that fails, I have found a place that deserves uncertainty. Among the many ways to be certain, I choose the elegant one.

An LLM is the uncertainty term itself: a distribution over what to do next. An agent puts shape into that uncertainty, and crystallization moves the shaped part out into deterministic code. What remains is the uncertainty that belongs.

## A model-fitting view

The clearest way I know to say this is statistical. Treat a workflow as a model, y = f(x) + ε.

A raw LLM is ε in its widest form: even when it runs deterministically, you can't know what it will do without running it. Wrapping it in an agent, with tools, a contract, and bounded moves, gives that term a stated distribution. Each crystallized step moves structure from ε into f, so the residual left to the model shrinks.

| Model fitting | Agentic work |
| --- | --- |
| Fitted structure, f(x) | Crystallized, deterministic code |
| Residual, ε | Where the agent works |
| Residuals with structure left in them | Keep crystallizing: there is still pattern to capture |
| Residuals that look like noise | Genuine uncertainty, left to the agent under a stated contract |
| Overfitting | Certainty about the wrong things, brittle to new data |
| Regularization | Elegance: certainty has to earn its keep |
| Well-behaved errors | Error tolerance: ε is never zero, only bounded and visible |

The sections below unpack those rows.

## Fit the structure

Complex analyses should be compositions of small, explicit, meaningful transformations. The tidyverse is my reference point for the shape:

```
data → filter → join → transform → group → summarize → plot
```

Abstract implementation mechanics; keep scientific decisions explicit. A choice is scientific if a plausible alternative could move the conclusion.

Understanding moves along one path:

```
unknown → agentic → understood → specified → deterministic → static
```

An agent always tries to move its step along that path. When it can't, the failure is information: that step deserves uncertainty, and the agent keeps it.

The path also runs backward. A one-click pipeline is fixed against one state of the world, and keeping it working as the source evolves takes human effort. When that effort costs more than it returns, I let an agent absorb the drift instead: the science stays fixed, and the operation around it flexes.

## Don't fit to the outcome

During construction, the agent does not inspect the output it is building and tweak it. Inspection belongs to review, and a change motivated by review becomes a new explicit request.

Tuning a process by watching its result is fitting to the outcome; in scientific analysis, it is the garden of forking paths. The barrier is enforced by the environment, not by instructions, because only a closed channel can be audited.

This hard rule is also what locates uncertainty. A step that silently depends on looking cannot survive it, so its dependencies are forced into the spec, into a check, or into view as a gap.

The agent may still know the hypothesis and the expected story. What it may not do is steer construction by watching the result.

## Choose elegant certainty

There are countless ways to be certain and only a few worth keeping. Pinning file hashes and asserting every intermediate is certainty about incidental things. Like an overfit model, it holds for the current state of the world and breaks when the source evolves.

A good check states what an operation means:

- A join is one-to-one.
- Allele harmonization preserves |z| and flips the sign exactly when alleles swap.
- A relabeling preserves observations, identifiers, and values.

A check never guards the agent against its own uncertainty. If a human would not write it by hand, it does not belong.

## Tolerate error

Agents will err, and so will people. Aviation does not demand infallible pilots; it builds systems that catch an inevitable error before it matters. I design for errors that are:

- detectable, through checks that state meaning;
- contained, by bounded moves that cannot change the science;
- recoverable, through retained history and replay.

Error is tolerated; hidden error is not. Each failure becomes a change to the system, not a reprimand to the agent.

## Who holds the freedom

Every free choice in a workflow is a degree of freedom. Scientific freedom stays with a human, at declared decision points. Operational freedom can go to the agent, within a contract.

Swarms follow the same rule. Agents may independently produce or verify a result, but never revise each other's work. Agreement between them is a check; mutual revision is just a larger feedback loop.

## Where this shows up

- **fungen-operator.** The FunGen-xQTL protocol is the source of truth, and for a while one click ran the whole analysis. As the protocol evolved, maintaining that one-click path stopped being worth the effort, so agents took over its operation. fungen-operator bounds them: state-changing actions are fixed notebook cells with bounded slots, a scientific parameter changes only with an explicit human yes, and the notebook is both the recipe and the history.
- **Data librarian.** A privileged local model reads protected results, and hosted agents work on placeholders. The builder never sees the result directly: the construction barrier, enforced by the environment.
