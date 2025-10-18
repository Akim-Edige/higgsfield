"""Higgsfield provider adapter for API communication."""
import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProviderError(Exception):
    """Base provider error."""

    def __init__(self, message: str, code: str = "PROVIDER_ERROR", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class RateLimitError(ProviderError):
    """Rate limit error."""

    def __init__(self, message: str = "Rate limited"):
        super().__init__(message, code="RATE_LIMITED", retryable=True)


class InvalidParamsError(ProviderError):
    """Invalid parameters error."""

    def __init__(self, message: str = "Invalid parameters"):
        super().__init__(message, code="INVALID_PARAMS", retryable=False)


class HiggsfieldProvider:
    """Higgsfield API provider."""

    def __init__(self):
        self.base_url = settings.HIGGSFIELD_BASE
        self.api_key = settings.HIGGSFIELD_API_KEY
        self.secret = settings.HIGGSFIELD_SECRET
        self.client = httpx.AsyncClient(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "hf-api-key": self.api_key,
            "hf-secret": self.secret,
            "Content-Type": "application/json",
        }

    async def start_generation(self, model_key: str, parameters: dict, prompt: str) -> str:
        """
        Start a generation job.
        
        Args:
            model_key: Model identifier
            parameters: Model-specific parameters
            prompt: Enhanced prompt
        
        Returns:
            provider_job_set_id
        
        Raises:
            ProviderError: On API errors
        """
        url = f"{self.base_url}/v1/models/{model_key}/generate"
        payload = {"params": {**parameters, "prompt": prompt}}

        try:
            logger.info("starting_generation", model_key=model_key, url=url)
            response = await self.client.post(url, headers=self._headers(), json=payload)

            if response.status_code == 429:
                raise RateLimitError("Rate limited by provider")
            elif response.status_code == 400:
                raise InvalidParamsError(f"Invalid params: {response.text}")
            elif response.status_code >= 500:
                # Retryable server error
                raise ProviderError(
                    f"Provider server error: {response.status_code}",
                    code="PROVIDER_SERVER_ERROR",
                    retryable=True,
                )
            elif response.status_code != 200:
                raise ProviderError(
                    f"Provider error: {response.status_code} - {response.text}",
                    code="PROVIDER_ERROR",
                    retryable=False,
                )

            data = response.json()
            job_set_id = data.get("job_set_id") or data.get("id")
            if not job_set_id:
                raise ProviderError("No job_set_id in response", code="INVALID_RESPONSE")

            logger.info("generation_started", job_set_id=job_set_id, model_key=model_key)
            return job_set_id

        except httpx.RequestError as e:
            # Network error - retryable
            raise ProviderError(
                f"Network error: {str(e)}", code="NETWORK_ERROR", retryable=True
            ) from e

    async def get_job_set(self, job_set_id: str) -> dict[str, Any]:
        """
        Get job set status.
        
        Args:
            job_set_id: Provider job set ID
        
        Returns:
            Normalized job set data:
            {
                "status": "queued" | "processing" | "completed" | "failed",
                "results": [{"type": "image|video", "min_url": "...", "raw_url": "..."}]
            }
        
        Raises:
            ProviderError: On API errors
        """
        url = f"{self.base_url}/v1/job-sets/{job_set_id}"

        try:
            response = await self.client.get(url, headers=self._headers())

            if response.status_code == 429:
                raise RateLimitError("Rate limited by provider")
            elif response.status_code >= 500:
                # Retryable server error
                raise ProviderError(
                    f"Provider server error: {response.status_code}",
                    code="PROVIDER_SERVER_ERROR",
                    retryable=True,
                )
            elif response.status_code == 404:
                raise ProviderError("Job set not found", code="JOB_NOT_FOUND", retryable=False)
            elif response.status_code != 200:
                raise ProviderError(
                    f"Provider error: {response.status_code} - {response.text}",
                    code="PROVIDER_ERROR",
                    retryable=False,
                )

            data = response.json()
            return self._normalize_job_set(data)

        except httpx.RequestError as e:
            # Network error - retryable
            raise ProviderError(
                f"Network error: {str(e)}", code="NETWORK_ERROR", retryable=True
            ) from e

    def _normalize_job_set(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize provider response to our internal format.
        
        Provider may return various formats; we normalize to:
        {
            "status": "queued" | "processing" | "completed" | "failed",
            "results": [{"type": "image|video", "min_url": "...", "raw_url": "..."}]
        }
        """
        status = data.get("status", "").lower()
        
        # Map provider status to our normalized status
        status_map = {
            "queued": "queued",
            "pending": "queued",
            "processing": "processing",
            "running": "processing",
            "in_progress": "processing",
            "completed": "completed",
            "succeeded": "completed",
            "success": "completed",
            "failed": "failed",
            "error": "failed",
        }
        normalized_status = status_map.get(status, "queued")

        results = []
        if normalized_status == "completed":
            # Extract results
            raw_results = data.get("results", []) or data.get("outputs", [])
            for r in raw_results:
                result_type = r.get("type", "image")
                min_url = r.get("min_url") or r.get("thumbnail_url") or r.get("url")
                raw_url = r.get("raw_url") or r.get("url")
                results.append({
                    "type": result_type,
                    "min_url": min_url,
                    "raw_url": raw_url,
                })

        return {
            "status": normalized_status,
            "results": results,
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global provider instance
_provider: HiggsfieldProvider | None = None


def get_provider() -> HiggsfieldProvider:
    """Get global provider instance."""
    global _provider
    if _provider is None:
        _provider = HiggsfieldProvider()
    return _provider

