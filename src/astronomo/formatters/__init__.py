"""Protocol response formatters for Astronomo.

This package contains formatters that convert protocol-specific responses
to Gemtext lines for unified display in the GemtextViewer.
"""

from astronomo.formatters.finger import fetch_finger
from astronomo.formatters.gopher import GopherFetchResult, fetch_gopher
from astronomo.formatters.nex import fetch_nex

__all__ = ["fetch_finger", "fetch_gopher", "fetch_nex", "GopherFetchResult"]
