# Astra-led Scout: playbooks, independent checks, and learning

**Status: discussion draft. No new research protocol or playbook is activated.**
This defines the next part of the existing v2.0 work, using Michael's discussion
and the GPT handoff. autoMesaV2 remains paused until review. Implementation is
specified separately in the [staged plan](scout-playbook-learning-plan.md).

## The proposal in brief

Scout should become a reliable resource researcher whose ordinary work can be
performed by Astra using accumulated, versioned research guidance. Other AIs
provide sampled independent comparisons and focused challenges that help expose
weaknesses and improve that guidance. Human curation determines the final resource
package. Reliability must be demonstrated through coverage, consequential errors,
curator effort and research time; reproducing every AI's candidate list is not
the objective.

Playbooks are Scout's durable memory of **how to research**. They can change the
goals, methods, sequence and number of passes. They do not change Astra's model
weights, certify resource facts, or constitute a list of remembered answers.
An Astra-only ordinary run can coexist with occasional independent evaluation.

Use Claude for a blind comparison on Employment and on a random third of
subsequent eligible category assignments. Michael accepted the one-third starting
frequency during design review. Targeted checks can supplement that sample. It
remains a trial setting, not an established optimum or active configuration;
the remainder of the learning design is still under review.

## Existing work to reuse

The current `v2.0` checkout already implements improved writing, existing-resource
updates, classification, maintenance, source-bound review and package evidence
capture. The JSON playbook library, focused-pass workflow and source-hidden replay
provide additional foundations. Employment's `employment-focused-v2` already
contains seven focuses improved through earlier research experience. It is the
starting playbook, not something to invent again.

The missing connection is a repeatable route from observed misses to evaluated
playbook revisions, and from those revisions to category-specific execution.
Maintenance currently seals a roster whose challenger stages are required; it
does not implement the proposed sampling policy. Its current assignments do not
resolve the focused playbook into a reusable maintenance pass plan. Evidence
capture is implemented; automated lesson activation and adaptive scheduling are
not. Old pilots and the current run are evidence, not proof these features exist.

## Assignment, pass, and playbook

An **assignment** is the outcome for one category in one office: improve its known
resources, discover useful additions, or both. It identifies the package, scope,
taxonomy, evidence date, research conditions and completion requirements.

A **pass** is a bounded piece of that assignment with a specific question and
source strategy: public workforce pathways, employment inside community agencies,
or resolving contradictory enrollment instructions. Several passes can contribute
to the same resource; their findings are reconciled into one coherent proposal.

A **playbook** tells Scout how to plan and perform those passes. It contains:

- Scope, useful vocabulary, source channels and category-specific access concerns.
- A menu of focuses, their dependencies, coverage obligations and circumstances
  that justify using them. Existing four default focuses and Employment's seven
  are reusable starting definitions, not a mandated universal pass count.
- Whole-resource checks, identity distinctions and known failure patterns.
- Configured follow-up, time-budget and stopping rules, with examples and exceptions.
- The lessons and evidence supporting its current version.

Each assignment stores its resolved instructions and hashes, not just filenames.
Later edits to a playbook cannot silently change an existing assignment.

## Research and comparison sequence

1. **Establish the baseline.** Preserve the exact input package and scope. A
   different office's package supplies examples and taxonomy, not proof its
   resources serve the target community. Separate discovery from known-resource
   rechecks so one cannot masquerade as the other.
2. **Plan Astra's work.** Use the category playbook, known resources and access
   gaps to name the passes and explain their purposes. Reuse current evidence
   when appropriate, identifying its age and limitations. A reused result is not
   counted as fresh discovery or an independent replication.
3. **Research and assess coverage.** After each pass, record supported additions,
   consequential corrections, unresolved questions, duplicates, methods used and
   time. Astra may propose a targeted follow-up with an explicit reason. Code
   validates permitted scope and budgets; semantic coverage judgments remain
   evidence-backed research judgments, not keyword or count heuristics.
4. **Review and freeze Astra's result.** Check the resource as a whole: descriptions,
   contact fields, Information, Categories, Types and groups must agree. Preserve
   this result before any external critique is revealed. Astra's own critical
   review is valuable but is not labeled an independent check.
