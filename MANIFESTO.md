# Agents Toward Determinism

*Hao Sun · October 2026*

This is the working philosophy behind fungen-operator, the reliability layer that lets coding agents operate the [FunGen-xQTL protocol](https://github.com/StatFunGen/xqtl-protocol). It grew out of scientific analysis and figure generation.

## Core thesis

The world is uncertain, and analysis needs certainty. So I try to make every step certain. Where that fails, I have found a place where uncertainty belongs, and I route it through a single channel: the LLM.

## The model

The argument is easiest to state statistically. Think of any workflow as y = f(x) + ε, with x the input and y the outcome. This is a general argument, not a literal regression.

f is the explicit structure: code whose behavior can be read and replayed. ε is everything f does not yet explain. That is not a property of the world; it is what the model has not captured.

A good model routes all its unexplained variance into one term, so you always know where its ignorance lives. A workflow should do the same, and the LLM is that term. Unlike ε, it can be interrogated: you can ask it why. Agents give it shape, and each step that becomes understood moves out of the LLM and into f.

## Fit what you can

Complex analyses should be compositions of small, explicit, meaningful transformations. The tidyverse is my reference point for the shape:

```
data → filter → join → transform → group → summarize → plot
```

Abstract implementation mechanics; keep scientific decisions explicit. A choice is scientific if a plausible alternative could move the conclusion.

Understanding moves along one path:

```
unknown → agentic → understood → specified → deterministic → static
```

An agent always tries to move its step along that path. When it can't, the failure is information: that step deserves uncertainty, and it stays with the LLM.

## Select iteratively

This is model selection, repeated. Construction fits a candidate. Review evaluates it: interpretation, surprising findings, aesthetics, whether a new analysis is warranted. A change motivated by review becomes the next candidate, as an explicit request.

Review never leaks into the fit. During construction, the agent does not inspect the output it is building and tweak it; that would be tuning on the evaluation, which in scientific analysis is the garden of forking paths. The barrier is enforced by the environment, not by instructions, because only a closed channel can be audited.

The agent may still know the hypothesis and the expected story. What it may not do is steer construction by watching the result.

The barrier also locates uncertainty. A step that silently depends on looking cannot survive it, so its dependencies are forced into the spec, into a check, or into view as a gap.

I do not know in advance what the elegant system looks like. Like the true model in model selection, elegance is what the iteration approaches, not what grades it.

## Reduce the uncertainty that moves conclusions

Not all certainty is worth having. Pinning file hashes and asserting every intermediate removes uncertainty about sameness: is this the same file, the same state as last time? Sameness is not correctness. A changed input can still give a right result and an unchanged one a wrong result, so the outcome stays as uncertain as before, and the pins break as soon as the source evolves.

A check is worth writing when the uncertainty it removes could move the conclusion: a practically significant effect, not merely a detectable one. That is the same test as for a scientific choice. Such checks state what an operation means:

- A join is one-to-one.
- Allele harmonization preserves |z| and flips the sign exactly when alleles swap.
- A relabeling preserves observations, identifiers, and values.

The same test applies to whole pipelines. A one-click path that stays alive only through constant maintenance is certainty spent on the operation, not the science. When keeping it costs more than it returns, I hand its operation back to an agent: the science stays fixed, and the operation around it flexes.

## Tolerate error

Agents will err, and so will people. Aviation does not demand infallible pilots; it builds systems that catch an inevitable error before it matters. I design for errors that are:

- detectable, through checks that state meaning;
- contained, by bounded moves that cannot change the science;
- recoverable, through retained history and replay.

Error is tolerated; hidden error is not. Each failure becomes a change to the system, not a reprimand to the agent.

## Who holds the freedom

Every free choice in a workflow is a degree of freedom. Scientific freedom stays with a human, at declared decision points. Operational freedom can go to the agent, within a contract.

## Where this shows up

- **fungen-operator.** The FunGen-xQTL protocol is the source of truth, and for a while one click ran the whole analysis. As the protocol evolved, maintaining that one-click path stopped being worth the effort, so agents took over its operation. fungen-operator bounds them: state-changing actions are fixed notebook cells with bounded slots, a scientific parameter changes only with an explicit human yes, and the notebook is both the recipe and the history.
- **Data librarian.** A privileged local model reads protected results, and hosted agents work on placeholders. It uses the same barrier shape, applied to privacy: the builder never sees the protected result directly.
