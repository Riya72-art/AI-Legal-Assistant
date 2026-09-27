"""
Ephemeral, in-memory, server-side session store.

This exists only as a placeholder for future multi-turn "Ask Nyaya"
context — nothing currently writes to it. Two things matter if you build
on this:

1. In-memory means it's wiped on every server restart, and won't work
   once you run more than one server process/replica. Swap for Redis
   with a short TTL (e.g. 30 min) before this holds real content —
   keep the TTL short given the sensitivity of what's discussed here.
2. Guest mode is the product's default (see the frontend: "no history by
   default"). This store must never survive a request beyond what's
   needed for the immediate conversation, and the panic-clear endpoint
   (app/routers/safety.py) must be able to wipe any given session
   instantly.
"""
_SESSIONS: dict[str, dict] = {}


def get_session(session_id: str) -> dict | None:
    return _SESSIONS.get(session_id)


def set_session(session_id: str, data: dict) -> None:
    _SESSIONS[session_id] = data


def clear_session(session_id: str) -> bool:
    return _SESSIONS.pop(session_id, None) is not None
