# Working on masked manuscripts

- Read and edit only the masked manuscript and its slot-status file.
- Preserve placeholders exactly, for example `{{VALUE-ABCD}}`.
- Request a new private value by writing a **bold description of the value needed** in its sentence. The next operator import assigns its slot ID.
- Never reuse an ID for a different quantity. Request a new slot instead.
- If a read is denied, request a slot instead of retrying another way.
- Use real Markdown headings (`#`, `##`, etc.) for structural bold. Every bold span in body text requests protection, including a standalone bold paragraph.
- The user or local librarian runs export, import, retrieval and dictionary publication. Hosted agents never run those commands on real data, inspect the dictionary, or open the human manuscript or librarian logs.

## Local scribe workers

Use the [scribe setup and debugging guide](SCRIBES.md) for extra bounded local-model lookups.
`librarian --scribe --me "<exact bounded scientific task>"` routes only to a healthy isolated scribe;
`--scribe --check --me` computes a table in two independent parallel sessions and compares normalized tables,
with a third reviewer on mismatch or when no table is defined. Keep scientific answers in private files.
At most one call may use the librarian GPU at a time; the wrapper enforces that lock. Run agent sessions
from the login/session host, or in LSF jobs placed with `-m "air_cpu dwc_cpu"` (the `lh06c*` ondemand nodes lack
user namespaces, which Codex's sandbox needs).
