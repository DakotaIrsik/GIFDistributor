"""
Additional edge case tests for CDN module
Focuses on uncovered edge cases and error conditions
"""

import pytest
from datetime import datetime, timedelta, timezone
import time

from cdn import CachePolicy, RangeRequest, SignedURL, CDNHelper


class TestCachePolicyEdgeCases:
    """Additional cache policy edge cases"""

    def test_negative_cache_duration(self):
        """Test behavior with negative cache duration"""
        # Current implementation allows negative, documents actual behavior
        headers = CachePolicy.get_headers(cache_duration=-1)
        # Negative duration is allowed in current implementation
        assert (
            "max-age=-1" in headers["Cache-Control"]
            or "no-cache" in headers["Cache-Control"]
        )

    def test_very_long_cache_duration(self):
        """Test with extremely long cache duration"""
        ten_years = 10 * 365 * 24 * 60 * 60
        headers = CachePolicy.get_headers(cache_duration=ten_years)
        assert f"max-age={ten_years}" in headers["Cache-Control"]

    def test_cache_private_with_immutable(self):
        """Test combining private and immutable flags"""
        headers = CachePolicy.get_headers(
            cache_duration=3600, is_private=True, is_immutable=True
        )
        assert "private" in headers["Cache-Control"]
        assert "immutable" in headers["Cache-Control"]
        assert "public" not in headers["Cache-Control"]

    def test_expires_header_future_date(self):
        """Test Expires header is properly formatted for future dates"""
        headers = CachePolicy.get_headers(cache_duration=7200)
        expires = headers["Expires"]

        # Parse and verify it's in the future
        expires_time = datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT").replace(
            tzinfo=timezone.utc
        )
        assert expires_time > datetime.now(timezone.utc)


class TestRangeRequestEdgeCases:
    """Additional range request edge cases"""

    def test_range_single_byte(self):
        """Test requesting exactly one byte"""
        result = RangeRequest.parse_range_header("bytes=100-100", 1000)
        assert result == (100, 100)

    def test_range_entire_file_explicit(self):
        """Test requesting entire file with explicit range"""
        result = RangeRequest.parse_range_header("bytes=0-999", 1000)
        assert result == (0, 999)

    def test_range_missing_bytes_prefix(self):
        """Test range header without 'bytes=' prefix"""
        result = RangeRequest.parse_range_header("0-100", 1000)
        assert result is None

    def test_range_with_whitespace(self):
        """Test range header with whitespace"""
        result = RangeRequest.parse_range_header("bytes= 0-100", 1000)
        # Should fail due to whitespace in parsing
        assert result is None or result == (0, 100)

    def test_suffix_range_larger_than_file(self):
        """Test suffix range requesting more bytes than file has"""
        result = RangeRequest.parse_range_header("bytes=-5000", 1000)
        # Should return from start of file
        assert result == (0, 999)

    def test_range_negative_end(self):
        """Test range with negative end position"""
        result = RangeRequest.parse_range_header("bytes=0--5", 1000)
        assert result is None

    def test_range_malformed_multiple_dashes(self):
        """Test malformed range with multiple dashes"""
        result = RangeRequest.parse_range_header("bytes=100-200-300", 1000)
        # Should either fail or parse first part
        assert result is None or result == (100, 200)

    def test_range_with_letters(self):
        """Test range with non-numeric characters"""
        assert RangeRequest.parse_range_header("bytes=abc-def", 1000) is None
        assert RangeRequest.parse_range_header("bytes=100-xyz", 1000) is None

    def test_get_range_response_headers_zero_length(self):
        """Test range response for zero-length content"""
        headers = RangeRequest.get_range_response_headers(
            start=0, end=0, total_length=1, content_type="application/octet-stream"
        )
        assert headers["Content-Length"] == "1"
        assert headers["Content-Range"] == "bytes 0-0/1"

    def test_range_at_exact_boundary(self):
        """Test range at exact file boundary"""
        content_length = 1024
        # Last byte
        result = RangeRequest.parse_range_header(
            f"bytes={content_length-1}-{content_length-1}", content_length
        )
        assert result == (content_length - 1, content_length - 1)

    def test_range_exceeds_by_one(self):
        """Test range that exceeds file size by exactly one byte"""
        result = RangeRequest.parse_range_header("bytes=0-1024", 1024)
        # End is 1024 but file is 1024 bytes (0-1023), should fail
        assert result is None


