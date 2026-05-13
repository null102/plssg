"""
plssg rss - generate build/html/rss.xml from all .html pages

Walks build_html_dir directly, no need for the raw site list — the first
path component of each .html relative path is treated as the sub-site
identifier (already NN_-stripped during build).
"""
import os
import xml.etree.ElementTree as ET
from email.utils import formatdate


_ASSET_DIRS = {"assets", "images", "_img", "static", "media", "pub"}


def generate_rss(build_html_dir, sites, info, base_url=""):
    """Walk build_html_dir for *.html (excluding _temp.html), emit rss.xml.
       Sorted by mtime, newest first, capped at 50 items.
       sites arg kept for backwards compat; not actually used."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text       = info.get("rss_title", "plssg RSS")
    ET.SubElement(channel, "link").text        = base_url + info.get("rss_link", "/rss.xml")
    ET.SubElement(channel, "description").text = info.get("rss_description", "")

    items = []
    for root, dirs, files in os.walk(build_html_dir):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".")
                   and not d.startswith("_")
                   and d.lower() not in _ASSET_DIRS]
        for f in files:
            if not f.endswith(".html") or f == "_temp.html":
                continue
            full = os.path.join(root, f)
            rel  = os.path.relpath(full, build_html_dir)
            parts = rel.replace(os.sep, "/").split("/")
            # First path component is the site id (after NN_ stripping during build).
            # In flat mode there's no parent dir, so site stays "".
            site = parts[0] if len(parts) > 1 else ""
            items.append({
                "title": os.path.splitext(f)[0],
                "site":  site,
                "link":  base_url + "/" + "/".join(parts),
                "mtime": os.path.getmtime(full),
            })

    items.sort(key=lambda x: x["mtime"], reverse=True)
    for item in items[:50]:
        it = ET.SubElement(channel, "item")
        title = (f"[{item['site']}] {item['title']}"
                 if item["site"] else item["title"])
        ET.SubElement(it, "title").text   = title
        ET.SubElement(it, "link").text    = item["link"]
        ET.SubElement(it, "guid").text    = item["link"]
        ET.SubElement(it, "pubDate").text = formatdate(item["mtime"])

    out_path = os.path.join(build_html_dir, "rss.xml")
    ET.ElementTree(rss).write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"  [rss] {out_path} ({len(items)} items)")
    return out_path
