# Working on masked manuscripts

- Read and edit only the masked manuscript and its slot-status file.
- Preserve placeholders exactly, for example `{{VALUE-ABCD}}`.
- Request a new private value by writing a **bold description of the value needed** in its sentence. The next operator import assigns its slot ID.
- Never reuse an ID for a different quantity. Request a new slot instead.
- If a read is denied, request a slot instead of retrying another way.
- Use real Markdown headings (`#`, `##`, etc.) for structural bold. Every bold span in body text requests protection, including a standalone bold paragraph.
- The user or local librarian runs export, import, retrieval and dictionary publication. Hosted agents never run those commands on real data, inspect the dictionary, or open the human manuscript or librarian logs.
