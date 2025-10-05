"""
Tests for Microsoft Teams Message Extension
"""

import pytest
from teams_extension import (
    TeamsMessageExtension,
    GIFCard,
    AdaptiveCardBuilder,
    CardType,
    MessageExtensionType,
    TeamsAttachment,
)


@pytest.fixture
def sample_gif():
    """Create a sample GIF card for testing"""
    return GIFCard(
        asset_id="test123",
        title="Funny Cat GIF",
        mp4_url="https://cdn.example.com/test123.mp4",
        gif_url="https://cdn.example.com/test123.gif",
        thumbnail_url="https://cdn.example.com/test123_thumb.jpg",
        canonical_url="https://gifdist.io/a/test123",
        short_url="https://gifdist.io/s/Ab12Cd34",
        file_size=1024000,
        width=480,
        height=270,
        duration_ms=3000,
        tags=["cat", "funny", "pets"],
        description="A hilarious cat doing backflips",
    )


@pytest.fixture
def teams_extension():
    """Create Teams message extension instance"""
    return TeamsMessageExtension(
        app_id="test-app-id",
        app_secret="test-app-secret",
        bot_endpoint="https://bot.example.com/messages",
    )


class TestAdaptiveCardBuilder:
    """Test adaptive card builder"""

    def test_create_preview_card(self, sample_gif):
        """Test creating preview card"""
        card = AdaptiveCardBuilder.create_gif_card(sample_gif, CardType.PREVIEW)

        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.5"
        assert len(card["body"]) == 1
        assert card["body"][0]["type"] == "ColumnSet"

    def test_create_full_card(self, sample_gif):
        """Test creating full card with media"""
        card = AdaptiveCardBuilder.create_gif_card(sample_gif, CardType.FULL)

        assert card["type"] == "AdaptiveCard"
        assert "body" in card
        assert "actions" in card

        # Check for media element
        media_elements = [item for item in card["body"] if item.get("type") == "Media"]
        assert len(media_elements) == 1
        assert media_elements[0]["poster"] == sample_gif.thumbnail_url
        assert media_elements[0]["sources"][0]["url"] == sample_gif.mp4_url

    def test_create_hero_card(self, sample_gif):
        """Test creating hero card"""
        card = AdaptiveCardBuilder.create_gif_card(sample_gif, CardType.HERO)

        assert card["contentType"] == "application/vnd.microsoft.card.hero"
        assert card["content"]["title"] == sample_gif.title
        assert len(card["content"]["buttons"]) == 2

    def test_full_card_includes_tags(self, sample_gif):
        """Test that full card includes tags"""
        card = AdaptiveCardBuilder.create_gif_card(sample_gif, CardType.FULL)

        # Find tags in card body
        tag_blocks = [
            item
            for item in card["body"]
            if item.get("type") == "TextBlock" and "cat" in item.get("text", "")
        ]
        assert len(tag_blocks) > 0

    def test_full_card_includes_description(self, sample_gif):
        """Test that full card includes description"""
        card = AdaptiveCardBuilder.create_gif_card(sample_gif, CardType.FULL)

        # Find description in card body
        desc_blocks = [
            item
            for item in card["body"]
            if item.get("type") == "TextBlock"
            and sample_gif.description in item.get("text", "")
        ]
        assert len(desc_blocks) > 0

    def test_full_card_without_description(self):
        """Test full card when description is empty"""
        gif = GIFCard(
            asset_id="test456",
            title="Test GIF",
            mp4_url="https://cdn.example.com/test.mp4",
            gif_url="https://cdn.example.com/test.gif",
            thumbnail_url="https://cdn.example.com/test_thumb.jpg",
            canonical_url="https://gifdist.io/a/test456",
            short_url="https://gifdist.io/s/Ef56Gh78",
            file_size=500000,
            width=320,
            height=180,
            duration_ms=2000,
        )

        card = AdaptiveCardBuilder.create_gif_card(gif, CardType.FULL)
        assert card["type"] == "AdaptiveCard"

    def test_file_size_formatting(self):
        """Test file size formatting"""
        # Test bytes
        assert "500 B" in AdaptiveCardBuilder._format_file_size(500)

        # Test KB
        assert "1.0 KB" in AdaptiveCardBuilder._format_file_size(1024)

        # Test MB
        assert "2.0 MB" in AdaptiveCardBuilder._format_file_size(2 * 1024 * 1024)


