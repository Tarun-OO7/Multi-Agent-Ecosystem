from google_adk import Skill
from google_adk.models import Gemini25Flash

# Define the model to use across skills
model = Gemini25Flash()

@Skill(name="sales_growth_skill", description="Extract strategic narrative meanings from sales JSON payload without recalculating.", model=model)
def sales_growth_skill(sales_json: str) -> str:
    """
    Takes the sales JSON payload and constructs a strict prompt for Gemini to extract strategic narrative meanings, 
    prohibiting the LLM from trying to recalculate the numbers.
    """
    prompt = f"""
    Analyze the following sales data JSON payload.
    Extract the strategic narrative meanings and business implications.
    CRITICAL: Do NOT attempt to recalculate any numbers or metrics. Rely solely on the provided values.
    
    Payload: {sales_json}
    """
    return prompt

@Skill(name="forecasting_skill", description="Interpret trend metrics to build business scenarios.", model=model)
def forecasting_skill(inventory_json: str) -> str:
    """
    Interprets the trend metrics to build business scenarios.
    """
    prompt = f"""
    Analyze the following inventory data JSON payload.
    Interpret the trend metrics and construct plausible business scenarios (e.g., stockout risks, excess inventory).
    CRITICAL: Do NOT recalculate any numbers. Rely solely on the provided values.
    
    Payload: {inventory_json}
    """
    return prompt

@Skill(name="sentiment_skill", description="Extract emotional tone, intent, and recurring feature requests from feedback.", model=model)
def sentiment_skill(feedback_json: str) -> str:
    """
    Takes the pre-filtered customer feedback JSON text chunks and uses Gemini 2.5 Flash 
    to extract emotional tone, intent, and recurring feature requests.
    """
    prompt = f"""
    Analyze the following customer feedback JSON payload.
    Extract the emotional tone, underlying intent, and any recurring feature requests or complaints.
    
    Payload: {feedback_json}
    """
    return prompt

@Skill(name="reporting_skill", description="Synthesize multiple data strings into executive paragraphs.", model=model)
def reporting_skill(summaries: dict) -> str:
    """
    Synthesizes multiple data strings into executive paragraphs.
    """
    prompt = f"""
    Synthesize the following summaries into cohesive executive paragraphs.
    Format the output as a beautiful, professional Markdown document containing exactly these sections:
    1. Executive Summary
    2. Critical Risks
    3. 30-day Action Plan
    
    Summaries:
"""
    for k, v in summaries.items():
        prompt += f"    - {k}: {v}\n"
    return prompt
