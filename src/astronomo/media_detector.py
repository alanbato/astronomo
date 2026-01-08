"""Media type detection for images, audio, and video.

This module provides utilities for detecting different media types based on
MIME types and file extensions. Designed to be extensible for future media
types (audio, video, etc.).
"""

from enum import Enum


class MediaType(Enum):
    """Supported media types."""

    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    UNKNOWN = "unknown"


class MediaDetector:
    """Detects media types from MIME types and file extensions."""

    # Supported image formats
    IMAGE_MIMES = frozenset(
        {
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/gif",
            "image/webp",
        }
    )

    IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})

    # Future: Audio formats (for when we add audio support)
    AUDIO_MIMES = frozenset(
        {
            "audio/mpeg",
            "audio/mp3",
            "audio/ogg",
            "audio/wav",
            "audio/flac",
        }
    )

    AUDIO_EXTENSIONS = frozenset({".mp3", ".ogg", ".wav", ".flac", ".m4a"})

    # Future: Video formats (for when we add video support)
    VIDEO_MIMES = frozenset(
        {
            "video/mp4",
            "video/webm",
            "video/ogg",
            "video/mpeg",
        }
    )

    VIDEO_EXTENSIONS = frozenset({".mp4", ".webm", ".ogv", ".mpeg", ".mpg"})

    @classmethod
    def detect_media_type(cls, mime_type: str | None, url: str) -> MediaType:
        """Detect media type from MIME type and URL.

        Args:
            mime_type: MIME type from server response (may be None)
            url: URL or filename to check extension

        Returns:
            MediaType enum value
        """
        # Check MIME type first (most reliable)
        if mime_type:
            if mime_type in cls.IMAGE_MIMES:
                return MediaType.IMAGE
            if mime_type in cls.AUDIO_MIMES:
                return MediaType.AUDIO
            if mime_type in cls.VIDEO_MIMES:
                return MediaType.VIDEO

        # Fallback: check file extension
        url_lower = url.lower()
        for ext in cls.IMAGE_EXTENSIONS:
            if url_lower.endswith(ext):
                return MediaType.IMAGE
        for ext in cls.AUDIO_EXTENSIONS:
            if url_lower.endswith(ext):
                return MediaType.AUDIO
        for ext in cls.VIDEO_EXTENSIONS:
            if url_lower.endswith(ext):
                return MediaType.VIDEO

        return MediaType.UNKNOWN

    @classmethod
    def is_image(cls, mime_type: str | None, url: str) -> bool:
        """Check if content is an image.

        Args:
            mime_type: MIME type from server response
            url: URL or filename

        Returns:
            True if content is a supported image format
        """
        return cls.detect_media_type(mime_type, url) == MediaType.IMAGE

    @classmethod
    def is_audio(cls, mime_type: str | None, url: str) -> bool:
        """Check if content is audio.

        Args:
            mime_type: MIME type from server response
            url: URL or filename

        Returns:
            True if content is a supported audio format
        """
        return cls.detect_media_type(mime_type, url) == MediaType.AUDIO

    @classmethod
    def is_video(cls, mime_type: str | None, url: str) -> bool:
        """Check if content is video.

        Args:
            mime_type: MIME type from server response
            url: URL or filename

        Returns:
            True if content is a supported video format
        """
        return cls.detect_media_type(mime_type, url) == MediaType.VIDEO
