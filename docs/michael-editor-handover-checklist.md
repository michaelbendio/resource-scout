# Michael's checklist: handing Scout work to an editor

Use this when asking another frontier-level AI to prepare resources for human curators. You do not need to assemble the entire Scout database or reproduce the long design conversation.

**Your cue: “Prepare for an editor handover.”** On that request, the assistant should review this checklist for you, inspect the available files, and summarize what is ready, what is missing and any decision needed. Confirm the office, task, authoritative input, full/partial scope, latest edits, expected outputs and whether to withhold earlier editorial decisions. Do not silently launch another editor or a new research run.

## What to send

1. **The editor handover** — `frontier-editor-handover.md`, with the report template and decision format. The prepared ZIP includes all three.
2. **The resources to work on** — preferably a current resource-package ZIP. A complete `auto[Location].html` is also an accepted starting point. Sending both is helpful when they represent the same collection: the package supplies data/attachments, and the HTML demonstrates navigation and editing.
3. **A short assignment** — office, which collection or categories to review, what changes you want, whether new research is allowed, and what result you expect. The fill-in note below covers this.
4. **Any essential local guidance** — current scope decisions and relevant curator feedback. Include the actual calling script only if you want the editor to assess alignment with it. Do not assume the AI already has that script.

## Which input should I choose?

| You want to… | Send… |
| --- | --- |
| Test another editor's independent judgment on the Mesa research | The main handover packet's original **460-resource** ZIP and matching HTML. Keep Astra's reference packet separate until the editor saves its first decisions. |
| Improve the current reduced autoMesa | The **268-resource** draft package and `autoMesa.html` from the Astra reference packet, plus your new instructions. This is an informed revision. |
| Review an office's latest curated collection | Its current saved office resource package, with its office name, date and intended scope. Add the corresponding HTML if useful. |
| Review a new Scout draft available only as HTML | The complete HTML file, not just a screenshot or a URL the AI cannot open. State whether it is the original generated file or whether you have made browser edits. Include attachments separately if they are not carried in the file. |

**Before sending, check whether the file contains the work you mean to send.** Editing in a browser does not necessarily rewrite the original HTML file. Recent edits can live in that browser's local storage. Copying the HTML to another AI can therefore send an earlier embedded version.

**Scout supports complete research-draft packages as well as curated-only exports.** Choose the full draft for a whole-collection editor handover. The current autoMesa's **What changed → research draft package** link contains all 268 edited resources; the original autoMesaV2 handoff supplies its complete 460-resource draft.

The current Scout Resources editor's **Save a package of … curated resources** button exports only the marked entries. The ordinary office application's **Save Resource Package** saves its current office data. These are different paths; verify the resulting file's count and contents rather than relying on the words “save package” alone.

A supplied full research-draft download is a generated snapshot and may predate later browser edits. If you need all current draft entries including those edits, have the snapshot prepared or refreshed and checked. Do not mark entries Curated just to manufacture a full export. For the supplied Mesa packets, the authoritative ZIPs contain the full stated collections: 460 original or 268 edited resources.

If you send a package and HTML that differ, say which is authoritative. If unsure, ask the editor to compare their contents before editing. A filename or modification date alone does not establish the right baseline.

## A note you can copy and fill in

> Please read the Resource Scout editor handover. Real service missionaries will use these resources to help people in need; human curators will check the details and contact providers after your work.
>
> Office: **[Mesa / Provo / another office]**.
>
> Input: **[filename(s), expected resource count if known, and whether this is the whole collection or a subset]**. Use **[file]** as the authoritative data. **[No later browser edits / later edits are included in the package / I am unsure whether later edits are included.]**
>
> Task: **[prepare a useful, manageable collection / revise the existing selection / review particular categories]**. You may recommend retaining, combining, reserving or excluding resources and improve writing, groups and types within the handover's scope. Preserve important details, evidence, identities and human work. Explain if you think a different approach would be better.
>
> Research: **[use the saved evidence only / make targeted additional web checks for consequential gaps]**. **[Deadline or budget, if any.]** Do not start other paid AI services as part of this assignment.
>
> Return a short outcome report in the common format, a complete decision ledger, and a separate edited resource package and usable auto[Location].html where your tools support them. If artifact construction is unavailable, return complete changes by resource ID and clearly state what remains to be built. Do not mark your selections human-curated or publish them to the office.
>
> Comparison: **[save your first decisions before seeing Astra's reference / use Astra's result from the beginning]**. Give concise progress updates and tell me promptly if something prevents you from proceeding.

You can delete options that do not apply. There is no target count per category. For a fair comparison, use the same baseline and shared guidance; record additional research separately.

## When the editor finishes

- Read its short report first: what changed, important remaining questions, and whether the result is complete.
- Check that every input resource is accounted for and that combined entries are included in the final count. Ask about useful alternatives that may have been lost, not just the size of the reduction.
- Keep the output, decision ledger and recommendations together with the input version. Do not replace the original files.
- Review a small, varied set of consequential decisions and disagreements. The full evidence should be available without requiring you to read hundreds of rows.
- Give the prepared collection to the human curators for their normal checking and provider calls. Their later edits and resolved questions are potential learning evidence, not automatic new playbook rules.

## Where the files are

GitHub repository: [michaelbendio/resource-scout](https://github.com/michaelbendio/resource-scout). **Use the `v2.0` branch** for this work; `main` retains the established Scout line.

- Current instructions: [`docs/frontier-editor-handover.md`](frontier-editor-handover.md).
- Report: [`docs/frontier-editor-report-template.md`](frontier-editor-report-template.md).
- Decision format: [`docs/frontier-editor-decision-format.md`](frontier-editor-decision-format.md).
- Dated Mesa trial packets: [`handoffs/mesa-editorial-20260909/`](https://github.com/michaelbendio/resource-scout/tree/v2.0/handoffs/mesa-editorial-20260909). These preserve that day's inputs and results; they are not automatically the latest office data for a future trial.

Your local copies are in **iCloud Drive → Documents → TSO → Scout Editor Handover**. For an AI that cannot access the repository, upload the packet directly. For a future office run, supply that office's current package rather than reusing the Mesa example by accident.
