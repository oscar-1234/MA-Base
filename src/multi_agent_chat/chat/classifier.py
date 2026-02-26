from datapizza.clients.openai import OpenAIClient
from ..config import OPENAI_API_KEY, OPENAI_MODEL

def classify_user_intent(query: str) -> str:
    """
    Classify user query into task: "weather", "transfer_booking", or "generic".
    """
    client = OpenAIClient(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
        system_prompt="""
Classify into EXACTLY ONE primary task: "weather", "transfer_booking", "generic".

Rules:
- "weather": pure weather/forecast requests (meteo, temperatura, clima, previsioni).
- "transfer_booking": booking/transfer/viaggio/prenota + route details (cities, dates).
- "generic": everything else.

Multi-task: pick MOST IMPORTANT (booking > weather).
Output ONLY the task name (single word, lowercase).
                """,
        temperature=0.1,
    )

    context = f"Query: {query}"

    response = client.invoke(context)
    
    task = response.text
    print("\n=== CLASSIFIER OUTPUT ===")
    print(task)
    return task if task in {"weather", "transfer_booking", "generic"} else "generic"

def classify_user_intent_2(query: str, ltm_facts: str = "", recent_stm: str = "") -> str:
    """
    Classify user query into task: "weather", "transfer_booking", or "generic".
    """
    client = OpenAIClient(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
        system_prompt="""
Classify into EXACTLY ONE primary task: "weather", "transfer_booking", "generic".

Rules:
- "weather": pure weather/forecast requests (meteo, temperatura, clima, previsioni).
- "transfer_booking": booking/transfer/viaggio/prenota + route details (cities, dates).
- "generic": everything else.

Multi-task: pick MOST IMPORTANT (booking > weather).
Output ONLY the task name (single word, lowercase).
                """,
        temperature=0.1,
    )

    context = f"Query: {query}\nLTM: {ltm_facts}\nRecent chat: {recent_stm}"

    response = client.invoke(context)
    
    task = response.text
    print("\n=== CLASSIFIER OUTPUT ===")
    print(task)
    return task if task in {"weather", "transfer_booking", "generic"} else "generic"
