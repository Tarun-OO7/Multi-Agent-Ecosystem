from google import genai
import os
from dotenv import load_dotenv

load_dotenv('.env')
client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))
for m in client.models.list():
    print(m.name)
