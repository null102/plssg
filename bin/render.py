"""
plssg render - file-level scheduler

Walk one sub-site's src dir, render every .md through html.py,
substitute the result into <site>/_temp.html, write <site>/<name>.html.

Conventions:
- index.md -> index.html (in same directory)
- NN_xxx.md -> xxx.html  (strip the NN_ prefix)
- _xxx and assets/ are skipped
- Sub-directories recurse
"""
import os
import re
import sys
import importlib.util

# Robustly import bin/html.py (avoids stdlib `html` shadowing trouble)
_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "plssg_html", os.path.join(_BIN_DIR, "html.py"))
plssg_html = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plssg_html)


NUM_PREFIX_RE  = re.compile(r"^(\d+)_")
MAIN_RE        = re.compile(r"<main\b[^>]*>(.*?)</main>", re.DOTALL | re.IGNORECASE)
BODY_RE        = re.compile(r"<body\b[^>]*>(.*?)</body>", re.DOTALL | re.IGNORECASE)
PAGE_TITLE_RE  = re.compile(r'<h1\b[^>]*class="page-title"[^>]*>(.*?)</h1>', re.DOTALL | re.IGNORECASE)
TITLE_RE       = re.compile(r"<title\b[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
FOOTER_RE      = re.compile(r"<footer\b[^>]*>.*?</footer>", re.DOTALL | re.IGNORECASE)
ASIDE_RE       = re.compile(r"<aside\b[^>]*>.*?</aside>", re.DOTALL | re.IGNORECASE)
SCRIPT_RE      = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
STYLE_RE       = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
TAG_STRIP_RE   = re.compile(r"<[^>]+>")


def strip_num_prefix(name):
    return NUM_PREFIX_RE.sub("", name)


def display_name(name):
    name = strip_num_prefix(name)
    return name.replace("_", " ").replace("-", " ")


def extract_first_h1(md_text):
    """Find first '# heading' line for page title, if any."""
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def extract_html_article(html_text):
    """Extract article body from a full HTML document.
       Strategy: take <main> content, strip <aside>, <footer>, <script>,
       <style>, <h1 class="page-title">. Fall back to <body> if no <main>."""
    m = MAIN_RE.search(html_text)
    if m:
        content = m.group(1)
    else:
        b = BODY_RE.search(html_text)
        content = b.group(1) if b else html_text
    content = SCRIPT_RE.sub("", content)
    content = STYLE_RE.sub("", content)
    content = ASIDE_RE.sub("", content)
    content = FOOTER_RE.sub("", content)
    content = PAGE_TITLE_RE.sub("", content)
    return content.strip()


def extract_html_page_title(html_text):
    """Find a sensible page title from the HTML.
       Prefer <h1 class="page-title">, fall back to <title>."""
    m = PAGE_TITLE_RE.search(html_text)
    if m:
        return TAG_STRIP_RE.sub("", m.group(1)).strip()
    m = TITLE_RE.search(html_text)
    if m:
        t = TAG_STRIP_RE.sub("", m.group(1)).strip()
        # Strip " — site name" or " | site name" suffix
        for sep in (" — ", " | ", " - "):
            if sep in t:
                t = t.split(sep)[0].strip()
                break
        return t
    return None


_ASSET_DIRS = {"assets", "images", "_img", "static", "media", "pub"}

# Matches href="/foo" or src="/foo" but NOT href="//cdn" (protocol-relative).
_ABS_URL_RE = re.compile(r'(href|src)="(/(?!/)[^"]*)"')


def _to_relative(html, depth):
    """Rewrite absolute URLs (starting with single '/') to relative paths
       so the page works under both http(s):// and file://.
       depth = number of directory levels from build_html_root to the page.
       e.g. build/html/index.html         → depth 0 ('' prefix)
            build/html/foo/index.html     → depth 1 ('../')
            build/html/foo/bar/baz.html   → depth 2 ('../../')"""
    prefix = "../" * depth
    def fix(m):
        attr, path = m.group(1), m.group(2)
        # path always starts with a single '/'. Strip it, prepend the
        # relative-path prefix.
        new = prefix + path.lstrip("/")
        # If the link targets a directory (ends with '/' or empty after
        # stripping), explicitly point at index.html. file:// browsers do
        # NOT auto-serve index.html from directory links and would show a
        # directory listing instead; HTTP servers serve it either way.
        if new == "" or new.endswith("/"):
            new += "index.html"
        return f'{attr}="{new}"'
    return _ABS_URL_RE.sub(fix, html)


def post_process_relative_urls(build_html_dir):
    """Walk build_html_dir/*.html and rewrite absolute href/src to relative.
       Lets users `right-click → open in browser` any single .html via file://
       without breaking CSS / links / images."""
    n = 0
    for root, dirs, files in os.walk(build_html_dir):
        for f in files:
            if not f.endswith(".html") or f == "_temp.html":
                continue
            full = os.path.join(root, f)
            rel  = os.path.relpath(full, build_html_dir)
            depth = rel.count(os.sep)
            with open(full, "r", encoding="utf-8") as fp:
                html = fp.read()
            new = _to_relative(html, depth)
            if new != html:
                with open(full, "w", encoding="utf-8") as fp:
                    fp.write(new)
                n += 1
    return n


def _synth_index_html(src_dir, files, subdirs):
    """Build a minimal article body listing the contents of a directory that
       has no index.md / index.html. Used as a fallback so that navigating to
       any directory always lands on *something* instead of a 404."""
    name = display_name(os.path.basename(src_dir)) or "/"
    out = [f"<h1>{name}</h1>",
           "<p><em>(this directory has no <code>index.md</code>; "
           "showing its contents instead)</em></p>",
           "<ul>"]
    for f in sorted(files):
        if not f.endswith((".md", ".html")):
            continue
        base = os.path.splitext(f)[0]
        if base.lower() == "index":
            continue
        link = strip_num_prefix(base) + ".html"
        out.append(f'<li><a href="{link}">{display_name(base)}</a></li>')
    for d in sorted(subdirs):
        link = strip_num_prefix(d) + "/"
        out.append(f'<li><a href="{link}">{display_name(d)}/</a></li>')
    out.append("</ul>")
    return "\n".join(out)


def render_site(site_name, site_src, site_build, html_conf_path):
    """For each .md or .html under site_src, render to .html under site_build,
       preserving sub-directory structure (with NN_ prefix stripped from paths).
       Any directory without an index.md / index.html gets a synthesised
       directory-listing index.html so navigation never 404s."""
    conf = plssg_html.load_html_conf(html_conf_path)

    temp_path = os.path.join(site_build, "_temp.html")
    with open(temp_path, "r", encoding="utf-8") as f:
        template = f.read()

    def write(out_path, article_html, page_title):
        final_html = template
        final_html = final_html.replace("{{article_content}}", article_html)
        final_html = final_html.replace("{{page_title}}", page_title or "")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_html)

    def out_dir_for(rel_root):
        if rel_root == ".":
            return site_build
        cleaned = "/".join(strip_num_prefix(p) for p in rel_root.split(os.sep))
        return os.path.join(site_build, cleaned)

    count = 0
    for root, dirs, files in os.walk(site_src):
        # Prune hidden / _xxx / asset dirs.
        # For the ROOT pseudo-site (site_name==""), also prune all sub-dirs at
        # the top level — those are sub-sites handled by their own render pass.
        if site_name == "" and root == site_src:
            kept_dirs = []
        else:
            kept_dirs = [d for d in sorted(dirs)
                         if not d.startswith(".")
                         and not d.startswith("_")
                         and d.lower() not in _ASSET_DIRS]
        dirs[:] = kept_dirs
        rel_root = os.path.relpath(root, site_src)

        # If both <name>.md and <name>.html exist, prefer .md
        bases_with_md = {os.path.splitext(f)[0] for f in files if f.endswith(".md")}

        for fname in sorted(files):
            if fname.endswith(".md"):
                kind = "md"
            elif fname.endswith(".html"):
                base = os.path.splitext(fname)[0]
                if base in bases_with_md:
                    continue
                kind = "html"
            else:
                continue

            src_path = os.path.join(root, fname)
            with open(src_path, "r", encoding="utf-8") as f:
                src_text = f.read()

            if kind == "md":
                article_html = plssg_html.render_markdown(src_text, conf)
                page_title = extract_first_h1(src_text)
            else:
                article_html = extract_html_article(src_text)
                page_title = extract_html_page_title(src_text)

            name_no_ext = os.path.splitext(fname)[0]
            if name_no_ext.lower() == "index":
                out_basename = "index.html"
            else:
                out_basename = strip_num_prefix(name_no_ext) + ".html"

            out_path = os.path.join(out_dir_for(rel_root), out_basename)
            if not page_title:
                page_title = display_name(name_no_ext)
            write(out_path, article_html, page_title)
            count += 1
            print(f"    [render] {os.path.relpath(out_path, site_build)}")

        # If this directory lacks an index, synth one so navigation doesn't 404
        has_index = any(f.lower() in ("index.md", "index.html") for f in files)
        if not has_index and (kept_dirs or any(f.endswith((".md", ".html")) for f in files)):
            article_html = _synth_index_html(root, files, kept_dirs)
            page_title = display_name(os.path.basename(root)) or display_name(site_name)
            out_path = os.path.join(out_dir_for(rel_root), "index.html")
            write(out_path, article_html, page_title)
            count += 1
            print(f"    [synth ] {os.path.relpath(out_path, site_build)}")
    return count
