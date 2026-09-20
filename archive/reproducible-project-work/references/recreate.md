# Recreate

To recreate is to reconstruct the process that produces the outputs, in a comparable environment, with every external requirement declared, to an explicitly stated equivalence criterion.

Recreation requires the tracked environment declaration, canonical entrypoint, inputs and parameters, provenance, site-configuration boundary, external-requirement declarations, nondeterminism declaration, and documented commands. It does not require bitwise-identical output unless the project explicitly chooses bitwise identity as its criterion, and it does not require external data, credentials, services, or hardware to be stored in the project.

State the equivalence criterion in observable terms a stranger can test. Default to functional equivalence: the canonical path completes, declared assertions hold, output schema and meaning match, and variation stays within declared nondeterministic bounds.
