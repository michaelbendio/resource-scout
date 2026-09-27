# Review of the Scout evaluation and discovery design, from WSRS-TSO

September 27, 2026. Claude, working in WSRS-TSO, at Michael's request. Reviews
[scout-evaluation-and-discovery-design-20260927.md](scout-evaluation-and-discovery-design-20260927.md)
and its [discussion handoff](scout-discussion-handoff-20260927.md), on branch
`docs/scout-evaluation-design-20260927`. For Astra and Codex.

## New context that reframes the design

Michael will not own Scout indefinitely. His service ends around November 2027 (he
may extend it; time will tell), and Scout will then become the responsibility of **a
Church employee running it on the Church's Anthropic plan**. He wants to leave a good design, good documentation, a
handover as good as Jake Lindsay's, and a product that can evolve. The cost of a
run matters: roughly 50 hours per office is too much.

So the question the design should answer is not only "can Scout be cheaper for
Michael", but **"what does Scout look like when a Church employee runs it on Claude,
within a cost target, without Michael?"** The DeepSeek evaluation, the challenger and
the reserve's scope should each be judged by that.

Two facts are unknown and are being asked of Jake:

- **The Church's Anthropic plan:** per-token API billing or seat subscriptions, and who
  administers it. The two have very different cost shapes.
- **Where Scout should live:** it is in Michael's personal GitHub account
  (`michaelbendio/resource-scout`). GitHub suits a handover, since a repository moves
  with its history, but it should end in a Church-controlled account, and WSRS-TSO's
  notes record that the Church does not otherwise use GitHub.

## What the design gets right

Keep all of this:

- It separates three questions: model choice, discovery policy, and how much gets fully
  prepared. Otherwise a cheaper run can look better merely because it did less.
- It is honest about the baseline: the 50 hours is cumulative effort across layered
  rounds, and 1,885 identities is not a fresh run.
- The comparison is fair: no leakage of Codex answers into DeepSeek's exclusion lists,
  capped and failed runs reported as such.
- The workflow direction: screen before preparing; core, reserve and archive kept
  distinct; stop by assessed coverage with the stop reason recorded; zero challenger
  additions is a valid result; human data never overwritten.

## Recommendations, in order of effect

### 1. Plan for Claude as the provider, and check DeepSeek is permitted

Scout's workers today are Codex, with DeepSeek as challenger, designed in ChatGPT. On
the Church's plan they will need to be Claude. **Michael expects the Church will not
allow DeepSeek** ("I'd be surprised if the Church allows DeepSeek"), so a careful
DeepSeek evaluation would answer a question the successor cannot act on. Recommend
**setting it aside**, and spending the same care on the arrangement the successor will
have: Claude, tiered by task. Either way, **one provider** is far easier to hand over
than three.

Within Anthropic, use **tiered models**: a small model for screening and light reserve
records, a stronger one for research and final review. That is likely a larger saving
than switching provider, and it stays within one account and one bill.

### 2. Set a cost target per office, and design toward it

Name one, for example: *one office in about a day of machine time, at a cost the Church
would approve*. Measure against it. Without a target, the evaluation can only report
what the current approach costs.

### 2a. Guard against the wrong account and runaway cost

Michael was once charged **more than $125 in overage on his personal Claude account**
for an early run he believed was on his Church account. Nothing warned him until the
bill. It is the same class of mistake as a browser silently signing in with the wrong
account, and a successor can make it just as easily. It is also the kind of mistake
that would cost Scout the Church's trust, so the design should make it hard:

- **State the account before any paid run:** the provider, the organization or
  workspace, and whose billing it is, then wait for an explicit yes. WSRS-TSO's data
  scripts use the same pattern: they refuse production unless `ALLOW_PROD=1` is given.
- **Estimate the cost first**, from categories and expected resource counts, the way a
  dry run shows what it will change.
- **Stop at a spending limit** the run cannot raise by itself; recommend also setting a
  workspace spend limit in the Anthropic console, as a second guard independent of
  Scout's code.
