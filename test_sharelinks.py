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


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_create_asset_hash_empty_file(self):
        """Test hashing an empty file"""
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            temp_path = f.name

        try:
            hash_result = create_asset_hash(temp_path)
            # SHA-256 of empty file is known
            assert len(hash_result) == 64
            assert hash_result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        finally:
            os.unlink(temp_path)

    def test_create_asset_hash_file_not_found(self):
        """Test hashing a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            create_asset_hash("/nonexistent/path/to/file.gif")

    def test_create_asset_hash_large_file(self):
        """Test hashing a large file (tests chunked reading)"""
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            # Write 10MB of data
            f.write(b'x' * (10 * 1024 * 1024))
            temp_path = f.name

        try:
            hash_result = create_asset_hash(temp_path)
            assert len(hash_result) == 64
            assert hash_result.isalnum()
        finally:
            os.unlink(temp_path)

    def test_create_asset_hash_binary_data(self):
        """Test hashing binary GIF-like data"""
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            # GIF header
            f.write(b'GIF89a\x01\x00\x01\x00\x80\x00\x00')
            temp_path = f.name

        try:
            hash_result = create_asset_hash(temp_path)
            assert len(hash_result) == 64
        finally:
            os.unlink(temp_path)

    def test_asset_id_with_special_characters(self):
        """Test canonical URL with special characters in asset ID"""
        gen = ShareLinkGenerator()
        # Test URL-safe characters
        asset_id = "test-123_ABC.xyz"
        url = gen.create_canonical_url(asset_id)
        assert url == "https://gifdist.io/a/test-123_ABC.xyz"

    def test_short_code_character_set(self):
        """Test that short codes only use alphanumeric characters"""
        gen = ShareLinkGenerator()
        for _ in range(50):
            code = gen.generate_short_code()
            # Check each character is alphanumeric
            for char in code:
                assert char in ShareLinkGenerator.ALPHABET

    def test_empty_title_and_tags(self):
        """Test creating share link with empty strings and None"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset123", title="", tags=None)
        link_data = gen._links_db[result["short_code"]]
        assert link_data["title"] == ""
        assert link_data["tags"] == []

    def test_empty_tags_list(self):
        """Test creating share link with empty tags list"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset123", tags=[])
        link_data = gen._links_db[result["short_code"]]
        assert link_data["tags"] == []

    def test_very_long_asset_id(self):
        """Test with very long asset ID"""
        gen = ShareLinkGenerator()
        long_id = "a" * 256
        url = gen.create_canonical_url(long_id)
        assert url == f"https://gifdist.io/a/{long_id}"

    def test_hash_based_id_short_hash(self):
        """Test hash-based ID with hash shorter than 16 chars"""
        gen = ShareLinkGenerator()
        short_hash = "abc123"
        asset_id = gen.generate_hash_based_id(short_hash)
        assert asset_id == "abc123"  # Should return what it can

    def test_created_at_timestamp_format(self):
        """Test that created_at timestamp is in ISO format"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link("asset999")
        link_data = gen._links_db[result["short_code"]]
        created_at = link_data["created_at"]
        # Should be parseable as ISO format
        from datetime import datetime
        parsed_time = datetime.fromisoformat(created_at)
        assert parsed_time is not None


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_full_asset_workflow(self):
        """Test complete workflow: hash file -> generate ID -> create share link -> resolve"""
        # Create test file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            f.write(b"Test GIF content")
            temp_path = f.name

        try:
            # Step 1: Hash the file
            content_hash = create_asset_hash(temp_path)
            assert len(content_hash) == 64

            # Step 2: Generate asset ID from hash
            gen = ShareLinkGenerator()
            asset_id = gen.generate_hash_based_id(content_hash)
            assert len(asset_id) == 16

            # Step 3: Create share link
            result = gen.create_share_link(
                asset_id,
                title="Test GIF",
                tags=["test"]
            )
            assert result["short_code"] is not None

            # Step 4: Resolve the link
            resolved = gen.resolve_short_link(result["short_code"])
            assert resolved["asset_id"] == asset_id
            assert resolved["title"] == "Test GIF"
            assert resolved["clicks"] == 1

            # Step 5: Get metadata
            metadata = gen.get_share_metadata(result["short_code"])
            assert metadata["asset_id"] == asset_id
            assert metadata["canonical_url"] == f"https://gifdist.io/a/{asset_id}"
        finally:
            os.unlink(temp_path)

    def test_duplicate_asset_detection(self):
        """Test that same content generates same asset ID (deduplication)"""
        content = b"Identical content"

        # Create two identical files
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f2:
            f2.write(content)
            path2 = f2.name

        try:
            hash1 = create_asset_hash(path1)
            hash2 = create_asset_hash(path2)

            # Same content should produce same hash
            assert hash1 == hash2

            gen = ShareLinkGenerator()
            id1 = gen.generate_hash_based_id(hash1)
            id2 = gen.generate_hash_based_id(hash2)

            # Same hash should produce same ID
            assert id1 == id2
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_multiple_share_links_same_asset(self):
        """Test creating multiple share links for the same asset"""
        gen = ShareLinkGenerator()
        asset_id = "shared_asset"

        # Create 3 different share links for same asset
        link1 = gen.create_share_link(asset_id, title="Link 1")
        link2 = gen.create_share_link(asset_id, title="Link 2")
        link3 = gen.create_share_link(asset_id, title="Link 3")

        # All should have different short codes
        assert link1["short_code"] != link2["short_code"]
        assert link2["short_code"] != link3["short_code"]
        assert link1["short_code"] != link3["short_code"]

        # But same canonical URL
        assert link1["canonical_url"] == link2["canonical_url"]
        assert link2["canonical_url"] == link3["canonical_url"]

    def test_click_tracking_multiple_links(self):
        """Test click tracking across multiple share links"""
        gen = ShareLinkGenerator()
        link1 = gen.create_share_link("asset1")
        link2 = gen.create_share_link("asset2")

        # Click link1 twice
        gen.resolve_short_link(link1["short_code"])
        gen.resolve_short_link(link1["short_code"])

        # Click link2 once
        gen.resolve_short_link(link2["short_code"])

        # Verify independent tracking
        assert gen._links_db[link1["short_code"]]["clicks"] == 2
        assert gen._links_db[link2["short_code"]]["clicks"] == 1


