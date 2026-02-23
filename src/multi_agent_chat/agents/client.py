from datapizza.clients.openai import OpenAIClient
from ..config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAIClient(
    api_key=OPENAI_API_KEY,
    model=OPENAI_MODEL,
)
