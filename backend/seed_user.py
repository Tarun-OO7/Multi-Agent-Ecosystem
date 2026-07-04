import asyncio
import os
from dotenv import load_dotenv
load_dotenv(".env")
from motor.motor_asyncio import AsyncIOMotorClient
from auth import hash_password

async def run():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    await db.users.update_one({'email': 'admin@sentinel.ai'}, {'$set': {'email': 'admin@sentinel.ai', 'full_name': 'Admin', 'role': 'admin', 'password_hash': hash_password('admin123'), 'active': True}}, upsert=True)
    print('User admin@sentinel.ai created with password admin123')

asyncio.run(run())
