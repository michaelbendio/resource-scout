# Real operating-policy comparison

Completed September 9, 2026 (Mountain time), after Michael explicitly authorized two isolated Astra research sessions. **Both real runs completed; evaluation is inconclusive and the policy remains inactive.** See [the short results report](../../docs/scout-operating-real-comparison-results.md). Browser controls were not used for research; each isolated Astra respondent used the web research tool.

## Hypothesis and scope

Under equal source limits, asking the researcher to follow a linked dedicated intake/eligibility page when an overview is unclear may produce more actionable Clothing referrals without losing important options. The hypothesis comes from the saved Mesa maintenance pilot's PINCH finding. That is one manual observation, not proven learning or an independent discovery result.

Compare the existing four Clothing pass directions with the same four directions plus that instruction. All other policy fields, model (`gpt-6-astra`), starting package, geography, taxonomy, pass order, required needs and allowances stay fixed. Both arms have zero outside checks to isolate the instruction; this does not change the ordinary research policy. Exclude the earlier pilot's example providers from both arms. The source package is an empty research starting collection, not the current 268-resource Mesa office package. These results must not be described as additions proven absent from the full office collection.

Each arm can search Mesa and practically reachable East Valley services, examine up to 16 pages and eight search queries within 16 web calls, and write at most three leads. Four focused passes each have a sublimit of four pages, two queries and three web calls. Remaining allowance can settle consequential gaps during synthesis. Maximum elapsed allowance is 30 minutes per arm. Incomplete coverage is reported, never supplied from inference to get a positive result.

Both results need fresh contexts, actual source evidence, complete scheduler receipts and model identity. The evaluator checks claims and missing conditions against primary sources. Use stable semantic finding keys and distinguish a lead, a material access clarification, duplicates and unresolved gaps. Dollar cost remains unknown unless measured; subscription usage is not a zero-dollar claim. One pair is too small for a general efficiency or rollout conclusion.

## Saved preparation

`prepared.json` contains the reference/proposal/trial and initial manifest IDs. `source-package.zip`, `source.json`, `design.json`, the two policy JSON files and `common-research-instructions.json` are sealed preparation inputs. No arm packets were dispatched during preparation. That historical preparation snapshot remains unchanged; subsequent packets and completed responses are archived under `baseline/` and `candidate/`. The local database is `output/operating-real-20260909/comparison.sqlite3` and remains outside Git.

`prepare.py` documents preparation and refuses to overwrite an existing trial. `controller.py` supplies transport-neutral `start`, `next`, `submit`, and `status` actions for one arm. It launches no model. Each authorized isolated researcher used its own arm through this controller. The original instructions and actual scheduler assignment contracts both apply. The controller preserves raw deliveries and exact packet hashes; it never invents research receipts or approves a policy.

Original operator sequence (do not rerun a completed arm):

```sh
python3 experiments/operating-real-20260909/controller.py start baseline
python3 experiments/operating-real-20260909/controller.py next baseline
# The isolated baseline researcher writes its real response in its own output directory.
python3 experiments/operating-real-20260909/controller.py submit baseline output/operating-real-20260909/baseline/response.json
```

Repeat independently for the candidate. Never let either researcher read the other arm's policies, prompts, output, previous experiments or expected editorial judgments. Archive web call/search/page counts and actual elapsed time separately from reported model effort. Capture incomplete or limit-hit work and stop when allowances expire. Evaluation and any later authorized activation are separate steps; this task grants no production activation.

## Preparation finding

Scout's normal previous-run lookup could expose one completed experimental arm to the other, or expose experimental results to future ordinary research. The fix limits experimental assignments to their sealed package identities and omits previous-run lookups. Ordinary runs also exclude experiment projects from those lookups. A regression test completes one arm before preparing the other and verifies isolation, while preserving identities and tombstones already in the source package.

## Completed evidence and replay

`comparison-summary.json` contains the measured comparison; `quality-review.json` attributes the coordinator’s source-based judgments. `assessment.json` and `evaluation.json` preserve the formal decision and blockers. Every accepted assignment/result, the original model outcomes, corrected timing alongside original estimates, and the baseline schema retry are archived per arm. Normalized comparison results use ten matched final-draft issue groups; they do not turn differing researcher finding-list lengths into a quality score.

`execution-audit.json` hashes every raw web delivery and verifies its explicit request counts. Full raw web replies remain in the local `output/operating-real-20260909` folders; they are not bulk republished into Git. Coordinator verification used six opened pages plus four in-page finds, in two separate tool calls; this work is outside both research allowances. Source retrieval does not establish phone verification.

Run `python3 experiments/operating-real-20260909/verify.py` for offline artifact checks. It launches no models. `audit.py` can refresh the execution audit from the preserved local database; `finalize.py` documents actual result capture/evaluation and refuses to overwrite differing archived results. The SQLite database remains local and is not required for offline hash/contract verification.

All 14 research stages were accepted, both contexts were isolated, source ceilings were respected, and the original empty operating manifest remained unchanged. The result is not an active lesson or an office resource package.
