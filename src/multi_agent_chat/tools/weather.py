from datapizza.tools import tool

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

# === FALLBACK costanti ===
WEATHER_UNAVAILABLE = "Weather data temporarily unavailable — please try again shortly."

# === INNER FUNCTION con retry ===
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),  # 1s → 2s → 4s
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    reraise=False  # non rilancia, gestiamo nel chiamante
)
def _fetch_weather(location: str, when: str) -> str:
    """
    Chiamata reale al servizio meteo.
    Tenacity retry su errori transienti (timeout, connessione).
    """
    # ── qui andrà la chiamata API reale ──
    # es: response = requests.get(f"https://api.weather.com/{location}")
    # Per ora mock:
    return f"Weather in {location} on {when}: 10°C, partly cloudy"

# === FLAG DI TEST (rimuovi in produzione) ===
SIMULATE_FAILURE_COUNT = 0        # contatore interno
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s → 2s → 4s
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    reraise=False  # non rilancia, gestiamo nel chiamante
)
def _fetch_weather_failure(location: str, when: str) -> str:    
    # ── SIMULAZIONE FAILURE ──
    global SIMULATE_FAILURE_COUNT

    if  SIMULATE_FAILURE_COUNT < 2:
        SIMULATE_FAILURE_COUNT += 1
        print(f"[TEST] 💥 Simulated TimeoutError (attempt {SIMULATE_FAILURE_COUNT}/3)")
        raise TimeoutError("Simulated connection timeout")
    
    SIMULATE_FAILURE_COUNT = 0
    return f"Weather in {location} on {when}: 10°C, partly cloudy"

# === TOOL WRAPPER con fallback ===
@tool
def get_weather(location: str, when: str) -> str:
    """Retrieves weather information with retry and fallback."""
    if not location or not location.strip():
        return "Cannot retrieve weather: location not specified."
    
    try:
        result = _fetch_weather(location, when)
#       per SIMULAZIONE FAILURE
#        result = _fetch_weather_failure(location, when)
        print(f"[TOOL] ✅ get_weather({location}, {when})")
        return result
    
    except RetryError as e:
        # Tutti e 3 i tentativi falliti
        print(f"[TOOL] ❌ get_weather failed after 3 attempts: {e}")
        return WEATHER_UNAVAILABLE
    
    except Exception as e:
        # Errore non-transiente (bad input, auth...) → fail fast, no retry
        print(f"[TOOL] ❌ get_weather unexpected error: {type(e).__name__}: {e}")
        return f"Weather service error: {str(e)}"
