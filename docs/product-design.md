# Resource Scout product design

## Product boundary

Resource Scout prepares a focused assignment, accepts responses copied from chats,
consolidates submitted leads conservatively, compares them with an optional source
package, and hands the resulting candidates to Resource Curator.

Scout does not decide whether a candidate is worthwhile. Curator does not require
a separate outcome form. A specialist's operational decision is expressed by
finishing a resource and marking it **Ready for package**; candidates that are not
ready remain pending.

## Discovery contract

The assignment requests leads rather than complete resource dossiers. It asks for
organization, program, website, readily available contact fields, lead role,
service area, a concise reason the lead matters, and uncertainty. Category guidance
defines what to include and what should not be treated as a candidate. Unknown
details are acceptable and do not by themselves discard a lead.

The response parser preserves the original text and source label. Parsed claims are
leads, not verified facts. Agreement among chats is useful identity evidence but is
not treated as truth.

## Consolidation

Exact repeated submissions collapse deterministically. Clear same-program naming
variants and matching access-point aliases collapse automatically. Similar
identities otherwise remain separate. A shared website alone is never identity
evidence. Named programs remain distinct when their service, population, intake,
or administration is materially different. Ordinary locations are not counted as
separate services. Directories and routing systems remain available as source-only
records rather than inflating the candidate count.

Candidate inclusion requires a credible indication of category relevance and
service to the selected area. Scout preserves uncertainty for the specialist.

## Contact completion

Website presence is the trigger for additional contact research. A confirmed
current website makes a lead actionable even if a phone number is not yet known.
A known official website that is dead, followed by unsuccessful replacement and
phone searches, may be recorded as unreachable. Closure or program termination
requires credible evidence. Inconclusive results remain candidates and receive a
plain-language Notes checklist with specific next searches.

## Completed-run reconciliation

A completed discovery remains linked to the package that shaped its original
assignment. When the connected package's normalized resources or taxonomy change,
Scout may append a reconciliation against that newer snapshot without repeating
discovery or rewriting the original record. Re-uploading unchanged content does
not offer reconciliation.

The newest reconciliation becomes the package basis for a replacement Curator.
A candidate is omitted as already represented only when the package and candidate
share an exact identity and an exact website or address. Weaker similarities remain
visible as possible relationships. Reconciliation never copies unverified candidate
fields into an existing curated resource.

## Curator handoff

Completed discovery exports one self-contained Curator scoped to that run. It has
Editors and Notes work areas, stable candidate and draft IDs, optional known-resource
relationship review, printable client-facing output, portable work checkpoints,
and additions-only package creation when a source package exists. Multiple distinct
programs from one organization appear together in a collapsible organization group;
specialists are not asked to resolve speculative submission relationships.

The Curator export excludes the Scout database, source-package full records,
credentials, old research machinery, and hidden outcome or teaching fields.
