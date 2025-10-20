from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]

payloads = db.create_collection("webhook_payloads", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["payload", "timestamp", "parse_status"],
        "properties": {
            "payload": {
                "bsonType": "object",
            },
            "timestamp": {
                "bsonType": "date",      
          },
            "parse_status": {
                "bsonType": "bool",
            }
        }
    }
})

media = db.create_collection("media_collection", validator={ 
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["media_id", "video_path", "audio_path"],
        "properties": {
            "media_id": {
                "bsonType": "string",
            },
            "video_path": {
                "bsonType": "string",
            },
            "audio_path": {
                "bsonType": "string",
            }
        }
    }
})