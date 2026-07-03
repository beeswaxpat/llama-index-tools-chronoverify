"""ChronoVerify tool spec."""

import os
from typing import Any, Dict, Optional

import requests

from llama_index.core.tools.tool_spec.base import BaseToolSpec

DEFAULT_BASE_URL = "https://chronoverify.com"
DEFAULT_TIMEOUT = 30.0


class ChronoVerifyToolSpec(BaseToolSpec):
    """
    ChronoVerify image provenance tool spec.

    ChronoVerify (https://chronoverify.com) checks when a photo was taken
    and where it came from. It validates C2PA Content Credentials, reads
    EXIF capture metadata, and runs pixel-level consistency checks, then
    returns a structured verdict with a confidence score.

    ChronoVerify validates provenance. It is not a deepfake or
    AI-generation detector. Treat results as investigative triage,
    not proof.

    Args:
        api_key: ChronoVerify API key (starts with ``cv_live_``). If not
            provided, reads the ``CHRONOVERIFY_API_KEY`` environment
            variable. Without a key, requests use the keyless tier, which
            is free and rate limited. Get a free key by sending an
            ``email`` form field to
            ``POST https://chronoverify.com/v1/keys/free``.
        base_url: API base URL. Defaults to ``https://chronoverify.com``.
        timeout: Request timeout in seconds. Defaults to 30.

    """

    spec_functions = ["verify_image_provenance"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with parameters."""
        self.api_key = api_key or os.environ.get("CHRONOVERIFY_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def verify_image_provenance(
        self,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify when a photo was taken and its provenance.

        Checks an image for C2PA Content Credentials, EXIF capture
        metadata, and pixel-level consistency, and returns a structured
        verdict. Use this to confirm a claimed capture time, to check
        whether an image carries valid signed provenance, or to flag
        metadata anomalies before relying on an image. ChronoVerify
        validates provenance; it is not a deepfake or AI-generation
        detector, and results are investigative triage, not proof.

        Provide exactly one of ``url`` or ``file_path``.

        Args:
            url: Public URL of the image to verify.
            file_path: Local path of an image file to upload and verify.

        Returns:
            The API response as a dict, with keys including ``verdict``
            (one of ``provenance_confirmed``, ``consistent``,
            ``inconclusive``, ``metadata_anomaly``,
            ``manipulation_indicated``), ``confidence`` (0 to 100),
            ``capture_time``, ``capture_device``, ``capture_location``,
            a ``c2pa`` block, and ``integrity`` hashes (sha256, sha512).
            Full schema: https://chronoverify.com/v1/verify.schema.json

        Raises:
            ValueError: If neither or both of ``url`` and ``file_path``
                are provided.
            requests.HTTPError: If the API returns an error status. The
                error detail from the response body is included in the
                message.

        """
        if url is not None and file_path is not None:
            raise ValueError("Provide exactly one of 'url' or 'file_path', not both.")

        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = f"{self.base_url}/v1/verify"

        if url is not None:
            response = requests.post(
                endpoint,
                data={"url": url},
                headers=headers,
                timeout=self.timeout,
            )
        elif file_path is not None:
            with open(file_path, "rb") as file_obj:
                response = requests.post(
                    endpoint,
                    files={"file": (os.path.basename(file_path), file_obj)},
                    headers=headers,
                    timeout=self.timeout,
                )
        else:
            raise ValueError("Provide exactly one of 'url' or 'file_path'.")

        if response.status_code >= 400:
            detail = self._error_detail(response)
            raise requests.HTTPError(
                f"ChronoVerify API error {response.status_code}: {detail}",
                response=response,
            )

        return response.json()

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        """Extract a readable error detail from an error response body."""
        try:
            body = response.json()
        except ValueError:
            return response.text[:500]
        if isinstance(body, dict):
            for key in ("detail", "error", "message"):
                value = body.get(key)
                if value:
                    return str(value)
        return str(body)[:500]
