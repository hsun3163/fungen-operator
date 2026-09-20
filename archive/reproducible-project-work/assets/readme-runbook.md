# <project name>

<One paragraph: purpose, canonical path, and functional-equivalence criterion.>

## Requirements

- Environment spec: `<path>`
- Site configuration: `<path>`
- External data, credentials, services, or hardware: `<what, source, acquisition, expected location>`
- Secret names and sources: `<names and sources; no values>`

## Project map

- Canonical program or workflow: `<path>`
- Smoke configuration and input: `<paths>`
- Inputs and provenance: `<paths>`
- Outputs: `<path>`
- Logs: `<path>`
- Run records: `<path>`
- Decision log: `<path>`
- Handoff: `<path>`

## Build the environment

`<one executable command>`

## Run the smoke test

`<documented command through the canonical entrypoint and execution route>`

Expected: `<tracked assertions and run-record location>`

## Run

`<canonical command>`

## Monitor

`<platform-native command or documented manual operation>`

## Resume

`<same canonical entrypoint with resume arguments>`

## Run one step for one input

`<canonical entrypoint with step and input arguments>`

## Scale

`<canonical entrypoint with scaled configuration or arguments>`

## Debug a failure

1. Read `<declared log and run-record locations>`.
2. Identify the named step and input.
3. Reproduce through `<documented bounded command>`.

## Inputs, provenance, and nondeterminism

<Origins, integrity identities, generating commands and code identities, parameters, nondeterministic sources, and accepted bounds.>

## Current verification

<Cited run-record identifiers for verified claims; unverified claims with reasons.>
