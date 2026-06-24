"""Web Search tool. Uses Bocha search backend.

Provider selection
  - strategy 'auto' (default): picks bocha when configured.
  - strategy 'fixed': use the configured provider; if its credential is
    missing at call time, silently fall back to auto order.

Credentials
  - bocha   : tools.web_search.bocha_api_key  ->  env BOCHA_API_KEY
"""

import json
import os
from typing import Any, Dict, List, Optional

import requests

from agent.tools.base_tool import BaseTool, ToolResult
from common.log import logger
from config import conf


DEFAULT_TIMEOUT = 30

# Canonical fallback order.
PROVIDER_ORDER = ("bocha",)

PROVIDER_LABELS = {
    "bocha": "Bocha",
}


def _tools_web_search_conf() -> dict:
    """Return the tools.web_search config block (dict-like)."""
    tools_cfg = conf().get("tools") or {}
    if not isinstance(tools_cfg, dict):
        return {}
    block = tools_cfg.get("web_search") or {}
    return block if isinstance(block, dict) else {}


def _get_api_key(provider: str) -> str:
    """Resolve API key for a provider, with conf -> env fallback."""
    if provider == "bocha":
        key = (_tools_web_search_conf().get("bocha_api_key") or "").strip()
        return key or os.environ.get("BOCHA_API_KEY", "").strip()
    return ""


def configured_providers() -> List[str]:
    """Return configured providers in canonical order."""
    return [p for p in PROVIDER_ORDER if _get_api_key(p)]


def _configured_strategy() -> str:
    return (_tools_web_search_conf().get("strategy") or "auto").strip().lower()


def _configured_provider() -> str:
    return (_tools_web_search_conf().get("provider") or "").strip().lower()


