"""
Comprehensive tests for CDN module
Tests cache headers, Range requests, and signed URLs
"""

import pytest
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import time

from cdn import CachePolicy, RangeRequest, SignedURL, CDNHelper


class TestCachePolicy:
    """Test cache policy header generation"""

    def test_long_cache_public(self):
        """Test long cache policy with public caching"""
        headers = CachePolicy.get_headers(
            cache_duration=CachePolicy.LONG_CACHE, is_immutable=False, is_private=False
        )

        assert "Cache-Control" in headers
        assert "public" in headers["Cache-Control"]
        assert "max-age=86400" in headers["Cache-Control"]
        assert "Expires" in headers

    def test_immutable_cache(self):
        """Test immutable cache policy"""
        headers = CachePolicy.get_headers(
            cache_duration=CachePolicy.IMMUTABLE_CACHE, is_immutable=True
        )

        assert "immutable" in headers["Cache-Control"]
        assert "max-age=31536000" in headers["Cache-Control"]

    def test_private_cache(self):
        """Test private cache policy"""
        headers = CachePolicy.get_headers(cache_duration=3600, is_private=True)

        assert "private" in headers["Cache-Control"]
        assert "public" not in headers["Cache-Control"]

    def test_no_cache(self):
        """Test no-cache policy"""
        headers = CachePolicy.get_headers(cache_duration=0)

        assert "no-cache" in headers["Cache-Control"]
        assert "no-store" in headers["Cache-Control"]
        assert "must-revalidate" in headers["Cache-Control"]
        assert headers["Expires"] == "0"
        assert "Pragma" in headers

    def test_short_cache(self):
        """Test short cache policy"""
        headers = CachePolicy.get_headers(cache_duration=CachePolicy.SHORT_CACHE)

        assert "max-age=3600" in headers["Cache-Control"]

    def test_expires_header_format(self):
        """Test that Expires header has correct format"""
        headers = CachePolicy.get_headers(cache_duration=3600)

        # Should be in HTTP date format
        expires = headers["Expires"]
        assert "GMT" in expires
        # Parse to verify it's valid
        datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT")


class TestRangeRequest:
    """Test HTTP Range request parsing and headers"""

    def test_parse_full_range(self):
        """Test parsing a full range specification"""
        result = RangeRequest.parse_range_header("bytes=0-1023", 2048)

        assert result == (0, 1023)

    def test_parse_range_from_start(self):
        """Test parsing range from start to end"""
        result = RangeRequest.parse_range_header("bytes=1024-", 2048)

        assert result == (1024, 2047)

    def test_parse_suffix_range(self):
        """Test parsing suffix range (last N bytes)"""
        result = RangeRequest.parse_range_header("bytes=-500", 2048)

        assert result == (1548, 2047)

    def test_parse_invalid_range(self):
        """Test invalid range returns None"""
        assert RangeRequest.parse_range_header("bytes=2000-1000", 2048) is None
        assert RangeRequest.parse_range_header("bytes=5000-6000", 2048) is None
        assert RangeRequest.parse_range_header("invalid", 2048) is None
        assert RangeRequest.parse_range_header("bytes=", 2048) is None

    def test_parse_no_range_header(self):
        """Test that missing range header returns None"""
        assert RangeRequest.parse_range_header("", 2048) is None
        assert RangeRequest.parse_range_header(None, 2048) is None

    def test_parse_multipart_range_uses_first(self):
        """Test that multipart ranges use only the first range"""
        result = RangeRequest.parse_range_header("bytes=0-100,200-300", 2048)

        assert result == (0, 100)

    def test_get_range_response_headers(self):
        """Test range response header generation"""
        headers = RangeRequest.get_range_response_headers(
            start=0, end=1023, total_length=2048, content_type="image/gif"
        )

        assert headers["Content-Type"] == "image/gif"
        assert headers["Content-Length"] == "1024"
        assert headers["Content-Range"] == "bytes 0-1023/2048"
        assert headers["Accept-Ranges"] == "bytes"

    def test_get_full_response_headers(self):
        """Test full content response headers"""
        headers = RangeRequest.get_full_response_headers(
            total_length=2048, content_type="video/mp4"
        )

        assert headers["Content-Type"] == "video/mp4"
        assert headers["Content-Length"] == "2048"
        assert headers["Accept-Ranges"] == "bytes"

    def test_range_boundary_conditions(self):
        """Test range parsing at boundaries"""
        # First byte only
        assert RangeRequest.parse_range_header("bytes=0-0", 2048) == (0, 0)

        # Last byte only
        assert RangeRequest.parse_range_header("bytes=2047-2047", 2048) == (2047, 2047)

        # Entire content
        assert RangeRequest.parse_range_header("bytes=0-2047", 2048) == (0, 2047)

    def test_range_edge_cases(self):
        """Test edge cases in range parsing"""
        # Negative start
        assert RangeRequest.parse_range_header("bytes=-1-100", 2048) is None

        # End beyond content length
        assert RangeRequest.parse_range_header("bytes=0-3000", 2048) is None

        # Empty range
        assert RangeRequest.parse_range_header("bytes=-", 2048) is None


