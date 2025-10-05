"""
Tests for AI Safety Scanner
Tests OpenAI moderation and vision API integration
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock openai module before importing ai_safety_scanner
sys.modules["openai"] = Mock()

from ai_safety_scanner import (
    AISafetyError,
    SafetyScanResult,
    OpenAIModerationScanner,
    OpenAIVisionScanner,
    AISafetyPipeline,
)


class TestOpenAIModerationScanner:
    """Test OpenAI moderation scanner"""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key"""
        scanner = OpenAIModerationScanner(api_key="test-key")
        assert scanner.api_key == "test-key"

    def test_init_from_env(self):
        """Test initialization from environment variable"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            scanner = OpenAIModerationScanner()
            assert scanner.api_key == "env-key"

    def test_init_no_api_key(self):
        """Test initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AISafetyError, match="API key not provided"):
                OpenAIModerationScanner()

    def test_scan_text_safe_content(self):
        """Test scanning safe text content"""
        mock_response = Mock()
        mock_result = Mock()
        mock_result.flagged = False
        mock_result.category_scores = Mock()
        mock_result.category_scores.model_dump.return_value = {
            "sexual": 0.001,
            "hate": 0.001,
            "violence": 0.001,
        }
        mock_response.results = [mock_result]
        mock_response.model = "text-moderation-latest"

        scanner = OpenAIModerationScanner(api_key="test-key")
        scanner.client = Mock()
        scanner.client.moderations.create.return_value = mock_response

        result = scanner.scan_text("This is a cute cat GIF")

        assert result.is_safe is True
        assert result.confidence > 0.9
        assert len(result.violations) == 0
        assert result.metadata["flagged"] is False

    def test_scan_text_empty(self):
        """Test scanning empty text"""
        scanner = OpenAIModerationScanner(api_key="test-key")
        result = scanner.scan_text("")

        assert result.is_safe is True
        assert result.confidence == 1.0
        assert len(result.violations) == 0


class TestAISafetyPipeline:
    """Test complete AI safety pipeline"""

    def test_init_with_vision(self):
        """Test initialization with vision enabled"""
        pipeline = AISafetyPipeline(api_key="test-key", enable_vision=True)
        assert pipeline.enable_vision is True
        assert pipeline.vision_scanner is not None

    def test_init_without_vision(self):
        """Test initialization with vision disabled"""
        pipeline = AISafetyPipeline(api_key="test-key", enable_vision=False)
        assert pipeline.enable_vision is False
        assert pipeline.vision_scanner is None

    def test_is_safe_all_pass(self):
        """Test is_safe when all scans pass"""
        pipeline = AISafetyPipeline(api_key="test-key")

        scan_results = {
            "text": SafetyScanResult(
                is_safe=True, confidence=0.95, violations=[], categories_flagged={}
            ),
            "visual": SafetyScanResult(
                is_safe=True, confidence=0.90, violations=[], categories_flagged={}
            ),
        }

        is_safe, violations, confidence = pipeline.is_safe(scan_results)

        assert is_safe is True
        assert len(violations) == 0
        assert confidence == 0.90  # Min of all confidences

    def test_is_safe_text_fails(self):
        """Test is_safe when text scan fails"""
        pipeline = AISafetyPipeline(api_key="test-key")

        scan_results = {
            "text": SafetyScanResult(
                is_safe=False,
                confidence=0.85,
                violations=["Sexual content"],
                categories_flagged={"sexual": 0.95},
            ),
            "visual": SafetyScanResult(
                is_safe=True, confidence=0.90, violations=[], categories_flagged={}
            ),
        }

        is_safe, violations, confidence = pipeline.is_safe(scan_results)

        assert is_safe is False
        assert len(violations) == 1
        assert "text: Sexual content" in violations
        assert confidence == 0.85