5. **Run selected outside checks.** Claude receives a neutral independent assignment
   where selected. ChatGPT, Grok or Perplexity can receive a specific challenge
   where warranted. Record which role each actually performed.
6. **Compare, verify and reconcile.** Independently inspect supporting sources for
   material disagreements and useful additions. Preserve every actual finding's
   disposition. Keep both Astra's original result and the assisted final result,
   so improvements are not credited retrospectively to Astra alone.
7. **Deliver for curation and capture experience.** Produce the usual review file,
   with concise handouts and concrete curator questions. Record possible method
   lessons without activating them merely because the research finished.

## The outside researchers' roles

**Claude is the independent comparison researcher.** It receives the original
package's known-resource context, office scope, taxonomy definitions and common
writing requirements. It does not receive Astra's results, challenger findings,
learned search vocabulary, proposed additions or questions derived from their
answers. Its task is to independently discover and recheck the same category.
This can be transported in several smaller packets while remaining one category
comparison; transport packets are not additional research passes.

Use a fresh Claude conversation with access to the correct neutral packet.
For experiments evaluating Astra itself, use a fresh Astra research context with
only allowed inputs as well. The coordinator may hold sealed reference evidence;
the research context must not inherit it. Existing conversations that have seen
answers cannot become blind tests through a prompt instruction alone. Any access
or context-isolation failure is recorded and excludes a clean blind claim.

**ChatGPT, Grok and Perplexity are targeted challengers.** They may inspect Astra's
proposal and evidence to investigate a material contradiction, questionable
eligibility restriction, uncertain identity or suspected coverage gap. Scout
usually chooses one suitable challenger, recording the reason; all three are
not required by default. An auditor who sees the draft is not relabeled a blind
researcher. Broader multi-AI comparisons remain available occasionally to check
whether Astra and Claude share blind spots. Claude is not treated as ground truth.

## Sampling and availability

For the first trial, Employment receives a deliberate Claude comparison. For
the subsequent planned categories, choose a uniform random sample without
replacement of `ceil(category count / 3)`. Store the eligible category IDs, seed,
selection algorithm/version and chosen set before research. Keep these selection
flags out of Astra's research inputs. A restart retains the selection; it does
not draw an easier sample. Scope additions receive a separate recorded sampling
amendment. Report the deliberate pilot separately from the random sample.

Targeted checks are additional: for example, a new office or major playbook
revision, a repeated consequential error, or an unresolved critical access claim.
Their selection reasons and results must remain separate from random-sample
statistics. Easy, high-yield categories cannot substitute for randomly selected
ones. Report category sizes and service families because a category sample is
not automatically representative of every resource.

Check a selected provider's availability before dispatch. A missing required
comparison leaves that category awaiting comparison, while independent work on
other categories can continue. Announce the limitation promptly. Do not silently
substitute a provider, reroll the sample or record an unavailable check as a
zero-finding result. An operator-authorized protocol change preserves the unmet
check and its implications. This changes the earlier all-providers-must-be-ready
rule only if this design is approved.

Start with existing subscriptions and browser workflows. No plan upgrade, paid
API, additional credits or billing change is part of this design. Measure actual
use in the sampled role before recommending more capacity. Selected comparisons
must be completed before their research output is labeled ready for curation;
human review/export remains a separate stage for all categories.

Michael will upgrade his Claude subscription if its limits halt progress. Report
the actual limiting condition promptly so he can act; do not purchase an upgrade
or change billing automatically. Preserve the pending comparison and allow
independent work to continue while its availability is resolved.

## Learning: observation to tested guidance

Record **what changed and why it might matter** before deciding it is a lesson.
Possible causes include a missing search branch, inaccessible source, wrong
program identity, poor source interpretation, an instruction that was ignored,
or a fact that changed after research. Repeatedly appending guidance is not the
answer when the existing instruction was already adequate.

| Evidence | Permitted use |
| --- | --- |
| Raw AI finding | A lead to investigate; neither a verified resource nor an active lesson |
| Independently source-checked discovery or correction | Propose and test a scoped research-method hypothesis |
| Later human package addition | Investigate timing, discoverability, scope and provenance before calling it a miss |
| Explicit telephone/local confirmation | Evidence for the identified resource facts and practical-access lessons, with date and scope |
| Michael's or Stephanie's explicit design instruction | A directly authorized guidance change, not a statistical inference |

