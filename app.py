from fastapi import FastAPI
from dotenv import load_dotenv
from routers import webhooks
load_dotenv()

crimeapp = FastAPI()
crimeapp.include_router(webhooks.router)
