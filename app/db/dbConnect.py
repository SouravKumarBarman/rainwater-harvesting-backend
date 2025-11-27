from pymongo import AsyncMongoClient
from ..config import settings

client = None
db = None


async def connect_db():
    try:
        global client, db
        client = AsyncMongoClient(settings.mongodb_url)
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
            conn = await client.close()
            if conn is None:
                print("Disconnected from the database successfully")
    except Exception as e:
        print(f"Error disconnecting from the database: {e}")


async def get_user_collection():
    global db
    if db is None:
        # try to establish a connection if not already connected
        connected = await connect_db()
        if not connected or db is None:
            raise RuntimeError("Database is not connected")
    return db.get_collection("users")

async def get_project_collection():
    global db
    if db is None:
        # try to establish a connection if not already connected
        connected = await connect_db()
        if not connected or db is None:
            raise RuntimeError("Database is not connected")
    return db.get_collection("projects")
