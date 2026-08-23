# Optimization playbook audits

`optimization-playbook-audit-v1` is the immutable planning receipt required
before a revised optimization corpus can be frozen. It makes the calibration
contract reviewable without moving category-specific guidance into reusable
Python code.

Each audit binds a selected category, stage, target location, regional scope,
playbook-library version, canonical hashes of `base.json` and the category
playbook, and the exact coverage-plan hash. The coverage hash includes the
required discovery branches but deliberately excludes dynamic operational
branches such as one-current-status-query-per-identity and one-current-search-
per-historical-lead. The complete query plan is still independently snapshotted
and hashed by the optimization configuration.

The audit must classify every actual query-plan branch as either coverage or
operational. It also records:

- service needs, populations, and practical barriers;
- authoritative source families and how each may be used;
- explicit geography rules;
- the exact candidate roles that may count and the roles preserved as
  noncandidates;
- required factual fields, the access-critical subset, and supplementary
  fields;
- gap-search triggers; and
- current-status and successor signals.

The validator compares the audit with the selected playbook and query plan. A
stale playbook hash, missing or extra branch, changed role policy, changed field
contract, category, stage, location, or referral component fails closed. The
revised freeze command requires the audit and records its hash plus both
playbook-source hashes in immutable configuration provenance.

The first reviewed artifact is
`resource_research_agent/optimization_playbook_audits/mesa-housing-urgent-v1.json`.
It is calibration data, not Housing-specific architecture. It confirms that
unknown `petPolicy` is supplementary and cannot block a candidate, while
identity, geography, service relevance, actionability, current status, and
evidence readiness remain candidate gates. Its plan is structurally ready, but
the final freeze remains execution-blocked until the exact prior-result branch
finishes and every newly recovered identity is reviewed.

Do not copy this Mesa artifact to another category. After the Housing and Curator
cycle supplies observed evidence, review each category's own playbook and create
an audit from that category's stages, fields, service needs, geography, sources,
and gaps. The generic validator has a Food regression specifically to prevent a
Housing fallback.
