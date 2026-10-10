"""Paths, the one allowed model, and the limits that keep token use in check."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent
HW5_DIR = BACKEND_DIR.parent
# The key can live in hw5/.env or the course folder's .env (neither is committed).
load_dotenv(HW5_DIR / ".env")
load_dotenv(HW5_DIR.parent / ".env")

PROMPTS_DIR = BACKEND_DIR / "prompts"
DATA_DIR = HW5_DIR / "data"
ORIGINAL_DB = DATA_DIR / "campus_customs.db"
# Env overrides exist only so tests can use scratch copies; normal runs use the defaults.
WORKING_DB = Path(os.getenv("CAMPUS_DB_PATH", DATA_DIR / "campus_customs_new.db"))
MCP_SERVER_SCRIPT = HW5_DIR / "mcp_server" / "server.py"
AUDIT_PATH = Path(os.getenv("CAMPUS_AUDIT_PATH", HW5_DIR / "output" / "audit_trail.json"))

# The assignment allows exactly one model, for every agent. Deliberately not overridable.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# --- Token / loop budget -------------------------------------------------------
# One ticket = one Boss run plus every delegated sub-run. All of them share a single
# usage counter, so these caps apply to the whole ticket, not to each agent.
TICKET_USAGE_LIMITS = UsageLimits(
    request_limit=40,          # model calls across the whole team for one ticket
    tool_calls_limit=80,       # MCP + delegation calls for one ticket
    total_tokens_limit=300_000,
)
MAX_DELEGATION_DEPTH = 2       # boss(0) -> specialist(1) -> specialist(2); depth 2 can't delegate
MAX_DELEGATIONS_PER_TICKET = 8
AUDIT_TEXT_LIMIT = 4000        # truncate long payloads in the audit log


class AgentUnavailable(RuntimeError):
    """The model can't be reached (missing key, network, provider error)."""


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey - the only model any agent uses."""
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentUnavailable("PORTKEY_API_KEY is not set (put it in a .env file).")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={
            "x-portkey-api-key": api_key,
            # Shop data changes as tickets resolve; never answer from Portkey's cache.
            "x-portkey-cache-force-refresh": "true",
        },
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
