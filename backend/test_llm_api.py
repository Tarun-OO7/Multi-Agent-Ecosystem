import asyncio
from dotenv import load_dotenv
load_dotenv('.env')
from llm_client import call_llm_json

async def test():
    result = await call_llm_json(
        'Respond only with valid JSON.',
        'Return JSON: {"status": "ok", "test": true}',
        'test-session'
    )
    print(result)

asyncio.run(test())
