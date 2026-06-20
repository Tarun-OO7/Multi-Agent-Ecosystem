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

# ---------------------------------------------------------------------------
# Capability routing rules.
#
# Every pattern here describes an ACTION the user is asking for (sum a
# column, spot a trend, forecast next month, draw a chart, summarize the
# data) — never a business-domain noun. There is no "sales", "revenue",
# "inventory", or "quantity" anywhere below, so the same rules apply
# whether the uploaded file is a sales sheet, a hospital admissions log,
# or a sensor export. Order is priority order: the first capability whose
# pattern matches wins (mirrors the original if/elif precedence).
# ---------------------------------------------------------------------------
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
    """Read a CSV/XLSX file and return lightweight, LLM-safe metadata.

    Never returns the full dataframe — only schema and a small sample —
    so downstream prompts stay within token budget regardless of dataset size.
    """
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
    """Classify a user question into one of five capabilities.

    Generalized for ANY dataset: matching is based purely on the action the
    user is asking for (sum, trend, forecast, chart, summary, ...), never on
    business vocabulary. dataset_context is accepted (not just the query) so
    the schema is available for audit logging and for future column-aware
    disambiguation if the LLM router below is wired in later.

    Returns:
        (capability, confidence) — confidence is "high" on an explicit
        keyword match and "low" when nothing matched and we fell back to
        the default, per the "low confidence -> DataQueryAgent" requirement.
    """
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
        # 1. Extract dataset metadata (never the raw dataframe)
        try:
            dataset_context = extract_dataset_context(file_path)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return "Error: Could not process dataset metadata."

        # 2. Build LLM routing payload (schema + samples only, no raw data).
        # self.router/routing_prompt are wired for direct Gemini-based routing;
        # today's active path is the deterministic classifier below, matching
        # the existing "simulated" behavior already in this project.
        routing_prompt = build_routing_prompt(query, dataset_context)

        # 3. Classify capability using the question + dataset_context
        detected_capability, confidence = classify_capability(query, dataset_context)

        # 4. Debug logging
        logger.info("--- Routing Debug Log ---")
        logger.info(f"Question: {query}")
        logger.info(f"Dataset columns: {dataset_context['columns']}")
        logger.info(f"Detected Intent: {detected_capability} (confidence={confidence})")
        logger.info("-------------------------")

        # 5. Map capability to existing specialized agents (backward compatible).
        # Prompts sent to legacy agents are dataset-agnostic on purpose — no
        # "sales"/"inventory"/"customer" assumptions baked in.
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
                summaries={
                    "DataQuery_Analytics_Summary": sales_output,
                    "Forecasting_Summary": inventory_output,
                    "Category_Segmentation_Summary": customer_output,
                }
            )

        return "Routing failed. Unrecognized capability."


coordinator_agent = Coordinator()
