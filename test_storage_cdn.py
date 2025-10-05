"""
Test suite for storage_cdn.py
Tests object storage, CDN integration, and signed URLs
"""

import os
import sys
import pytest
import tempfile
import shutil
import time
import hashlib
import hmac
import base64
from pathlib import Path
from datetime import datetime, timezone

# Import module
from storage_cdn import (
    StorageBackend,
    CachePolicy,
    StorageConfig,
    ObjectMetadata,
    SignedUrlConfig,
    LocalStorageBackend,
    SignedUrlGenerator,
    CDNManager,
    StorageManager,
)


class TestLocalStorageBackend:
    """Test local filesystem storage backend"""

    @pytest.fixture
    def backend(self, tmp_path):
        """Create local storage backend"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="test-bucket",
            base_path=str(tmp_path / "storage"),
        )
        return LocalStorageBackend(config)

    def test_put_object(self, backend):
        """Test storing object"""
        data = b"Hello, World!"
        metadata = backend.put_object(
            "test/file.txt",
            data,
            content_type="text/plain",
            metadata={"user": "test"},
            cache_control="public, max-age=3600",
        )

        assert metadata.key == "test/file.txt"
        assert metadata.size_bytes == len(data)
        assert metadata.content_type == "text/plain"
        assert metadata.cache_control == "public, max-age=3600"
        assert metadata.custom_metadata == {"user": "test"}
        assert metadata.etag == hashlib.md5(data).hexdigest()

    def test_get_object(self, backend):
        """Test retrieving object"""
        original_data = b"Test content"
        backend.put_object("test.txt", original_data)

        data, metadata = backend.get_object("test.txt")

        assert data == original_data
        assert metadata.key == "test.txt"
        assert metadata.size_bytes == len(original_data)

    def test_get_nonexistent_object(self, backend):
        """Test retrieving non-existent object"""
        with pytest.raises(FileNotFoundError):
            backend.get_object("nonexistent.txt")

    def test_delete_object(self, backend):
        """Test deleting object"""
        backend.put_object("delete-me.txt", b"data")

        assert backend.object_exists("delete-me.txt")
        success = backend.delete_object("delete-me.txt")
        assert success
        assert not backend.object_exists("delete-me.txt")

    def test_delete_nonexistent_object(self, backend):
        """Test deleting non-existent object"""
        success = backend.delete_object("nonexistent.txt")
        assert not success

    def test_list_objects(self, backend):
        """Test listing objects"""
        # Create multiple objects
        backend.put_object("a/file1.txt", b"data1")
        backend.put_object("a/file2.txt", b"data2")
        backend.put_object("b/file3.txt", b"data3")

        # List all
        objects = backend.list_objects()
        assert len(objects) == 3

        # List with prefix
        objects = backend.list_objects(prefix="a/")
        assert len(objects) == 2
        assert all(obj.key.startswith("a/") for obj in objects)

    def test_list_objects_max_keys(self, backend):
        """Test listing objects with max keys limit"""
        # Create many objects
        for i in range(10):
            backend.put_object(f"file{i}.txt", b"data")

        objects = backend.list_objects(max_keys=5)
        assert len(objects) <= 5

    def test_object_exists(self, backend):
        """Test checking object existence"""
        assert not backend.object_exists("test.txt")

        backend.put_object("test.txt", b"data")
        assert backend.object_exists("test.txt")

    def test_metadata_persistence(self, backend):
        """Test that metadata persists"""
        backend.put_object(
            "meta-test.txt",
            b"data",
            content_type="text/plain",
            metadata={"foo": "bar"},
            cache_control="public, max-age=3600",
        )

        data, metadata = backend.get_object("meta-test.txt")

        assert metadata.content_type == "text/plain"
        assert metadata.custom_metadata == {"foo": "bar"}
        assert metadata.cache_control == "public, max-age=3600"

    def test_directory_traversal_protection(self, backend):
        """Test protection against directory traversal"""
        # Try to store outside base path
        backend.put_object("../../../etc/passwd", b"malicious")

        # Should be stored safely within base path
        assert backend.object_exists("../../../etc/passwd")
        # But not actually outside the base path
        full_path = backend._get_full_path("../../../etc/passwd")
        assert backend.base_path in full_path


class TestSignedUrlGenerator:
    """Test signed URL generation and verification"""

    @pytest.fixture
    def generator(self):
        """Create URL signer"""
        return SignedUrlGenerator("test-secret-key")

    def test_generate_signed_url(self, generator):
        """Test generating signed URL"""
        url = generator.generate_signed_url(
            "https://cdn.example.com",
            "test/file.jpg",
            SignedUrlConfig(expires_in_seconds=3600),
        )

        assert "https://cdn.example.com/test%2Ffile.jpg" in url
        assert "expires=" in url
        assert "signature=" in url

    def test_verify_signed_url_valid(self, generator):
        """Test verifying valid signed URL"""
        expires = int(time.time()) + 3600
        key = "test/file.jpg"

        # Generate signature manually
        payload = f"{key}:{expires}"
        signature = hmac.new(
            b"test-secret-key", payload.encode(), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        # Verify
        is_valid = generator.verify_signed_url(key, sig_b64, expires)
        assert is_valid

    def test_verify_signed_url_expired(self, generator):
        """Test verifying expired URL"""
        expires = int(time.time()) - 100  # Expired
        key = "test/file.jpg"

        payload = f"{key}:{expires}"
        signature = hmac.new(
            b"test-secret-key", payload.encode(), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        is_valid = generator.verify_signed_url(key, sig_b64, expires)
        assert not is_valid

    def test_verify_signed_url_invalid_signature(self, generator):
        """Test verifying URL with invalid signature"""
        expires = int(time.time()) + 3600
        key = "test/file.jpg"

        # Use wrong signature
        is_valid = generator.verify_signed_url(key, "invalid-signature", expires)
        assert not is_valid

    def test_signed_url_with_content_type(self, generator):
        """Test signed URL with content type"""
        url = generator.generate_signed_url(
            "https://cdn.example.com",
            "test.jpg",
            SignedUrlConfig(expires_in_seconds=3600, content_type="image/jpeg"),
        )

        assert "content_type=image%2Fjpeg" in url

    def test_signed_url_with_custom_params(self, generator):
        """Test signed URL with custom parameters"""
        url = generator.generate_signed_url(
            "https://cdn.example.com",
            "file.txt",
            SignedUrlConfig(
                expires_in_seconds=3600,
                custom_params={"download": "true", "filename": "myfile.txt"},
            ),
        )

        assert "download=true" in url
        assert "filename=myfile.txt" in url


class TestCDNManager:
    """Test CDN manager"""

    @pytest.fixture
    def cdn(self):
        """Create CDN manager"""
        return CDNManager("cdn.example.com")

    def test_get_cdn_url_https(self, cdn):
        """Test getting HTTPS CDN URL"""
        url = cdn.get_cdn_url("test/file.jpg", use_https=True)
        assert url == "https://cdn.example.com/test%2Ffile.jpg"

    def test_get_cdn_url_http(self, cdn):
        """Test getting HTTP CDN URL"""
        url = cdn.get_cdn_url("test/file.jpg", use_https=False)
        assert url == "http://cdn.example.com/test%2Ffile.jpg"

    def test_get_cdn_url_without_domain(self):
        """Test getting CDN URL without domain configured"""
        cdn = CDNManager(None)
        with pytest.raises(ValueError):
            cdn.get_cdn_url("file.jpg")

    def test_get_cache_headers_public(self, cdn):
        """Test cache headers for public policy"""
        headers = cdn.get_cache_headers(policy=CachePolicy.PUBLIC, max_age=3600)

        assert "Cache-Control" in headers
        assert "public" in headers["Cache-Control"]
        assert "max-age=3600" in headers["Cache-Control"]
        assert "Expires" in headers

    def test_get_cache_headers_private(self, cdn):
        """Test cache headers for private policy"""
        headers = cdn.get_cache_headers(policy=CachePolicy.PRIVATE, max_age=1800)

        assert "private" in headers["Cache-Control"]
        assert "max-age=1800" in headers["Cache-Control"]

    def test_get_cache_headers_no_cache(self, cdn):
        """Test cache headers for no-cache policy"""
        headers = cdn.get_cache_headers(policy=CachePolicy.NO_CACHE)

        assert "no-cache" in headers["Cache-Control"]
        assert "Expires" not in headers

    def test_get_cache_headers_immutable(self, cdn):
        """Test cache headers with immutable flag"""
        headers = cdn.get_cache_headers(
            policy=CachePolicy.IMMUTABLE, max_age=31536000, immutable=True
        )

        assert "immutable" in headers["Cache-Control"]

    def test_get_cache_headers_stale_while_revalidate(self, cdn):
        """Test cache headers with stale-while-revalidate"""
        headers = cdn.get_cache_headers(
            policy=CachePolicy.PUBLIC, max_age=3600, stale_while_revalidate=86400
        )

        assert "stale-while-revalidate=86400" in headers["Cache-Control"]

    def test_invalidate_cache(self, cdn):
        """Test cache invalidation"""
        result = cdn.invalidate_cache(["file1.jpg", "file2.jpg"])

        assert "invalidation_id" in result
        assert result["keys"] == ["file1.jpg", "file2.jpg"]
        assert result["status"] == "pending"


class TestStorageManager:
    """Test high-level storage manager"""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create storage manager"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="test-bucket",
            base_path=str(tmp_path / "storage"),
            cdn_domain="cdn.example.com",
        )
        return StorageManager(config, signing_secret="test-secret")

    def test_upload_object(self, manager):
        """Test uploading object"""
        data = b"Test data"
        metadata = manager.upload(
            "test.txt",
            data,
            content_type="text/plain",
            cache_policy=CachePolicy.PUBLIC,
            max_age=3600,
        )

        assert metadata.key == "test.txt"
        assert metadata.size_bytes == len(data)
        assert metadata.content_type == "text/plain"
        assert metadata.cdn_url == "https://cdn.example.com/test.txt"
        assert "public" in metadata.cache_control
        assert "max-age=3600" in metadata.cache_control

    def test_upload_with_auto_content_type(self, manager):
        """Test uploading with auto content type detection"""
        metadata = manager.upload("image.jpg", b"\xff\xd8\xff\xe0")

        assert metadata.content_type == "image/jpeg"

    def test_download_object(self, manager):
        """Test downloading object"""
        original_data = b"Download test"
        manager.upload("download.txt", original_data)

        data, metadata = manager.download("download.txt")

        assert data == original_data
        assert metadata.key == "download.txt"

    def test_delete_object(self, manager):
        """Test deleting object"""
        manager.upload("delete.txt", b"data")

        assert manager.exists("delete.txt")
        success = manager.delete("delete.txt")
        assert success
        assert not manager.exists("delete.txt")

    def test_list_objects(self, manager):
        """Test listing objects"""
        manager.upload("a/file1.txt", b"data1")
        manager.upload("a/file2.txt", b"data2")
        manager.upload("b/file3.txt", b"data3")

        # List all
        objects = manager.list()
        assert len(objects) == 3
        # All should have CDN URLs
        assert all(obj.cdn_url is not None for obj in objects)

        # List with prefix
        objects = manager.list(prefix="a/")
        assert len(objects) == 2

    def test_generate_signed_url(self, manager):
        """Test generating signed URL"""
        url = manager.generate_signed_url(
            "test.jpg", expires_in=3600, content_type="image/jpeg"
        )

        assert "https://cdn.example.com/test.jpg" in url
        assert "expires=" in url
        assert "signature=" in url
        assert "content_type=image%2Fjpeg" in url

    def test_verify_signed_url(self, manager):
        """Test verifying signed URL"""
        # Generate URL
        url = manager.generate_signed_url("test.jpg", expires_in=3600)

        # Extract parameters (simplified - in real code would parse URL)
        expires = int(time.time()) + 3600

        # Create correct signature
        payload = f"test.jpg:{expires}"
        signature = hmac.new(b"test-secret", payload.encode(), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        # Verify
        is_valid = manager.verify_signed_url("test.jpg", sig_b64, expires)
        assert is_valid

    def test_get_stats(self, manager):
        """Test getting storage statistics"""
        # Upload some files
        manager.upload("file1.txt", b"data1", content_type="text/plain")
        manager.upload("file2.txt", b"data2", content_type="text/plain")
        manager.upload(
            "image.jpg", b"\xff\xd8\xff\xe0" * 100, content_type="image/jpeg"
        )

        stats = manager.get_stats()

        assert stats["total_objects"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["backend"] == "local"
        assert stats["cdn_enabled"] is True
        assert "text/plain" in stats["by_content_type"]
        assert stats["by_content_type"]["text/plain"]["count"] == 2

    def test_upload_with_metadata(self, manager):
        """Test uploading with custom metadata"""
        metadata_dict = {"user_id": "123", "category": "images"}

        obj_meta = manager.upload("meta-test.jpg", b"data", metadata=metadata_dict)

        assert obj_meta.custom_metadata == metadata_dict

        # Verify metadata persists
        data, retrieved_meta = manager.download("meta-test.jpg")
        assert retrieved_meta.custom_metadata == metadata_dict


class TestStorageConfig:
    """Test storage configuration"""

    def test_config_creation(self):
        """Test creating storage config"""
        config = StorageConfig(
            backend=StorageBackend.S3,
            bucket_name="my-bucket",
            region="us-east-1",
            access_key="key",
            secret_key="secret",
            endpoint_url="https://s3.amazonaws.com",
            cdn_domain="cdn.example.com",
        )

        assert config.backend == StorageBackend.S3
        assert config.bucket_name == "my-bucket"
        assert config.region == "us-east-1"
        assert config.cdn_domain == "cdn.example.com"

    def test_config_local_backend(self):
        """Test config for local backend"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="local-bucket",
            base_path="/tmp/storage",
        )

        assert config.backend == StorageBackend.LOCAL
        assert config.base_path == "/tmp/storage"


