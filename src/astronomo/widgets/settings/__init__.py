"""Settings widgets for Astronomo."""

from astronomo.widgets.settings.appearance import AppearanceSettings
from astronomo.widgets.settings.browsing import BrowsingSettings
from astronomo.widgets.settings.certificates import CertificatesSettings
from astronomo.widgets.settings.known_hosts import KnownHostsSettings

__all__ = [
    "AppearanceSettings",
    "BrowsingSettings",
    "CertificatesSettings",
    "KnownHostsSettings",
]
