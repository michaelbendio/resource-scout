# Authoritative referral graphs

`authoritative-one-hop-referrals-v1` expands carefully reviewed relationships
without counting a referral page, directory entry, location, or partner logo as a
candidate.

Each edge records:

- the authoritative source URL, title, and authority class;
- the named organization and specific program;
- the exact public destination URL;
- the selected category-playbook stage;
- the relationship type; and
- a bounded nearby context excerpt showing why the edge exists.

The accepted source classes are a direct provider, a government or coordinated
referral source, and an explicitly reviewed reputable secondary source. A generic
directory cannot seed an edge. Self-loops, duplicate edges, more than 25 edges
from one page, more than 200 edges in one graph, category/location mismatches,
and stages outside the selected playbook fail closed.

The graph is one hop. Scout does not recursively harvest the destination page's
partners or links. A separate `reviewed-referral-destinations-v1` manifest must
cover every edge key exactly and classify it as `candidate`, `unresolved`, or
`excluded`. Candidate decisions carry the same category-neutral qualification
fields used by ordinary discovery. A changed historical program name requires an
explicit identity-resolution reason. Unresolved and excluded decisions cannot
smuggle in an identity.

New referral-review manifests also declare
`reviewed-evidence-scope-and-identity-v1`. Every eligible destination identity
then carries the same reviewed authority, full-page or exact-section scope, and
organization/program label receipts as an ordinary reviewed search result. The
referral manifest is validated before Scout creates a corpus run, and the shared
discovery path checks those receipts against the freshly fetched destination.
This keeps referral expansion from becoming a legacy evidence path with weaker
identity or section rules.

Scout persists each edge and creates a lead for its exact destination. The edge
context remains provenance and is not copied into the candidate's evidence. A
candidate decision must cite the destination URL, and its exact reviewed excerpt
must be present in a fresh successful fetch before the page can become evidence.
Only a currently eligible identity can produce a packet. An unresolved or
excluded edge remains in the ledger without being fetched into a candidate or
affecting query saturation.

Several edges may lead to one identity, and several materially distinct programs
may belong to one parent organization. Identity deduplication still uses
organization plus specific program. Access locations, organization-only records,
directories, and referral systems remain noncandidate roles unless an access or
assessment service is independently actionable under the role gate.

The graph is stored in `optimization_referral_graphs`; each edge and its resume
status is stored in `optimization_referral_edges`. Completed expansion is
replay-safe. The graph, edges, current leads, identities, and fetched destination
evidence are all included in the frozen corpus ledger hashes.

The first Mesa Housing graph was built from newly inspected direct-provider,
City, coordinated-entry, and authoritative referral pages as a versioned
calibration artifact, not a Housing-specific Python path. Its 16 reviewed edges
contain seven candidate decisions, six unresolved leads, and three excluded dead
or misdirected links. A live referral-only pilot fetched six urgent-stage packets;
the seventh candidate was correctly routed to stabilization. Four urgent-stage
identities were new to the prior qualification manifest. Confidential shelters
may use a public safe-contact destination; Scout must not attempt to discover or
publish a confidential address.
