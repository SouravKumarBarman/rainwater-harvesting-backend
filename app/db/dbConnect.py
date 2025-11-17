import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()
client=None
db=None

async def connect_db():
    try:
        global client, db
        client = AsyncMongoClient(os.environ["MONGODB_URL"])
        db = client["rainwater-harvesting"]
        print("Connected to the database successfully")
        return True
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None
    
async def disconnect_db():
    try:
        global client
        if client:
            conn=await client.close()
            if conn is None:
                print("Disconnected from the database successfully")
    except Exception as e:
        print(f"Error disconnecting from the database: {e}")


