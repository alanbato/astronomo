"""Image widget for displaying inline images rendered with Chafa."""

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, Static

if TYPE_CHECKING:
    from astronomo.astronomo_app import Astronomo

# Try to import Chafa - it's an optional dependency
try:
    from chafa import (
        Canvas,
        CanvasConfig,
        CanvasMode,
        ColorSpace,
        DitherMode,
        PixelMode,
    )
    from chafa.loader import Loader

    CHAFA_AVAILABLE = True
except ImportError:
    CHAFA_AVAILABLE = False


class GemtextImageWidget(Static):
    """Widget for displaying rendered images with download button.

    Renders images using Chafa to ANSI art and displays them inline.
    Provides a download button to save the original image to ~/Downloads.
    """

    DEFAULT_CSS = """
    GemtextImageWidget {
        width: 100%;
        height: auto;
        border: solid $primary;
        margin: 1 0;
        padding: 0;
    }

    GemtextImageWidget .image-header {
        background: $primary-muted;
        padding: 0 1;
        text-style: bold;
        width: 100%;
        height: auto;
    }

    GemtextImageWidget .image-content {
        padding: 1;
        width: 100%;
        height: auto;
    }

    GemtextImageWidget .image-footer {
        padding: 0 1;
        width: 100%;
        height: auto;
        align: center middle;
    }

    GemtextImageWidget Button {
        margin: 0 1;
    }
    """

    class DownloadRequested(Message):
        """Message posted when user requests to download the image.

        Attributes:
            url: Original image URL
            filename: Suggested filename for download
            image_data: Raw image bytes
        """

        def __init__(self, url: str, filename: str, image_data: bytes) -> None:
            self.url = url
            self.filename = filename
            self.image_data = image_data
            super().__init__()

    def __init__(
        self,
        url: str,
        filename: str,
        image_data: bytes,
        mime_type: str,
        **kwargs,
    ) -> None:
        """Initialize image widget.

        Args:
            url: Original image URL
            filename: Image filename
            image_data: Raw image bytes
            mime_type: MIME type of the image
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.url = url
        self.filename = filename
        self.image_data = image_data
        self.mime_type = mime_type

        # Prevent width constraint from GemtextViewer
        self.add_class("-full-width")

    def compose(self) -> ComposeResult:
        """Compose image display with header, rendered image, and download button."""
        with Vertical():
            # Header with filename and dimensions
            yield Label(f"📷 {self.filename}", classes="image-header")

            # Rendered image content
            rendered = self._render_image()
            if rendered is not None:
                yield Static(rendered, classes="image-content")
            else:
                yield Label(
                    "Failed to render image (Chafa not available or rendering error)",
                    classes="image-content",
                )

            # Footer with download button
            with Horizontal(classes="image-footer"):
                yield Button("💾 Download Image", id=f"download-{id(self)}")

    def _render_image(self) -> Text | None:
        """Render image to ANSI text using Chafa.

        Returns:
            Rich Text object with ANSI art, or None on error
        """
        if not CHAFA_AVAILABLE:
            return None

        try:
            import tempfile

            # Get quality setting from app config
            quality = "medium"
            try:
                app: Astronomo = self.app  # type: ignore[assignment]
                quality = app.config_manager.image_quality
            except AttributeError:
                pass  # Use default if app not available

            # Get max width from config
            max_width = 80  # Default
            try:
                app: Astronomo = self.app  # type: ignore[assignment]
                configured_width = app.config_manager.max_content_width
                if configured_width > 0:
                    max_width = configured_width
            except AttributeError:
                pass

            # Map quality to Chafa settings
            quality_settings = self._get_quality_settings(quality)

            # Chafa needs a file path, so write to temp file
            with tempfile.NamedTemporaryFile(
                suffix=f".{self.mime_type.split('/')[-1]}", delete=False
            ) as tmp:
                tmp.write(self.image_data)
                tmp_path = tmp.name

            try:
                # Load image pixels using Loader
                loader = Loader(tmp_path)

                # Configure Chafa canvas
                config = CanvasConfig()
                config.width = max_width

                # Calculate proper height preserving aspect ratio
                # Terminal chars are ~2x taller than wide, so font_ratio ~0.5
                config.calc_canvas_geometry(
                    src_width=loader.width,
                    src_height=loader.height,
                    font_ratio=0.5,
                    zoom=False,
                    stretch=False,
                )

                # Apply quality settings
                if "pixel_mode" in quality_settings:
                    config.pixel_mode = quality_settings["pixel_mode"]
                if "canvas_mode" in quality_settings:
                    config.canvas_mode = quality_settings["canvas_mode"]
                if "color_space" in quality_settings:
                    config.color_space = quality_settings["color_space"]
                if "dither_mode" in quality_settings:
                    config.dither_mode = quality_settings["dither_mode"]
                if "work_factor" in quality_settings:
                    config.work_factor = quality_settings["work_factor"]

                # Create canvas and draw pixels
                canvas = Canvas(config)
                canvas.draw_all_pixels(
                    loader.pixel_type,
                    loader.get_pixels(),
                    loader.width,
                    loader.height,
                    loader.rowstride,
                )

                # Get ANSI output
                ansi_output = canvas.print().decode("utf-8")

                # Return as Rich Text with ANSI parsing
                return Text.from_ansi(ansi_output)
            finally:
                # Clean up temp file
                import os

                os.unlink(tmp_path)

        except Exception as e:
            # Log error and return None to show fallback message
            try:
                app: Astronomo = self.app  # type: ignore[assignment]
                app.notify(f"Image rendering failed: {e}", severity="warning")
            except AttributeError:
                pass
            return None

    def _get_quality_settings(self, quality: str) -> dict:
        """Get Chafa settings for given quality level.

        Args:
            quality: Quality level ("low", "medium", or "high")

        Returns:
            Dictionary of Chafa configuration settings
        """
        base_settings = {
            "pixel_mode": PixelMode.CHAFA_PIXEL_MODE_SYMBOLS,
        }

        if quality == "low":
            # 256 colors, no dithering, RGB colorspace, minimal optimization
            base_settings["canvas_mode"] = CanvasMode.CHAFA_CANVAS_MODE_INDEXED_256
            base_settings["color_space"] = ColorSpace.CHAFA_COLOR_SPACE_RGB
            base_settings["dither_mode"] = DitherMode.CHAFA_DITHER_MODE_NONE
            base_settings["work_factor"] = 0.25
        elif quality == "high":
            # Truecolor, diffusion dithering, DIN99D colorspace, maximum optimization
            base_settings["canvas_mode"] = CanvasMode.CHAFA_CANVAS_MODE_TRUECOLOR
            base_settings["color_space"] = ColorSpace.CHAFA_COLOR_SPACE_DIN99D
            base_settings["dither_mode"] = DitherMode.CHAFA_DITHER_MODE_ORDERED
            base_settings["work_factor"] = 1.0
        else:  # medium
            # 256 colors, ordered dithering, DIN99D colorspace, balanced optimization
            base_settings["canvas_mode"] = CanvasMode.CHAFA_CANVAS_MODE_TRUECOLOR
            base_settings["color_space"] = ColorSpace.CHAFA_COLOR_SPACE_DIN99D
            base_settings["dither_mode"] = DitherMode.CHAFA_DITHER_MODE_DIFFUSION
            base_settings["work_factor"] = 0.5

        return base_settings

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle download button press."""
        if event.button.id == f"download-{id(self)}":
            self.post_message(
                self.DownloadRequested(self.url, self.filename, self.image_data)
            )
