#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.local_qwen import LOCAL_QWEN_MAX_COMPLETION_TOKENS
from resource_research_agent.optimization_models import OptimizationModelPipeline
from resource_research_agent.optimization_runtime import LocalQwenJSONClient, PINNED_MODELS
from resource_research_agent.mlx_server_workaround import WORKAROUND_VERSION
from resource_research_agent.playbooks import PLAYBOOK_LIBRARY_VERSION
from resource_research_agent.storage import ResearchStore


parser = argparse.ArgumentParser(description="Run one pinned quantization over a frozen corpus")
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--corpus-id", type=int, required=True)
parser.add_argument("--quantization", choices=tuple(PINNED_MODELS), required=True)
arguments = parser.parse_args()

store = ResearchStore(arguments.database, recover_interrupted=True)
with store.connect() as connection:
    row = connection.execute(
        """SELECT configuration.snapshot_json
           FROM optimization_corpora AS corpus
           JOIN optimization_runs AS run ON run.id = corpus.discovery_run_id
           JOIN optimization_configurations AS configuration
             ON configuration.id = run.configuration_id
           WHERE corpus.id = ? AND corpus.status = 'frozen'""",
        (arguments.corpus_id,),
    ).fetchone()
if not row:
    raise SystemExit("The requested frozen corpus does not exist")

configuration = json.loads(row["snapshot_json"])
configuration.update(
    {
        "label": f"mesa-housing-urgent-{arguments.quantization}-verifier-patch-v10",
        "modelArtifact": PINNED_MODELS[arguments.quantization],
        "quantization": arguments.quantization,
        "modelProvider": "qwen-local",
        "modelEndpoint": "http://127.0.0.1:8080/v1",
        "mlxVersion": f"mlx-lm-0.31.3_2;mlx-0.32.1;{WORKAROUND_VERSION}",
        "dshVersion": "not-used-direct-openai-compatible-endpoint",
        "promptPolicyVersion": "schema-playbook-dossier-v1-and-independent-verifier-decision-patch-v1;frozen-candidate-identity-v1",
        "playbookVersion": PLAYBOOK_LIBRARY_VERSION,
        "localQwenProxyTimeoutSeconds": 7200,
    }
)
configuration["limits"] = {
    **configuration["limits"],
    "modelMaxCompletionTokens": LOCAL_QWEN_MAX_COMPLETION_TOKENS,
    "modelRequestTimeoutSeconds": 7200,
}
client = LocalQwenJSONClient(
    arguments.quantization,
    timeout_seconds=7200,
    max_completion_tokens=LOCAL_QWEN_MAX_COMPLETION_TOKENS,
)
print(json.dumps(client.validate(), indent=2, sort_keys=True), flush=True)
pipeline = OptimizationModelPipeline(
    store,
    configuration,
    arguments.corpus_id,
    extract=client,
    verify=client,
    required_coverage_needs=(
        {"key": "emergency-adult", "label": "Adult emergency access", "query": '"Mesa" adult emergency shelter intake'},
        {"key": "families-with-children", "label": "Family shelter", "query": '"Mesa" family emergency shelter children'},
        {"key": "domestic-violence", "label": "Domestic-violence shelter", "query": '"Mesa" domestic violence emergency shelter'},
        {"key": "medical-respite", "label": "Medical respite", "query": '"Mesa" medical respite homeless program'},
        {"key": "veterans", "label": "Veteran emergency housing", "query": '"Mesa" veteran emergency housing'},
        {"key": "pets", "label": "Pet-compatible shelter", "query": '"Mesa" homeless shelter pets'},
        {"key": "transportation", "label": "Transportation to shelter", "query": '"Mesa" shelter transportation intake'},
    ),
    progress=lambda event: print(json.dumps(event, sort_keys=True), flush=True),
)
result = pipeline.run()
print(json.dumps(result.__dict__, indent=2, sort_keys=True))
