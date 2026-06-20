from google_adk import Agent
from google_adk.config import AgentConfig
from google_adk.models import Gemini25Flash
from skills.agent_skills import forecasting_skill

config = AgentConfig(
    name="inventory_agent",
    model=Gemini25Flash(),
    system_instruction="You are a world-class forecasting and projection engine. You only speak in highly concise, fact-based bullet points based strictly on the JSON payload provided. Do not hallucinate external values or perform mathematical computations."
)

inventory_agent = Agent(
    config=config,
    skills=[forecasting_skill]
)
