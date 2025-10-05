"""
AI Safety Scanner using OpenAI Moderation + Vision API
Provides real AI-powered content moderation for uploads
Issue: #1
"""

import os
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import io


class AISafetyError(Exception):
    """Exception raised when AI safety scanning fails"""

    pass


@dataclass
class SafetyScanResult:
    """Result from AI safety scanning"""

    is_safe: bool
    confidence: float  # 0.0 to 1.0
    violations: List[str]
    categories_flagged: Dict[str, float]  # category -> score
    metadata: Dict = None


class OpenAIModerationScanner:
    """OpenAI Moderation API integration"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI moderation scanner

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise AISafetyError("OpenAI API key not provided")

        # Import openai here to make it optional
        try:
            import openai

            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise AISafetyError("openai package not installed. Run: pip install openai")

    def scan_text(self, text: str) -> SafetyScanResult:
        """
        Scan text content using OpenAI Moderation API

        Args:
            text: Text to scan (title, description, tags, etc.)

        Returns:
            SafetyScanResult with moderation results
        """
        if not text or not text.strip():
            return SafetyScanResult(
                is_safe=True,
                confidence=1.0,
                violations=[],
                categories_flagged={},
                metadata={"text_length": 0},
            )

        try:
            response = self.client.moderations.create(input=text)
            result = response.results[0]

            # Extract flagged categories
            categories_flagged = {}
            violations = []

            if result.flagged:
                # Map OpenAI categories to our violations
                category_map = {
                    "sexual": "Sexual content",
                    "sexual/minors": "Sexual content involving minors",
                    "hate": "Hate speech",
                    "hate/threatening": "Threatening hate speech",
                    "harassment": "Harassment",
                    "harassment/threatening": "Threatening harassment",
                    "self-harm": "Self-harm content",
                    "self-harm/intent": "Self-harm intent",
                    "self-harm/instructions": "Self-harm instructions",
                    "violence": "Violence",
                    "violence/graphic": "Graphic violence",
                }

                for category, score in result.category_scores.model_dump().items():
                    if score > 0.5:  # Threshold for flagging
                        categories_flagged[category] = score
                        violations.append(category_map.get(category, category))

            # Calculate confidence (inverse of highest score)
            max_score = (
                max(result.category_scores.model_dump().values())
                if result.category_scores
                else 0.0
            )
            confidence = 1.0 - max_score if result.flagged else 1.0 - (max_score * 0.5)

            return SafetyScanResult(
                is_safe=not result.flagged,
                confidence=confidence,
                violations=violations,
                categories_flagged=categories_flagged,
                metadata={
                    "text_length": len(text),
                    "model": response.model,
                    "flagged": result.flagged,
                },
            )

        except Exception as e:
            raise AISafetyError(f"Moderation API failed: {str(e)}")


class OpenAIVisionScanner:
    """OpenAI Vision API integration for visual content scanning"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI vision scanner

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise AISafetyError("OpenAI API key not provided")

        try:
            import openai

            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise AISafetyError("openai package not installed. Run: pip install openai")

    def _encode_image(self, file_path: str, max_size: int = 1024) -> str:
        """
        Encode image to base64 for API submission

        Args:
            file_path: Path to image file
            max_size: Maximum dimension (width or height) for resizing

        Returns:
            Base64 encoded image string
        """
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize if too large
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Encode to base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                return base64.b64encode(buffer.getvalue()).decode("utf-8")

        except Exception as e:
            raise AISafetyError(f"Failed to encode image: {str(e)}")

    def scan_image(self, file_path: str, check_nsfw: bool = True) -> SafetyScanResult:
        """
        Scan image/GIF content using OpenAI Vision API

        Args:
            file_path: Path to image or GIF file
            check_nsfw: Whether to check for NSFW content

        Returns:
            SafetyScanResult with vision analysis results
        """
        try:
            # Encode image
            base64_image = self._encode_image(file_path)

            # Create safety checking prompt
            prompt = """Analyze this image for safety and content moderation. Check for:
1. NSFW/adult content (nudity, sexual content, explicit imagery)
2. Violence or gore
3. Hate symbols or hateful imagery
4. Illegal content
5. Other harmful or inappropriate content

Respond with a JSON object containing:
- is_safe (boolean): true if content is safe for all audiences
- violations (array): list of specific violations found (empty if safe)
- confidence (float 0-1): how confident you are in this assessment
- description (string): brief description of the content

Be strict - flag anything questionable."""

            # Call Vision API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use gpt-4o-mini for cost efficiency
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
                temperature=0.0,  # Consistent, deterministic results
            )

            # Parse response
            result_text = response.choices[0].message.content

            # Try to parse as JSON
            import json

            try:
                result_json = json.loads(result_text)
                is_safe = result_json.get("is_safe", False)
                violations = result_json.get("violations", [])
                confidence = result_json.get("confidence", 0.5)
                description = result_json.get("description", "")
            except json.JSONDecodeError:
                # Fallback: simple text analysis
                is_safe = (
                    "is_safe: true" in result_text.lower()
                    or "safe" in result_text.lower()
                )
                violations = []
                confidence = 0.7
                description = result_text

                # Extract violations from text
                if not is_safe:
                    if "nsfw" in result_text.lower() or "sexual" in result_text.lower():
                        violations.append("NSFW/Sexual content")
                    if (
                        "violence" in result_text.lower()
                        or "gore" in result_text.lower()
                    ):
                        violations.append("Violence/Gore")
                    if "hate" in result_text.lower():
                        violations.append("Hate imagery")

            # Build categories flagged
            categories_flagged = {}
            for violation in violations:
                categories_flagged[violation] = (
                    0.8  # Default high score for flagged items
                )

            return SafetyScanResult(
                is_safe=is_safe,
                confidence=confidence,
                violations=violations,
                categories_flagged=categories_flagged,
                metadata={
                    "description": description,
                    "model": response.model,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                },
            )

        except Exception as e:
            raise AISafetyError(f"Vision API failed: {str(e)}")