class WebSearch(BaseTool):
    """Tool for searching the web across multiple providers."""

    name: str = "web_search"
    description: str = "Search the web for real-time information. Returns titles, URLs, and snippets."

    params: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string"
            },
            "count": {
                "type": "integer",
                "description": "Number of results to return (1-50, default: 10)"
            },
            "freshness": {
                "type": "string",
                "description": (
                    "Time range filter. Options: "
                    "'noLimit' (default), 'oneDay', 'oneWeek', 'oneMonth', 'oneYear', "
                    "or date range like '2025-01-01..2025-02-01'"
                )
            },
            "summary": {
                "type": "boolean",
                "description": "Whether to include text summary for each result (default: false)"
            }
        },
        "required": ["query"]
    }

    def __init__(self, config: dict = None):
        self.config = config or {}

    @staticmethod
    def is_available() -> bool:
        """Tool is offered to the agent when at least one provider has a key."""
        return bool(configured_providers())

    @classmethod
    def get_json_schema(cls) -> dict:
        """Augment the static schema with a `provider` field — only when the
        user has ≥2 providers configured AND strategy is 'auto'. Otherwise
        the backend picks silently and exposing the field would only waste
        the agent's tokens."""
        schema = {
            "name": cls.name,
            "description": cls.description,
            "parameters": json.loads(json.dumps(cls.params)),  # deep copy
        }
        if _configured_strategy() != "auto":
            return schema
        available = configured_providers()
        if len(available) < 2:
            return schema

        schema["parameters"]["properties"]["provider"] = {
            "type": "string",
            "enum": available,
            "description": "Optional. Specifies the search backend. You may switch between providers when the user wants results from a particular source or from multiple sources.",
        }
        return schema

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------

    def _resolve_provider(self, requested: Optional[str]) -> Optional[str]:
        """Pick a provider for this call.

        Priority: caller-supplied (if configured) > fixed strategy (if
        configured) > first configured in PROVIDER_ORDER. Silent fallback
        when the desired one has no key.
        """
        available = configured_providers()
        if not available:
            return None

        if requested:
            req = requested.strip().lower()
            if req in available:
                return req
            logger.warning(f"[WebSearch] requested provider '{requested}' unavailable, falling back")

        if _configured_strategy() == "fixed":
            pinned = _configured_provider()
            if pinned in available:
                return pinned
            if pinned:
                logger.warning(f"[WebSearch] pinned provider '{pinned}' unavailable, falling back to auto")

        return available[0]

    @staticmethod
    def _resolution_reason(requested: Optional[str], chosen: str) -> str:
        """Human-readable explanation for why `chosen` won the resolver."""
        if requested and requested.strip().lower() == chosen:
            return "caller-requested"
        strategy = _configured_strategy()
        if strategy == "fixed" and _configured_provider() == chosen:
            return "fixed-strategy"
        return "auto-fallback"

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        query = (args.get("query") or "").strip()
        if not query:
            return ToolResult.fail("Error: 'query' parameter is required")

        count = args.get("count", 10)
        freshness = args.get("freshness", "noLimit")
        summary = args.get("summary", False)
        if not isinstance(count, int) or count < 1 or count > 50:
            count = 10

        requested = args.get("provider")
        provider = self._resolve_provider(requested)
        if not provider:
            return ToolResult.fail(
                "Error: No search provider configured. "
                "Configure BOCHA_API_KEY in tools.web_search.bocha_api_key."
            )

        # Always log the routing decision so multi-provider deployments can
        # tell at a glance which backend served any given query.
        available = configured_providers()
        reason = self._resolution_reason(requested, provider)
        q_preview = query if len(query) <= 60 else (query[:57] + "...")
        logger.info(
            f"[WebSearch] provider={provider} reason={reason} "
            f"available={list(available)} query={q_preview!r} count={count} freshness={freshness}"
        )

        try:
            if provider == "bocha":
                return self._search_bocha(query, count, freshness, summary)
            return ToolResult.fail(f"Error: Unknown provider '{provider}'")
        except requests.Timeout:
            return ToolResult.fail(f"Error: Search request timed out after {DEFAULT_TIMEOUT}s")
        except requests.ConnectionError:
            return ToolResult.fail("Error: Failed to connect to search API")
        except Exception as e:
            logger.error(f"[WebSearch] Unexpected error ({provider}): {e}", exc_info=True)
            return ToolResult.fail(f"Error: Search failed - {str(e)}")

    # ------------------------------------------------------------------
    # Bocha
    # ------------------------------------------------------------------

    def _search_bocha(self, query: str, count: int, freshness: str, summary: bool) -> ToolResult:
        api_key = _get_api_key("bocha")
        url = "https://api.bochaai.com/v1/web-search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"query": query, "count": count, "freshness": freshness, "summary": summary}

        logger.debug(f"[WebSearch] bocha: query='{query}', count={count}")
        resp = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)

        if resp.status_code == 401:
            return ToolResult.fail("Error: Invalid bocha API key.")
        if resp.status_code == 403:
            return ToolResult.fail("Error: bocha API — insufficient balance. Top up at https://open.bochaai.com")
        if resp.status_code == 429:
            return ToolResult.fail("Error: bocha API rate limit reached.")
        if resp.status_code != 200:
            return ToolResult.fail(f"Error: bocha API returned HTTP {resp.status_code}")

        data = resp.json()
        api_code = data.get("code")
        if api_code is not None and api_code != 200:
            msg = data.get("msg") or "Unknown error"
            return ToolResult.fail(f"Error: bocha API error (code={api_code}): {msg}")

        pages = (data.get("data") or {}).get("webPages", {}).get("value", []) or []
        results = []
        for p in pages:
            item = {
                "title": p.get("name", ""),
                "url": p.get("url", ""),
                "snippet": p.get("snippet", ""),
                "siteName": p.get("siteName", ""),
                "datePublished": p.get("datePublished") or p.get("dateLastCrawled", ""),
            }
            if p.get("summary"):
                item["summary"] = p["summary"]
            results.append(item)
        total = (data.get("data") or {}).get("webPages", {}).get("totalEstimatedMatches", len(results))
        return ToolResult.success({
            "query": query, "backend": "bocha",
            "total": total, "count": len(results), "results": results,
        })


