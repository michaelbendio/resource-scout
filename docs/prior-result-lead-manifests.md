# Prior-result lead manifests

Prior-result lead manifests let Scout reuse preserved research as a search lead
list without treating old output as current evidence. The format and reader are
category- and location-generic. DeepSeek is one possible historical source, not a
permanent code path.

## Safety boundary

A manifest may contain only:

- an organization and specific program name, when both are known;
- historical aliases;
- canonical public HTTP or HTTPS URLs;
- the historical disposition; and
- source run, stage, date, kind, and artifact provenance.

It cannot contain phone numbers, addresses, hours, eligibility, service claims,
availability, or other current factual fields. The validator rejects extra lead
fields rather than ignoring them. Importing the manifest persists it in the
discovery ledger and contributes zero queries, identities, evidence sources, or
candidates by itself.

`prior-result-leads-v1` appends one current search per preserved lead. The branch
runs every planned lead instead of using early saturation. Only results of those
new searches may proceed through current identity, role, geography,
actionability, package, status, and evidence gates. The manifest and its rows are
hashed into any resulting frozen corpus.

The first Mesa Housing harvest is a one-time calibration input. The generic
reader and builder remain useful for later periodic Scout work, but future runs
should normally use their immediately preceding preserved results rather than
repeatedly injecting this original benchmark history.

## Preserved Mesa Housing v1 harvest

The ignored benchmark artifact is:

`data/benchmarks/mesa-qwen-2026-08-21/optimization/prior-leads/mesa-housing-preserved-v1.json`

It was built from frozen DeepSeek research run 1; preserved Qwen research runs
21 through 24; and Qwen optimization discovery runs 1, 3, 5, 10, and 12 through
19. It contains 623 deduplicated leads from 22 run-stage sources:

- 100 normalized organization-plus-program identities;
- 523 unresolved canonical URL leads;
- 86 leads whose strongest historical disposition was candidate;
- 14 whose strongest historical disposition was routed; and
- 523 unresolved leads.

The canonical manifest content SHA-256 is
`ff96127c335ac250c6c3d88780e20d3745db5a9e2305a704ec83b674910df0a6`.
Per-source dispositions remain attached to provenance even when the same lead
appeared with different outcomes in different runs.

The harvest is reproducible with a pinned timestamp and explicit run list:

```sh
python3 build-prior-lead-manifest.py \
  --database data/benchmarks/mesa-qwen-2026-08-21/mesa-qwen-benchmark.sqlite3 \
  --output data/benchmarks/mesa-qwen-2026-08-21/optimization/prior-leads/mesa-housing-preserved-v1.json \
  --manifest-id mesa-housing-preserved-v1 \
  --category-id housing \
  --target-location Mesa \
  --created-at 2026-08-23T00:00:00+00:00 \
  --research-run 1:deepseek \
  --research-run 21:qwen \
  --research-run 22:qwen \
  --research-run 23:qwen \
  --research-run 24:qwen \
  --optimization-discovery-run 1 \
  --optimization-discovery-run 3 \
  --optimization-discovery-run 5 \
  --optimization-discovery-run 10 \
  --optimization-discovery-run 12 \
  --optimization-discovery-run 13 \
  --optimization-discovery-run 14 \
  --optimization-discovery-run 15 \
  --optimization-discovery-run 16 \
  --optimization-discovery-run 17 \
  --optimization-discovery-run 18 \
  --optimization-discovery-run 19
```

Regeneration must reproduce the recorded canonical content hash before the
manifest is used in a new query plan.

The resumable Mesa calibration cache appends the manifest to the exact qualified
base plan while reusing every earlier response:

```sh
python3 cache-qwen-housing-searches.py \
  --cache NEW-CACHE.json --review NEW-REVIEW.json \
  --previous-cache QUALIFIED-CACHE.json \
  --previous-review QUALIFIED-REVIEW.json \
  --candidate-status-review QUALIFIED-REVIEW.json \
  --targeted-expansion resource_research_agent/optimization_query_plans/mesa-housing-coordinated-entry-depth-v1.json \
  --prior-lead-manifest data/benchmarks/mesa-qwen-2026-08-21/optimization/prior-leads/mesa-housing-preserved-v1.json \
  --all-identity-status
```

The cache writes after every query. Re-running the same command resumes the
smallest incomplete historical lead and refuses a changed plan or manifest hash.
