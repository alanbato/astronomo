"""Tests for link navigation and scrolling behavior."""

import pytest

from astronomo.astronomo_app import Astronomo
from astronomo.widgets import GemtextViewer


def is_link_visible(viewer: GemtextViewer, link_index: int) -> bool:
    """Check if a link at the given index is visible in the viewport.

    Uses the link widget's virtual_region to check if it's within the visible area.
    virtual_region gives the position within the scrollable content area.

    Args:
        viewer: The GemtextViewer widget
        link_index: The index of the link widget

    Returns:
        True if the link widget is within the visible viewport
    """
    if not (0 <= link_index < len(viewer._link_widgets)):
        return False

    link_widget = viewer._link_widgets[link_index]

    # Get the link widget's virtual region (position within scrollable content)
    link_region = link_widget.virtual_region

    # Get the viewport bounds
    viewport_top = viewer.scroll_y
    viewport_bottom = viewer.scroll_y + viewer.scrollable_content_region.height

    # Check if the link's y position is within the viewport
    link_top = link_region.y
    link_bottom = link_region.y + link_region.height

    # Link is visible if any part of it is in the viewport
    return link_top < viewport_bottom and link_bottom > viewport_top


class TestLinkScrolling:
    """Test suite for link navigation scrolling behavior."""

    @pytest.mark.asyncio
    async def test_link_scrolling_with_real_document(self):
        """Test link navigation with a real Gemini document.

        Navigates to gemini://geminiprotocol.net/docs/faq.gmi and tests
        that links remain visible when navigating through them.
        """
        app = Astronomo(initial_url="gemini://geminiprotocol.net/docs/faq.gmi")

        # Use constrained viewport to force scrolling
        async with app.run_test(size=(80, 24)) as pilot:
            # Wait for the page to load
            await pilot.pause(delay=1.0)

            viewer = app.query_one("#content", GemtextViewer)

            # Make sure we have links to navigate
            assert len(viewer._link_widgets) > 0, "Page should have links"

            # Navigate through links (up to 9 links if available)
            max_links = min(9, len(viewer._link_widgets))
            for i in range(max_links):
                # Press right to go to next link (first press selects link 1)
                if i > 0:
                    await pilot.press("right")
                    await pilot.pause()

                # Verify the current link is visible
                link_widget = viewer._link_widgets[viewer.current_link_index]
                assert is_link_visible(viewer, viewer.current_link_index), (
                    f"Link {viewer.current_link_index} should be visible "
                    f"(link region: {link_widget.region}, "
                    f"viewport: {viewer.scroll_y} to {viewer.scroll_y + viewer.size.height})"
                )

    @pytest.mark.asyncio
    async def test_link_8_to_9_visible(self):
        """Specifically test that after navigating from 8th to 9th link, link is visible.

        This tests the specific case mentioned in requirements: after going from
        the 8th to the 9th link, we should verify the link is displayed on screen.
        """
        app = Astronomo(initial_url="gemini://geminiprotocol.net/docs/faq.gmi")

        async with app.run_test(size=(80, 24)) as pilot:
            # Wait for page to load
            await pilot.pause(delay=1.0)

            viewer = app.query_one("#content", GemtextViewer)

            # Need at least 9 links for this test
            if len(viewer._link_widgets) < 9:
                pytest.skip("Page doesn't have at least 9 links")

            # Navigate to the 8th link (index 7, since we start at 0)
            for _ in range(7):
                await pilot.press("right")
                await pilot.pause()

            assert viewer.current_link_index == 7, "Should be at 8th link (index 7)"

            # Now navigate to the 9th link (index 8)
            await pilot.press("right")
            await pilot.pause()

            assert viewer.current_link_index == 8, "Should be at 9th link (index 8)"

            # The key assertion: 9th link must be visible
            link_widget = viewer._link_widgets[8]
            assert is_link_visible(viewer, 8), (
                f"9th link (index 8) should be visible after navigation "
                f"(link region: {link_widget.region}, "
                f"viewport: {viewer.scroll_y} to {viewer.scroll_y + viewer.size.height})"
            )

    @pytest.mark.asyncio
    async def test_wrap_around_last_to_first(self):
        """Test that navigating past the last link wraps to the first."""
        app = Astronomo(initial_url="gemini://geminiprotocol.net/docs/faq.gmi")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(delay=1.0)

            viewer = app.query_one("#content", GemtextViewer)

            if len(viewer._link_widgets) < 2:
                pytest.skip("Page needs at least 2 links")

            num_links = len(viewer._link_widgets)

            # Navigate to last link
            for _ in range(num_links - 1):
                await pilot.press("right")
                await pilot.pause()

            assert viewer.current_link_index == num_links - 1, "Should be at last link"

            # Navigate once more to wrap around
            await pilot.press("right")
            await pilot.pause()

            assert viewer.current_link_index == 0, "Should wrap to first link"

            # First link should be visible
            assert is_link_visible(viewer, 0), (
                "First link (index 0) should be visible after wrap-around"
            )

    @pytest.mark.asyncio
    async def test_wrap_around_first_to_last(self):
        """Test that navigating before the first link wraps to the last."""
        app = Astronomo(initial_url="gemini://geminiprotocol.net/docs/faq.gmi")

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(delay=1.0)

            viewer = app.query_one("#content", GemtextViewer)

            if len(viewer._link_widgets) < 2:
                pytest.skip("Page needs at least 2 links")

            num_links = len(viewer._link_widgets)

            # Starting at first link (index 0)
            assert viewer.current_link_index == 0, "Should start at first link"

            # Navigate backward to wrap to last link
            await pilot.press("left")
            await pilot.pause()

            assert viewer.current_link_index == num_links - 1, (
                "Should wrap to last link"
            )

            # Last link should be visible
            assert is_link_visible(viewer, num_links - 1), (
                f"Last link (index {num_links - 1}) should be visible after wrap-around"
            )

    @pytest.mark.asyncio
    async def test_no_scroll_when_link_already_visible(self):
        """Test that scrolling doesn't occur when navigating to an already-visible link."""
        app = Astronomo(initial_url="gemini://geminiprotocol.net/docs/faq.gmi")

        # Use larger viewport so multiple links are visible
        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause(delay=1.0)

            viewer = app.query_one("#content", GemtextViewer)

            if len(viewer._link_widgets) < 3:
                pytest.skip("Page needs at least 3 links")

            # Record initial scroll position
            initial_scroll_y = viewer.scroll_y

            # If first few links are visible, navigating between them shouldn't scroll
            # First check that links 0 and 1 are both visible
            if is_link_visible(viewer, 0) and is_link_visible(viewer, 1):
                await pilot.press("right")
                await pilot.pause()

                # Scroll position should not have changed
                assert viewer.scroll_y == initial_scroll_y, (
                    f"Scroll position should not change when navigating to "
                    f"already-visible link (was {initial_scroll_y}, now {viewer.scroll_y})"
                )
