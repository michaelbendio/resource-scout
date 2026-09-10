# Start Scout with an editor

Michael can start this through the assistant working in the Scout checkout. No terminal commands are needed from him. The assistant carries out the stages using Scout's saved workflows; this is not an unattended background service.

## What to say

For new research:

> Run Scout for **[office and categories]**, then have **[Astra or another editor]** prepare the results for human curators. Continue through editing and deliver the edited auto[Location].html, full resource package, and a short report. Use **[starting package, if any]**. **[Deadline or spending limit, if any.]**

For research already finished:

> Start the editor workflow for **[office]** using **[Scout draft package or complete auto[Location].html]**. Have **[editor]** prepare it for human curators.

For an interrupted workflow:

> Resume the Scout-and-editor workflow for **[office]** from its checkpoint.

If no editor is named, use the current frontier assistant and record its actual identity. Another product's availability and any necessary spending authorization must be established before assigning it work. Do not substitute a different editor silently.

An assistant may propose the complete assignment for Michael to review. His
“go” starts that proposal with the subsequently agreed changes; he need not
repeat its scope, model choices or limits. The [independent research checker](configurable-independent-checker.md)
is configurable separately from the final editor.

“Prepare for an editor handover” still means review the [handover checklist](michael-editor-handover-checklist.md); it does not start editing. “Start the editor workflow” authorizes the editing work.

## What the assistant does

1. Establish the office, selected categories, authoritative input, and full or partial collection scope from the request and current files. Check for later browser edits and packaged attachments. Ask only for consequential missing choices. If only HTML is supplied, inspect its embedded data and build and verify a standard resource package before using the editor command; HTML alone is not accepted by that command.
2. Save a short run note with the input path/hash, database path, project IDs, actual research/editor roles, agreed limits, output directory and next action. Keep it beside the output and update it at stage transitions. Announce the scope and intended editor. On resume, read both that note and Scout's durable status before assigning more work.
3. For new discovery, use the existing early selection → research → final editing workflow in the [operator guide](scout-learning-editor-operations.md). Carry out the configured research assignments, checks and reconciliation. Preserve coverage gaps. For an already finished package, enter final editing directly with `editor prepare-final`; do not fabricate early decisions or rerun research just to reach the editor.
4. Continue to the named editor as part of the requested job. Give it the [handover](frontier-editor-handover.md), [report format](frontier-editor-report-template.md), sealed final assignment and package with attachments. The assignment's JSON contract governs submission; the report adds the concise human explanation. Editing judges practical usefulness, overlap, writing and supported classifications. Ordinary provider questions go to the curator and should not halt unrelated work.
5. Validate the returned decisions through Scout. Account for every resource; preserve original evidence, identities, attachments and human answers. Export a separate edited HTML and full draft ZIP. Include the decision ledger and short report with important remaining questions and proposed lessons. Highlight changes in **bold** when showing comparisons. Do not manufacture human approval or publish the office's collection.
6. Report completion and the paths to the deliverables. Human curators then check details and contact providers. Editor decisions are learning evidence; later curator packages and resolved questions add evidence. Lessons still need evaluation before activation.

Give brief progress updates at stage/category boundaries and every eight minutes during long work, with estimates when measurements support them. Report a blocker promptly, including what is saved and what is needed. A closed or unavailable assistant session does not guarantee continued execution; the database and run note support resuming it.

## Operator entry for a finished package

Run from the `v2.0` checkout. Use the explicit editor configuration described in the operator guide; `sourceScope` describes the supplied collection, not proof of exhaustive research.

```sh
python3 -m resource_research_agent --database office-editor.sqlite3 editor prepare-final finished-draft.zip editor.json --office 'Mesa'
python3 -m resource_research_agent --database office-editor.sqlite3 editor packet EDITOR_PROJECT final
# Carry out the editor assignment, save its response and actual model receipt:
python3 -m resource_research_agent --database office-editor.sqlite3 editor submit EDITOR_PROJECT final final-response.json editor-receipt.json
python3 -m resource_research_agent --database office-editor.sqlite3 editor export EDITOR_PROJECT new-output-directory
```

Preparation saves the exact input bytes and starts at `final-editor`. Repeating it with the same input/configuration and unchanged guidance returns the same project. To resume after guidance changes, use the saved project ID with `editor status EDITOR_PROJECT` and `editor packet EDITOR_PROJECT final`; the original assignment remains sealed. Preparation neither calls an AI nor certifies that an external research run finished. There is no invented early editorial result or research run. Existing coverage qualifications survive final export; absent coverage remains unknown. The original early-editor entry remains available for new discovery.