class TestTeamsMessageExtension:
    """Test Teams message extension"""

    def test_initialization(self):
        """Test message extension initialization"""
        ext = TeamsMessageExtension(app_id="test-id", app_secret="test-secret")

        assert ext.app_id == "test-id"
        assert ext.app_secret == "test-secret"
        assert ext.enable_link_unfurling is True

    def test_register_gif(self, teams_extension, sample_gif):
        """Test registering a GIF"""
        result = teams_extension.register_gif(sample_gif)

        assert result is True
        assert sample_gif.asset_id in teams_extension._gif_registry

    def test_register_gif_without_id(self, teams_extension):
        """Test registering GIF without asset ID fails"""
        gif = GIFCard(
            asset_id="",
            title="Test",
            mp4_url="https://example.com/test.mp4",
            gif_url="https://example.com/test.gif",
            thumbnail_url="https://example.com/thumb.jpg",
            canonical_url="https://example.com/a/test",
            short_url="https://example.com/s/test",
            file_size=1000,
            width=100,
            height=100,
            duration_ms=1000,
        )

        result = teams_extension.register_gif(gif)
        assert result is False

    def test_search_query(self, teams_extension, sample_gif):
        """Test handling search query"""
        teams_extension.register_gif(sample_gif)

        result = teams_extension.handle_search_query("cat")

        assert result.type == "result"
        assert len(result.attachments) == 1
        assert (
            result.attachments[0].content_type
            == "application/vnd.microsoft.card.adaptive"
        )

    def test_search_query_no_results(self, teams_extension):
        """Test search query with no results"""
        result = teams_extension.handle_search_query("nonexistent")

        assert result.type == "result"
        assert len(result.attachments) == 0

    def test_search_tracks_queries(self, teams_extension, sample_gif):
        """Test that search queries are tracked"""
        teams_extension.register_gif(sample_gif)

        teams_extension.handle_search_query("cat")
        teams_extension.handle_search_query("funny")

        assert len(teams_extension._search_queries) == 2
        assert teams_extension._search_queries[0]["query"] == "cat"
        assert teams_extension._search_queries[1]["query"] == "funny"

    def test_search_with_context(self, teams_extension, sample_gif):
        """Test search with context"""
        teams_extension.register_gif(sample_gif)

        context = {"user_id": "user123", "channel_id": "channel456"}
        result = teams_extension.handle_search_query("cat", context=context)

        assert len(teams_extension._search_queries) == 1
        assert teams_extension._search_queries[0]["context"] == context

    def test_search_limit(self, teams_extension):
        """Test search result limit"""
        # Register multiple GIFs with same tag
        for i in range(20):
            gif = GIFCard(
                asset_id=f"test{i}",
                title=f"Cat GIF {i}",
                mp4_url=f"https://cdn.example.com/test{i}.mp4",
                gif_url=f"https://cdn.example.com/test{i}.gif",
                thumbnail_url=f"https://cdn.example.com/test{i}_thumb.jpg",
                canonical_url=f"https://gifdist.io/a/test{i}",
                short_url=f"https://gifdist.io/s/test{i}",
                file_size=1000,
                width=100,
                height=100,
                duration_ms=1000,
                tags=["cat"],
            )
            teams_extension.register_gif(gif)

        result = teams_extension.handle_search_query("cat", limit=5)
        assert len(result.attachments) == 5

    def test_get_gif_card(self, teams_extension, sample_gif):
        """Test getting GIF card by ID"""
        teams_extension.register_gif(sample_gif)

        card = teams_extension.get_gif_card(sample_gif.asset_id, CardType.FULL)

        assert card is not None
        assert card["type"] == "AdaptiveCard"

    def test_get_gif_card_not_found(self, teams_extension):
        """Test getting non-existent GIF card"""
        card = teams_extension.get_gif_card("nonexistent")
        assert card is None

    def test_unfurl_link(self, teams_extension, sample_gif):
        """Test link unfurling"""
        teams_extension.register_gif(sample_gif)

        attachment = teams_extension.unfurl_link(sample_gif.canonical_url)

        assert attachment is not None
        assert attachment.content_type == "application/vnd.microsoft.card.adaptive"

    def test_unfurl_link_disabled(self, sample_gif):
        """Test link unfurling when disabled"""
        ext = TeamsMessageExtension(
            app_id="test-id", app_secret="test-secret", enable_link_unfurling=False
        )

        ext.register_gif(sample_gif)
        attachment = ext.unfurl_link(sample_gif.canonical_url)

        assert attachment is None

    def test_unfurl_unknown_link(self, teams_extension):
        """Test unfurling unknown link"""
        attachment = teams_extension.unfurl_link("https://unknown.com/gif")
        assert attachment is None

    def test_track_card_interaction(self, teams_extension):
        """Test tracking card interactions"""
        teams_extension.track_card_interaction(
            asset_id="test123", interaction_type="view", user_id="user456"
        )

        assert len(teams_extension._card_interactions) == 1
        assert teams_extension._card_interactions[0]["asset_id"] == "test123"
        assert teams_extension._card_interactions[0]["interaction_type"] == "view"

    def test_track_interaction_with_metadata(self, teams_extension):
        """Test tracking interaction with metadata"""
        metadata = {"channel": "general", "team": "marketing"}

        teams_extension.track_card_interaction(
            asset_id="test123", interaction_type="click", metadata=metadata
        )

        assert teams_extension._card_interactions[0]["metadata"] == metadata

    def test_get_analytics(self, teams_extension, sample_gif):
        """Test getting analytics"""
        teams_extension.register_gif(sample_gif)
        teams_extension.handle_search_query("cat")
        teams_extension.track_card_interaction("test123", "view")

        analytics = teams_extension.get_analytics()

        assert analytics["total_gifs"] == 1
        assert analytics["total_searches"] == 1
        assert analytics["total_interactions"] == 1

    def test_popular_queries(self, teams_extension, sample_gif):
        """Test popular queries tracking"""
        teams_extension.register_gif(sample_gif)

        # Perform multiple searches
        teams_extension.handle_search_query("cat")
        teams_extension.handle_search_query("cat")
        teams_extension.handle_search_query("funny")

        analytics = teams_extension.get_analytics()
        popular = analytics["popular_queries"]

        assert len(popular) == 2
        assert popular[0]["query"] == "cat"
        assert popular[0]["count"] == 2

    def test_popular_gifs(self, teams_extension):
        """Test popular GIFs tracking"""
        teams_extension.track_card_interaction("gif1", "view")
        teams_extension.track_card_interaction("gif1", "click")
        teams_extension.track_card_interaction("gif2", "view")

        analytics = teams_extension.get_analytics()
        popular = analytics["popular_gifs"]

        assert len(popular) == 2
        assert popular[0]["asset_id"] == "gif1"
        assert popular[0]["interactions"] == 2

    def test_verify_request_signature(self, teams_extension):
        """Test request signature verification"""
        payload = '{"test": "data"}'

        import hmac
        import hashlib

        signature = hmac.new(
            teams_extension.app_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        assert teams_extension.verify_request_signature(payload, signature) is True

    def test_verify_invalid_signature(self, teams_extension):
        """Test invalid signature rejection"""
        payload = '{"test": "data"}'
        invalid_signature = "invalid"

        assert (
            teams_extension.verify_request_signature(payload, invalid_signature)
            is False
        )

    def test_create_compose_extension_response(self, teams_extension, sample_gif):
        """Test creating compose extension response"""
        response = teams_extension.create_compose_extension_response(sample_gif)

        assert "composeExtension" in response
        assert response["composeExtension"]["type"] == "result"
        assert len(response["composeExtension"]["attachments"]) == 1

    def test_get_registered_gifs(self, teams_extension, sample_gif):
        """Test getting all registered GIFs"""
        teams_extension.register_gif(sample_gif)

        gifs = teams_extension.get_registered_gifs()

        assert len(gifs) == 1
        assert gifs[0].asset_id == sample_gif.asset_id

    def test_clear_registry(self, teams_extension, sample_gif):
        """Test clearing GIF registry"""
        teams_extension.register_gif(sample_gif)
        teams_extension.clear_registry()

        assert len(teams_extension._gif_registry) == 0

    def test_clear_analytics(self, teams_extension, sample_gif):
        """Test clearing analytics data"""
        teams_extension.register_gif(sample_gif)
        teams_extension.handle_search_query("cat")
        teams_extension.track_card_interaction("test123", "view")

        teams_extension.clear_analytics()

        assert len(teams_extension._search_queries) == 0
        assert len(teams_extension._card_interactions) == 0


class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self):
        """Test complete workflow from registration to interaction"""
        ext = TeamsMessageExtension(app_id="test-id", app_secret="test-secret")

        # Register a GIF
        gif = GIFCard(
            asset_id="workflow123",
            title="Workflow Test GIF",
            mp4_url="https://cdn.example.com/workflow.mp4",
            gif_url="https://cdn.example.com/workflow.gif",
            thumbnail_url="https://cdn.example.com/workflow_thumb.jpg",
            canonical_url="https://gifdist.io/a/workflow123",
            short_url="https://gifdist.io/s/Wf12Lo34",
            file_size=2048000,
            width=640,
            height=360,
            duration_ms=5000,
            tags=["workflow", "test"],
            description="Testing the full workflow",
        )

        assert ext.register_gif(gif) is True

        # Search for the GIF
        result = ext.handle_search_query("workflow")
        assert len(result.attachments) == 1

        # Track interaction
        ext.track_card_interaction("workflow123", "view", user_id="user789")

        # Get analytics
        analytics = ext.get_analytics()
        assert analytics["total_gifs"] == 1
        assert analytics["total_searches"] == 1
        assert analytics["total_interactions"] == 1

    def test_multiple_search_strategies(self, teams_extension):
        """Test searching by title, tags, and description"""
        gif = GIFCard(
            asset_id="multi123",
            title="Dancing Penguin",
            mp4_url="https://cdn.example.com/penguin.mp4",
            gif_url="https://cdn.example.com/penguin.gif",
            thumbnail_url="https://cdn.example.com/penguin_thumb.jpg",
            canonical_url="https://gifdist.io/a/multi123",
            short_url="https://gifdist.io/s/Mp12Ng34",
            file_size=1500000,
            width=400,
            height=300,
            duration_ms=4000,
            tags=["penguin", "dance", "antarctica"],
            description="A cute penguin dancing on ice",
        )

        teams_extension.register_gif(gif)

        # Search by title
        result = teams_extension.handle_search_query("penguin")
        assert len(result.attachments) == 1

        # Search by tag
        result = teams_extension.handle_search_query("antarctica")
        assert len(result.attachments) == 1

        # Search by description
        result = teams_extension.handle_search_query("ice")
        assert len(result.attachments) == 1

    def test_grid_vs_list_layout(self, teams_extension):
        """Test attachment layout based on result count"""
        # Single result should use list layout
        gif1 = GIFCard(
            asset_id="single",
            title="Single GIF",
            mp4_url="https://cdn.example.com/single.mp4",
            gif_url="https://cdn.example.com/single.gif",
            thumbnail_url="https://cdn.example.com/single_thumb.jpg",
            canonical_url="https://gifdist.io/a/single",
            short_url="https://gifdist.io/s/Sn12Gl34",
            file_size=1000,
            width=100,
            height=100,
            duration_ms=1000,
            tags=["unique"],
        )
        teams_extension.register_gif(gif1)

        result = teams_extension.handle_search_query("unique")
        assert result.attachment_layout == "list"

        # Multiple results should use grid layout
        gif2 = GIFCard(
            asset_id="multi1",
            title="Multi GIF 1",
            mp4_url="https://cdn.example.com/multi1.mp4",
            gif_url="https://cdn.example.com/multi1.gif",
            thumbnail_url="https://cdn.example.com/multi1_thumb.jpg",
            canonical_url="https://gifdist.io/a/multi1",
            short_url="https://gifdist.io/s/Mt12Gi34",
            file_size=1000,
            width=100,
            height=100,
            duration_ms=1000,
            tags=["common"],
        )
        gif3 = GIFCard(
            asset_id="multi2",
            title="Multi GIF 2",
            mp4_url="https://cdn.example.com/multi2.mp4",
            gif_url="https://cdn.example.com/multi2.gif",
            thumbnail_url="https://cdn.example.com/multi2_thumb.jpg",
            canonical_url="https://gifdist.io/a/multi2",
            short_url="https://gifdist.io/s/Mt34Gi56",
            file_size=1000,
            width=100,
            height=100,
            duration_ms=1000,
            tags=["common"],
        )
        teams_extension.register_gif(gif2)
        teams_extension.register_gif(gif3)

        result = teams_extension.handle_search_query("common", limit=10)
        assert result.attachment_layout == "grid"