- **Record each run's actual cost** alongside the estimate, so later estimates rest on
  real figures and the handover can state what an office costs.

On speed: Michael found Claude slow when it was one of four challengers. That is one
configuration in one role, not a verdict. With tiered models most calls are small and
fast; on per-token billing slowness costs turnaround rather than money, and parallel
categories recover most of that. Measure one category with current models before
deciding.

### 3. Decide the reserve's service level now, before evaluating

The largest cost driver is fully preparing every usable resource: five Information
sections, evidence and review. The design keeps that scope for the evaluation and
defers the decision. Decide it first, because it changes almost every later answer.

Proposed:

- **Core = the union of the starter sets.** At 7–10 per category across about 21
  categories, that is roughly 150–200 distinct resources, Michael's target. (Mesa's first
  four categories had 37 starter placements covering 34 distinct resources.) This
  replaces the separate "core preparation candidate" concept, and it is exactly what
  WSRS-TSO shows curators first.
- **Everything else = a light reserve record:** name, contact, one or two sentences of
  what it offers and for whom, categories and Types, and the source link. Enough for a
  missionary to find it and call, which is what WSRS-TSO's printed warning already tells
  them to do.
- **Full preparation on demand:** when a curator promotes a reserve resource, or a
  missionary saves one for review in WSRS-TSO, that one resource is prepared fully.

WSRS-TSO would need a small change to accept shorter reserve records; the contract
already makes most reserve fields optional in practice.

### 4. Make turnaround a design section, not a line

Turnaround is priority one. Categories are independent until final review, so running
several in parallel is the most direct way to shorten calendar time. Give it its own
section: how many at once, what they share, where they must wait for each other.

### 5. Move the shared Utah base forward

Six of the next offices are in Utah (Welfare Square, St. George, Cedar City, Ogden,
Logan, Brigham City). DWS, Medicaid, 211, Utah Legal Services and statewide lines will
recur in each. Research a **shared state-level base once**, and have each office add only
its local layer. The design has evidence reuse as increment 7; for the rollout it is
probably the biggest saving after the reserve decision.

### 6. Make the evaluation proportionate

Sealed manifests, anonymized scoring, three clocks, cache-token accounting, sensitivity
scenarios and 14 tickets are each defensible, but together they may cost more of
Michael's time and plan than they save. Suggest Stage A answer one question, in one
category, with one measure: **how much correction does the output need, compared with
the incumbent's?** Run it with Claude models the successor will use (a small model for
screening and light records, a stronger one for research and review), not DeepSeek.

### 7. Let people define the essential pathways, and use WSRS-TSO's outcomes

The essential pathways, frozen before scoring, decide the comparison; if a model writes
them, AI is grading AI. They should come from Michael or Stephanie; each office's Types
catalog is a ready starting point.

The design calls office vetting the strongest feedback and defers it. WSRS-TSO will now
produce exactly that: which starters curators keep or delete, which reserve resources
missionaries save for review, and why suggestions are declined. **Starters kept by
curators** is the most direct quality measure Scout can have.

## For the handover itself

What made Jake's handover exemplary, and what Scout's needs:

- what the tool is for, in plain words;
- how to run an office, step by step, with one command;
- what a run costs, and what makes it cost more;
- what can go wrong, and how you would know;
- what is decided, what is open, and why.

That is far easier to write about a simpler system: one repository, one main branch
(the merge now pending is a good start: it has seven conflicting files, including
`scout_curation.py` and `scout_review.py`, and should be resolved locally with tests,
not with GitHub's button), one provider, one documented run. The **prepared-resources
contract** is the seam that lets Scout and WSRS-TSO each evolve independently; keep it
versioned and documented, and Scout's internals can change entirely without WSRS-TSO
noticing.

## Summary

The design is a good plan for evaluating Scout carefully. What Scout needs first is to
**do less**: a light reserve, core as the starter sets, categories in parallel, a shared
Utah base, and one provider the Church can use. Then a small evaluation confirms the
result, and the handover describes a system a successor can run.
