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
