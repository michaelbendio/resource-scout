# Research playbook library

Version 1.0.0

These files are the human-reviewed source of truth for category research. Each category has one JSON file named for its category ID. The application reads and validates the library when it starts; a malformed file stops startup with a message naming the file and field that needs attention.

To sharpen a playbook, edit its ordinary-language fields:

- `assignment`: the initial direction shown to the user and sent to the agent. Use `{service_area}` where the place belongs.
- `include`: services and pathways that belong in the category.
- `exclude`: attractive but irrelevant or misleading results the agent should leave out.
- `verificationQuestions`: facts that must be settled before a candidate is useful.
- `stages`: four bounded passes through the subject. Keys are stable identifiers; titles and instructions can be improved.

Keep entries concrete and access-oriented. Name the programs, benefits, services, relationships, and barriers worth following. Do not turn a playbook into a list of known providers: those belong in the resource package and are supplied separately as existing knowledge.

After editing, run `python3 -m unittest discover -s tests -v`. Increase `libraryVersion` in `base.json` when the reviewed guidance materially changes. Existing runs retain the assignment, category brief, and stage instructions they actually used; changes affect only future runs.
