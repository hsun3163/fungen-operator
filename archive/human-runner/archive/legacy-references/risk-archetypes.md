# Illustrative risk archetypes

Use these examples only to interpret the six yes/no conditions. Do not classify a project by archetype or infer obligations from a domain label.

| Condition | Small standalone program | Shared or costly workflow | Persistent operation |
|---|---|---|---|
| Interruption | Usually no when rerunning is cheaper than a bounded test | Often yes when completed units are expensive | Often yes when restart loses material state or service |
| Repetition hazard | Yes only when outputs can be overwritten or effects duplicated | Often yes for shared outputs, submissions, or publication | Often yes for deployments, messages, transactions, or remote mutation |
| Nondeterminism | Yes for stochastic algorithms or unstable external inputs | Common in sampling, parallel reduction, and scientific computation | Common with concurrency, timing, traffic, and external services |
| Reuse | No for a discarded check; yes for retained analysis or code | Usually yes for collaborators, reruns, or downstream consumers | Yes while operators or clients depend on it |
| External impact | Usually no for isolated local output | Yes for shared compute, data, or another person's outputs | Usually yes for users, shared state, or external systems |
| Live state | Only when claiming what is running or available now | Yes for job, queue, task, and output-progress claims | Yes for service health, deployment, and current state |

Examples do not prescribe containers, workflow engines, wrappers, manifests, dashboards, or runbooks. Use an existing practitioner-native facility when a true condition needs it. If satisfying a condition would require more machinery than the risk warrants, reduce the claim and report the evidence limit.
