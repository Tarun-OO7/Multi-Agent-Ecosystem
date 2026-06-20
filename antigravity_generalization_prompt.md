# Task: Finish generalizing the Multi-Agent Data Intelligence Platform

## Role and context
You're working in an existing Python project: a multi-agent data intelligence platform built on Google's Agent Development Kit (ADK), with a Streamlit frontend, MCP-based data tools, and Gemini 2.5 Flash as the model. The system must answer questions about uploaded CSV/XLSX files of ANY domain, not just sales/retail data.

`coordinator.py` has already been refactored to remove business-specific keyword routing (no "sales", "revenue", "inventory", "quantity" anywhere in the routing logic) and now classifies user questions into five generic capabilities — DataQueryAgent, AnalyticsAgent, ForecastAgent, VisualizationAgent, ReportAgent — using a `dataset_context` built from schema + a small sample of rows (never the full dataframe).

**First step: replace your current `coordinator.py` with the version below.** Treat it as the source of truth for the rest of this task.

```python
import re
import logging
from typing import Any, Dict, List, Tuple

import pandas as pd
from google_adk import Agent
from google_adk.config import AgentConfig
from google_adk.models import Gemini25Flash

# Import specialized agents (kept for backward compatibility as execution engines)
from agents.sales_agent import sales_agent
from agents.inventory_agent import inventory_agent
from agents.customer_agent import customer_agent
from agents.report_agent import report_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = AgentConfig(
    name="coordinator_router_agent",
    model=Gemini25Flash(),
    system_instruction="""You are a strict Capability Router.
Analyze dataset metadata and user questions to route to exactly ONE of these capabilities:
- DataQueryAgent
- AnalyticsAgent
- ForecastAgent
- VisualizationAgent
- ReportAgent
If confidence is low, output exactly: DataQueryAgent
Do not provide any other text.
"""
)

coordinator_router = Agent(config=config)

CAPABILITY_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("ForecastAgent", [r"\bforecast", r"\bpredict", r"\bfuture\b", r"\bprojection"]),
    ("ReportAgent", [r"\breport", r"\bsummar", r"\bcomprehensive\b"]),
    ("VisualizationAgent", [r"\bvisual", r"\bchart", r"\bgraph", r"\bplot\b"]),
    ("AnalyticsAgent", [r"\banaly[sz]e", r"\btrend", r"\bcompare", r"\banomal",
                         r"\binsight", r"\bcorrelat", r"\boutlier"]),
    ("DataQueryAgent", [r"\bsum\b", r"\baverage\b", r"\bavg\b", r"\bcount\b",
                         r"\bfilter", r"\bgroup ?by\b", r"\baggregat",
                         r"\btotal\b", r"\bmean\b"]),
]

DEFAULT_CAPABILITY = "DataQueryAgent"


def extract_dataset_context(file_path: str) -> Dict[str, Any]:
    """Read a CSV/XLSX file and return lightweight, LLM-safe metadata."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    return {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "row_count": len(df),
        "sample_rows": df.head(3).to_dict(orient="records"),
    }


def build_routing_prompt(query: str, dataset_context: Dict[str, Any]) -> str:
    """Compose a compact, schema-only prompt for the LLM router (no raw data)."""
    return f"""
User Question: "{query}"

Dataset Metadata:
- Columns: {dataset_context['columns']}
- Data Types: {dataset_context['dtypes']}
- Total Rows: {dataset_context['row_count']}
- Sample Rows (subset, for context only): {dataset_context['sample_rows']}

Select the most appropriate capability.
"""


def classify_capability(query: str, dataset_context: Dict[str, Any]) -> Tuple[str, str]:
    """Classify a user question into one of five capabilities, generically."""
    query_lower = query.lower()

    for capability, patterns in CAPABILITY_KEYWORDS:
        if any(re.search(pattern, query_lower) for pattern in patterns):
            return capability, "high"

    logger.info(
        "No capability keywords matched query=%r (columns=%s); "
        "defaulting to %s (low confidence).",
        query, dataset_context.get("columns"), DEFAULT_CAPABILITY,
    )
    return DEFAULT_CAPABILITY, "low"


class Coordinator:
    def __init__(self):
        self.router = coordinator_router

    def process_query(self, query: str, file_path: str) -> str:
        try:
            dataset_context = extract_dataset_context(file_path)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return "Error: Could not process dataset metadata."

        routing_prompt = build_routing_prompt(query, dataset_context)
        detected_capability, confidence = classify_capability(query, dataset_context)

        logger.info("--- Routing Debug Log ---")
        logger.info(f"Question: {query}")
        logger.info(f"Dataset columns: {dataset_context['columns']}")
        logger.info(f"Detected Intent: {detected_capability} (confidence={confidence})")
        logger.info("-------------------------")

        if detected_capability in ("DataQueryAgent", "AnalyticsAgent"):
            logger.info("Selected Agent: sales_agent (Data Query/Analytics engine)")
            return sales_agent.execute(file_path=file_path, prompt=query)

        elif detected_capability == "ForecastAgent":
            logger.info("Selected Agent: inventory_agent (Forecasting engine)")
            return inventory_agent.execute(file_path=file_path, prompt=query)

        elif detected_capability == "VisualizationAgent":
            logger.info("Selected Agent: None (Visualization handled via UI)")
            return "For visualizations, please refer to the charts automatically generated in the left sidebar."

        elif detected_capability == "ReportAgent":
            logger.info("Selected Agent: report_agent (Reporting engine)")
            sales_output = sales_agent.execute(
                file_path=file_path, prompt="Summarize the key metrics and patterns in this dataset."
            )
            inventory_output = inventory_agent.execute(
                file_path=file_path, prompt="Summarize any time-based or quantity-based patterns in this dataset."
            )
            customer_output = customer_agent.execute(
                file_path=file_path, prompt="Identify and summarize key categories or segments in this dataset."
            )

            return report_agent.execute(
                sales_summary=sales_output,
                inventory_summary=inventory_output,
                customer_summary=customer_output,
            )

        return "Routing failed. Unrecognized capability."


coordinator_agent = Coordinator()
```

