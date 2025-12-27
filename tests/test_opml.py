"""Tests for OPML import/export functionality."""

import tempfile
from pathlib import Path

import pytest

from astronomo.feeds import FeedManager
from astronomo.opml import export_opml, import_opml


class TestOpmlExport:
    """Tests for OPML export functionality."""

    @pytest.fixture
    def temp_config_dir(self) -> Path:
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> FeedManager:
        """Create a FeedManager with temporary storage."""
        return FeedManager(config_dir=temp_config_dir)

    @pytest.fixture
    def populated_manager(self, manager: FeedManager) -> FeedManager:
        """Create a manager with sample feeds."""
        # Add root-level feeds
        manager.add_feed("gemini://example.com/feed.xml", "Example Feed")
        manager.add_feed("gemini://another.com/feed.xml", "Another Feed")

        # Add folder with feeds
        folder = manager.add_folder("Tech News")
        manager.add_feed(
            "gemini://tech.com/rss", "Tech Blog", folder_id=folder.id
        )
        manager.add_feed(
            "gemini://dev.com/atom", "Dev Updates", folder_id=folder.id
        )

        return manager

    def test_export_creates_file(
        self, populated_manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test that export creates an OPML file."""
        output_path = temp_config_dir / "feeds.opml"
        export_opml(populated_manager, output_path)

        assert output_path.exists()
        assert output_path.is_file()

    def test_export_valid_xml(
        self, populated_manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test that exported file is valid XML."""
        import xml.etree.ElementTree as ET

        output_path = temp_config_dir / "feeds.opml"
        export_opml(populated_manager, output_path)

        # Should parse without error
        tree = ET.parse(output_path)
        root = tree.getroot()

        assert root.tag == "opml"
        assert root.get("version") == "2.0"

    def test_export_has_head(
        self, populated_manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test that exported OPML has a head element."""
        import xml.etree.ElementTree as ET

        output_path = temp_config_dir / "feeds.opml"
        export_opml(populated_manager, output_path)

        tree = ET.parse(output_path)
        root = tree.getroot()
        head = root.find("head")

        assert head is not None
        title = head.find("title")
        assert title is not None
        assert title.text == "Astronomo Feeds"

    def test_export_root_feeds(
        self, populated_manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test that root-level feeds are exported correctly."""
        import xml.etree.ElementTree as ET

        output_path = temp_config_dir / "feeds.opml"
        export_opml(populated_manager, output_path)

        tree = ET.parse(output_path)
        body = tree.getroot().find("body")
        assert body is not None

        # Find root-level feed outlines
        root_feeds = [
            o for o in body.findall("outline")
            if o.get("type") == "rss"
        ]

        assert len(root_feeds) == 2
        urls = {feed.get("xmlUrl") for feed in root_feeds}
        assert "gemini://example.com/feed.xml" in urls
        assert "gemini://another.com/feed.xml" in urls

    def test_export_folders_with_feeds(
        self, populated_manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test that folders and their feeds are exported correctly."""
        import xml.etree.ElementTree as ET

        output_path = temp_config_dir / "feeds.opml"
        export_opml(populated_manager, output_path)

        tree = ET.parse(output_path)
        body = tree.getroot().find("body")
        assert body is not None

        # Find folder outlines (no type="rss")
        folders = [
            o for o in body.findall("outline")
            if o.get("type") != "rss"
        ]

        assert len(folders) == 1
        folder = folders[0]
        assert folder.get("text") == "Tech News"

        # Check feeds within folder
        folder_feeds = folder.findall("outline")
        assert len(folder_feeds) == 2

        urls = {feed.get("xmlUrl") for feed in folder_feeds}
        assert "gemini://tech.com/rss" in urls
        assert "gemini://dev.com/atom" in urls

    def test_export_empty_manager(
        self, manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test exporting with no feeds."""
        import xml.etree.ElementTree as ET

        output_path = temp_config_dir / "feeds.opml"
        export_opml(manager, output_path)

        tree = ET.parse(output_path)
        body = tree.getroot().find("body")
        assert body is not None

        outlines = body.findall("outline")
        assert len(outlines) == 0


class TestOpmlImport:
    """Tests for OPML import functionality."""

    @pytest.fixture
    def temp_config_dir(self) -> Path:
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir: Path) -> FeedManager:
        """Create a FeedManager with temporary storage."""
        return FeedManager(config_dir=temp_config_dir)

    @pytest.fixture
    def simple_opml(self, temp_config_dir: Path) -> Path:
        """Create a simple OPML file for testing."""
        opml_content = """<?xml version="1.0" encoding="utf-8"?>
<opml version="2.0">
  <head>
    <title>Test Feeds</title>
  </head>
  <body>
    <outline type="rss" text="Example Feed" title="Example Feed" xmlUrl="gemini://example.com/feed.xml"/>
    <outline type="rss" text="Another Feed" title="Another Feed" xmlUrl="gemini://another.com/feed.xml"/>
  </body>
</opml>"""
        opml_path = temp_config_dir / "test.opml"
        opml_path.write_text(opml_content)
        return opml_path

    @pytest.fixture
    def opml_with_folders(self, temp_config_dir: Path) -> Path:
        """Create an OPML file with folders."""
        opml_content = """<?xml version="1.0" encoding="utf-8"?>
<opml version="2.0">
  <head>
    <title>Test Feeds</title>
  </head>
  <body>
    <outline type="rss" text="Root Feed" xmlUrl="gemini://root.com/feed.xml"/>
    <outline text="Tech" title="Tech">
      <outline type="rss" text="Tech Feed 1" xmlUrl="gemini://tech1.com/feed.xml"/>
      <outline type="rss" text="Tech Feed 2" xmlUrl="gemini://tech2.com/feed.xml"/>
    </outline>
    <outline text="News" title="News">
      <outline type="rss" text="News Feed" xmlUrl="gemini://news.com/feed.xml"/>
    </outline>
  </body>
</opml>"""
        opml_path = temp_config_dir / "folders.opml"
        opml_path.write_text(opml_content)
        return opml_path

    @pytest.fixture
    def opml_with_http_feeds(self, temp_config_dir: Path) -> Path:
        """Create an OPML file with HTTP feeds (should be skipped)."""
        opml_content = """<?xml version="1.0" encoding="utf-8"?>
<opml version="2.0">
  <head>
    <title>Mixed Feeds</title>
  </head>
  <body>
    <outline type="rss" text="Gemini Feed" xmlUrl="gemini://example.com/feed.xml"/>
    <outline type="rss" text="HTTP Feed" xmlUrl="https://example.com/feed.xml"/>
    <outline type="rss" text="Another HTTP" xmlUrl="http://example.org/feed.xml"/>
  </body>
</opml>"""
        opml_path = temp_config_dir / "mixed.opml"
        opml_path.write_text(opml_content)
        return opml_path

    def test_import_simple_feeds(
        self, manager: FeedManager, simple_opml: Path
    ) -> None:
        """Test importing simple feeds without folders."""
        feeds_added, feeds_skipped = import_opml(manager, simple_opml)

        assert feeds_added == 2
        assert feeds_skipped == 0
        assert len(manager.feeds) == 2

        urls = {feed.url for feed in manager.feeds}
        assert "gemini://example.com/feed.xml" in urls
        assert "gemini://another.com/feed.xml" in urls

    def test_import_with_folders(
        self, manager: FeedManager, opml_with_folders: Path
    ) -> None:
        """Test importing feeds organized in folders."""
        feeds_added, feeds_skipped = import_opml(manager, opml_with_folders)

        assert feeds_added == 4
        assert feeds_skipped == 0
        assert len(manager.feeds) == 4
        assert len(manager.folders) == 2

        # Check folders were created
        folder_names = {folder.name for folder in manager.folders}
        assert "Tech" in folder_names
        assert "News" in folder_names

        # Check feeds are in correct folders
        tech_folder = next(f for f in manager.folders if f.name == "Tech")
        tech_feeds = manager.get_feeds_in_folder(tech_folder.id)
        assert len(tech_feeds) == 2

        news_folder = next(f for f in manager.folders if f.name == "News")
        news_feeds = manager.get_feeds_in_folder(news_folder.id)
        assert len(news_feeds) == 1

        # Check root feed
        root_feeds = manager.get_root_feeds()
        assert len(root_feeds) == 1

    def test_import_skips_http_feeds(
        self, manager: FeedManager, opml_with_http_feeds: Path
    ) -> None:
        """Test that HTTP/HTTPS feeds are skipped during import."""
        feeds_added, feeds_skipped = import_opml(manager, opml_with_http_feeds)

        assert feeds_added == 1
        assert feeds_skipped == 2
        assert len(manager.feeds) == 1
        assert manager.feeds[0].url == "gemini://example.com/feed.xml"

    def test_import_skips_duplicates(
        self, manager: FeedManager, simple_opml: Path
    ) -> None:
        """Test that duplicate feeds are skipped."""
        # Add one feed that's in the OPML
        manager.add_feed("gemini://example.com/feed.xml", "Existing Feed")

        feeds_added, feeds_skipped = import_opml(manager, simple_opml)

        # Should skip the existing one, add the new one
        assert feeds_added == 1
        assert feeds_skipped == 1
        assert len(manager.feeds) == 2

    def test_import_into_existing_folder(
        self, manager: FeedManager, opml_with_folders: Path
    ) -> None:
        """Test importing into a folder that already exists."""
        # Create "Tech" folder beforehand
        existing_folder = manager.add_folder("Tech")
        manager.add_feed("gemini://existing.com/feed.xml", "Existing", folder_id=existing_folder.id)

        feeds_added, feeds_skipped = import_opml(manager, opml_with_folders)

        # Should still be only 2 folders (Tech already existed)
        assert len(manager.folders) == 2

        # Tech folder should have existing + imported feeds
        tech_folder = next(f for f in manager.folders if f.name == "Tech")
        tech_feeds = manager.get_feeds_in_folder(tech_folder.id)
        assert len(tech_feeds) == 3  # 1 existing + 2 imported

    def test_import_nonexistent_file(self, manager: FeedManager) -> None:
        """Test importing from a nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            import_opml(manager, Path("/nonexistent/file.opml"))

    def test_import_invalid_xml(
        self, manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test importing invalid XML raises error."""
        invalid_path = temp_config_dir / "invalid.opml"
        invalid_path.write_text("not valid xml")

        with pytest.raises(Exception):  # Will raise XML parsing error
            import_opml(manager, invalid_path)

    def test_import_invalid_opml_structure(
        self, manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test importing file with wrong root element."""
        invalid_opml = temp_config_dir / "invalid.opml"
        invalid_opml.write_text("""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Not OPML</title>
  </channel>
</rss>""")

        with pytest.raises(ValueError, match="root element is not 'opml'"):
            import_opml(manager, invalid_opml)

    def test_import_opml_without_body(
        self, manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test importing OPML without body element."""
        no_body_opml = temp_config_dir / "no_body.opml"
        no_body_opml.write_text("""<?xml version="1.0"?>
<opml version="2.0">
  <head>
    <title>No Body</title>
  </head>
</opml>""")

        with pytest.raises(ValueError, match="no 'body' element found"):
            import_opml(manager, no_body_opml)

    def test_import_empty_opml(
        self, manager: FeedManager, temp_config_dir: Path
    ) -> None:
        """Test importing OPML with no feeds."""
        empty_opml = temp_config_dir / "empty.opml"
        empty_opml.write_text("""<?xml version="1.0"?>
<opml version="2.0">
  <head>
    <title>Empty</title>
  </head>
  <body>
  </body>
</opml>""")

        feeds_added, feeds_skipped = import_opml(manager, empty_opml)

        assert feeds_added == 0
        assert feeds_skipped == 0


class TestOpmlRoundTrip:
    """Tests for exporting and re-importing OPML."""

    @pytest.fixture
    def temp_config_dir(self) -> Path:
        """Create a temporary directory for test config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_export_import_roundtrip(self, temp_config_dir: Path) -> None:
        """Test that data survives export/import round trip."""
        # Create manager with feeds
        manager1 = FeedManager(config_dir=temp_config_dir / "manager1")
        folder1 = manager1.add_folder("Tech")
        folder2 = manager1.add_folder("News")

        manager1.add_feed("gemini://root1.com/feed.xml", "Root Feed 1")
        manager1.add_feed("gemini://root2.com/feed.xml", "Root Feed 2")
        manager1.add_feed("gemini://tech1.com/feed.xml", "Tech 1", folder_id=folder1.id)
        manager1.add_feed("gemini://tech2.com/feed.xml", "Tech 2", folder_id=folder1.id)
        manager1.add_feed("gemini://news.com/feed.xml", "News", folder_id=folder2.id)

        # Export
        opml_path = temp_config_dir / "export.opml"
        export_opml(manager1, opml_path)

        # Import into new manager
        manager2 = FeedManager(config_dir=temp_config_dir / "manager2")
        feeds_added, feeds_skipped = import_opml(manager2, opml_path)

        # Verify
        assert feeds_added == 5
        assert feeds_skipped == 0
        assert len(manager2.feeds) == 5
        assert len(manager2.folders) == 2

        # Verify folder names
        folder_names = {f.name for f in manager2.folders}
        assert folder_names == {"Tech", "News"}

        # Verify feed URLs
        feed_urls = {f.url for f in manager2.feeds}
        assert feed_urls == {
            "gemini://root1.com/feed.xml",
            "gemini://root2.com/feed.xml",
            "gemini://tech1.com/feed.xml",
            "gemini://tech2.com/feed.xml",
            "gemini://news.com/feed.xml",
        }

    def test_multiple_export_import_cycles(self, temp_config_dir: Path) -> None:
        """Test multiple export/import cycles maintain data integrity."""
        manager1 = FeedManager(config_dir=temp_config_dir / "m1")
        manager1.add_folder("Tech")
        manager1.add_feed("gemini://example.com/feed.xml", "Example")

        opml1 = temp_config_dir / "export1.opml"
        export_opml(manager1, opml1)

        manager2 = FeedManager(config_dir=temp_config_dir / "m2")
        import_opml(manager2, opml1)

        opml2 = temp_config_dir / "export2.opml"
        export_opml(manager2, opml2)

        manager3 = FeedManager(config_dir=temp_config_dir / "m3")
        import_opml(manager3, opml2)

        # After two cycles, data should be intact
        assert len(manager3.feeds) == 1
        assert len(manager3.folders) == 1
        assert manager3.feeds[0].url == "gemini://example.com/feed.xml"
