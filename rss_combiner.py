import feedparser
import requests
import csv
import argparse
import os

def get_feeds_from_google_sheet(csv_url):
    resp = requests.get(csv_url)
    lines = resp.text.splitlines()
    reader = csv.reader(lines)
    feeds = [row[0] for row in reader if row]  # assume URLs in first column
    return feeds

def parse_feeds(csv_url):
    feeds = get_feeds_from_google_sheet(csv_url)
    all_entries = []
    for url in feeds:
        feed = feedparser.parse(url)
        entries = feed.entries
        all_entries.extend(entries)
    return all_entries

def remove_duplicates(entries):
    seen = set()
    unique = []
    for entry in entries:
        key = entry.get("link", entry.get("id", ""))
        if key not in seen:
            unique.append(entry)
            seen.add(key)
    return unique

def write_combined_feed(entries, feed_title, output_path):
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    title = SubElement(channel, "title")
    title.text = feed_title
    for entry in entries:
        item = SubElement(channel, "item")
        item_title = SubElement(item, "title")
        item_title.text = entry.get("title", "")
        link = SubElement(item, "link")
        link.text = entry.get("link", "")
        description = SubElement(item, "description")
        description.text = entry.get("summary", "")
    xml_str = minidom.parseString(tostring(rss)).toprettyxml(indent="  ")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-url", required=True, help="Google Sheets CSV URL")
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--no-duplicates", action="store_true")
    args = parser.parse_args()
    
    # Use the provided CSV URL or default to the one from user context
    csv_url = args.csv_url or "https://docs.google.com/spreadsheets/d/e/2PACX-1vQOJhsHTO7hWYd15XnQpGvscmeCqYa3NPT6yt6nai0gRs8ocbuTZsuh_FxxcJqIBS9_RDsSNM5fbLVp/pub?gid=1623404092&single=true&output=csv"
    
    entries = parse_feeds(csv_url)
    entries.sort(key=lambda x: x.get("published_parsed", None), reverse=True)
    if args.no_duplicates:
        entries = remove_duplicates(entries)
    write_combined_feed(entries, args.title, args.output)

if __name__ == "__main__":
    main()