class AISafetyPipeline:
    """Complete AI safety scanning pipeline combining text and vision analysis"""

    def __init__(self, api_key: Optional[str] = None, enable_vision: bool = True):
        """
        Initialize AI safety pipeline

        Args:
            api_key: OpenAI API key
            enable_vision: Whether to enable vision scanning (slower but more accurate)
        """
        self.moderation_scanner = OpenAIModerationScanner(api_key=api_key)
        self.vision_scanner = (
            OpenAIVisionScanner(api_key=api_key) if enable_vision else None
        )
        self.enable_vision = enable_vision

    def scan_upload(
        self,
        file_path: Optional[str] = None,
        title: str = "",
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> Dict[str, SafetyScanResult]:
        """
        Perform complete safety scan on upload

        Args:
            file_path: Path to media file (image/GIF)
            title: Asset title
            tags: Asset tags
            description: Asset description

        Returns:
            Dictionary with 'text' and optionally 'visual' scan results
        """
        results = {}

        # Scan text metadata
        text_content = " ".join(
            filter(None, [title, " ".join(tags or []), description])
        )

        if text_content.strip():
            results["text"] = self.moderation_scanner.scan_text(text_content)

        # Scan visual content if enabled and file provided
        if self.enable_vision and file_path and self.vision_scanner:
            results["visual"] = self.vision_scanner.scan_image(file_path)

        return results

    def is_safe(
        self, scan_results: Dict[str, SafetyScanResult]
    ) -> Tuple[bool, List[str], float]:
        """
        Determine if content is safe based on all scan results

        Args:
            scan_results: Results from scan_upload()

        Returns:
            Tuple of (is_safe, violations, confidence)
        """
        all_violations = []
        min_confidence = 1.0
        is_safe = True

        for scan_type, result in scan_results.items():
            if not result.is_safe:
                is_safe = False
                all_violations.extend([f"{scan_type}: {v}" for v in result.violations])
            min_confidence = min(min_confidence, result.confidence)

        return is_safe, all_violations, min_confidence