class TestSignedURL:
    """Test signed URL generation and validation"""

    def test_generate_signed_url(self):
        """Test basic signed URL generation"""
        signer = SignedURL("test-secret-key")
        url = signer.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=3600
        )

        assert "expires=" in url
        assert "signature=" in url
        assert "https://cdn.example.com/assets/image.gif" in url

    def test_validate_valid_url(self):
        """Test validation of valid signed URL"""
        signer = SignedURL("test-secret-key")
        signed_url = signer.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=3600
        )

        is_valid, error = signer.validate_signed_url(signed_url)

        assert is_valid is True
        assert error is None

    def test_validate_expired_url(self):
        """Test validation of expired URL"""
        signer = SignedURL("test-secret-key")

        # Create URL that expires in 1 second
        signed_url = signer.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=1
        )

        # Wait for expiration
        time.sleep(1.1)

        is_valid, error = signer.validate_signed_url(signed_url)

        assert is_valid is False
        assert "expired" in error.lower()

    def test_validate_tampered_signature(self):
        """Test validation detects tampered signature"""
        signer = SignedURL("test-secret-key")
        signed_url = signer.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=3600
        )

        # Tamper with the signature
        tampered_url = signed_url.replace("signature=", "signature=tampered")

        is_valid, error = signer.validate_signed_url(tampered_url)

        assert is_valid is False
        assert "signature" in error.lower()

    def test_validate_missing_signature(self):
        """Test validation detects missing signature"""
        signer = SignedURL("test-secret-key")

        is_valid, error = signer.validate_signed_url(
            "https://cdn.example.com/assets/image.gif?expires=12345"
        )

        assert is_valid is False
        assert "signature" in error.lower()

    def test_validate_missing_expiration(self):
        """Test validation detects missing expiration"""
        signer = SignedURL("test-secret-key")

        is_valid, error = signer.validate_signed_url(
            "https://cdn.example.com/assets/image.gif?signature=abc123"
        )

        assert is_valid is False
        assert "expiration" in error.lower()

    def test_different_keys_produce_different_signatures(self):
        """Test that different keys produce different signatures"""
        signer1 = SignedURL("key1")
        signer2 = SignedURL("key2")

        url1 = signer1.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=3600
        )
        url2 = signer2.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=3600
        )

        # Extract signatures
        sig1 = parse_qs(urlparse(url1).query)["signature"][0]
        sig2 = parse_qs(urlparse(url2).query)["signature"][0]

        assert sig1 != sig2

    def test_wrong_key_fails_validation(self):
        """Test that wrong key fails validation"""
        signer1 = SignedURL("correct-key")
        signer2 = SignedURL("wrong-key")

        signed_url = signer1.generate_signed_url(
            "https://cdn.example.com/assets/image.gif", expiration_seconds=3600
        )

        is_valid, error = signer2.validate_signed_url(signed_url)

        assert is_valid is False

    def test_additional_params(self):
        """Test signed URL with additional parameters"""
        signer = SignedURL("test-secret-key")
        url = signer.generate_signed_url(
            "https://cdn.example.com/assets/image.gif",
            expiration_seconds=3600,
            additional_params={"width": "500", "quality": "high"},
        )

        assert "width=500" in url
        assert "quality=high" in url

        # Should still validate
        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_empty_secret_key_raises_error(self):
        """Test that empty secret key raises error"""
        with pytest.raises(ValueError, match="Secret key cannot be empty"):
            SignedURL("")

    def test_url_with_existing_params(self):
        """Test signing URL that already has query parameters"""
        signer = SignedURL("test-secret-key")
        url = signer.generate_signed_url(
            "https://cdn.example.com/assets/image.gif?version=2",
            expiration_seconds=3600,
        )

        assert "version=2" in url
        assert "expires=" in url
        assert "signature=" in url

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True


