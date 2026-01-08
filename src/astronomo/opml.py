"""OPML import/export for Astronomo feeds.

OPML (Outline Processor Markup Language) is an XML format commonly used
for exchanging lists of RSS/Atom feeds between feed readers.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from astronomo.feeds import FeedManager


def export_opml(manager: FeedManager, output_path: Path) -> None:
    """Export feeds to OPML format.

    Args:
        manager: FeedManager instance with feeds to export
        output_path: Path where OPML file will be written
    """
    # Create OPML structure
    opml = ET.Element("opml", version="2.0")

    # Head element with metadata
    head = ET.SubElement(opml, "head")
    title = ET.SubElement(head, "title")
    title.text = "Astronomo Feeds"
    date_created = ET.SubElement(head, "dateCreated")
    date_created.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

    # Body element with feeds
    body = ET.SubElement(opml, "body")

    # Export root-level feeds
    for feed in manager.get_root_feeds():
        ET.SubElement(
            body,
            "outline",
            type="rss",
            text=feed.title,
            title=feed.title,
            xmlUrl=feed.url,
        )

    # Export folders and their feeds
    for folder in manager.get_all_folders():
        folder_outline = ET.SubElement(
            body,
            "outline",
            text=folder.name,
            title=folder.name,
        )

        feeds_in_folder = manager.get_feeds_in_folder(folder.id)
        for feed in feeds_in_folder:
            ET.SubElement(
                folder_outline,
                "outline",
                type="rss",
                text=feed.title,
                title=feed.title,
                xmlUrl=feed.url,
            )

    # Write to file with pretty formatting
    tree = ET.ElementTree(opml)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def import_opml(manager: FeedManager, input_path: Path) -> tuple[int, int]:
    """Import feeds from OPML format.

    Args:
        manager: FeedManager instance to add feeds to
        input_path: Path to OPML file to import

    Returns:
        Tuple of (feeds_added, feeds_skipped) counts
    """
    # Parse OPML file
    tree = ET.parse(input_path)
    root = tree.getroot()

    if root.tag != "opml":
        raise ValueError("Invalid OPML file: root element is not 'opml'")

    body = root.find("body")
    if body is None:
        raise ValueError("Invalid OPML file: no 'body' element found")

    feeds_added = 0
    feeds_skipped = 0

    # Process outlines (feeds and folders)
    for outline in body.findall("outline"):
        xml_url = outline.get("xmlUrl")
        text = outline.get("text", "")
        title = outline.get("title", text)

        # Check if this is a feed (has xmlUrl) or a folder
        if xml_url:
            # It's a feed
            if not xml_url.startswith("gemini://"):
                # Skip non-Gemini feeds
                feeds_skipped += 1
                continue

            # Check if feed already exists
            if manager.feed_exists(xml_url):
                feeds_skipped += 1
                continue

            # Add the feed
            manager.add_feed(url=xml_url, title=title)
            feeds_added += 1
        else:
            # It's a folder
            folder_name = title or text
            if not folder_name:
                continue

            # Check if folder already exists
            existing_folder = None
            for folder in manager.get_all_folders():
                if folder.name == folder_name:
                    existing_folder = folder
                    break

            # Create folder if it doesn't exist
            if existing_folder is None:
                existing_folder = manager.add_folder(folder_name)

            # Process feeds within this folder
            for feed_outline in outline.findall("outline"):
                feed_url = feed_outline.get("xmlUrl")
                if not feed_url:
                    continue

                if not feed_url.startswith("gemini://"):
                    feeds_skipped += 1
                    continue

                # Check if feed already exists
                if manager.feed_exists(feed_url):
                    feeds_skipped += 1
                    continue

                feed_text = feed_outline.get("text", "")
                feed_title = feed_outline.get("title", feed_text)

                # Add the feed to the folder
                manager.add_feed(
                    url=feed_url,
                    title=feed_title,
                    folder_id=existing_folder.id,
                )
                feeds_added += 1

    return feeds_added, feeds_skipped
