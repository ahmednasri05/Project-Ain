import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv
# from routers import webhooks
from services.pipeline import run_pipeline

# load_dotenv()

# crimeapp = FastAPI()
# crimeapp.include_router(webhooks.router)

if __name__ == "__main__":
    # Run the interactive pipeline when the file is executed directly:
    #   python app.py
    # (This does NOT start the FastAPI server - use uvicorn for that)
    asyncio.run(run_pipeline())
