# Resource Scout

Scout researches community services, prepares resource candidates, and supports
review for TSO offices. Its current data handoff to WSRS-TSO is
`prepared-resources.json`: stable resource identities, sources, taxonomy, explained
starter sets, and reserve resources. AI preparation and review do not confer human
approval or agency verification.

Start with [SCOUT_STATUS.md](SCOUT_STATUS.md) for the current checkout, run state,
deliveries and holds. Read [the documentation guide](docs/README.md) for current
policy and contracts. Scout is stopped pending Welfare Square rule/run preparation;
commands below describe capabilities, not authorization to start paid work.

## Current workflow

1. Research under the [office-fit rules](docs/office-fit-rules-20260928.md), preserving
   source evidence and sealed assignments.
2. Prepare supported candidates and reconcile identities and taxonomy.
3. Review content, useful starter sets and reserve explanations under the
   [prepared-resource contract](docs/scout-prepared-resources-contract.md).
4. Export validated JSON for WSRS-TSO; the office makes its own curation decisions.

Scope, providers and review authority come from the current handoff and Michael's
instructions. Follow [orchestration](docs/scout-orchestration.md) for monitoring,
checkpointing, interruptions and recovery. Do not replay unknown-outcome requests.

Scout also supports legacy `auto[Location].html` workbenches and candidate ZIPs.
See [legacy curation](docs/scout-curation.md) and
[workbench readiness](docs/scout-workbench-readiness.md). Their historical tiers,
provider rosters and section formats do not override the prepared-resource contract
or current office-fit policy.

## Local interface

Python 3.10 or newer is required for the core application. Optional evaluation
tooling may have separate dependencies; follow its specific instructions.

```sh
./run.sh
```

The default interface is [localhost:8765](http://127.0.0.1:8765).
For private access through Tailscale:

```sh
./run-tailscale.sh --port 8767
```

The command prints the private address. A dashboard server is not a research worker.
For service management, see `./background-service.sh` and its `status`, `logs`,
`install` and `restart` commands. Installing or restarting a service is an explicit
operational action; this cleanup leaves Scout stopped.

## Repository and data

- `resource_research_agent/`, `scripts/`, `tests/`: implementation and checks.
- `docs/`, `schemas/`, `registry/`: policies, contracts and committed identities.
- `deliveries/`: versioned handoffs; check scope and acceptance status before import.
- `data/`: ignored local research databases, responses, runtime evidence and previews.
  It also currently contains a separate Git worktree at `data/evaluations/implementation`.
  Do not bulk-delete this directory or use `git clean -fdx` to tidy the repository.

Git pushes do not back up ignored runtime evidence. Connected source packages,
research evidence and human decisions must be preserved. Do not commit credentials
or private client information.

## Verification

```sh
python3 -m unittest discover -s tests
```

Use focused checks for a scoped change and the appropriate delivery validators.
Passing structural tests does not establish resource quality or office approval.

Older version notes and workflow descriptions are preserved in the
[pre-cleanup README](docs/archive/20260928/README.md). Historical operational
checkpoints are in the [status archive](docs/archive/20260928/SCOUT_STATUS.md).
