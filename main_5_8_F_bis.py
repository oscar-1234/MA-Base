"""
Semplice AI Agent - Streaming del processo di esecuzione dell'agente (ogni singolo passo)
(Non trasmette in streaming la singola risposta)
"""

import os
from dotenv import load_dotenv
import json

from datapizza.agents import Agent, StepResult
from datapizza.clients.openai import OpenAIClient
from datapizza.tools import tool
from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

load_dotenv()

def prune_memory_old(memory: Memory, max_turns: int = 3) -> None:
    data = json.loads(memory.json_dumps())  # lista di turni

    print("\n=== JSON RAW (PRE PRUNE) ===")
    print(data)

    if len(data) <= max_turns:
        return
    
    data = data[-max_turns:]  # tieni ultimi N

    print("\n=== JSON RAW (POST PRUNE) ===")
    print(data)

    memory.clear()
    memory.json_loads(json.dumps(data))  # ricarica

def prune_memory(memory: Memory, max_turns: int = 6) -> None:
    data = json.loads(memory.json_dumps())

    print("\n=== JSON RAW (PRE PRUNE) ===")
    print(data)

    if len(data) <= max_turns:
        return
    
    window = data[-max_turns:]
    
    # Se non c'è nessun user turn nella finestra, aggiungilo forzatamente
    has_user = any(t["role"] == "user" for t in window)
    if not has_user:
        # Trova l'ultimo user turn fuori dalla finestra
        outside = data[:-max_turns]
        last_user = next((t for t in reversed(outside) if t["role"] == "user"), None)
        if last_user:
            window = [last_user] + window  # Prependi

    print("\n=== JSON RAW (POST PRUNE) ===")
    print(window)

    memory.clear()
    memory.json_loads(json.dumps(window))

@tool
def get_weather(location: str, when: str) -> str:
    """Retrives weather information"""
    return f"Weather in {location} on {when}: 10°C, partly cloudy"


client = OpenAIClient(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
)

memory = Memory()

orchestrator_agent = Agent(
    name="orchestrator_agent",
    client=client,
    system_prompt="You are an helpful assistant. Use sub-agent when needed.",
    memory=memory,
    planning_interval=3,
    max_steps=10,
)

weather_agent = Agent(
    name="weather_agent",
    client=client,
    system_prompt="You are an expert weather assistant. Use tools when needed.",
    tools=[get_weather],
    memory=memory,
    max_steps=10,
)

orchestrator_agent.can_call(weather_agent)


user_query = "What is the weather tomorrow in Milan?"

memory.add_turn(TextBlock(content=user_query), role=ROLE.USER)

memory.add_turn(TextBlock(content="STEP: 0 | AGENT: orchestrator_agent"), role=ROLE.ASSISTANT)

## ===== PRUNING PRE-QUERY (storia conversazione) =====
#prune_memory(memory, max_turns=10) 

for step in orchestrator_agent.stream_invoke(user_query):

#    if isinstance(step, Plan):
#        step_info = f"STEP: PLAN | AGENT: {orchestrator_agent.name} | {step.content}"
#        memory.add_turn(TextBlock(content=step_info), role=ROLE.ASSISTANT)
#        continue

    if isinstance(step, StepResult):
        if step.tools_used:
            current_agent_name = f"{orchestrator_agent.name} -> {step.tools_used[0].name}"
        else:
            current_agent_name = orchestrator_agent.name

        step_info = f"STEP: {step.index} | AGENT: {current_agent_name}"
        memory.add_turn(TextBlock(content=step_info), role=ROLE.ASSISTANT)

        for block in step.content:
            if hasattr(block, 'arguments'):
                text = f"TOOL CALL: {block.name} ARGS: {block.arguments}"
                memory.add_to_last_turn(TextBlock(content=text))
            elif hasattr(block, 'result'):
                text = f"TOOL RESULT: {block.result}"
                memory.add_to_last_turn(TextBlock(content=text))
            elif hasattr(block, 'content'):
                text = f"TEXT CONTENT: {block.content}"
                memory.add_to_last_turn(TextBlock(content=text))

        # PRUNING INTRA-RUN: ogni N step
        if step.index % 10 == 0:        
            prune_memory(memory, max_turns=5)

    else:
        # È un Plan (o altro tipo sconosciuto) — ispezioniamo cosa contiene
        print(f"\n=== PLAN OBJECT ===")
        print(f"Type: {type(step).__name__}")
        print(f"Attrs: {vars(step)}")  # tutti gli attributi e valori

        step_info = f"STEP: {type(step).__name__} | AGENT: {orchestrator_agent.name} | Attrs: {vars(step)}"
        memory.add_turn(TextBlock(content=step_info), role=ROLE.ASSISTANT)

### Print di utility
print("\n=== JSON RAW ===")
raw_json = memory.json_dumps()
print(raw_json)

def safe_content(block):
    return str(block.get('content', 'N/A'))

print("\n=== MEMORY FORMATTATA ===")
data = json.loads(memory.json_dumps())
for i, turn in enumerate(data):
    print(f"TURN {i+1}: role={turn.get('role')}")
    for j, block in enumerate(turn.get('blocks', [])):
        b_type = block.get('type', 'unknown')
        content_str = safe_content(block)
        print(f"  Block {j+1} ({b_type}): {content_str}")



