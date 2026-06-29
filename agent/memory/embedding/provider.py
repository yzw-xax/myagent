"""
Embedding providers for memory

Supports OpenAI-compatible embedding vendors:
  - openai     (text-embedding-3-small / large)
  - dashscope  (Aliyun Tongyi text-embedding-v4)
  - custom     (any OpenAI-compatible endpoint)

Custom providers (bot_type "custom" or "custom:<id>") reuse the same
OpenAI-compatible REST client with user-supplied api_key / api_base.

Vendor-specific behaviors (truncation, query instruction prefix) are
configured via metadata.
"""

import hashlib
import math
from abc import ABC, abstractmethod
from typing import List, Optional

# HTTP read timeout for a single embeddings request (seconds). A batch of
# 64+ chunks can take 30-50s end-to-end from China-side networks, so 30s is
# routinely too tight; 90s gives meaningful headroom without letting bad
# endpoints hang forever.
EMBEDDING_HTTP_TIMEOUT = 90


class EmbeddingProvider(ABC):
    """Base class for embedding providers"""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text (treated as a query by default)"""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (treated as documents)"""
        pass

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query string (may apply vendor instruction prefix)"""
        return self.embed(text)

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Effective embedding dimensions"""
        pass


# ---------------------------------------------------------------------------
# Vendor metadata table
# ---------------------------------------------------------------------------
#
# Each entry describes how to reach a vendor's OpenAI-compatible /embeddings
# endpoint.
# Fields:
#   default_base_url        : default API base when not overridden by user
#   default_model           : default embedding model name
#   default_dimensions      : recommended unified dim when explicit path is enabled
#   supports_dim_param      : whether the API accepts a `dimensions` request param
#   needs_client_truncate   : whether to slice + L2-normalize on the client side
#   needs_client_normalize  : whether to L2-normalize on the client (always safe)
#   query_instruction       : optional prefix for asymmetric retrieval
#   max_batch_size          : max texts per /embeddings request; embed_batch
#                             auto-paginates above this. Conservative defaults.
#
EMBEDDING_VENDORS = {
    "openai": {
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "text-embedding-3-small",
        # Match the legacy default so users adding `embedding_provider: openai`
        # to an existing index don't need to rebuild. Override via
        # embedding_dimensions if you want 1024 / 1536 / 3072.
        "default_dimensions": 1536,
        "supports_dim_param": True,
        "needs_client_truncate": False,
        "needs_client_normalize": False,
        "query_instruction": "",
        # OpenAI permits up to 2048 items per request, but a single call
        # carrying hundreds of long chunks routinely exceeds the 30s read
        # timeout from China-side networks. 64 keeps each call well under
        # both the token-per-request budget and a reasonable wall clock.
        "max_batch_size": 64,
    },
    "dashscope": {
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "text-embedding-v4",
        "default_dimensions": 1024,
        "supports_dim_param": True,
        "needs_client_truncate": False,
        "needs_client_normalize": False,
        "query_instruction": "",
        "max_batch_size": 10,  # DashScope hard cap (text-embedding-v4)
    },
    # Custom provider — any OpenAI-compatible /embeddings endpoint. The
    # user must supply api_key + api_base + model via the web console
    # (stored in custom_providers list or legacy custom_api_key / custom_api_base).
    # Dimensions defaults to 1024 but can be overridden via config's
    # embedding_dimensions. No dim-param support assumption — safest
    # default for unknown endpoints.
    "custom": {
        "default_base_url": "",
        "default_model": "",
        "default_dimensions": 1024,
        "supports_dim_param": False,
        "needs_client_truncate": False,
        "needs_client_normalize": True,
        "query_instruction": "",
        "max_batch_size": 64,
    },
}


