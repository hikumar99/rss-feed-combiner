import feedparser
import requests
import csv
import argparse
import os
import time
from email.utils import parsedate, formatdate

def get_feeds_from_google_sheet(csv_url):
    """Fetches a list of RSS feed URLs from a published Google Sheet CSV."""
    resp = requests.get(csv_url)
    lines = resp.text.splitlines()
    reader = csv.reader(lines)
    feeds = [row[0] for row in reader if row and row[0].strip()]
    return feeds

def get_entry_date(entry):
    """Safely gets a date from a feed entry, with fallbacks."""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return entry.published_parsed
    elif hasattr(entry, 'published') and entry.published:
        try:
            # Parse the date string into a time.struct_time tuple
            parsed_tuple = parsedate(entry.published)
            if parsed_tuple:
                return time.struct_time(parsed_tuple)
        except Exception:
            # Ignore parsing errors
            pass
    # Fallback to the current time if no date is found
    return time.gmtime()

def parse_feeds(csv_url):
    """Parses multiple RSS feeds from a list of URLs."""
    feeds = get_feeds_from_google_sheet(csv_url)
    all_entries = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                # Log non-well-formed feeds but continue
                print(f"WARNING: Feed may be malformed: {url}")
            all_entries.extend(feed.entries)
        except Exception as e:
            print(f"ERROR: Could not parse feed {url}: {e}")
            continue
    return all_entries

def remove_duplicates(entries):
    """Removes duplicate entries based on their link."""
    seen_links = set()
    unique_entries = []
    for entry in entries:
        link = entry.get("link", "")
        if link and link not in seen_links:
            unique_entries.append(entry)
            seen_links.add(link)
    return unique_entries

def write_combined_feed(entries, feed_title, output_path):
    """Writes a list of entries to a combined RSS XML file."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    title = SubElement(channel, "title")
    title.text = feed_title

    for entry in entries:
        item = SubElement(channel, "item")
        
        # Add core elements
        item_title = SubElement(item, "title")
        item_title.text = entry.get("title", "No Title")
        link = SubElement(item, "link")
        link.text = entry.get("link", "")
        description = SubElement(item, "description")
        description.text = entry.get("summary", "")
        
        # Add the publication date
        pub_date_element = SubElement(item, "pubDate")
        date_tuple = get_entry_date(entry)
        # Format the date into RFC 822 format required for RSS
        pub_date_element.text = formatdate(time.mktime(date_tuple))

    # Create a nicely formatted XML string
    xml_str = minidom.parseString(tostring(rss, 'utf-8')).toprettyxml(indent="  ")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

def main():
    """Main function to run the RSS combiner."""
    parser = argparse.ArgumentParser(description="Combine multiple RSS feeds into one.")
    parser.add_argument("--csv-url", required=True, help="URL of the Google Sheet published as CSV.")
    parser.add_argument("--output", required=True, help="Path for the output combined.xml file.")
    parser.add_argument("--title", default="My Combined RSS Feed", help="Title for the combined feed.")
    parser.add_argument("--no-duplicates", action="store_true", help="Remove duplicate entries based on link.")
    
    args = parser.parse_args()
    
    # Parse all entries from the feed URLs
    entries = parse_feeds(args.csv_url)
    
    # Sort entries by date, newest first, using the robust date getter
    entries.sort(key=get_entry_date, reverse=True)
    
    # Remove duplicates if requested
    if args.no_duplicates:
        entries = remove_duplicates(entries)
        
    # Write the final combined feed
    write_combined_feed(entries, args.title, args.output)
    print(f"Successfully generated combined RSS feed with {len(entries)} entries.")

if __name__ == "__main__":
    main()
