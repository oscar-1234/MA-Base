import json
from datapizza.memory import Memory
from ..memory.ltm import save_to_ltm


def prune_memory(memory: Memory, max_turns: int = 3) -> None:
    """
    Pruning per TURN COMPLETI (SOTA).
    Turn = USER + tutti gli ASSISTANT che seguono fino al prossimo USER.
    """
    data = json.loads(memory.json_dumps())
    turns, current_turn = [], []
    for msg in data:
        if msg["role"] == "user":
            if current_turn:
                turns.append(current_turn)
            current_turn = [msg]
        else:
            current_turn.append(msg)
    if current_turn:
        turns.append(current_turn)

    print(f"\n=== TURNS IDENTIFIED: {len(turns)} (max: {max_turns}) ===")
    if len(turns) <= max_turns:
        return

    expiring_flat = [msg for turn in turns[:-max_turns] for msg in turn]
    if expiring_flat:
        save_to_ltm(expiring_flat)

    window_flat = [msg for turn in turns[-max_turns:] for msg in turn]
    print(f"=== POST PRUNE: {len(window_flat)} messaggi da {len(turns[-max_turns:])} turn ===")
    memory.clear()
    memory.json_loads(json.dumps(window_flat))
