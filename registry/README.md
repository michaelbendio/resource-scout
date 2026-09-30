# Scout resource identity registry

`resource-identities.json` is production identity state, committed and backed up
with this repository on Michael's Mac mini. Preserve its namespace, sequence,
resource records, aliases and event history. A successor can restore this checkout
without a hosted service or Michael's account credentials.

Use `resource_identity.register_reviewed` through the prepared exporter. The model
may propose matches; code owns IDs. Review at the program level, not one identity
per organization or domain. Aliases use `[sourceNamespace, legacyId]` JSON keys to
avoid delimiter collisions. New source IDs are bound only after explicit review.

Missing registry: restore the committed file from Git or backup, then validate it
with `resource_identity.load_registry`. **Do not initialize another namespace.**
Back up the `data/` audit directories separately: they are not tracked in Git.
Committed deliveries retain the exact import payload, receipt and legacy-ID map.

Only one Scout writer operates on the Mac mini. The atomic save checks the previous
registry fingerprint and refuses stale state. It is not a distributed concurrency
protocol. If another machine or concurrent writer is introduced, design that change
before using both; no lease service is required for the current deployment.

For a rename, retain the canonical ID and change the resource text. For rediscovery
under a new source ID, use a reviewed `match` to the existing canonical ID. For
ambiguous merges/splits, stop and preserve both histories until an explicit migration
also reconciles affected human decisions. Never silently recycle or delete IDs.

Explicit supervisor-reviewed consolidations use `migrate_reviewed_identities`
under the same export lock, with an expected registry fingerprint on save. Each
decision names existing source/survivor IDs, reason and evidence. Preserve the old
record and sequence with `redirectTo`, rebind aliases, and append an `identity-merged`
event. Retired IDs resolve to the survivor on future matches, including chained
consolidations; cycles and dangling targets fail validation. The operation does not
change consumer approvals, edits or deletions. Plans/receipts belong in `migrations/`.

The exporter includes relevant retired canonical IDs in `identity-migration.json`
`aliases`, and identifies those entries as `canonicalMerges`. The consumer must
reconcile existing canonical references as well as legacy source references before
import. Conflicting human records require administrator reconciliation; no overwrite
or loss of a hidden decision is authorized. Verify that consumer behavior at handoff.