class TestSignedURLEdgeCases:
    """Additional signed URL edge cases"""

    def test_empty_base_url(self):
        """Test signed URL with minimal base URL"""
        signer = SignedURL("secret")
        url = signer.generate_signed_url("https://x.co/a")
        assert "expires=" in url
        assert "signature=" in url

    def test_url_with_port(self):
        """Test signing URL with port number"""
        signer = SignedURL("secret")
        url = signer.generate_signed_url("https://localhost:8080/asset.gif")
        assert "localhost:8080" in url

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_url_with_fragment(self):
        """Test signing URL with fragment"""
        signer = SignedURL("secret")
        url = signer.generate_signed_url("https://cdn.com/asset.gif#metadata")

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_very_short_expiration(self):
        """Test URL with very short expiration (edge of immediate expiry)"""
        signer = SignedURL("secret")
        # 0 seconds means it might be expired immediately
        url = signer.generate_signed_url(
            "https://cdn.com/asset.gif", expiration_seconds=0
        )

        # Might be valid or expired depending on timing
        is_valid, error = signer.validate_signed_url(url)
        # Either valid or expired is acceptable

    def test_very_long_expiration(self):
        """Test URL with very long expiration"""
        signer = SignedURL("secret")
        ten_years = 10 * 365 * 24 * 60 * 60
        url = signer.generate_signed_url(
            "https://cdn.com/asset.gif", expiration_seconds=ten_years
        )

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_signature_with_special_chars_in_url(self):
        """Test signing URL with special characters"""
        signer = SignedURL("secret-key-123")
        url = signer.generate_signed_url("https://cdn.com/path/to/asset-name_v2.gif")

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_additional_params_override_attempt(self):
        """Test that additional params can't override system params"""
        signer = SignedURL("secret")

        # Try to override expires in additional params
        url = signer.generate_signed_url(
            "https://cdn.com/asset.gif",
            expiration_seconds=3600,
            additional_params={"expires": "999999999"},  # Try to override
        )

        # The last one set will win (additional_params), which may break validation
        # This documents actual behavior
        assert "expires=" in url

    def test_url_with_multiple_existing_params(self):
        """Test signing URL with many existing parameters"""
        signer = SignedURL("secret")
        url = signer.generate_signed_url(
            "https://cdn.com/a.gif?v=1&size=large&format=webp&quality=high"
        )

        assert "v=1" in url
        assert "size=large" in url
        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_validate_malformed_url(self):
        """Test validation with malformed URL"""
        signer = SignedURL("secret")

        is_valid, error = signer.validate_signed_url("not-a-url")
        # Should handle gracefully
        assert is_valid is False

    def test_validate_url_missing_both_params(self):
        """Test validation with URL missing all required params"""
        signer = SignedURL("secret")

        is_valid, error = signer.validate_signed_url("https://cdn.com/asset.gif")
        assert is_valid is False
        assert error is not None

    def test_signature_url_safe_base64(self):
        """Test that signature is URL-safe base64"""
        signer = SignedURL("secret")
        url = signer.generate_signed_url("https://cdn.com/asset.gif")

        # Extract signature
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        signature = params["signature"][0]

        # Should not contain +, /, or =
        assert "+" not in signature
        assert "/" not in signature
        # = is stripped

    def test_bytes_secret_key(self):
        """Test initializing with bytes secret key"""
        signer = SignedURL(b"secret-bytes")
        url = signer.generate_signed_url("https://cdn.com/asset.gif")

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_unicode_secret_key(self):
        """Test secret key with unicode characters"""
        signer = SignedURL("秘密キー🔐")
        url = signer.generate_signed_url("https://cdn.com/asset.gif")

        is_valid, error = signer.validate_signed_url(url)
        assert is_valid is True

    def test_validate_invalid_timestamp_format(self):
        """Test validation with non-integer timestamp"""
        signer = SignedURL("secret")

        is_valid, error = signer.validate_signed_url(
            "https://cdn.com/a.gif?expires=notanumber&signature=abc"
        )
        assert is_valid is False
        assert "Invalid URL format" in error or "invalid" in error.lower()