class TestCDNHelper:
    """Test unified CDN helper functionality"""

    def test_get_asset_headers_full_content(self):
        """Test getting headers for full content delivery"""
        helper = CDNHelper()
        headers, range_spec, status = helper.get_asset_headers(
            content_type="image/gif", content_length=2048
        )

        assert status == 200
        assert range_spec is None
        assert headers["Content-Type"] == "image/gif"
        assert headers["Content-Length"] == "2048"
        assert "Cache-Control" in headers

    def test_get_asset_headers_with_range(self):
        """Test getting headers for range request"""
        helper = CDNHelper()
        headers, range_spec, status = helper.get_asset_headers(
            content_type="video/mp4", content_length=4096, range_header="bytes=0-1023"
        )

        assert status == 206  # Partial Content
        assert range_spec == (0, 1023)
        assert headers["Content-Type"] == "video/mp4"
        assert headers["Content-Length"] == "1024"
        assert headers["Content-Range"] == "bytes 0-1023/4096"

    def test_get_asset_headers_immutable(self):
        """Test getting headers for immutable content"""
        helper = CDNHelper()
        headers, range_spec, status = helper.get_asset_headers(
            content_type="image/gif",
            content_length=2048,
            is_immutable=True,
            cache_duration=CachePolicy.IMMUTABLE_CACHE,
        )

        assert "immutable" in headers["Cache-Control"]
        assert "max-age=31536000" in headers["Cache-Control"]

    def test_create_signed_url(self):
        """Test creating signed URL through helper"""
        helper = CDNHelper(secret_key="test-key")
        url = helper.create_signed_asset_url(
            "https://cdn.example.com/asset.gif", expiration_seconds=1800
        )

        assert "signature=" in url
        assert "expires=" in url

    def test_create_signed_url_without_key_raises_error(self):
        """Test that creating signed URL without key raises error"""
        helper = CDNHelper()  # No secret key

        with pytest.raises(ValueError, match="not configured"):
            helper.create_signed_asset_url("https://cdn.example.com/asset.gif")

    def test_validate_url(self):
        """Test validating signed URL through helper"""
        helper = CDNHelper(secret_key="test-key")
        url = helper.create_signed_asset_url("https://cdn.example.com/asset.gif")

        is_valid, error = helper.validate_asset_url(url)

        assert is_valid is True
        assert error is None

    def test_validate_url_without_key_raises_error(self):
        """Test that validating URL without key raises error"""
        helper = CDNHelper()  # No secret key

        with pytest.raises(ValueError, match="not configured"):
            helper.validate_asset_url("https://cdn.example.com/asset.gif?signature=abc")

    def test_invalid_range_returns_full_content(self):
        """Test that invalid range request returns full content"""
        helper = CDNHelper()
        headers, range_spec, status = helper.get_asset_headers(
            content_type="image/gif",
            content_length=2048,
            range_header="bytes=5000-6000",  # Invalid range
        )

        assert status == 200  # Full content, not 206
        assert range_spec is None
        assert headers["Content-Length"] == "2048"


class TestIntegration:
    """Integration tests combining multiple components"""

    def test_full_cdn_workflow(self):
        """Test complete CDN workflow with signed URL and range request"""
        # Initialize helper
        helper = CDNHelper(secret_key="integration-test-key")

        # Create signed URL
        signed_url = helper.create_signed_asset_url(
            "https://cdn.example.com/large-video.mp4", expiration_seconds=3600
        )

        # Validate URL
        is_valid, error = helper.validate_asset_url(signed_url)
        assert is_valid is True

        # Get headers for range request
        headers, range_spec, status = helper.get_asset_headers(
            content_type="video/mp4",
            content_length=10485760,  # 10MB
            range_header="bytes=0-1048575",  # First 1MB
            cache_duration=CachePolicy.LONG_CACHE,
        )

        assert status == 206
        assert range_spec == (0, 1048575)
        assert headers["Content-Range"] == "bytes 0-1048575/10485760"
        assert "Cache-Control" in headers

    def test_immutable_asset_with_signed_url(self):
        """Test serving immutable asset with signed URL"""
        helper = CDNHelper(secret_key="test-key")

        # Create signed URL for immutable asset
        url = helper.create_signed_asset_url(
            "https://cdn.example.com/static/logo-v2.gif",
            expiration_seconds=31536000,  # 1 year
        )

        # Get headers with immutable cache
        headers, _, status = helper.get_asset_headers(
            content_type="image/gif",
            content_length=4096,
            is_immutable=True,
            cache_duration=CachePolicy.IMMUTABLE_CACHE,
        )

        assert status == 200
        assert "immutable" in headers["Cache-Control"]
        assert "max-age=31536000" in headers["Cache-Control"]

    def test_progressive_video_loading(self):
        """Test progressive video loading with range requests"""
        helper = CDNHelper()

        # Simulate video player requesting chunks
        content_length = 20971520  # 20MB video
        chunk_size = 1048576  # 1MB chunks

        for i in range(3):
            start = i * chunk_size
            end = start + chunk_size - 1

            headers, range_spec, status = helper.get_asset_headers(
                content_type="video/mp4",
                content_length=content_length,
                range_header=f"bytes={start}-{end}",
            )

            assert status == 206
            assert range_spec == (start, end)
            assert int(headers["Content-Length"]) == chunk_size
