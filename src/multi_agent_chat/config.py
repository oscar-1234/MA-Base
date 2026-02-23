import os
from dotenv import load_dotenv

load_dotenv()

# User
USER_ID: str = "user_default"

# LTM
WHITELISTED_TOOLS: set[str] = {"get_user_profile", "get_preferences"}

# Models
OPENAI_MODEL: str = "gpt-4o-mini"
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# STM
STM_MAX_TURNS: int = 4
