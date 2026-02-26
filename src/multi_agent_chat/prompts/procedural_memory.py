
"""
"Procedural Injection" + "Dynamic Toolset Injection" (o "Task-Conditional Tool Availability")
"""

PROC_MEMORY = {
    "weather": {
        "instruction": """
STANDALONE WEATHER FLOW:
1. Extract location and when from user query.
2. Call weather_agent(location, when).
3. Return concise forecast to user: "Weather in X on Y: Z°C, condition".
STOP HERE. No transfer/booking/parse_weather unless explicitly requested next.
        """,
        "available_agents": [
            "weather_agent(location:str, when:str) → Weather expert with get_weather tool"
        ]
    },

    "transfer_booking": {
        "instruction": """
TRANSFER BOOKING FLOW (ALWAYS weather-dependent):
1. Extract origin, destination, when from query/LTM.
2. Don't overcomplicate: for example, Milan is already a location, you don't need to have a specific pickup point
3. Call weather_agent(location=destination, when=when).
4. Call parse_weather_agent(EXACT full weather string from step 2).
5. mode = "plane" if int(temperature) < 10 else "train".
6. Call transfer_agent(mode, origin, destination, when).
7. Return: "Booked [mode] from X to Y on Z (ref: XXX)".
Ask 1 clarification ONLY if origin/destination/when truly missing.
        """,
        "available_agents": [
            "weather_agent(location:str, when:str) → Weather expert with get_weather tool",
            "parse_weather_agent(weather_string:str) → Extracts temperature °C as integer (returns \"N/A\" if not found)",
            "transfer_agent(mode:str, origin:str, destination:str, when:str) → Books transfer (mode: \"plane\" or \"train\")"
        ]
    },

    "generic": {
        "instruction": """
GENERIC FLOW (no specialization):
1. Think step-by-step about CURRENT request only.
2. NO automatic delegation - answer directly using LTM if relevant.
3. Ask 1 clarification question maximum.
NO weather/transfer/booking workflows unless explicitly requested.
        """,
        "available_agents": []
    }
}