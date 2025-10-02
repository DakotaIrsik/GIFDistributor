"""
Tests for Share Links Module
Issue: #40
"""
import pytest
from sharelinks import ShareLinkGenerator, create_asset_hash
import tempfile
import os


class TestShareLinkGenerator:
    """Test cases for ShareLinkGenerator class"""

    def test_initialization(self):
        """Test that generator initializes with default base URL"""
        gen = ShareLinkGenerator()
        assert gen.base_url == "https://gifdist.io"

    def test_custom_base_url(self):
        """Test initialization with custom base URL"""
        gen = ShareLinkGenerator("https://custom.com")
        assert gen.base_url == "https://custom.com"

    def test_base_url_trailing_slash(self):
        """Test that trailing slash is removed from base URL"""
        gen = ShareLinkGenerator("https://custom.com/")
        assert gen.base_url == "https://custom.com"

    def test_generate_short_code(self):
        """Test short code generation"""
        gen = ShareLinkGenerator()
        code = gen.generate_short_code()
        assert len(code) == 8
        assert code.isalnum()

    def test_short_code_uniqueness(self):
        """Test that short codes are unique"""
        gen = ShareLinkGenerator()
        codes = [gen.generate_short_code() for _ in range(100)]
        assert len(codes) == len(set(codes))  # All unique

    def test_create_canonical_url(self):
        """Test canonical URL creation"""
        gen = ShareLinkGenerator()
        url = gen.create_canonical_url("test123")
        assert url == "https://gifdist.io/a/test123"

    def test_create_canonical_url_custom_base(self):
        """Test canonical URL with custom base"""
        gen = ShareLinkGenerator("https://example.com")
        url = gen.create_canonical_url("test456")
        assert url == "https://example.com/a/test456"

    def test_create_share_link_basic(self):
        """Test basic share link creation"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset123")

        assert "short_url" in result
        assert "canonical_url" in result
        assert "short_code" in result
        assert result["canonical_url"] == "https://gifdist.io/a/asset123"
        assert result["short_url"].startswith("https://gifdist.io/s/")

    def test_create_share_link_with_metadata(self):
        """Test share link creation with title and tags"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link(
            "asset456",
            title="Test GIF",
            tags=["funny", "cats"]
        )

        assert result["short_code"] in gen._links_db
        link_data = gen._links_db[result["short_code"]]
        assert link_data["title"] == "Test GIF"
        assert link_data["tags"] == ["funny", "cats"]

    def test_resolve_short_link(self):
        """Test resolving a short link"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset789", title="My GIF")
        short_code = result["short_code"]

        resolved = gen.resolve_short_link(short_code)
        assert resolved is not None
        assert resolved["asset_id"] == "asset789"
        assert resolved["title"] == "My GIF"

    def test_resolve_nonexistent_link(self):
        """Test resolving a link that doesn't exist"""
        gen = ShareLinkGenerator()
        resolved = gen.resolve_short_link("notfound")
        assert resolved is None

    def test_click_tracking(self):
        """Test that clicks are tracked"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset999")
        short_code = result["short_code"]

        # Initial clicks should be 0
        assert gen._links_db[short_code]["clicks"] == 0

        # Resolve link 3 times
        gen.resolve_short_link(short_code)
        gen.resolve_short_link(short_code)
        gen.resolve_short_link(short_code)

        # Clicks should be 3
        assert gen._links_db[short_code]["clicks"] == 3

    def test_generate_hash_based_id(self):
        """Test generating asset ID from hash"""
        gen = ShareLinkGenerator()
        test_hash = "abcdef1234567890" + "0" * 48  # 64 char hash
        asset_id = gen.generate_hash_based_id(test_hash)
        assert asset_id == "abcdef1234567890"
        assert len(asset_id) == 16

    def test_get_share_metadata(self):
        """Test getting metadata for Open Graph tags"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link(
            "asset111",
            title="Epic GIF",
            tags=["awesome", "viral"]
        )

        metadata = gen.get_share_metadata(result["short_code"])
        assert metadata is not None
        assert metadata["title"] == "Epic GIF"
        assert metadata["tags"] == ["awesome", "viral"]
        assert metadata["asset_id"] == "asset111"

    def test_get_share_metadata_default_title(self):
        """Test that default title is used when none provided"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset222")

        metadata = gen.get_share_metadata(result["short_code"])
        assert metadata["title"] == "GIF from GIFDistributor"

    def test_get_share_metadata_nonexistent(self):
        """Test getting metadata for nonexistent link"""
        gen = ShareLinkGenerator()
        metadata = gen.get_share_metadata("notfound")
        assert metadata is None


class TestAssetHash:
    """Test cases for asset hashing"""

    def test_create_asset_hash(self):
        """Test creating hash from file"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("test content")
            temp_path = f.name

        try:
            hash_result = create_asset_hash(temp_path)
            assert len(hash_result) == 64  # SHA-256 hex digest length
            assert hash_result.isalnum()
        finally:
            os.unlink(temp_path)

    def test_create_asset_hash_consistency(self):
        """Test that same content produces same hash"""
        content = b"consistent test data"

        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            f.write(content)
            temp_path = f.name

        try:
            hash1 = create_asset_hash(temp_path)
            hash2 = create_asset_hash(temp_path)
            assert hash1 == hash2
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
