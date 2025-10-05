"""
CDN Module for GIF Distributor
Provides cache headers, Range support, and signed URLs
Issue: #34
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import base64
from urllib.parse import urlencode, urlparse, parse_qs


class CachePolicy:
    """Cache control policies for different content types"""

    # Cache durations in seconds
    IMMUTABLE_CACHE = 31536000  # 1 year for immutable assets
    LONG_CACHE = 86400  # 24 hours for stable content
    SHORT_CACHE = 3600  # 1 hour for dynamic content
    NO_CACHE = 0  # No caching

    @staticmethod
    def get_headers(
        cache_duration: int = LONG_CACHE,
        is_immutable: bool = False,
        is_private: bool = False,
    ) -> Dict[str, str]:
        """
        Generate cache control headers

        Args:
            cache_duration: Cache duration in seconds
            is_immutable: Whether the content is immutable
            is_private: Whether the content should only be cached by browsers (not CDN)

        Returns:
            Dictionary of cache-related headers
        """
        if cache_duration == 0:
            return {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }

        cache_control_parts = []

        if is_private:
            cache_control_parts.append("private")
        else:
            cache_control_parts.append("public")

        cache_control_parts.append(f"max-age={cache_duration}")

        if is_immutable:
            cache_control_parts.append("immutable")

        headers = {"Cache-Control": ", ".join(cache_control_parts)}

        # Add Expires header for HTTP/1.0 compatibility
        expires_time = datetime.now(timezone.utc) + timedelta(seconds=cache_duration)
        headers["Expires"] = expires_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        return headers


class RangeRequest:
    """Handles HTTP Range requests for partial content delivery"""

    @staticmethod
    def parse_range_header(
        range_header: str, content_length: int
    ) -> Optional[Tuple[int, int]]:
        """
        Parse HTTP Range header

        Args:
            range_header: The Range header value (e.g., "bytes=0-1023")
            content_length: Total content length in bytes

        Returns:
            Tuple of (start, end) byte positions, or None if invalid
        """
        if not range_header or not range_header.startswith("bytes="):
            return None

        try:
            range_spec = range_header[6:]  # Remove "bytes="

            # Handle single range only (not multipart ranges)
            if "," in range_spec:
                range_spec = range_spec.split(",")[0]

            if "-" not in range_spec:
                return None

            start_str, end_str = range_spec.split("-", 1)

            # Handle different range formats
            if not start_str and not end_str:
                return None
            elif not start_str:
                # Suffix range: last N bytes (e.g., "-500")
                suffix_length = int(end_str)
                start = max(0, content_length - suffix_length)
                end = content_length - 1
            elif not end_str:
                # Range from start to end (e.g., "100-")
                start = int(start_str)
                end = content_length - 1
            else:
                # Full range (e.g., "100-200")
                start = int(start_str)
                end = int(end_str)

            # Validate range
            if start < 0 or end >= content_length or start > end:
                return None

            return (start, end)

        except (ValueError, IndexError):
            return None

    @staticmethod
    def get_range_response_headers(
        start: int,
        end: int,
        total_length: int,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, str]:
        """
        Generate headers for a range response

        Args:
            start: Start byte position
            end: End byte position (inclusive)
            total_length: Total content length
            content_type: MIME type of the content

        Returns:
            Dictionary of response headers
        """
        return {
            "Content-Type": content_type,
            "Content-Length": str(end - start + 1),
            "Content-Range": f"bytes {start}-{end}/{total_length}",
            "Accept-Ranges": "bytes",
        }

    @staticmethod
    def get_full_response_headers(
        total_length: int, content_type: str = "application/octet-stream"
    ) -> Dict[str, str]:
        """
        Generate headers for a full content response

        Args:
            total_length: Total content length
            content_type: MIME type of the content

        Returns:
            Dictionary of response headers
        """
        return {
            "Content-Type": content_type,
            "Content-Length": str(total_length),
            "Accept-Ranges": "bytes",
        }


class SignedURL:
    """Generates and validates signed URLs for secure content delivery"""

    def __init__(self, secret_key: str):
        """
        Initialize with a secret key

        Args:
            secret_key: Secret key for signing URLs
        """
        if not secret_key:
            raise ValueError("Secret key cannot be empty")
        self.secret_key = (
            secret_key.encode() if isinstance(secret_key, str) else secret_key
        )

    def generate_signed_url(
        self,
        base_url: str,
        expiration_seconds: int = 3600,
        additional_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate a signed URL with expiration

        Args:
            base_url: The base URL to sign
            expiration_seconds: Seconds until the URL expires
            additional_params: Additional query parameters to include

        Returns:
            Signed URL string
        """
        # Calculate expiration timestamp
        expires = int(
            (datetime.now(timezone.utc) + timedelta(seconds=expiration_seconds)).timestamp()
        )

        # Parse URL to get path and existing params
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)

        # Flatten params (parse_qs returns lists)
        flat_params = {k: v[0] if isinstance(v, list) else v for k, v in params.items()}

        # Add expiration
        flat_params["expires"] = str(expires)

        # Add any additional parameters
        if additional_params:
            flat_params.update(additional_params)

        # Create signature payload (path + sorted params)
        payload = parsed.path + "?" + urlencode(sorted(flat_params.items()))

        # Generate signature
        signature = hmac.new(self.secret_key, payload.encode(), hashlib.sha256).digest()

        # Base64 encode and make URL-safe
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        # Add signature to params
        flat_params["signature"] = signature_b64

        # Construct final URL
        signed_url = (
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(flat_params)}"
        )

        return signed_url

    def validate_signed_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a signed URL

        Args:
            url: The signed URL to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, None)
            If invalid: (False, error_message)
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Flatten params
            flat_params = {
                k: v[0] if isinstance(v, list) else v for k, v in params.items()
            }

            # Check for required fields
            if "expires" not in flat_params:
                return False, "Missing expiration parameter"

            if "signature" not in flat_params:
                return False, "Missing signature parameter"

            # Extract and remove signature
            provided_signature = flat_params.pop("signature")

            # Check expiration
            expires = int(flat_params["expires"])
            now = int(datetime.now(timezone.utc).timestamp())

            if now >= expires:
                return False, "URL has expired"

            # Recreate payload
            payload = parsed.path + "?" + urlencode(sorted(flat_params.items()))

            # Generate expected signature
            expected_signature = hmac.new(
                self.secret_key, payload.encode(), hashlib.sha256
            ).digest()

            expected_signature_b64 = (
                base64.urlsafe_b64encode(expected_signature).decode().rstrip("=")
            )

            # Compare signatures (constant time comparison)
            if not hmac.compare_digest(provided_signature, expected_signature_b64):
                return False, "Invalid signature"

            return True, None

        except (ValueError, KeyError) as e:
            return False, f"Invalid URL format: {str(e)}"


