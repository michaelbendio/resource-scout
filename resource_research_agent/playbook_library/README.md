# Category discovery guidance

Each JSON file contains the compact, human-reviewed guidance used to prepare a
chat-discovery assignment for one resource category.

- `categoryId` is the stable package-facing identifier.
- `label` is the display name.
- `aliases` match alternate package labels.
- `assignment` is the short category-specific direction and may use only the
  `{service_area}` placeholder.
- `include` identifies useful services and pathways to seek.
- `exclude` identifies tempting results that should not become candidates.

These files guide lead discovery. They do not define dossier fields, verification
gates, research stages, known providers, or candidate outcomes. Existing resources
come from the connected package.

After editing guidance, run `python3 -m unittest discover -s tests`.