**Proposed refinement to the earlier learning gate:** research-method hypotheses
may be proposed and tested in isolated experiments before the human-vetting
threshold is met. Activation still requires explicit review and evaluation.
The existing 25 ordinary-vetting outcomes / three categories / 15 accepted
candidates / 90% unambiguous provenance gate remains a review trigger for broader
inferences from human outcomes. This is not permission to treat public web
research as telephone confirmation or to activate the lesson backlog in bulk.

A lesson record names its scope, evidence IDs, apparent cause, alternatives,
counterexamples, exact proposed instruction change and evaluation plan. Lifecycle:
observed → proposed → approved-for-experiment → evaluated → approved-active or
rejected; active versions can later be superseded or retired. A single strong
example can justify an experiment; it cannot establish a universal rule.

Example from Education: several initial drafts left usable enrollment details
unresolved until deeper program pages were read. A proposed instruction is:

> Before declaring enrollment details unknown, inspect registration instructions,
> department contacts and the current catalog. Distinguish registration hours
> from class hours and compare conflicting locations across the catalog.

Check whether existing guidance already required this and why it failed. Test
the revision on unfamiliar programs, including a case where no such detail is
published. Success requires fewer unsupported unknowns without invented answers.
Keep the original provider names in evidence; the reusable rule describes the
method. Do not infer another AI's actual search process from its final answer.

## Evaluation and diminishing returns

Use a new community or appropriately withheld examples to assess transfer.
Preserve reference identities outside the research context until work is frozen.
Comparable trials record time budgets, source access, package scope, actual model
identifiers when available and playbook versions. Missing model metadata remains
unknown. Retrospective recovery is useful and labeled separately.

Measure supported unique additions, discovery coverage against the validated
comparison set, consequential factual errors, unresolved access problems,
duplicate/scope errors, curator editing burden and active research time. Track
provider waiting separately. The union of researchers is an incomplete reference
set, not proof of every available service. Human practical usefulness becomes
measurable when actual curation outcomes arrive.

The first implementation executes the approved focus plan and permits documented
follow-up. It does not pretend to have learned an optimal schedule. Later,
evaluated outcomes can recommend adding, revising, combining or retiring passes
for a particular category and context. Michael reviews significant policy
revisions as a short bundle, rather than scoring individual research actions.

A category may finish when its required scope has been examined, significant
unresolved matters are resolved or clearly handed to curators, and no promising
untried pass justifies its expected cost. A budget stop is recorded with remaining
gaps. Low yield alone cannot eliminate required resource checks or establish
complete coverage. Sparse but important services must not lose attention merely
because they contribute few candidates. Stopping settings and audit rates live
in configuration and change through reviewed versions.

## Durable design and curator experience

Extend the existing playbook loader, focused research, maintenance stages and
evidence ledger. Keep SQLite for research history and exact artifacts; keep
canonical instructions in JSON/Markdown. Introduce a validated active manifest
selecting compatible playbooks, lessons, planning and sampling policies. Resolve
general/category/office scope explicitly and reject conflicting instructions.
Archive superseded manifests and activate a complete revision atomically.

An execution record binds package hash, assignment scope, exact resolved guidance,
pass plan, provider roles, sampling decision, model information and snapshots.
Pass receipts retain results, evidence, coverage judgments, timing and retry
history. Comparison records distinguish Astra-only and assisted results. Lessons
link these records to human outcomes when attribution is supported. Resume,
rollback and explicit replanning preserve history instead of overwriting it.

Keep Scout standalone and package-based. `autoMesaV2.html` is the curation
workspace; `mesa.html` remains the operational missionary application. Preserve
all three Admin editors, resource printing, Curated marking, selected export and
office-package merge compatibility. Export the exact approved revision; edits
invalidate its prior Curated state according to the existing workflow. Isolate
browser storage/artifact identities and databases as well as Git branches.

