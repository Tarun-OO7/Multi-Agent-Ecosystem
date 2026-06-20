from google_adk import Agent
from google_adk.config import AgentConfig
from google_adk.models import Gemini25Flash
from skills.agent_skills import sales_growth_skill

config = AgentConfig(
    name="sales_agent",
    model=Gemini25Flash(),
    system_instruction="You are a world-class data query and analytics engine. You only speak in highly concise, fact-based bullet points based strictly on the JSON payload provided. Do not hallucinate external values or perform mathematical computations."
)

sales_agent = Agent(
    config=config,
    skills=[sales_growth_skill]
)
