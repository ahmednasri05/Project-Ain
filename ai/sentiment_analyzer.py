import os
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json
from .schemas import SentimentAnalysis

load_dotenv()

class SentimentAnalyzer:
    """Sentiment analyzer as prefiltering phase for possible crime videos using OpenAI GPT-4o-mini."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def analyze_sentiment(self, text: str) -> SentimentAnalysis:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are an expert comment classifier for social media relating to possible crime videos in Egypt."
                    " You will analyze a batch of Egyptian Arabic or English comments and classify their intent as one of exactly these three:"
                    "\n- CRIME_REPORT: The comments refers to a real crime or credible suspicion of a crime."
                    "\n- SPAM_SARCASM: The comments is spam, sarcasm, a meme, or otherwise clearly not a genuine report."
                    "\n- AMBIGUOUS: The comments could not be confidently placed in either category or is unclear."
                    "\n\nRespond ONLY with a valid JSON object exactly in this format:"
                    "\n{\"label\": \"CRIME_REPORT\"|\"SPAM_SARCASM\"|\"AMBIGUOUS\", \"explanation\": \"A SHORT explanation for your choice.\"}"
                )},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=100
        )
        return SentimentAnalysis(**json.loads(response.choices[0].message.content.strip()))