Resolved curator questions are durable package data, not temporary review-page
notes. Preserve each question's ID, text, explanation, source, resolution status,
answer and dated decision history through autoMesaV2 selected export, mesa.html
merge, office save/reload and later office-package export to Scout. Merge question
history independently of other resource edits: an older unanswered question or a
newer contact edit without questions must not erase a resolution. Conflicting
decisions retain both answers and require curator review. Keep these fields out
of patron handouts. Both applications must use the updated common application
code before this workflow is considered ready; the current iCloud mesa.html was
checked on September 7 and does not yet contain the question-aware merge code.

Initial discovery establishes a new office's resources; periodic maintenance is
expected to provide the main ongoing learning opportunities. On receiving a
package, Scout identifies previously unseen question decisions alongside resource
edits, without requiring a separate curator submission or fixed maintenance
schedule. Resolutions are potential learning evidence, not automatically active
lessons or blanket provider verification. Retain resource-specific answers and
evaluate reusable method hypotheses through the bounded experiment process.

Continue the five approved Information sections and concise, respectful writing
without a fixed word cap. Description includes a useful coverage/location cue.
Keep detailed research and call-preparation evidence outside handouts; curator
questions explain the conflicting facts in plain language. Bold changed wording
in comparisons. Review summaries show a few consequential examples, with complete
evidence available on demand. No new learning-score chores for curators.

Categories describe needs, Types describe services, and groups describe targeted
or meaningfully accommodated populations. Preserve the targeting/accommodating
evidence. Revisit classifications after substantive corrections. The input
taxonomy is the starting point, not a universal fixed catalog; new or revised
terms use explicit existing human-review paths. General eligibility alone does
not justify a group. Population browsing is not a list of every general service
a member could use.

Human edits, dated telephone evidence, IDs, history and attachments survive
regeneration. Source disagreement triggers review rather than silently replacing
local confirmation. Missing pages and partial-package absence do not prove
closure. Coverage is assessed against the original office package plus proposals,
and revisited after material rejection, consolidation or reclassification.

## Applying this to autoMesaV2

Michael accepts replacing or redoing work where the better design requires it.
Archive the current run as an attributable baseline anyway. Create a separate
execution revision/database and artifact identity for the new protocol; never
rewrite its prior roster, sealed assignments or completed comparisons in place.

Begin the new protocol with a bounded Mesa Employment pilot using the enhanced
playbook and a deliberate Claude comparison. Earlier research is available as
labeled evidence; it cannot be secretly supplied to an allegedly fresh test.
This pilot tests execution, research quality and curation usability. Claims about
general learning require a later withheld/new-community experiment.

After reviewing the pilot, resume or redo the remaining autoMesaV2 work under an
explicit manifest. Education need not finish the old protocol merely to preserve
sunk effort. If its already dispatched replies are later collected, archive them
as old-protocol evidence. Report reused, newly researched, independently compared
and still-incomplete scopes distinctly. Seven completed categories are neither
discarded automatically nor relabeled as products of the new method.

## How the GPT handoff influenced this design

Adopted: standalone/package-based operation, the full curator workflow,
whole-resource consistency, practical coverage, evidence-backed distinctions,
human-edit protection, a representative Employment pilot and tests that reflect
actual behavior. It correctly recognized earlier Employment playbook learning.

Updated from the older handoff: v2.0 and many proposed capabilities already
exist; the five-section writing approach is approved. No fresh branch or
wholesale rewrite is needed. The ongoing discussion now proposes Astra-led
execution with sampled Claude comparisons instead of universal challengers.

Not adopted as defaults: a numeric handout word cap, treating lead counts as
coverage, a universal taxonomy, automatic lesson activation, or changing shared
renderer ownership. Historical artifact counts are reference observations, not
current office state. Claude's return is proposed here; no subscription upgrade
or research restart has occurred.

## Review decisions

The recommended first implementation is the fixed enhanced Employment playbook,
a frozen Astra result, an independent Claude comparison, and a small set of
reviewable lesson proposals. The random-third rate is an accepted starting
setting for later categories, subject to evaluation. Research-method experiments before the human-outcome
gate are an explicit proposed amendment. Fully learned pass scheduling follows
measured experience rather than arriving as an untested first release.

These changes complete the missing part of grand-plan increment 5 and introduce
a bounded first piece of increment 6. The [implementation plan](scout-playbook-learning-plan.md)
defines the demonstrations and tests before wider use.