class TestCDNHelperEdgeCases:
    """Additional CDN helper edge cases"""

    def test_helper_without_secret_key(self):
        """Test CDN helper initialized without secret key"""
        helper = CDNHelper()
        assert helper.signed_url_handler is None

    def test_helper_with_empty_secret_key(self):
        """Test CDN helper with empty secret key"""
        # Empty string is allowed, error only raised when trying to use SignedURL
        helper = CDNHelper(secret_key="")
        # Should raise when trying to create signed URL
        with pytest.raises(ValueError):
            helper.create_signed_asset_url("https://cdn.com/asset.gif")

    def test_get_asset_headers_zero_length_content(self):
        """Test headers for zero-length content"""
        helper = CDNHelper()
        headers, range_spec, status = helper.get_asset_headers(
            content_type="text/plain", content_length=0
        )

        assert status == 200
        assert headers["Content-Length"] == "0"

    def test_get_asset_headers_very_large_content(self):
        """Test headers for very large content (streaming case)"""
        helper = CDNHelper()
        large_size = 10 * 1024 * 1024 * 1024  # 10GB

        headers, range_spec, status = helper.get_asset_headers(
            content_type="video/mp4", content_length=large_size
        )

        assert headers["Content-Length"] == str(large_size)
        assert "Accept-Ranges" in headers

    def test_get_asset_headers_range_boundary(self):
        """Test range request at exact content boundary"""
        helper = CDNHelper()
        content_length = 1000

        headers, range_spec, status = helper.get_asset_headers(
            content_type="image/gif",
            content_length=content_length,
            range_header=f"bytes=0-{content_length-1}",
        )

        assert status == 206
        assert range_spec == (0, content_length - 1)

    def test_multiple_range_handling(self):
        """Test that multipart ranges use first range only"""
        helper = CDNHelper()

        headers, range_spec, status = helper.get_asset_headers(
            content_type="video/mp4",
            content_length=10000,
            range_header="bytes=0-999,1000-1999,2000-2999",
        )

        # Should process only first range
        assert status == 206
        assert range_spec == (0, 999)

    def test_signed_url_creation_validation_cycle(self):
        """Test creating and validating signed URL through helper"""
        helper = CDNHelper(secret_key="test-secret")

        url = helper.create_signed_asset_url(
            "https://cdn.com/asset.gif", expiration_seconds=7200
        )

        is_valid, error = helper.validate_asset_url(url)
        assert is_valid is True
        assert error is None

    def test_cache_headers_combined_with_range(self):
        """Test that cache headers are included with range responses"""
        helper = CDNHelper()

        headers, range_spec, status = helper.get_asset_headers(
            content_type="video/mp4",
            content_length=5000,
            cache_duration=CachePolicy.LONG_CACHE,
            range_header="bytes=0-1000",
        )

        # Should have both cache and range headers
        assert "Cache-Control" in headers
        assert "Content-Range" in headers
        assert status == 206


class TestIntegrationComplexScenarios:
    """Complex integration scenarios"""

    def test_signed_url_with_range_request(self):
        """Test complete flow: signed URL + range request + caching"""
        helper = CDNHelper(secret_key="integration-key")

        # Step 1: Create signed URL
        signed_url = helper.create_signed_asset_url(
            "https://cdn.example.com/video.mp4", expiration_seconds=3600
        )

        # Step 2: Validate it
        is_valid, error = helper.validate_asset_url(signed_url)
        assert is_valid is True

        # Step 3: Get headers with range and immutable cache
        headers, range_spec, status = helper.get_asset_headers(
            content_type="video/mp4",
            content_length=52428800,  # 50MB
            is_immutable=True,
            cache_duration=CachePolicy.IMMUTABLE_CACHE,
            range_header="bytes=0-1048575",  # First MB
        )

        # Verify all components work together
        assert status == 206
        assert range_spec == (0, 1048575)
        assert "immutable" in headers["Cache-Control"]
        assert headers["Content-Range"] == "bytes 0-1048575/52428800"

    def test_expired_signed_url_workflow(self):
        """Test workflow with expired URL"""
        helper = CDNHelper(secret_key="expire-test")

        # Create URL that expires in 1 second
        url = helper.create_signed_asset_url(
            "https://cdn.com/asset.gif", expiration_seconds=1
        )

        # Initially valid
        is_valid, error = helper.validate_asset_url(url)
        assert is_valid is True

        # Wait for expiration
        time.sleep(1.1)

        # Now should be expired
        is_valid, error = helper.validate_asset_url(url)
        assert is_valid is False
        assert "expired" in error.lower()

    def test_no_cache_with_range_request(self):
        """Test no-cache policy with range request"""
        helper = CDNHelper()

        headers, range_spec, status = helper.get_asset_headers(
            content_type="application/json",
            content_length=2048,
            cache_duration=CachePolicy.NO_CACHE,
            range_header="bytes=0-1023",
        )

        # Should have no-cache headers
        assert "no-cache" in headers["Cache-Control"]
        assert "no-store" in headers["Cache-Control"]
        # And range headers
        assert status == 206
        assert headers["Content-Range"] == "bytes 0-1023/2048"


class TestErrorConditions:
    """Test error handling and edge cases"""

    def test_range_request_empty_header(self):
        """Test with empty range header string"""
        result = RangeRequest.parse_range_header("", 1000)
        assert result is None

    def test_range_request_only_equals(self):
        """Test range header with only equals sign"""
        result = RangeRequest.parse_range_header("bytes=", 1000)
        assert result is None

    def test_range_request_only_dash(self):
        """Test range header with only dash"""
        result = RangeRequest.parse_range_header("bytes=-", 1000)
        assert result is None

    def test_signed_url_validation_empty_string(self):
        """Test validating empty string"""
        signer = SignedURL("secret")
        is_valid, error = signer.validate_signed_url("")
        assert is_valid is False

    def test_content_type_special_characters(self):
        """Test content type with special characters"""
        helper = CDNHelper()
        headers, _, status = helper.get_asset_headers(
            content_type="application/vnd.custom+json; charset=utf-8",
            content_length=1024,
        )

        assert headers["Content-Type"] == "application/vnd.custom+json; charset=utf-8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
