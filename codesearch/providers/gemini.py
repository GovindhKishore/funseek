from codesearch.providers.base import BaseProvider

GEMINI_MODEL = "gemini-3.1-flash-lite"


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str, model_name: str | None = None):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name if model_name else GEMINI_MODEL

    def generate(self, prompt: str) -> str | None:
        from google.genai import types

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json"),
            )
            return response.text if response.text else None

        except Exception as e:
            print(f"Error {e}: \n\nSkipping reranking, showing fused results.")
            return None
