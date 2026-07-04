import asyncio
from llm_client import call_llm_json

async def test():
    result = await call_llm_json(
        'You are a test agent. Respond only with valid JSON.',
        'Return JSON: {"status": "ok", "test": true}',
        'test-session-1'
    )
    print(result)

asyncio.run(test())
