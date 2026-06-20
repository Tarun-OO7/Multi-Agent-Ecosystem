class AgentConfig:
    """Mock AgentConfig for Google ADK."""
    def __init__(self, name: str, model, system_instruction: str):
        self.name = name
        self.model = model
        self.system_instruction = system_instruction
