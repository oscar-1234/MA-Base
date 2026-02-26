from datapizza.tools import tool

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

# === FALLBACK costanti ===
BOOKING_UNAVAILABLE = "Booking data temporarily unavailable — please try again shortly."

# === INNER FUNCTION con retry ===
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),  # 1s → 2s → 4s
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    reraise=False  # non rilancia, gestiamo nel chiamante
)
def _real_book_transfer(mode: str, origin: str, destination: str, when: str) -> str:
    """
    Books a transfer. mode must be 'plane' or 'train'.
    """
    # ── qui andrà la chiamata API reale ──
    # Mock booking result (replace with real integration later)
    return f"TRANSFER BOOKED: {mode.upper()} from {origin} to {destination} on {when} (ref: TRF-001)"


# === FLAG DI TEST (rimuovi in produzione) ===
SIMULATE_FAILURE_COUNT = 0        # contatore interno
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s → 2s → 4s
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
    reraise=False  # non rilancia, gestiamo nel chiamante
)

# === TOOL WRAPPER con fallback ===
@tool
def book_transfer(mode: str, origin: str, destination: str, when: str) -> str:
    """
    Book a passenger transfer based on a chosen travel mode.

    Use this tool when you already know:
    - mode: "plane" or "train"
    - origin: departure city/station/airport (e.g., "Milan")
    - destination: arrival city/station/airport (e.g., "Rome")
    - when: date/time in natural language or ISO-like format (e.g., "tomorrow morning", "2026-03-01 09:00")

    Behavior:
    - Returns a single-line booking confirmation string containing the selected mode, route, date/time,
      and a booking reference id (or an error message if inputs are invalid).
    - This is a mock booking tool (no real purchase); treat the returned reference as the result.

    Validation rules:
    - mode must be exactly "plane" or "train" (case-insensitive).
    - origin, destination, and when must be non-empty.

    Example:
    book_transfer(mode="train", origin="Milan", destination="Rome", when="tomorrow 08:00")
    -> "TRANSFER BOOKED: TRAIN from Milan to Rome on tomorrow 08:00 (ref: TRF-001)"
    """


    mode = (mode or "").strip().lower()
    if mode not in {"plane", "train"}:
        return "Cannot book transfer: mode must be 'plane' or 'train'."

    if not origin or not origin.strip():
        return "Cannot book transfer: origin not specified."
    if not destination or not destination.strip():
        return "Cannot book transfer: destination not specified."
    if not when or not when.strip():
        return "Cannot book transfer: date/time not specified."

    try:
        result = _real_book_transfer(mode=mode, origin=origin, destination=destination, when=when)
#       per SIMULAZIONE FAILURE
#        result = _real_book_transfer_failure
        print(f"[TOOL] ✅ book_transfer({mode}, {origin}, {destination}, {when})")
        return result
    
    except RetryError as e:
        # Tutti e 3 i tentativi falliti
        print(f"[TOOL] ❌ book_transfer failed after 3 attempts: {e}")
        return BOOKING_UNAVAILABLE
    
    except Exception as e:
        # Errore non-transiente (bad input, auth...) → fail fast, no retry
        print(f"[TOOL] ❌ book_transfer unexpected error: {type(e).__name__}: {e}")
        return f"Weather service error: {str(e)}"