## What still needs to change

The coordinator now routes generically, but the agents and prompts it *calls* still carry assumptions left over from the original sales/inventory/customer-domain version of this project. Finish the generalization, in this order. After each numbered step, show a diff and a one-paragraph explanation before moving to the next one — don't bundle everything into one giant change.

1. **Inspect first.** Read `agents/sales_agent.py`, `agents/inventory_agent.py`, `agents/customer_agent.py`, `agents/report_agent.py` — their system instructions/prompts, and exactly what parameters `report_agent.execute()` accepts.

2. **Genericize `report_agent`'s interface.** It currently accepts `sales_summary`, `inventory_summary`, `customer_summary` keyword arguments. Rename these to domain-neutral equivalents — either `primary_summary` / `secondary_summary` / `tertiary_summary`, or better, a single `summaries: dict[str, str]` parameter. Update the call in `coordinator.py` to match. This *is* an interface change, and it's approved for this pass — the prior coordinator-only refactor intentionally left it alone, this step is meant to finish the job.

3. **Audit each agent's system instruction for hardcoded domain language** (e.g. "you are a sales analyst", "always look for a revenue or quantity column"). Rewrite to be schema-driven: each agent should work out what's relevant from the `dataset_context` columns/dtypes it's handed, not assume specific column names exist. Don't change `.execute(file_path=..., prompt=...)` signatures except where step 2 requires it for `report_agent`.

4. **Wire the LLM router for real — but only if you can confirm the API.** `coordinator_router` is built but never invoked; `classify_capability()` is keyword-only. If you can verify the correct invocation pattern for the installed `google_adk` version (e.g. a `Runner`/session-based call vs. a direct method — don't guess), wire it in as the primary classifier, with the existing keyword logic kept as a fallback when the LLM call fails, times out, or returns a label outside the five expected. If you can't confirm the API with confidence, leave this step alone and tell me what you'd need to check.

5. **VisualizationAgent path.** It currently returns a static string pointing at the Streamlit sidebar. Search the codebase first for an existing visualization/chart-recommendation agent or MCP tool. If one exists and isn't wired in, connect it. If none exists, leave the static string as-is — don't build a new visualization pipeline as part of this pass.

6. **Add unit tests for `classify_capability()`** using at least one dataset schema unrelated to sales (e.g. columns like `patient_id`, `admission_date`, `length_of_stay`) to prove the routing genuinely generalizes, plus the original sales-style schema to confirm no regression.

7. **Update README/docs only where they explicitly describe the old sales/inventory/customer agent framing** — reframe to DataQueryAgent/AnalyticsAgent/ForecastAgent/VisualizationAgent/ReportAgent. Don't touch anything else in the docs.

## Hard constraints
- Don't touch Streamlit UI code, MCP tool/server definitions, security middleware (file validation, prompt injection protection, rate limiting), or logging configuration.
- Never send a full dataframe to Gemini at any point you touch — only schema, aggregates, or computed results.
- No placeholder code, no `# TODO: implement` stubs — every change must be runnable as delivered.
- If a step needs information you don't have (the real ADK invocation signature, whether a visualization tool already exists elsewhere in the repo), stop and ask rather than guessing.

## Done when
- `coordinator_agent.process_query(query, file_path)` still has the exact same external call signature.
- The same query against two structurally different datasets (e.g. a retail CSV and a healthcare CSV) produces correct, identical-quality routing for both, with no business-domain keywords anywhere in the routing path.
- `report_agent.execute()` no longer has sales/inventory/customer-named parameters.
- All existing tests pass; new `classify_capability()` tests pass.
