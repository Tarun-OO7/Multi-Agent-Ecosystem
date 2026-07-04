import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from auth import hash_password

load_dotenv('.env')
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users_col = db['users']
    admin = await users_col.find_one({'role': 'admin'})
    if not admin:
        print('No admin found')
        return
    
    new_password = 'Password123!'
    new_hash = hash_password(new_password)
    await users_col.update_one({'_id': admin['_id']}, {'$set': {'password_hash': new_hash}})
    print('Admin email is:', admin['email'])
    print('Admin password reset to:', new_password)

if __name__ == '__main__':
    asyncio.run(main())
