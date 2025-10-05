"""
Tests for Slack Share Module
Issue: #41
"""

import pytest
from slack_share import SlackShareHandler, SlackUnfurlBlock


class TestSlackShareHandler:
    """Test suite for SlackShareHandler"""

    @pytest.fixture
    def handler(self):
        """Create a SlackShareHandler instance for testing"""
        return SlackShareHandler(base_url="https://gifdist.io")

    def test_initialization(self, handler):
        """Test handler initialization"""
        assert handler.base_url == "https://gifdist.io"
        assert handler.app_name == "GIFDistributor"

    def test_initialization_strips_trailing_slash(self):
        """Test that trailing slash is removed from base_url"""
        handler = SlackShareHandler(base_url="https://gifdist.io/")
        assert handler.base_url == "https://gifdist.io"

    def test_generate_unfurl_response_basic(self, handler):
        """Test basic unfurl response generation"""
        result = handler.generate_unfurl_response(
            asset_id="abc123", asset_url="https://cdn.gifdist.io/abc123.gif"
        )

        assert "unfurls" in result
        assert "https://gifdist.io/a/abc123" in result["unfurls"]

        unfurl = result["unfurls"]["https://gifdist.io/a/abc123"]
        assert unfurl["title"] == "GIF abc123"
        assert unfurl["title_link"] == "https://gifdist.io/a/abc123"
        assert unfurl["image_url"] == "https://cdn.gifdist.io/abc123.gif"
        assert unfurl["footer"] == "GIFDistributor"
        assert unfurl["color"] == "#FF6B35"

    def test_generate_unfurl_response_with_title(self, handler):
        """Test unfurl response with custom title"""
        result = handler.generate_unfurl_response(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.gif",
            title="Dancing Cat",
        )

        unfurl = result["unfurls"]["https://gifdist.io/a/abc123"]
        assert unfurl["title"] == "Dancing Cat"

    def test_generate_unfurl_response_with_tags(self, handler):
        """Test unfurl response with tags"""
        result = handler.generate_unfurl_response(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.gif",
            tags=["cat", "dancing", "funny"],
        )

        unfurl = result["unfurls"]["https://gifdist.io/a/abc123"]
        assert unfurl["text"] == "Tags: cat, dancing, funny"

    def test_generate_unfurl_response_with_all_params(self, handler):
        """Test unfurl response with all parameters"""
        result = handler.generate_unfurl_response(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.gif",
            title="Dancing Cat",
            tags=["cat", "dancing"],
            file_type="mp4",
        )

        unfurl = result["unfurls"]["https://gifdist.io/a/abc123"]
        assert unfurl["title"] == "Dancing Cat"
        assert unfurl["text"] == "Tags: cat, dancing"

    def test_create_message_attachment_basic(self, handler):
        """Test basic message attachment creation"""
        attachment = handler.create_message_attachment(
            asset_url="https://cdn.gifdist.io/abc123.gif"
        )

        assert attachment["fallback"] == "GIF from GIFDistributor"
        assert attachment["image_url"] == "https://cdn.gifdist.io/abc123.gif"
        assert attachment["color"] == "#FF6B35"

    def test_create_message_attachment_with_title(self, handler):
        """Test message attachment with title"""
        attachment = handler.create_message_attachment(
            asset_url="https://cdn.gifdist.io/abc123.gif", title="Dancing Cat"
        )

        assert attachment["title"] == "Dancing Cat"
        assert attachment["fallback"] == "Dancing Cat"

    def test_create_message_attachment_with_canonical_url(self, handler):
        """Test message attachment with canonical URL"""
        attachment = handler.create_message_attachment(
            asset_url="https://cdn.gifdist.io/abc123.gif",
            canonical_url="https://gifdist.io/a/abc123",
        )

        assert attachment["title_link"] == "https://gifdist.io/a/abc123"

    def test_create_message_attachment_with_tags(self, handler):
        """Test message attachment with tags"""
        attachment = handler.create_message_attachment(
            asset_url="https://cdn.gifdist.io/abc123.gif", tags=["cat", "funny"]
        )

        assert attachment["footer"] == "Tags: cat, funny"

    def test_build_share_message_basic(self, handler):
        """Test basic share message building"""
        message = handler.build_share_message(
            asset_url="https://cdn.gifdist.io/abc123.gif"
        )

        assert "attachments" in message
        assert len(message["attachments"]) == 1
        assert (
            message["attachments"][0]["image_url"]
            == "https://cdn.gifdist.io/abc123.gif"
        )

    def test_build_share_message_with_text(self, handler):
        """Test share message with text"""
        message = handler.build_share_message(
            asset_url="https://cdn.gifdist.io/abc123.gif",
            canonical_url="https://gifdist.io/a/abc123",
            include_text=True,
        )

        assert message["text"] == "https://gifdist.io/a/abc123"

    def test_build_share_message_without_text(self, handler):
        """Test share message without text"""
        message = handler.build_share_message(
            asset_url="https://cdn.gifdist.io/abc123.gif",
            canonical_url="https://gifdist.io/a/abc123",
            include_text=False,
        )

        assert "text" not in message

    def test_create_opengraph_metadata_basic(self, handler):
        """Test basic Open Graph metadata creation"""
        metadata = handler.create_opengraph_metadata(
            asset_id="abc123", asset_url="https://cdn.gifdist.io/abc123.gif"
        )

        assert metadata["og:type"] == "website"
        assert metadata["og:url"] == "https://gifdist.io/a/abc123"
        assert metadata["og:title"] == "GIF abc123"
        assert metadata["og:image"] == "https://cdn.gifdist.io/abc123.gif"
        assert metadata["og:image:type"] == "image/gif"
        assert metadata["og:site_name"] == "GIFDistributor"
        assert "Shared via GIFDistributor" in metadata["og:description"]

    def test_create_opengraph_metadata_with_title(self, handler):
        """Test Open Graph metadata with custom title"""
        metadata = handler.create_opengraph_metadata(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.gif",
            title="Dancing Cat",
        )

        assert metadata["og:title"] == "Dancing Cat"
        assert metadata["twitter:title"] == "Dancing Cat"

    def test_create_opengraph_metadata_with_tags(self, handler):
        """Test Open Graph metadata with tags"""
        metadata = handler.create_opengraph_metadata(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.gif",
            tags=["cat", "dancing"],
        )

        assert "cat, dancing" in metadata["og:description"]

    def test_create_opengraph_metadata_mp4_type(self, handler):
        """Test Open Graph metadata with MP4 file type"""
        metadata = handler.create_opengraph_metadata(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.mp4",
            file_type="mp4",
        )

        assert metadata["og:image:type"] == "video/mp4"

    def test_create_opengraph_metadata_webp_type(self, handler):
        """Test Open Graph metadata with WebP file type"""
        metadata = handler.create_opengraph_metadata(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.webp",
            file_type="webp",
        )

        assert metadata["og:image:type"] == "image/webp"

    def test_create_opengraph_metadata_twitter_card(self, handler):
        """Test Open Graph metadata includes Twitter card data"""
        metadata = handler.create_opengraph_metadata(
            asset_id="abc123",
            asset_url="https://cdn.gifdist.io/abc123.gif",
            title="Dancing Cat",
        )

        assert metadata["twitter:card"] == "summary_large_image"
        assert metadata["twitter:title"] == "Dancing Cat"
        assert metadata["twitter:image"] == "https://cdn.gifdist.io/abc123.gif"

    def test_handle_external_upload(self, handler):
        """Test external upload handler"""
        result = handler.handle_external_upload(
            file_data=b"fake_gif_data",
            filename="test.gif",
            channel_id="C123456",
            title="Test GIF",
            comment="Check this out!",
        )

        assert result["ok"] is True
        assert result["file"]["filename"] == "test.gif"
        assert result["file"]["title"] == "Test GIF"
        assert result["file"]["channels"] == ["C123456"]

    def test_handle_external_upload_without_optional_params(self, handler):
        """Test external upload without optional parameters"""
        result = handler.handle_external_upload(
            file_data=b"fake_gif_data", filename="test.gif", channel_id="C123456"
        )

        assert result["ok"] is True
        assert result["file"]["title"] == "test.gif"

    def test_validate_unfurl_event_valid(self, handler):
        """Test validation of valid unfurl event"""
        event = {
            "type": "link_shared",
            "channel": "C123456",
            "message_ts": "1234567890.123456",
            "links": [{"url": "https://gifdist.io/a/abc123"}],
        }

        assert handler.validate_unfurl_event(event) is True

    def test_validate_unfurl_event_missing_type(self, handler):
        """Test validation fails with missing type"""
        event = {"channel": "C123456", "message_ts": "1234567890.123456", "links": []}

        assert handler.validate_unfurl_event(event) is False

    def test_validate_unfurl_event_wrong_type(self, handler):
        """Test validation fails with wrong event type"""
        event = {
            "type": "message",
            "channel": "C123456",
            "message_ts": "1234567890.123456",
            "links": [],
        }

        assert handler.validate_unfurl_event(event) is False

    def test_validate_unfurl_event_missing_links(self, handler):
        """Test validation fails with missing links"""
        event = {
            "type": "link_shared",
            "channel": "C123456",
            "message_ts": "1234567890.123456",
        }

        assert handler.validate_unfurl_event(event) is False

    def test_validate_unfurl_event_invalid_links_type(self, handler):
        """Test validation fails with invalid links type"""
        event = {
            "type": "link_shared",
            "channel": "C123456",
            "message_ts": "1234567890.123456",
            "links": "not_a_list",
        }

        assert handler.validate_unfurl_event(event) is False

    def test_extract_asset_id_from_canonical_url(self, handler):
        """Test extracting asset ID from canonical URL"""
        url = "https://gifdist.io/a/abc123"
        asset_id = handler.extract_asset_id_from_url(url)

        assert asset_id == "abc123"

    def test_extract_asset_id_from_canonical_url_with_query(self, handler):
        """Test extracting asset ID from URL with query parameters"""
        url = "https://gifdist.io/a/abc123?source=slack"
        asset_id = handler.extract_asset_id_from_url(url)

        assert asset_id == "abc123"

    def test_extract_asset_id_from_canonical_url_with_fragment(self, handler):
        """Test extracting asset ID from URL with fragment"""
        url = "https://gifdist.io/a/abc123#top"
        asset_id = handler.extract_asset_id_from_url(url)

        assert asset_id == "abc123"

    def test_extract_asset_id_from_short_url(self, handler):
        """Test extracting short code from short URL"""
        url = "https://gifdist.io/s/xyz789"
        short_code = handler.extract_asset_id_from_url(url)

        assert short_code == "xyz789"

    def test_extract_asset_id_from_invalid_url(self, handler):
        """Test extracting asset ID from invalid URL"""
        url = "https://gifdist.io/invalid"
        asset_id = handler.extract_asset_id_from_url(url)

        assert asset_id is None

    def test_extract_asset_id_from_external_url(self, handler):
        """Test extracting asset ID from external URL"""
        url = "https://example.com/page"
        asset_id = handler.extract_asset_id_from_url(url)

        assert asset_id is None


