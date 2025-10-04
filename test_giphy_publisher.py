"""
Unit tests for GIPHY Publisher Module
Tests channel management, upload validation, and programmatic upload
Issue: #12
"""
import pytest
from giphy_publisher import (
    GiphyPublisher,
    GiphyUploadMetadata,
    GiphyContentRating,
    GiphyUploadResult,
    GiphyChannel,
    GiphyChannelType
)


class TestGiphyPublisher:
    """Test suite for GiphyPublisher class"""

    @pytest.fixture
    def publisher(self):
        """Create a test publisher instance"""
        return GiphyPublisher(
            api_key="test_api_key_123",
            username="testuser",
            sfw_only=True
        )

    @pytest.fixture
    def valid_metadata(self):
        """Create valid upload metadata"""
        return GiphyUploadMetadata(
            media_url="https://cdn.example.com/test.gif",
            title="Test GIF",
            tags=["funny", "reaction", "test"],
            content_rating=GiphyContentRating.G,
            source_url="https://example.com/source"
        )

    @pytest.fixture
    def test_channel(self):
        """Create a test channel"""
        return GiphyChannel(
            channel_id="channel_123",
            display_name="Test Channel",
            channel_type=GiphyChannelType.BRAND,
            slug="test-channel",
            description="A test channel",
            is_verified=False
        )

    def test_publisher_initialization(self):
        """Test publisher is initialized correctly"""
        publisher = GiphyPublisher(
            api_key="key123",
            username="testuser"
        )

        assert publisher.api_key == "key123"
        assert publisher.username == "testuser"
        assert publisher.sfw_only is True
        assert publisher.base_url == "https://upload.giphy.com/v1"

    def test_publisher_custom_base_url(self):
        """Test publisher with custom base URL"""
        publisher = GiphyPublisher(
            api_key="key",
            username="user",
            base_url="https://custom.api.com/v2/"
        )

        assert publisher.base_url == "https://custom.api.com/v2"

    def test_validate_metadata_success(self, publisher, valid_metadata):
        """Test metadata validation with valid data"""
        is_valid, error = publisher.validate_metadata(valid_metadata)

        assert is_valid is True
        assert error is None

    def test_validate_metadata_invalid_url(self, publisher):
        """Test validation fails with invalid URL"""
        metadata = GiphyUploadMetadata(
            media_url="not_a_url",
            title="Test",
            tags=["tag1"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Invalid media URL" in error

    def test_validate_metadata_empty_title(self, publisher):
        """Test validation fails with empty title"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="",
            tags=["tag1"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Title is required" in error

    def test_validate_metadata_title_too_long(self, publisher):
        """Test validation fails with title exceeding 140 characters"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="a" * 141,
            tags=["tag1"]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "140 characters or less" in error

    def test_validate_metadata_no_tags(self, publisher):
        """Test validation fails with no tags"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=[]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "At least one tag is required" in error

    def test_validate_metadata_too_many_tags(self, publisher):
        """Test validation fails with too many tags"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=[f"tag{i}" for i in range(26)]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Maximum 25 tags allowed" in error

    def test_validate_metadata_tag_too_long(self, publisher):
        """Test validation fails with tag exceeding 50 characters"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["a" * 51]
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "exceeds 50 character limit" in error

    def test_validate_metadata_sfw_only_enforced(self, publisher):
        """Test SFW-only mode rejects R-rated content"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["tag1"],
            content_rating=GiphyContentRating.R
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "G or PG rated content" in error

    def test_validate_metadata_pg_allowed_in_sfw(self, publisher):
        """Test PG rating is allowed in SFW-only mode"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["tag1"],
            content_rating=GiphyContentRating.PG
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is True
        assert error is None

    def test_validate_metadata_invalid_channel(self, publisher):
        """Test validation fails with non-existent channel"""
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Test",
            tags=["tag1"],
            channel_id="nonexistent_channel"
        )

        is_valid, error = publisher.validate_metadata(metadata)

        assert is_valid is False
        assert "Channel" in error and "not found" in error

    def test_sanitize_tags_removes_duplicates(self, publisher):
        """Test tag sanitization removes duplicates"""
        tags = ["funny", "FUNNY", "Funny", "test"]
        sanitized = publisher.sanitize_tags(tags)

        assert len(sanitized) == 2
        assert "funny" in sanitized
        assert "test" in sanitized

    def test_sanitize_tags_removes_empty(self, publisher):
        """Test tag sanitization removes empty tags"""
        tags = ["funny", "", "  ", "test"]
        sanitized = publisher.sanitize_tags(tags)

        assert len(sanitized) == 2
        assert "funny" in sanitized
        assert "test" in sanitized

    def test_sanitize_tags_replaces_spaces(self, publisher):
        """Test tag sanitization replaces spaces with hyphens"""
        tags = ["funny gif", "test tag"]
        sanitized = publisher.sanitize_tags(tags)

        assert "funny-gif" in sanitized
        assert "test-tag" in sanitized

    def test_sanitize_tags_lowercase(self, publisher):
        """Test tag sanitization converts to lowercase"""
        tags = ["FUNNY", "Test", "ReAction"]
        sanitized = publisher.sanitize_tags(tags)

        assert all(tag.islower() for tag in sanitized)

    def test_create_channel_success(self, publisher, test_channel):
        """Test channel creation is successful"""
        result = publisher.create_channel(test_channel)

        assert result is True
        assert test_channel.channel_id in publisher.channels

    def test_create_channel_invalid_data(self, publisher):
        """Test channel creation fails with invalid data"""
        channel = GiphyChannel(
            channel_id="",
            display_name="",
            channel_type=GiphyChannelType.BRAND,
            slug="test"
        )

        result = publisher.create_channel(channel)

        assert result is False

    def test_get_channel_success(self, publisher, test_channel):
        """Test retrieving an existing channel"""
        publisher.create_channel(test_channel)
        retrieved = publisher.get_channel(test_channel.channel_id)

        assert retrieved is not None
        assert retrieved.channel_id == test_channel.channel_id
        assert retrieved.display_name == test_channel.display_name

    def test_get_channel_not_found(self, publisher):
        """Test retrieving a non-existent channel returns None"""
        result = publisher.get_channel("nonexistent")

        assert result is None

    def test_list_channels(self, publisher, test_channel):
        """Test listing all channels"""
        channel2 = GiphyChannel(
            channel_id="channel_456",
            display_name="Second Channel",
            channel_type=GiphyChannelType.ARTIST,
            slug="second-channel"
        )

        publisher.create_channel(test_channel)
        publisher.create_channel(channel2)

        channels = publisher.list_channels()

        assert len(channels) == 2
        assert test_channel in channels
        assert channel2 in channels

    def test_build_upload_payload(self, publisher, valid_metadata):
        """Test building upload payload"""
        payload = publisher.build_upload_payload(valid_metadata)

        assert payload["source_image_url"] == valid_metadata.media_url
        assert payload["title"] == valid_metadata.title
        assert payload["rating"] == valid_metadata.content_rating.value
        assert payload["api_key"] == publisher.api_key
        assert payload["username"] == publisher.username
        assert "tags" in payload

    def test_build_upload_payload_with_channel(self, publisher, valid_metadata, test_channel):
        """Test building upload payload with channel"""
        publisher.create_channel(test_channel)
        valid_metadata.channel_id = test_channel.channel_id

        payload = publisher.build_upload_payload(valid_metadata)

        assert payload["channel_id"] == test_channel.channel_id

    def test_build_upload_payload_with_flags(self, publisher, valid_metadata):
        """Test building upload payload with hidden/private flags"""
        valid_metadata.is_hidden = True
        valid_metadata.is_private = True

        payload = publisher.build_upload_payload(valid_metadata)

        assert payload["is_hidden"] == "true"
        assert payload["is_private"] == "true"

    def test_upload_success(self, publisher, valid_metadata):
        """Test successful upload"""
        result = publisher.upload(valid_metadata)

        assert result.success is True
        assert result.giphy_id is not None
        assert result.giphy_url is not None
        assert result.embed_url is not None
        assert result.status_code == 200
        assert result.error_message is None

    def test_upload_validation_failure(self, publisher):
        """Test upload fails with invalid metadata"""
        metadata = GiphyUploadMetadata(
            media_url="invalid",
            title="Test",
            tags=["tag1"]
        )

        result = publisher.upload(metadata)

        assert result.success is False
        assert result.error_message is not None
        assert "Validation failed" in result.error_message

    def test_upload_generates_unique_ids(self, publisher, valid_metadata):
        """Test multiple uploads generate unique IDs"""
        result1 = publisher.upload(valid_metadata)
        result2 = publisher.upload(valid_metadata)

        assert result1.giphy_id != result2.giphy_id

    def test_check_upload_status(self, publisher):
        """Test checking upload status"""
        status = publisher.check_upload_status("test_id_123")

        assert status["giphy_id"] == "test_id_123"
        assert "status" in status
        assert "url" in status
        assert "views" in status

    def test_generate_giphy_search_url(self, publisher):
        """Test generating GIPHY search URL"""
        url = publisher.generate_giphy_search_url(["funny", "cat"])

        assert "giphy.com/search" in url
        assert "funny" in url or "cat" in url

    def test_format_tags_for_giphy(self, publisher):
        """Test formatting tags for GIPHY"""
        tags = ["Funny", "Test Tag", "REACTION"]
        formatted = publisher.format_tags_for_giphy(tags)

        assert "funny" in formatted
        assert "test-tag" in formatted
        assert "reaction" in formatted

    def test_format_tags_with_platform_tag(self, publisher):
        """Test formatting tags includes platform tag"""
        tags = ["funny"]
        formatted = publisher.format_tags_for_giphy(tags, include_platform_tags=True)

        assert "via-gifdistributor" in formatted

    def test_estimate_tag_reach(self, publisher):
        """Test estimating tag reach"""
        tags = ["funny", "reaction", "test"]
        estimate = publisher.estimate_tag_reach(tags)

        assert "estimated_monthly_searches" in estimate
        assert "competition_level" in estimate
        assert "recommended_tags" in estimate
        assert estimate["tag_count"] == len(tags)

    def test_batch_upload_success(self, publisher):
        """Test batch uploading multiple GIFs"""
        uploads = [
            GiphyUploadMetadata(
                media_url=f"https://example.com/test{i}.gif",
                title=f"Test {i}",
                tags=["test", f"batch{i}"]
            )
            for i in range(3)
        ]

        results = publisher.batch_upload(uploads)

        assert len(results) == 3
        assert all(result.success for result in results)
        assert len(set(r.giphy_id for r in results)) == 3  # All unique

    def test_batch_upload_partial_failure(self, publisher):
        """Test batch upload with some invalid items"""
        uploads = [
            GiphyUploadMetadata(
                media_url="https://example.com/test1.gif",
                title="Valid",
                tags=["test"]
            ),
            GiphyUploadMetadata(
                media_url="invalid_url",
                title="Invalid",
                tags=["test"]
            ),
            GiphyUploadMetadata(
                media_url="https://example.com/test2.gif",
                title="Valid 2",
                tags=["test"]
            )
        ]

        results = publisher.batch_upload(uploads)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    def test_get_user_stats(self, publisher):
        """Test retrieving user statistics"""
        stats = publisher.get_user_stats()

        assert stats["username"] == publisher.username
        assert "total_uploads" in stats
        assert "total_views" in stats
        assert "channel_count" in stats
        assert "upload_limit_remaining" in stats

    def test_get_channel_stats_success(self, publisher, test_channel):
        """Test retrieving channel statistics"""
        publisher.create_channel(test_channel)
        stats = publisher.get_channel_stats(test_channel.channel_id)

        assert stats is not None
        assert stats["channel_id"] == test_channel.channel_id
        assert stats["display_name"] == test_channel.display_name
        assert "total_gifs" in stats
        assert "total_views" in stats

    def test_get_channel_stats_not_found(self, publisher):
        """Test retrieving stats for non-existent channel"""
        stats = publisher.get_channel_stats("nonexistent")

        assert stats is None

    def test_update_gif_metadata_success(self, publisher):
        """Test updating GIF metadata"""
        result = publisher.update_gif_metadata(
            "test_id_123",
            title="New Title",
            tags=["new", "tags"]
        )

        assert result is True

    def test_update_gif_metadata_invalid_id(self, publisher):
        """Test updating GIF with invalid ID"""
        result = publisher.update_gif_metadata("", title="New Title")

        assert result is False

    def test_delete_gif_success(self, publisher):
        """Test deleting a GIF"""
        result = publisher.delete_gif("test_id_123")

        assert result is True

    def test_delete_gif_invalid_id(self, publisher):
        """Test deleting GIF with invalid ID"""
        result = publisher.delete_gif("")

        assert result is False

    def test_get_trending_tags(self, publisher):
        """Test retrieving trending tags"""
        tags = publisher.get_trending_tags(limit=5)

        assert len(tags) == 5
        assert all(isinstance(tag, str) for tag in tags)

    def test_get_trending_tags_default_limit(self, publisher):
        """Test retrieving trending tags with default limit"""
        tags = publisher.get_trending_tags()

        assert len(tags) == 10

    def test_search_similar_gifs(self, publisher):
        """Test searching for similar GIFs"""
        similar = publisher.search_similar_gifs("test_id_123", limit=3)

        assert len(similar) == 3
        assert all("giphy_id" in gif for gif in similar)
        assert all("url" in gif for gif in similar)

    def test_multiple_channels_different_types(self, publisher):
        """Test creating channels of different types"""
        brand_channel = GiphyChannel(
            channel_id="brand_1",
            display_name="Brand Channel",
            channel_type=GiphyChannelType.BRAND,
            slug="brand"
        )
        artist_channel = GiphyChannel(
            channel_id="artist_1",
            display_name="Artist Channel",
            channel_type=GiphyChannelType.ARTIST,
            slug="artist"
        )
        community_channel = GiphyChannel(
            channel_id="community_1",
            display_name="Community Channel",
            channel_type=GiphyChannelType.COMMUNITY,
            slug="community"
        )

        assert publisher.create_channel(brand_channel)
        assert publisher.create_channel(artist_channel)
        assert publisher.create_channel(community_channel)
        assert len(publisher.list_channels()) == 3

    def test_content_rating_values(self):
        """Test content rating enum values"""
        assert GiphyContentRating.G.value == "g"
        assert GiphyContentRating.PG.value == "pg"
        assert GiphyContentRating.PG13.value == "pg-13"
        assert GiphyContentRating.R.value == "r"

    def test_channel_type_values(self):
        """Test channel type enum values"""
        assert GiphyChannelType.BRAND.value == "brand"
        assert GiphyChannelType.ARTIST.value == "artist"
        assert GiphyChannelType.COMMUNITY.value == "community"

    def test_upload_with_all_optional_fields(self, publisher, test_channel):
        """Test upload with all optional metadata fields"""
        publisher.create_channel(test_channel)

        metadata = GiphyUploadMetadata(
            media_url="https://example.com/test.gif",
            title="Complete Test",
            tags=["complete", "test"],
            source_url="https://example.com/source",
            content_rating=GiphyContentRating.PG,
            channel_id=test_channel.channel_id,
            is_hidden=True,
            is_private=True
        )

        result = publisher.upload(metadata)

        assert result.success is True
        assert result.giphy_id is not None


class TestGiphyPublisherIntegration:
    """Integration tests for GiphyPublisher"""

    def test_full_upload_workflow(self):
        """Test complete upload workflow"""
        # Initialize publisher
        publisher = GiphyPublisher(
            api_key="integration_test_key",
            username="testuser"
        )

        # Create a channel
        channel = GiphyChannel(
            channel_id="test_channel",
            display_name="Integration Test Channel",
            channel_type=GiphyChannelType.BRAND,
            slug="integration-test"
        )
        publisher.create_channel(channel)

        # Prepare metadata
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/integration.gif",
            title="Integration Test GIF",
            tags=["integration", "test", "automation"],
            channel_id=channel.channel_id
        )

        # Upload
        result = publisher.upload(metadata)
        assert result.success is True

        # Check status
        status = publisher.check_upload_status(result.giphy_id)
        assert status["giphy_id"] == result.giphy_id

        # Get stats
        user_stats = publisher.get_user_stats()
        assert user_stats["channel_count"] == 1

        channel_stats = publisher.get_channel_stats(channel.channel_id)
        assert channel_stats is not None

    def test_workflow_with_tag_optimization(self):
        """Test workflow with tag formatting and reach estimation"""
        publisher = GiphyPublisher(
            api_key="test_key",
            username="testuser"
        )

        # Analyze tags
        original_tags = ["Funny Cat", "REACTION", "Cute Animals"]
        formatted_tags = publisher.format_tags_for_giphy(original_tags)
        reach = publisher.estimate_tag_reach(formatted_tags)

        # Upload with optimized tags
        metadata = GiphyUploadMetadata(
            media_url="https://example.com/optimized.gif",
            title="Tag Optimized GIF",
            tags=formatted_tags
        )

        result = publisher.upload(metadata)
        assert result.success is True
        assert reach["tag_count"] > 0
