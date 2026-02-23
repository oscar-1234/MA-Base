import sys
import os

from src.multi_agent_chat.chat.session import chat_turn
from src.multi_agent_chat.memory.ltm import close_mem0


if __name__ == "__main__":
    print("🤖 Multi-Agent Chat (digita 'quit' per uscire)")
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        chat_turn(user_input)
    close_mem0()