class CDNHelper:
    """Unified helper for CDN-related functionality"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize CDN helper

        Args:
            secret_key: Secret key for signed URLs (optional)
        """
        self.signed_url_handler = SignedURL(secret_key) if secret_key else None

    def get_asset_headers(
        self,
        content_type: str,
        content_length: int,
        is_immutable: bool = False,
        cache_duration: int = CachePolicy.LONG_CACHE,
        range_header: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Optional[Tuple[int, int]], int]:
        """
        Get complete headers for asset delivery

        Args:
            content_type: MIME type of content
            content_length: Total content length
            is_immutable: Whether content is immutable
            cache_duration: Cache duration in seconds
            range_header: HTTP Range header if present

        Returns:
            Tuple of (headers, range_spec, status_code)
            - headers: Complete response headers
            - range_spec: (start, end) if range request, else None
            - status_code: 200 or 206 (partial content)
        """
        headers = {}
        range_spec = None
        status_code = 200

        # Add cache headers
        cache_headers = CachePolicy.get_headers(
            cache_duration=cache_duration, is_immutable=is_immutable
        )
        headers.update(cache_headers)

        # Handle range requests
        if range_header:
            range_spec = RangeRequest.parse_range_header(range_header, content_length)

            if range_spec:
                start, end = range_spec
                range_headers = RangeRequest.get_range_response_headers(
                    start, end, content_length, content_type
                )
                headers.update(range_headers)
                status_code = 206  # Partial Content
            else:
                # Invalid range, return full content
                full_headers = RangeRequest.get_full_response_headers(
                    content_length, content_type
                )
                headers.update(full_headers)
        else:
            # No range request
            full_headers = RangeRequest.get_full_response_headers(
                content_length, content_type
            )
            headers.update(full_headers)

        return headers, range_spec, status_code

    def create_signed_asset_url(
        self, asset_url: str, expiration_seconds: int = 3600
    ) -> str:
        """
        Create a signed URL for an asset

        Args:
            asset_url: The asset URL to sign
            expiration_seconds: Seconds until expiration

        Returns:
            Signed URL

        Raises:
            ValueError: If signed URL handler is not configured
        """
        if not self.signed_url_handler:
            raise ValueError(
                "Signed URL handler not configured. Provide secret_key during initialization."
            )

        return self.signed_url_handler.generate_signed_url(
            asset_url, expiration_seconds
        )

    def validate_asset_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a signed asset URL

        Args:
            url: The URL to validate

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            ValueError: If signed URL handler is not configured
        """
        if not self.signed_url_handler:
            raise ValueError(
                "Signed URL handler not configured. Provide secret_key during initialization."
            )

        return self.signed_url_handler.validate_signed_url(url)