class TestSlackUnfurlBlock:
    """Test suite for SlackUnfurlBlock dataclass"""

    def test_unfurl_block_creation_minimal(self):
        """Test creating unfurl block with minimal parameters"""
        block = SlackUnfurlBlock(
            title="Test Title",
            title_link="https://gifdist.io/a/abc123",
            image_url="https://cdn.gifdist.io/abc123.gif",
        )

        assert block.title == "Test Title"
        assert block.title_link == "https://gifdist.io/a/abc123"
        assert block.image_url == "https://cdn.gifdist.io/abc123.gif"
        assert block.text is None
        assert block.footer is None

    def test_unfurl_block_creation_full(self):
        """Test creating unfurl block with all parameters"""
        block = SlackUnfurlBlock(
            title="Test Title",
            title_link="https://gifdist.io/a/abc123",
            image_url="https://cdn.gifdist.io/abc123.gif",
            text="Description text",
            footer="GIFDistributor",
            footer_icon="https://gifdist.io/icon.png",
            ts=1234567890,
        )

        assert block.title == "Test Title"
        assert block.text == "Description text"
        assert block.footer == "GIFDistributor"
        assert block.footer_icon == "https://gifdist.io/icon.png"
        assert block.ts == 1234567890


class TestSlackShareIntegration:
    """Integration tests for Slack share functionality"""

    @pytest.fixture
    def handler(self):
        """Create a SlackShareHandler instance for testing"""
        return SlackShareHandler(base_url="https://gifdist.io")

    def test_full_unfurl_workflow(self, handler):
        """Test complete unfurl workflow"""
        # Simulate receiving a link_shared event
        event = {
            "type": "link_shared",
            "channel": "C123456",
            "message_ts": "1234567890.123456",
            "links": [{"url": "https://gifdist.io/a/abc123"}],
        }

        # Validate event
        assert handler.validate_unfurl_event(event) is True

        # Extract asset ID
        asset_id = handler.extract_asset_id_from_url(event["links"][0]["url"])
        assert asset_id == "abc123"

        # Generate unfurl response
        unfurl = handler.generate_unfurl_response(
            asset_id=asset_id,
            asset_url="https://cdn.gifdist.io/abc123.gif",
            title="Dancing Cat",
            tags=["cat", "funny"],
        )

        # Verify unfurl structure
        assert "unfurls" in unfurl
        assert "https://gifdist.io/a/abc123" in unfurl["unfurls"]

        unfurl_data = unfurl["unfurls"]["https://gifdist.io/a/abc123"]
        assert unfurl_data["title"] == "Dancing Cat"
        assert unfurl_data["text"] == "Tags: cat, funny"

    def test_share_message_with_metadata(self, handler):
        """Test creating share message with Open Graph metadata"""
        asset_id = "abc123"
        asset_url = "https://cdn.gifdist.io/abc123.gif"
        title = "Dancing Cat"
        tags = ["cat", "funny"]

        # Generate message
        message = handler.build_share_message(
            asset_url=asset_url,
            title=title,
            canonical_url=f"https://gifdist.io/a/{asset_id}",
            tags=tags,
            include_text=True,
        )

        # Generate Open Graph metadata
        og_metadata = handler.create_opengraph_metadata(
            asset_id=asset_id, asset_url=asset_url, title=title, tags=tags
        )

        # Verify message structure
        assert message["text"] == "https://gifdist.io/a/abc123"
        assert message["attachments"][0]["title"] == "Dancing Cat"

        # Verify Open Graph metadata
        assert og_metadata["og:title"] == "Dancing Cat"
        assert "cat, funny" in og_metadata["og:description"]