def _l2_normalize(vec: List[float]) -> List[float]:
    """Normalize a vector to unit length (L2 norm). Returns input on zero vector."""
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI-compatible embedding provider.

    Used for openai/dashscope by configuring the metadata fields. The
    legacy two-arg constructor (model, api_key, api_base) keeps working,
    so the original OpenAI fallback code path is unchanged.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        dimensions: Optional[int] = None,
        supports_dim_param: bool = True,
        needs_client_truncate: bool = False,
        needs_client_normalize: bool = False,
        query_instruction: str = "",
        max_batch_size: int = 256,
    ):
        """
        Args:
            model: Model name (e.g. text-embedding-3-small, text-embedding-v4, embedding-3)
            api_key: API key (required)
            api_base: API base URL (defaults to OpenAI)
            extra_headers: Optional extra HTTP headers
            dimensions: Target output dimension. Required when supports_dim_param
                is False and needs_client_truncate is True (used to slice).
            supports_dim_param: Whether the vendor accepts a `dimensions` body param
            needs_client_truncate: Slice the returned vector to `dimensions`
            needs_client_normalize: L2-normalize on the client after slicing
            query_instruction: Optional prefix prepended to query texts only
            max_batch_size: Max items per /embeddings request; embed_batch
                auto-paginates above this.
        """
        self.model = model
        self.api_key = api_key
        self.api_base = api_base or "https://api.openai.com/v1"
        self.extra_headers = extra_headers or {}
        self.supports_dim_param = supports_dim_param
        self.needs_client_truncate = needs_client_truncate
        self.needs_client_normalize = needs_client_normalize
        self.query_instruction = query_instruction or ""
        self.max_batch_size = max(1, int(max_batch_size or 1))

        if not self.api_key or self.api_key in ["", "YOUR API KEY", "YOUR_API_KEY"]:
            raise ValueError("Embedding API key is not configured")

        if dimensions is not None and dimensions > 0:
            self._dimensions = dimensions
        else:
            # Legacy heuristic for OpenAI text-embedding-3-* family
            self._dimensions = 1536 if "small" in model else 3072

    def _call_api(self, input_data):
        """Call OpenAI-compatible /embeddings endpoint"""
        import requests

        url = f"{self.api_base}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            **self.extra_headers,
        }
        data = {
            "input": input_data,
            "model": self.model,
        }
        if self.supports_dim_param and self._dimensions:
            data["dimensions"] = self._dimensions

        try:
            response = requests.post(url, headers=headers, json=data, timeout=EMBEDDING_HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to embedding API at {url}. "
                f"Please check network and api_base. Error: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Embedding API request timed out. Error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid embedding API key")
            elif e.response.status_code == 429:
                raise ValueError("Embedding API rate limit exceeded")
            else:
                raise ValueError(
                    f"Embedding API request failed: "
                    f"{e.response.status_code} - {e.response.text}"
                )

    def _post_process(self, raw: List[float]) -> List[float]:
        """Apply optional client-side truncation + normalization"""
        vec = raw
        if self.needs_client_truncate and self._dimensions and len(vec) > self._dimensions:
            vec = vec[: self._dimensions]
        if self.needs_client_normalize:
            vec = _l2_normalize(vec)
        return vec

    def embed(self, text: str) -> List[float]:
        """Generate embedding (treated as document by default)"""
        result = self._call_api(text)
        return self._post_process(result["data"][0]["embedding"])

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query (applies vendor instruction prefix if any)"""
        if self.query_instruction:
            text = f"{self.query_instruction}{text}"
        return self.embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents.

        Automatically paginates by self.max_batch_size so callers can pass any
        number of texts. Order of returned vectors matches the input order.
        """
        if not texts:
            return []
        out: List[List[float]] = []
        step = self.max_batch_size
        for i in range(0, len(texts), step):
            chunk = texts[i:i + step]
            result = self._call_api(chunk)
            out.extend(self._post_process(item["embedding"]) for item in result["data"])
        return out

    @property
    def dimensions(self) -> int:
        return self._dimensions


class EmbeddingCache:
    """In-memory cache for embeddings to avoid recomputation"""

    def __init__(self):
        self.cache = {}

    def get(self, text: str, provider: str, model: str) -> Optional[List[float]]:
        key = self._compute_key(text, provider, model)
        return self.cache.get(key)

    def put(self, text: str, provider: str, model: str, embedding: List[float]):
        key = self._compute_key(text, provider, model)
        self.cache[key] = embedding

    @staticmethod
    def _compute_key(text: str, provider: str, model: str) -> str:
        content = f"{provider}:{model}:{text}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def clear(self):
        self.cache.clear()


def create_embedding_provider(
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    extra_headers: Optional[dict] = None,
    dimensions: Optional[int] = None,
) -> EmbeddingProvider:
    """
    Factory function to create an embedding provider.

    Backward compatible: when called with provider="openai"
    and no `dimensions` arg, behaves exactly as before (1536-dim OpenAI).

    Additional providers ("dashscope") require explicit configuration
    and use the unified default dimensions from EMBEDDING_VENDORS.

    Args:
        provider: Vendor key (one of EMBEDDING_VENDORS)
        model: Model name (uses vendor default if None)
        api_key: API key (required)
        api_base: API base URL (uses vendor default if None)
        extra_headers: Optional extra HTTP headers
        dimensions: Target output dimension (uses vendor default if None)

    Returns:
        EmbeddingProvider instance
    """
    meta = EMBEDDING_VENDORS.get(provider)
    if meta is None:
        raise ValueError(
            f"Unsupported embedding provider: {provider}. "
            f"Supported: {sorted(EMBEDDING_VENDORS.keys())}"
        )

    # Legacy two-arg call for openai keeps 1536-dim default behavior
    # so existing data isn't invalidated.
    is_legacy_call = (
        provider == "openai"
        and dimensions is None
    )
    if is_legacy_call:
        return OpenAIEmbeddingProvider(
            model=model or "text-embedding-3-small",
            api_key=api_key,
            api_base=api_base,
            extra_headers=extra_headers,
        )

    final_dim = dimensions if (dimensions and dimensions > 0) else meta["default_dimensions"]
    resolved_model = model or meta["default_model"]
    resolved_base = api_base or meta["default_base_url"]
    # Custom providers require explicit api_base and model — they cannot
    # fall back to OpenAI defaults like built-in vendors do.
    if provider == "custom":
        if not resolved_base:
            raise ValueError("Custom embedding provider requires an api_base URL")
        if not resolved_model:
            raise ValueError("Custom embedding provider requires a model name")
    return OpenAIEmbeddingProvider(
        model=resolved_model,
        api_key=api_key,
        api_base=resolved_base,
        extra_headers=extra_headers,
        dimensions=final_dim,
        supports_dim_param=meta["supports_dim_param"],
        needs_client_truncate=meta["needs_client_truncate"],
        needs_client_normalize=meta["needs_client_normalize"],
        query_instruction=meta["query_instruction"],
        max_batch_size=meta.get("max_batch_size", 256),
    )
