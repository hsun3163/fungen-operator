# Environment declaration checklist

Record the selected tier and its five classification factors. Express the declaration through the project's existing machine-readable convention; if none exists, choose the lightest conventional form for the domain and record the choice.

## Every tier

- [ ] Direct dependencies and versions
- [ ] Target environment and validation platform
- [ ] One documented build command
- [ ] Environment identity emitted in run records
- [ ] Site-specific facilities isolated in the site-configuration layer
- [ ] Required variables named and sourced in tracked declarations
- [ ] External data, credentials, services, and hardware declared
- [ ] Secret names and sources declared without values
- [ ] Tracked pin, vendored source, or setup-applied patch replaces every in-place modification

## Tier 1 evidence bar

- [ ] Direct dependency versions are sufficient to rebuild the short-lived, low-cost environment

## Tier 2 evidence bar

- [ ] Transitive dependencies are locked
- [ ] Validation platform identity is recorded
- [ ] A transferable artifact and its producing spec are available when the target has no network

## Tier 3 evidence bar

- [ ] The locked environment is a deployable artifact
- [ ] The producing spec and validation platform are recorded
- [ ] External service and durable-state compatibility requirements are declared
