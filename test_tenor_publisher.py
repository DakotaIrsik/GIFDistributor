"""
Unit tests for Tenor Publisher Module
Tests partner flow, upload validation, and tag management
Issue: #28
"""
import pytest
from tenor_publisher import (
    TenorPublisher,
    TenorUploadMetadata,
    TenorContentRating,
    TenorUploadResult
)


class TestTenorPublisher:
    """Test suite for TenorPublisher class"""

    @pytest.fixture
    def publisher(self):
        """Create a test publisher instance"""
        return TenorPublisher(
            api_key="test_api_key_123",
            partner_id="partner_456",
            sfw_only=True
        )

    @pytest.fixture
    def valid_metadata(self):
        """Create valid upload metadata"""
        return TenorUploadMetadata(
            media_url="https://cdn.example.com/test.gif",
            title="Test GIF",
            tags=["funny", "reaction", "test"],
            content_rating=TenorContentRating.HIGH,
            source_id="asset_123"
        )

    def test_publisher_initialization(self):
        """Test publisher is initialized correctly"""
        publisher = TenorPublisher(
            api_key="key123",
            partner_id="partner456"
        )

        assert publisher.api_key == "key123"
        assert publisher.partner_id == "partner456"
        assert publisher.sfw_only is True
        assert publisher.base_url == "https://tenor.googleapis.com/v2"

    def test_publisher_custom_base_url(self):
        """Test publisher with custom base URL"""
        publisher = TenorPublisher(
            api_key="key",
            partner_id="partner",
            base_url="https://custom.api.com/v1/"
        )

        assert publisher.base_url == "https://custom.api.com/v1"

    def test_validate_metadata_success(self, publisher, valid_metadata):
        """Test metadata validation with valid data"""
        is_valid, error = publisher.validate_metadata(valid_metadata)

        assert is_valid is True
        assert error is None

    def test_validate_metadata_invalid_url(self, publisher):
        """Test validation fails with invalid URL"""
        metadata = TenorUploadMetadata(
            media_url="not_a_url",
            title="Test",
            tags=["tag1"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Invalid media URL" in error

    def test_validate_metadata_empty_title(self, publisher):
        """Test validation fails with empty title"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="",
            tags=["tag1"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Title is required" in error

    def test_validate_metadata_title_too_long(self, publisher):
        """Test validation fails with title exceeding 100 characters"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="a" * 101,
            tags=["tag1"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "100 characters or less" in error

    def test_validate_metadata_no_tags(self, publisher):
        """Test validation fails with no tags"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=[]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "At least one tag is required" in error

    def test_validate_metadata_too_many_tags(self, publisher):
        """Test validation fails with too many tags"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=[f"tag{i}" for i in range(21)]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Maximum 20 tags" in error

    def test_validate_metadata_empty_tag(self, publisher):
        """Test validation fails with empty tag"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["valid", "", "another"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Empty tags are not allowed" in error

    def test_validate_metadata_tag_too_long(self, publisher):
        """Test validation fails with tag exceeding 50 characters"""
        long_tag = "a" * 51
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["valid", long_tag]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "exceeds 50 character limit" in error

    def test_validate_metadata_sfw_only_mode(self, publisher):
        """Test validation enforces SFW-only mode"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["test"],
            content_rating=TenorContentRating.MEDIUM
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "SFW-only mode" in error

    def test_validate_metadata_nsfw_allowed(self):
        """Test validation allows non-HIGH rating when SFW mode disabled"""
        publisher = TenorPublisher(
            api_key="key",
            partner_id="partner",
            sfw_only=False
        )

        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["test"],
            content_rating=TenorContentRating.MEDIUM
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is True
        assert error is None

    def test_sanitize_tags_removes_duplicates(self, publisher):
        """Test tag sanitization removes duplicates (case-insensitive)"""
        tags = ["Funny", "funny", "FUNNY", "test", "Test"]
        sanitized = publisher.sanitize_tags(tags)

        assert len(sanitized) == 2
        assert "Funny" in sanitized or "funny" in sanitized
        assert "test" in sanitized or "Test" in sanitized

    def test_sanitize_tags_strips_whitespace(self, publisher):
        """Test tag sanitization strips whitespace"""
        tags = ["  test  ", "funny", "  reaction  "]
        sanitized = publisher.sanitize_tags(tags)

        assert "test" in sanitized
        assert "funny" in sanitized
        assert "reaction" in sanitized
        assert "  test  " not in sanitized

    def test_sanitize_tags_removes_empty(self, publisher):
        """Test tag sanitization removes empty tags"""
        tags = ["test", "", "   ", "funny"]
        sanitized = publisher.sanitize_tags(tags)

        assert len(sanitized) == 2
        assert "test" in sanitized
        assert "funny" in sanitized

    def test_build_upload_payload(self, publisher, valid_metadata):
        """Test building upload payload"""
        payload = publisher.build_upload_payload(valid_metadata)

        assert payload["media_url"] == valid_metadata.media_url
        assert payload["title"] == valid_metadata.title
        assert payload["content_rating"] == "high"
        assert payload["key"] == publisher.api_key
        assert payload["partner_id"] == publisher.partner_id
        assert payload["source_id"] == "asset_123"

    def test_build_upload_payload_sanitizes_tags(self, publisher):
        """Test payload builder sanitizes tags"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["  test  ", "FUNNY", "funny", ""]
        )

        payload = publisher.build_upload_payload(metadata)

        assert len(payload["tags"]) == 2

    def test_upload_success(self, publisher, valid_metadata):
        """Test successful upload"""
        result = publisher.upload(valid_metadata)

        assert result.success is True
        assert result.tenor_id is not None
        assert result.tenor_url is not None
        assert "tenor.com/view/" in result.tenor_url
        assert result.status_code == 200
        assert result.error_message is None

    def test_upload_validation_failure(self, publisher):
        """Test upload fails with invalid metadata"""
        metadata = TenorUploadMetadata(
            media_url="invalid_url",
            title="Test",
            tags=["test"]
        )

        result = publisher.upload(metadata)

        assert result.success is False
        assert result.error_message is not None
        assert "Validation failed" in result.error_message
        assert result.tenor_id is None

    def test_check_upload_status(self, publisher):
        """Test checking upload status"""
        status = publisher.check_upload_status("tenor-abc123")

        assert status["tenor_id"] == "tenor-abc123"
        assert status["status"] == "approved"
        assert "url" in status
        assert "views" in status
        assert "shares" in status

    def test_generate_tenor_search_url(self, publisher):
        """Test generating Tenor search URL"""
        tags = ["funny", "cat", "reaction"]
        url = publisher.generate_tenor_search_url(tags)

        assert "tenor.com/search/" in url
        assert "funny" in url or "cat" in url or "reaction" in url

    def test_format_tags_for_tenor(self, publisher):
        """Test formatting tags for Tenor"""
        tags = ["test", "funny"]
        formatted = publisher.format_tags_for_tenor(tags)

        assert "test" in formatted
        assert "funny" in formatted
        assert "via-gifdistributor" in formatted

    def test_format_tags_for_tenor_no_platform_tags(self, publisher):
        """Test formatting tags without platform tags"""
        tags = ["test", "funny"]
        formatted = publisher.format_tags_for_tenor(tags, include_platform_tags=False)

        assert "test" in formatted
        assert "funny" in formatted
        assert "via-gifdistributor" not in formatted

    def test_estimate_tag_reach(self, publisher):
        """Test estimating tag reach"""
        tags = ["funny", "cat"]
        estimate = publisher.estimate_tag_reach(tags)

        assert "estimated_monthly_searches" in estimate
        assert "competition_level" in estimate
        assert "recommended_tags" in estimate
        assert estimate["tag_count"] == 2

    def test_batch_upload(self, publisher):
        """Test batch upload functionality"""
        uploads = [
            TenorUploadMetadata(
                media_url=f"https://example.com/test{i}.gif",
                title=f"Test {i}",
                tags=[f"tag{i}"]
            )
            for i in range(3)
        ]

        results = publisher.batch_upload(uploads)

        assert len(results) == 3
        assert all(isinstance(r, TenorUploadResult) for r in results)
        assert all(r.success for r in results)

    def test_batch_upload_handles_failures(self, publisher):
        """Test batch upload handles individual failures"""
        uploads = [
            TenorUploadMetadata(
                media_url="https://example.com/valid.gif",
                title="Valid",
                tags=["test"]
            ),
            TenorUploadMetadata(
                media_url="invalid_url",
                title="Invalid",
                tags=["test"]
            )
        ]

        results = publisher.batch_upload(uploads)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    def test_get_partner_stats(self, publisher):
        """Test getting partner statistics"""
        stats = publisher.get_partner_stats()

        assert stats["partner_id"] == publisher.partner_id
        assert "total_uploads" in stats
        assert "total_views" in stats
        assert "total_shares" in stats
        assert "top_tags" in stats
        assert "upload_limit_remaining" in stats


class TestTenorContentRating:
    """Test suite for TenorContentRating enum"""

    def test_content_rating_values(self):
        """Test content rating enum values"""
        assert TenorContentRating.HIGH.value == "high"
        assert TenorContentRating.MEDIUM.value == "medium"
        assert TenorContentRating.LOW.value == "low"


class TestTenorUploadMetadata:
    """Test suite for TenorUploadMetadata dataclass"""

    def test_metadata_creation(self):
        """Test creating upload metadata"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test GIF",
            tags=["funny", "test"]
        )

        assert metadata.media_url == "https://example.com/test.gif"
        assert metadata.title == "Test GIF"
        assert metadata.tags == ["funny", "test"]
        assert metadata.content_rating == TenorContentRating.HIGH

    def test_metadata_with_optional_fields(self):
        """Test metadata with optional fields"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["test"],
            source_id="asset_123",
            source_url="https://source.com/original"
        )

        assert metadata.source_id == "asset_123"
        assert metadata.source_url == "https://source.com/original"


class TestTenorIntegrationScenarios:
    """Integration test scenarios for Tenor publisher"""

    @pytest.fixture
    def publisher(self):
        return TenorPublisher(
            api_key="test_key",
            partner_id="test_partner"
        )

    def test_complete_upload_workflow(self, publisher):
        """Test complete upload workflow from validation to result"""
        metadata = TenorUploadMetadata(
            media_url="https://cdn.example.com/funny-cat.gif",
            title="Funny Cat Reaction",
            tags=["cat", "funny", "reaction", "animal"],
            source_id="asset_abc123"
        )

        # Validate
        is_valid, error = publisher.validate_metadata(metadata)
        assert is_valid is True

        # Upload
        result = publisher.upload(metadata)
        assert result.success is True
        assert result.tenor_id is not None

        # Check status
        status = publisher.check_upload_status(result.tenor_id)
        assert status["tenor_id"] == result.tenor_id

    def test_upload_with_tag_optimization(self, publisher):
        """Test upload with tag formatting and optimization"""
        original_tags = ["  Funny  ", "CAT", "cat", "Reaction"]

        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test GIF",
            tags=original_tags
        )

        # Format tags
        formatted_tags = publisher.format_tags_for_tenor(original_tags)

        # Should remove duplicates and add platform tag
        assert len(formatted_tags) <= len(original_tags) + 1
        assert "via-gifdistributor" in formatted_tags

        # Upload should succeed
        result = publisher.upload(metadata)
        assert result.success is True

    def test_sfw_enforcement_workflow(self, publisher):
        """Test SFW enforcement in upload workflow"""
        metadata = TenorUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["test"],
            content_rating=TenorContentRating.MEDIUM
        )

        # Should fail validation in SFW mode
        is_valid, error = publisher.validate_metadata(metadata)
        assert is_valid is False

        # Upload should fail
        result = publisher.upload(metadata)
        assert result.success is False
        assert "SFW-only" in result.error_message
