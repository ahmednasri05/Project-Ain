import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import webhooks, api
from services.pipeline import run_pipeline

load_dotenv()

crimeapp = FastAPI(title="Project Ain")

crimeapp.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

crimeapp.include_router(webhooks.router)
crimeapp.include_router(api.router)

if __name__ == "__main__":
    # Run the interactive pipeline when the file is executed directly:
    #   python app.py
    # (This does NOT start the FastAPI server - use uvicorn for that)
    asyncio.run(run_pipeline())
