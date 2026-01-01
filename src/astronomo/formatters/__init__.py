"""Protocol response formatters for Astronomo.

This package contains formatters that convert protocol-specific responses
to Gemtext lines for unified display in the GemtextViewer.
"""

from astronomo.formatters.finger import fetch_finger
from astronomo.formatters.gopher import GopherFetchResult, fetch_gopher

__all__ = ["fetch_finger", "fetch_gopher", "GopherFetchResult"]
