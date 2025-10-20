from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Read MongoDB connection settings from environment with sensible defaults
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "Farrag")

# Create MongoDB client and connect to the configured database
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]

# Collections
payloads = db["webhook_payloads"]
media = db["media_collection"]