class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self, tmp_path):
        """Test complete upload, download, and delete workflow"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="test",
            base_path=str(tmp_path / "storage"),
            cdn_domain="cdn.test.com",
        )

        manager = StorageManager(config, signing_secret="integration-test")

        # Upload
        original_data = b"Integration test data"
        upload_meta = manager.upload(
            "integration/test.txt",
            original_data,
            content_type="text/plain",
            cache_policy=CachePolicy.PUBLIC,
            max_age=7200,
            metadata={"test": "integration"},
        )

        assert upload_meta.cdn_url == "https://cdn.test.com/integration%2Ftest.txt"

        # Download
        downloaded_data, download_meta = manager.download("integration/test.txt")
        assert downloaded_data == original_data
        assert download_meta.custom_metadata == {"test": "integration"}

        # Generate signed URL
        signed_url = manager.generate_signed_url(
            "integration/test.txt", expires_in=1800
        )
        assert "expires=" in signed_url
        assert "signature=" in signed_url

        # List
        objects = manager.list(prefix="integration/")
        assert len(objects) == 1
        assert objects[0].key == "integration/test.txt"

        # Delete
        success = manager.delete("integration/test.txt")
        assert success
        assert not manager.exists("integration/test.txt")

    def test_multiple_file_operations(self, tmp_path):
        """Test handling multiple files"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="multi",
            base_path=str(tmp_path / "multi_storage"),
        )

        manager = StorageManager(config)

        # Upload multiple files
        files = [
            ("images/pic1.jpg", b"image1", "image/jpeg"),
            ("images/pic2.jpg", b"image2", "image/jpeg"),
            ("docs/file.txt", b"text", "text/plain"),
            ("videos/clip.mp4", b"video", "video/mp4"),
        ]

        for key, data, content_type in files:
            manager.upload(key, data, content_type=content_type)

        # List all
        all_objects = manager.list()
        assert len(all_objects) == 4

        # List images only
        images = manager.list(prefix="images/")
        assert len(images) == 2
        assert all("images/" in obj.key for obj in images)

        # Get stats
        stats = manager.get_stats()
        assert stats["total_objects"] == 4
        assert "image/jpeg" in stats["by_content_type"]
        assert stats["by_content_type"]["image/jpeg"]["count"] == 2

    def test_cache_policy_variations(self, tmp_path):
        """Test different cache policies"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="cache-test",
            base_path=str(tmp_path / "cache_storage"),
            cdn_domain="cache.cdn.test",
        )

        manager = StorageManager(config)

        # Public cache
        meta1 = manager.upload(
            "public.jpg", b"data", cache_policy=CachePolicy.PUBLIC, max_age=3600
        )
        assert "public" in meta1.cache_control
        assert "max-age=3600" in meta1.cache_control

        # Private cache
        meta2 = manager.upload(
            "private.jpg", b"data", cache_policy=CachePolicy.PRIVATE, max_age=1800
        )
        assert "private" in meta2.cache_control

        # No cache
        meta3 = manager.upload(
            "no-cache.jpg", b"data", cache_policy=CachePolicy.NO_CACHE
        )
        assert "no-cache" in meta3.cache_control


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_file_upload(self, tmp_path):
        """Test uploading empty file"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="edge",
            base_path=str(tmp_path / "edge_storage"),
        )

        manager = StorageManager(config)
        metadata = manager.upload("empty.txt", b"")

        assert metadata.size_bytes == 0

    def test_large_key_name(self, tmp_path):
        """Test handling large key names"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="edge",
            base_path=str(tmp_path / "edge_storage"),
        )

        manager = StorageManager(config)

        # Very long key
        long_key = "a/" * 50 + "file.txt"
        metadata = manager.upload(long_key, b"data")

        assert metadata.key == long_key
        assert manager.exists(long_key)

    def test_special_characters_in_key(self, tmp_path):
        """Test handling special characters in keys"""
        config = StorageConfig(
            backend=StorageBackend.LOCAL,
            bucket_name="special",
            base_path=str(tmp_path / "special_storage"),
        )

        manager = StorageManager(config)

        # Key with special characters
        key = "files/test file (copy) #1.txt"
        metadata = manager.upload(key, b"data")

        assert manager.exists(key)
        data, meta = manager.download(key)
        assert data == b"data"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
