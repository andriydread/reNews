import asyncio  # noqa , for testing only, delete later

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv  # delete later
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.models.models import ArticleCategory

load_dotenv()  # delete later


class AIAnalysisResult(BaseModel):
    summary: str = Field(description="A 3-5 sentence summary of the article.")
    category: ArticleCategory = Field(
        description="The most appropriate category from the predefined list."
    )
    score: int = Field(
        description="A score from 1 to 10. 1 = useless clickbait. 10 = highly insightful, new tech, or highly valuable knowledge."
    )
    language: str = Field(
        description="The language the article is written in (e.g., 'English', 'Ukrainian')."
    )


class AIProcessor:
    def __init__(self):
        self.client = genai.Client()

        self.model_name = "gemini-3.1-flash-lite-preview"

    async def extract_text_from_url(self, url: str) -> str | None:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with httpx.AsyncClient(
                headers=headers, follow_redirects=True
            ) as client:
                response = await client.get(url, timeout=15.0)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for element in soup(
                ["script", "style", "nav", "footer", "header", "aside"]
            ):
                element.decompose()

            text = soup.get_text(separator=" ", strip=True)

            return text[:15000]

        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None

    async def analyze_article(self, title: str, text: str) -> AIAnalysisResult | None:

        prompt = f"""
        Analyze the following article.
        Title: {title}
        
        Article Text:
        {text}
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIAnalysisResult,
                    temperature=0.2,
                ),
            )

            result = AIAnalysisResult.model_validate_json(response.text)
            return result

        except Exception as e:
            print(f"AI Processing failed: {e}")
            return None


# async def test():
#     ai = AIProcessor()
#     text = await ai.extract_text_from_url(
#         "https://en.wikipedia.org/wiki/Artificial_intelligence"
#     )
#     if text:
#         result = await ai.analyze_article("Artificial Intelligence", text)
#         print(f"Summary: {result.summary}")
#         print(f"Category: {result.category}")
#         print(f"Score: {result.score}/10")
#         print(f"Language: {result.language}")


# if __name__ == "__main__":
#     asyncio.run(test())
