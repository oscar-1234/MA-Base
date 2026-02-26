from datapizza.agents import Agent
from datapizza.memory import Memory

from ..agents.client import client
from ..prompts.system_prompts import (
    ORCHESTRATOR_PROMPT,
    WEATHER_SYSTEM_PROMPT,
    PARSE_WEATHER_SYSTEM_PROMPT,
    TRANSFER_SYSTEMPROMPT
)
from ..tools.weather import get_weather, get_parse_weather
from ..tools.transfer import book_transfer

def create_agents(memory: Memory) -> tuple[Agent, Agent, Agent, Agent]:
    """Factory: crea e collega gli agenti con la memory condivisa."""
    orchestrator = Agent(
        name="orchestrator_agent",
        client=client,
        system_prompt=ORCHESTRATOR_PROMPT,
        memory=memory,
        planning_interval=3,
        stateless=False,
        max_steps=10,
    )
    weather = Agent(
        name="weather_agent",
        client=client,
        system_prompt=WEATHER_SYSTEM_PROMPT,
        tools=[get_weather],
        memory=memory,
        max_steps=5,
    )
    parse_weather = Agent(
        name="parse_weather_agent",
        client=client,
        system_prompt=PARSE_WEATHER_SYSTEM_PROMPT,
        tools=[get_parse_weather],
        memory=memory,
        max_steps=1,  # Semplice, 1-step only
    )
    transfer = Agent(
        name="transfer_agent",
        client=client,
        system_prompt=TRANSFER_SYSTEMPROMPT,
        tools=[book_transfer],
        memory=memory,
        max_steps=5,
    )
    orchestrator.can_call([weather, parse_weather, transfer])

    return orchestrator, weather, parse_weather, transfer
