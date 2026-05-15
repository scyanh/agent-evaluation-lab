# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import os

from vertexai import types # type: ignore

from dotenv import load_dotenv

from shared.evaluation.evaluate import (
    evaluate_agent,
    get_custom_function_metric
)
from shared.evaluation.tool_metrics import (
    trajectory_precision_func, trajectory_recall_func
)

load_dotenv()

METRIC_THRESHOLD = 0.75
RESEARCHER_URL = os.environ["RESEARCHER_URL"]
ORCHESTRATOR_URL = os.environ["ORCHESTRATOR_URL"]
GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

if __name__ == "__main__":
    # TODO: implement evaluation
    eval_data_researcher = os.path.dirname(__file__) + "/eval_data_researcher.json"
    metrics=[
        # Compares the agent's output against a "Golden Answer"
        types.RubricMetric.FINAL_RESPONSE_MATCH,
        # Did the agent use the tools effectively?
        types.RubricMetric.TOOL_USE_QUALITY,
        # Custom metrics for tools trajectory analysis
        get_custom_function_metric("trajectory_precision", trajectory_precision_func),
        get_custom_function_metric("trajectory_recall", trajectory_recall_func)
    ]

    print("🧪 Running Researcher Evaluation...")
    eval_results = asyncio.run(
        # Run the evaluation and retrieve the results.
        evaluate_agent(
            agent_api_server=RESEARCHER_URL, # Agent Service URL (in Cloud Run).
            agent_name="agent", # Agent name as it's exposed by the server.
            evaluation_data_file=eval_data_researcher, # Evaluation data file.
            # GCS location for the Evaluation Service to store the result to.
            evaluation_storage_uri=f"gs://{GOOGLE_CLOUD_PROJECT}-agents/evaluation",
            metrics=metrics, # Metrics to use when evaluating the agent.
            project_id=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_REGION
        )
    )
    print(f"\n🧪 Researcher Evaluation results:\n{eval_results}")
    print(f"Evaluation Run ID: {eval_results.run_id}")


    METRIC_THRESHOLD = 0.75
    researcher_eval_failed = False
    if eval_results.state != types.EvaluationRunState.SUCCEEDED:
        print(f"🛑 Researcher Evaluation failed with state {eval_results.state}.")
        researcher_eval_failed = True
    else:
        for metric_name, metric_values in eval_results.metrics.items():
            if metric_values["mean"] < METRIC_THRESHOLD:
                print(f"🛑 Researcher Evaluation failed with metric `{metric_name}` below {METRIC_THRESHOLD} threshold.")
                researcher_eval_failed = True
    if researcher_eval_failed:
        exit(1)


    eval_data_orchestrator = os.path.dirname(__file__) + "/eval_data_orchestrator.json"
    metrics=[
        types.RubricMetric.HALLUCINATION,
    ]

    print("🧪 Running Orchestrator Evaluation...")
    eval_results = asyncio.run(evaluate_agent(
        agent_api_server=ORCHESTRATOR_URL,
        agent_name="agent",
        evaluation_data_file=eval_data_orchestrator,
        evaluation_storage_uri=f"gs://{GOOGLE_CLOUD_PROJECT}-agents/evaluation",
        metrics=metrics,
        project_id=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_REGION
    ))
    print(f"\n🧪 Orchestrator Evaluation results:\n{eval_results}")
    print(f"Evaluation Run ID: {eval_results.run_id}")
    METRIC_THRESHOLD = 0.75
    orchestrator_eval_failed = False
    if eval_results.state != types.EvaluationRunState.SUCCEEDED:
        print(f"🛑 Orchestrator Evaluation failed with state {eval_results.state}.")
        orchestrator_eval_failed = True
    else:
        for metric_name, metric_values in eval_results.metrics.items():
            if metric_values["mean"] < METRIC_THRESHOLD:
                print(f"🛑 Orchestrator Evaluation failed with metric `{metric_name}` below {METRIC_THRESHOLD} threshold.")
                orchestrator_eval_failed = True
    if orchestrator_eval_failed:
        exit(1)