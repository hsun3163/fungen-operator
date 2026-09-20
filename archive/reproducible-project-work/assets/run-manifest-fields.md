# Run manifest fields

Implement these fields in the canonical program or existing engine. The execution creates and finalizes the record; no person or agent writes it by hand.

## Identity

- Record schema version
- Unique run identifier
- Canonical command exactly as executed
- Version-control commit hash
- Version-control cleanliness state
- Environment-spec identity and resolved environment or artifact identity
- Configuration identity and resolved parameter identity

## Inputs and outputs

- Input origins, paths or stable identifiers, and integrity identities
- Declared output and log paths
- Produced output identities and checksums when cheap relative to the run
- Captured standard-output and standard-error locations

## Execution

- Start and end timestamps with time zone
- Final exit status, or an execution-produced incomplete or interrupted state
- Step and input identity for each failed or completed unit when the run has units
- Execution-platform, scheduler, deployment, or service identifiers supplied by the platform
- Resume parent or prior-run identifier when applicable

Prefer version-control output, platform accounting, engine records, captured streams, and platform lifecycle evidence over custom duplicates.