class TestSecurity:
    """Security-related tests"""

    def test_short_code_entropy(self):
        """Test that short codes have sufficient entropy"""
        gen = ShareLinkGenerator()
        codes = set()
        iterations = 1000

        for _ in range(iterations):
            codes.add(gen.generate_short_code())

        # With 62 chars and 8 positions, collision should be extremely rare
        # Expect 1000 unique codes from 1000 attempts
        assert len(codes) == iterations

    def test_no_sql_injection_in_asset_id(self):
        """Test handling of SQL-like strings in asset IDs"""
        gen = ShareLinkGenerator()
        malicious_id = "'; DROP TABLE assets; --"

        # Should handle without errors
        result = gen.create_share_link(malicious_id)
        assert result["canonical_url"] == f"https://gifdist.io/a/{malicious_id}"

        resolved = gen.resolve_short_link(result["short_code"])
        assert resolved["asset_id"] == malicious_id

    def test_xss_prevention_in_title(self):
        """Test that XSS attempts in titles are stored as-is"""
        gen = ShareLinkGenerator()
        xss_title = "<script>alert('xss')</script>"

        result = gen.create_share_link("asset123", title=xss_title)
        metadata = gen.get_share_metadata(result["short_code"])

        # Title should be stored as-is (escaping is frontend's job)
        assert metadata["title"] == xss_title

    def test_unicode_in_titles_and_tags(self):
        """Test handling of unicode characters"""
        gen = ShareLinkGenerator()
        result = gen.create_share_link(
            "asset_unicode",
            title="🎉 Cool GIF 你好",
            tags=["emoji😀", "中文"]
        )

        metadata = gen.get_share_metadata(result["short_code"])
        assert "🎉" in metadata["title"]
        assert "emoji😀" in metadata["tags"]


class TestPerformance:
    """Performance-related tests"""

    def test_bulk_link_creation(self):
        """Test creating many links quickly"""
        gen = ShareLinkGenerator()
        links = []

        for i in range(100):
            result = gen.create_share_link(f"asset_{i}")
            links.append(result["short_code"])

        # Verify all created successfully
        assert len(links) == 100
        assert len(set(links)) == 100  # All unique

    def test_bulk_resolution(self):
        """Test resolving many links quickly"""
        gen = ShareLinkGenerator()
        codes = []

        # Create 50 links
        for i in range(50):
            result = gen.create_share_link(f"asset_{i}")
            codes.append(result["short_code"])

        # Resolve all
        for code in codes:
            resolved = gen.resolve_short_link(code)
            assert resolved is not None
            assert resolved["clicks"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
