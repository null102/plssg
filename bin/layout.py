"""
plssg layout module - CSS + template + navigation + footer + assets

Responsibilities:
- Read etc/themes.conf and generate per-site CSS overlaying DEFAULT_CSS
- Read etc/info.conf for global site info (title, logo, footer)
- Build top horizontal nav (sub-site switcher)
- Build left sidebar nav (recursive directory walk, skip index.md, skip _xxx)
- Render _temp.html (template with placeholders filled except {{article_content}})
- Copy src/<site>/assets/ verbatim to build/html/<site>/assets/
"""
import os
import re
import shutil
import configparser


# Default CSS skeleton.
# All themeable values are CSS variables defined in :root below.
# Override any of them via etc/themes.conf [global] or [<site_id>] sections.
DEFAULT_CSS = """\
/* plssg default CSS - monochrome skeleton; all knobs are CSS variables */
:root {
  /* colors */
  --color-text:        #000;
  --color-bg:          #fff;
  --color-border:      #000;
  --color-hover-bg:    #eee;
  --color-code-bg:     #f5f5f5;
  /* font families */
  --font-family-body:  Helvetica, Verdana, Arial, 'Liberation Sans', FreeSans, sans-serif;
  --font-family-mono:  Menlo, Consolas, 'Liberation Mono', monospace;
  /* font sizes */
  --font-body:    84%;
  --font-nav:     1.5em;
  --font-banner:  1.9em;
  --font-sidebar: 120%;
  --font-h1:      145.5%;
  --font-h2:      115.5%;
  --font-h3:      105%;
  --font-pre:     1.05em;
  --font-code:    0.95em;
  --font-footer:  0.95em;
  /* layout */
  --sidebar-width:      16em;
  --content-max-width:  70em;
}
body {
  color: var(--color-text);
  background-color: var(--color-bg);
  font-family: var(--font-family-body);
  font-size: var(--font-body);
  margin: 0;
  padding: 0;
}
a { text-decoration: none; color: var(--color-text); }
a:hover { text-decoration: underline; }

/* Header */
header { padding: 0; margin: 0; }
header nav {
  background-color: var(--color-bg);
  color: var(--color-text);
  font-size: var(--font-nav);
  min-height: 1.6em;
  padding: 0.25ex 0.4em;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
}
header nav a { color: var(--color-text); padding: 0 0.5ex; }
header nav a:hover { background-color: var(--color-hover-bg); text-decoration: none; }
.home-button { font-weight: bold; display: inline-flex; align-items: center; gap: 0.4em; }
/* anchor logo size to root font so logo_size is independent of --font-nav */
.site-logo { font-size: 1rem; vertical-align: middle; }
.top-nav a { margin-left: 0.6em; }
.top-nav a.current {
  background-color: var(--color-text);
  color: var(--color-bg);
  padding: 0 0.4ex;
}

header h1 {
  background-color: var(--color-bg);
  color: var(--color-text);
  font-size: var(--font-banner);
  font-weight: normal;
  margin: 0;
  padding: 0.25ex 0 0.25ex 4mm;
  border: solid 0 var(--color-border);
  border-width: 0 0 1px 0;
}
header h1 a {
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
}
header h1 a, header h1 a:hover {
  color: var(--color-text);
  text-decoration: none;
}

/* Sidebar */
#side-bar {
  width: var(--sidebar-width);
  float: left;
  clear: left;
  border-right: 1px solid var(--color-border);
  background-color: var(--color-bg);
  padding: 0 0 0.3em 0;
  margin: 0;
}
#side-bar ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
#side-bar li { margin: 0; padding: 0.1ex 0; }
#side-bar li ul { padding-left: 0.6em; }
#side-bar a {
  color: var(--color-text);
  display: block;
  padding: 0.25em 1ex 0.25em 2mm;
  font-weight: bold;
  font-size: var(--font-sidebar);
  border-left: 0.2em solid transparent;
}
#side-bar a.current,
#side-bar a:hover {
  color: var(--color-text);
  background-color: var(--color-hover-bg);
  border-left: 0.2em solid var(--color-border);
  text-decoration: none;
}
#side-bar span {
  display: block;
  padding: 0.25em 1ex 0.25em 2mm;
  font-weight: bold;
  color: var(--color-text);
  font-size: var(--font-sidebar);
}

/* Main content area */
article {
  max-width: var(--content-max-width);
  color: var(--color-text);
  background-color: transparent;
  text-align: justify;
  line-height: 1.5em;
  margin: 0 0 0 var(--sidebar-width);
  padding: 0.5mm 5mm 5mm 5mm;
  border-left: 1px solid var(--color-border);
}
article h1, article h2 {
  color: var(--color-text);
  font-size: var(--font-h1);
  font-weight: bold;
  margin: 1.5em 0 0.3em 0;
  padding: 0.5ex 0 0.5ex 0.6ex;
  border-bottom: 2px solid var(--color-border);
}
article h2 {
  font-size: var(--font-h2);
  border-bottom: 1px solid var(--color-border);
}
article h3 {
  color: var(--color-text);
  font-size: var(--font-h3);
  font-weight: bold;
  margin: 1.2em 0 0.3em 0;
}
article p { margin: 1em 1ex; }
article ul, article ol { margin-left: 1ex; }
article pre {
  background: var(--color-code-bg);
  padding: 0.6em 0.9em;
  margin-left: 2em;
  border-left: 3px solid var(--color-border);
  font-family: var(--font-family-mono);
  font-size: var(--font-pre);
  overflow-x: auto;
}
article code {
  background: var(--color-code-bg);
  color: var(--color-text);
  padding: 0.05em 0.3em;
  border-radius: 2px;
  font-family: var(--font-family-mono);
  font-size: var(--font-code);
}
article pre code { background: none; padding: 0; color: inherit; }
article blockquote {
  border-left: 2px solid var(--color-border);
  color: var(--color-text);
  font-style: italic;
  margin: 1em 2em;
  padding-left: 1em;
}
article table { border: solid 1px var(--color-border); border-collapse: collapse; margin: 1em; }
article th { background-color: var(--color-bg); border: 1px solid var(--color-border);
             color: var(--color-text); padding: 0.3em 0.6em; text-align: center; }
article td { background-color: var(--color-bg); border: 1px solid var(--color-border);
             padding: 0.3em 0.6em; }
article img { max-width: 100%; height: auto; }

/* Footer */
footer {
  color: var(--color-text);
  background-color: var(--color-bg);
  padding: 1em;
  clear: both;
  border-top: 1px solid var(--color-border);
}
footer a { color: var(--color-text); }
.site-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-footer);
}
.site-footer img { height: 1.2em; vertical-align: middle; }
.footer-left, .footer-center, .footer-right {
  display: flex; gap: 0.6em; align-items: center;
}
"""


NUM_PREFIX_RE = re.compile(r"^(\d+)_")


def strip_num_prefix(name):
    """01_intro -> intro"""
    return NUM_PREFIX_RE.sub("", name)


def display_name(name):
    """01_intro -> intro (also _ and - to spaces, no title-case)"""
    name = strip_num_prefix(name)
    return name.replace("_", " ").replace("-", " ")


def list_sites(src_dir):
    """List level-1 sub-site directories under src/ (always returned).
       Hidden (./_) dirs and asset dirs excluded.
       Note: root-level .md/.html files at src/ are handled separately as a
       'root pseudo-site' by main.py and are NOT in this list."""
    if not os.path.exists(src_dir):
        return []
    subdirs = []
    for name in os.listdir(src_dir):
        if name.startswith(".") or name.startswith("_"):
            continue
        full = os.path.join(src_dir, name)
        if os.path.isdir(full) and name.lower() not in _ASSET_DIRS:
            subdirs.append(name)
    return sorted(subdirs)


def has_root_content(src_dir):
    """True iff src_dir has any .md or .html file directly at its top level
       (these become the 'root pseudo-site' rendered at build root)."""
    if not os.path.exists(src_dir):
        return False
    for name in os.listdir(src_dir):
        full = os.path.join(src_dir, name)
        if os.path.isfile(full) and name.endswith((".md", ".html")):
            return True
    return False


def read_info_conf(path):
    """Read etc/info.conf as INI, return a dict with sensible defaults."""
    info = {
        "site_title":       "plssg",
        "tagline":          "",
        "favicon":          "",
        "logo":             "",
        "logo_size":        "1.2em",
        "footer_left":      "",
        "footer_center":    "",
        "footer_right":     "",
        "rss_title":        "plssg RSS",
        "rss_description":  "",
        "rss_link":         "/rss.xml",
    }
    if not os.path.exists(path):
        return info
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(path, encoding="utf-8")
    if "site" in cfg:
        s = cfg["site"]
        info["site_title"]       = s.get("title",            info["site_title"]).strip().strip('"')
        info["tagline"]          = s.get("tagline",          info["tagline"]).strip().strip('"')
        info["favicon"]          = s.get("favicon",          info["favicon"]).strip().strip('"')
        info["logo"]             = s.get("logo",             info["logo"]).strip().strip('"')
        info["logo_size"]        = s.get("logo_size",        info["logo_size"]).strip().strip('"')
    if "footer" in cfg:
        f = cfg["footer"]
        info["footer_left"]   = f.get("left",   "")
        info["footer_center"] = f.get("center", "")
        info["footer_right"]  = f.get("right",  "")
    if "rss" in cfg:
        r = cfg["rss"]
        info["rss_title"]       = r.get("title",       info["rss_title"])
        info["rss_description"] = r.get("description", "")
        info["rss_link"]        = r.get("link",        info["rss_link"])
    return info


def ensure_themes_sections(themes_conf_path, sites):
    """For each sub-site, ensure themes.conf has an empty [<site_id>] section.
       Appends missing ones to the end of the file; existing sections (and their
       keys/values) are left untouched. No-op if themes.conf doesn't exist."""
    if not sites or not os.path.exists(themes_conf_path):
        return []
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(themes_conf_path, encoding="utf-8")
    existing = set(cfg.sections())
    to_add = [site_id_for(s) for s in sites
              if site_id_for(s) and site_id_for(s) not in existing]
    if not to_add:
        return []
    with open(themes_conf_path, "r", encoding="utf-8") as f:
        content = f.read()
    if content and not content.endswith("\n"):
        content += "\n"
    appended = []
    for sid in to_add:
        appended.append(
            f"\n# auto-generated for sub-site; override any [global] key here\n"
            f"[{sid}]\n"
        )
    with open(themes_conf_path, "w", encoding="utf-8") as f:
        f.write(content + "".join(appended))
    return to_add


def _themes_section_to_css_vars(section):
    """Translate an INI section's key=value pairs into a single :root { ... } block.
       INI key 'color_text' → CSS var '--color-text'. Empty section → empty string."""
    decls = []
    for k, v in section.items():
        v = v.strip().strip('"').strip("'")
        if not v:
            continue
        var_name = "--" + k.strip().replace("_", "-")
        decls.append(f"  {var_name}: {v};")
    if not decls:
        return ""
    return ":root {\n" + "\n".join(decls) + "\n}\n"


def generate_css(site_name, output_dir, themes_conf_path, info=None):
    """Write <output_dir>/style.css.
       Layer order: DEFAULT_CSS → themes.conf [global] → themes.conf [<site_id>].
       Later layers win because CSS cascade prefers later :root {} blocks.
       Any key in a themes.conf section becomes a CSS variable: 'color_text' → '--color-text'.
       site_id is the NN_-stripped sub-site name (e.g. [Yifan Lu] not [01_Yifan Lu])."""
    css = DEFAULT_CSS
    if os.path.exists(themes_conf_path):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(themes_conf_path, encoding="utf-8")
        if "global" in cfg:
            block = _themes_section_to_css_vars(cfg["global"])
            if block:
                css += "\n" + block
        lookup_key = site_id_for(site_name)
        if lookup_key and lookup_key in cfg:
            block = _themes_section_to_css_vars(cfg[lookup_key])
            if block:
                css += "\n" + block
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "style.css")
    with open(path, "w", encoding="utf-8") as f:
        f.write(css)
    return path


def site_id_for(site_name):
    """The URL/build-path identifier for a sub-site: NN_ prefix stripped.
       (Sub-site source dir lookup still uses the raw name with NN_.)"""
    return strip_num_prefix(site_name) if site_name else ""


def build_top_nav(sites, current_site):
    """Horizontal nav listing all sub-sites. Current site marked.
       Empty in flat mode (single anonymous site).
       NN_ prefixes are stripped from both display and href."""
    if not sites or (len(sites) == 1 and not sites[0]):
        return ""
    items = []
    for s in sites:
        cls = ' class="current"' if s == current_site else ""
        sid = site_id_for(s)
        items.append(f'<a href="/{sid}/"{cls}>{display_name(s)}</a>')
    return "\n  ".join(items)


def url_root_for(site_name):
    """Build-root-relative URL prefix for a site. Flat='/', multi='/<stripped>/'."""
    sid = site_id_for(site_name)
    return f"/{sid}/" if sid else "/"


_ASSET_DIRS = {"assets", "images", "_img", "static", "media", "pub"}
_CONTENT_EXTS = (".md", ".html")


def _walk_for_sidebar(path, url_root, rel=""):
    """Recursive helper for build_side_nav.
       Returns <ul>...</ul> HTML for the given directory.
       url_root is e.g. '/zone/' or '/' (already includes trailing slash)."""
    try:
        items = sorted(os.listdir(path))
    except FileNotFoundError:
        return ""
    parts = ["<ul>"]
    for item in items:
        full = os.path.join(path, item)
        if item.startswith(".") or item.startswith("_"):
            continue
        if item.lower() in _ASSET_DIRS:
            continue
        if item.lower() in ("index.md", "index.html"):
            continue
        if os.path.isfile(full) and item.endswith(_CONTENT_EXTS):
            base = os.path.splitext(item)[0]
            html_name = strip_num_prefix(base)
            disp = display_name(base)
            href = f"{url_root}{rel}{html_name}.html"
            parts.append(f'<li><a href="{href}">{disp}</a></li>')
        elif os.path.isdir(full):
            disp = display_name(item)
            sub_rel = rel + strip_num_prefix(item) + "/"
            has_index = (os.path.exists(os.path.join(full, "index.md")) or
                         os.path.exists(os.path.join(full, "index.html")))
            if has_index:
                href = f"{url_root}{sub_rel}"
                parts.append(f'<li><a href="{href}">{disp}</a>')
            else:
                parts.append(f'<li><span>{disp}</span>')
            sub = _walk_for_sidebar(full, url_root, sub_rel)
            if sub:
                parts.append(sub)
            parts.append("</li>")
    parts.append("</ul>")
    return "\n".join(parts)


def _list_root_only(src_dir, url_root):
    """Single-level listing for the root pseudo-site: only top-level files,
       no recursion into level-1 directories (those are sub-sites listed in top nav)."""
    if not os.path.isdir(src_dir):
        return ""
    parts = ["<ul>"]
    for item in sorted(os.listdir(src_dir)):
        if item.startswith(".") or item.startswith("_"):
            continue
        if item.lower() in _ASSET_DIRS:
            continue
        if item.lower() in ("index.md", "index.html"):
            continue
        full = os.path.join(src_dir, item)
        if os.path.isfile(full) and item.endswith(_CONTENT_EXTS):
            base = os.path.splitext(item)[0]
            html_name = strip_num_prefix(base)
            disp = display_name(base)
            href = f"{url_root}{html_name}.html"
            parts.append(f'<li><a href="{href}">{disp}</a></li>')
    parts.append("</ul>")
    # If the only item was the wrapper, return empty so sidebar can be omitted/empty
    return "\n".join(parts) if len(parts) > 2 else ""


def build_side_nav(site_name, site_src):
    """Build the sidebar <ul> tree for one site.
       For the root pseudo-site (site_name==''), only top-level files are listed
       (sub-site dirs are top-nav items, not sidebar entries)."""
    if site_name == "":
        return _list_root_only(site_src, url_root_for(site_name))
    return _walk_for_sidebar(site_src, url_root_for(site_name))


_LOGO_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def _find_site_logo(site_src_raw, site_id, themes_conf_path):
    """Resolve the per-sub-site logo shown on the orange <h1> band.
       Priority:
         1. themes.conf [<site_id>] logo / logo_size
         2. Auto-detect src/<raw_site>/assets/logo.{png|jpg|jpeg|gif|svg|webp}
       Returns (logo_url, logo_size). Empty url means no logo."""
    logo, size = "", "1.5em"
    if not site_id:
        return logo, size
    if os.path.exists(themes_conf_path):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(themes_conf_path, encoding="utf-8")
        if site_id in cfg:
            sec = cfg[site_id]
            if "logo" in sec:
                logo = sec["logo"].strip().strip('"')
            if "logo_size" in sec:
                size = sec["logo_size"].strip().strip('"')
    if not logo and site_src_raw:
        assets_dir = os.path.join(site_src_raw, "assets")
        if os.path.isdir(assets_dir):
            for ext in _LOGO_EXTS:
                if os.path.isfile(os.path.join(assets_dir, "logo" + ext)):
                    logo = f"/{site_id}/assets/logo{ext}"
                    break
    return logo, size


def _merge_site_info(global_info, site_src):
    """Per-site override: src/<site>/assets/info.conf can override global keys."""
    out = dict(global_info)
    site_info_path = os.path.join(site_src, "assets", "info.conf")
    if os.path.exists(site_info_path):
        override = read_info_conf(site_info_path)
        for k, v in override.items():
            if v and v != global_info.get(k, ""):
                out[k] = v
    return out


def generate_temp_html(site_name, site_src, site_build, sites,
                        template_path, info, themes_conf_path=None):
    """Render etc/template.html with all per-site placeholders filled
       (except {{article_content}} and {{page_title}}, left for render.py).
       Output: <site_build>/_temp.html"""
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    site_info = _merge_site_info(info, site_src)
    top_nav   = build_top_nav(sites, site_name)
    side_nav  = build_side_nav(site_name, site_src)

    url_root = url_root_for(site_name)
    # current_title: shown in the orange <h1> band. For the root pseudo-site
    # it's the global site title; for a sub-site it's the sub-site's display
    # name (NN_ stripped, underscores→spaces).
    if site_name:
        current_title = display_name(site_name)
    else:
        current_title = site_info.get("tagline") or site_info["site_title"]
    # logo_html: GLOBAL logo for the blue banner home-button.
    if site_info["logo"]:
        logo_html = (f'<img class="site-logo" src="{site_info["logo"]}" alt="" '
                     f'style="height: {site_info["logo_size"]}">')
    else:
        logo_html = ""
    # site_logo_html: PER-SUB-SITE logo for the orange <h1> band.
    # Only applies to sub-sites; root pseudo-site has no per-site logo.
    site_logo_html = ""
    if site_name and themes_conf_path:
        sl, sl_size = _find_site_logo(site_src, site_id_for(site_name), themes_conf_path)
        if sl:
            site_logo_html = (f'<img class="site-logo" src="{sl}" alt="" '
                              f'style="height: {sl_size}">')

    favicon = site_info.get("favicon", "")
    fav_ver = site_info.get("favicon_version", "")
    if favicon and fav_ver:
        favicon = f"{favicon}?v={fav_ver}"

    html = template
    html = html.replace("{{url_root}}",      url_root)
    html = html.replace("{{site_title}}",    site_info["site_title"])
    html = html.replace("{{current_title}}", current_title)
    html = html.replace("{{favicon}}",       favicon)
    html = html.replace("{{logo_html}}",      logo_html)
    html = html.replace("{{site_logo_html}}", site_logo_html)
    html = html.replace("{{top_nav}}",       top_nav)
    html = html.replace("{{side_nav}}",      side_nav)
    html = html.replace("{{footer_left}}",   site_info["footer_left"])
    html = html.replace("{{footer_center}}", site_info["footer_center"])
    html = html.replace("{{footer_right}}",  site_info["footer_right"])

    os.makedirs(site_build, exist_ok=True)
    out_path = os.path.join(site_build, "_temp.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def mirror_favicon(info, html_dir):
    """Copy info['favicon'] to <html_dir>/favicon.ico so browsers' default
       /favicon.ico probe (separate from the explicit <link rel="icon">) hits 200.
       Assumes copy_assets has already populated <html_dir>/.
       Returns the file's int(mtime) as a cache-busting version, or None if no
       favicon is configured / source file is missing."""
    rel = info.get("favicon", "").lstrip("/")
    if not rel:
        return None
    src = os.path.join(html_dir, rel)
    if not os.path.isfile(src):
        return None
    dst = os.path.join(html_dir, "favicon.ico")
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    return int(os.path.getmtime(src))


def copy_assets(site_src, site_build):
    """Copy any per-site static-asset dir (assets/, images/, _img/, static/,
       media/, pub/) verbatim into <site_build>/. Returns list of dst paths."""
    copied = []
    for name in _ASSET_DIRS:
        src = os.path.join(site_src, name)
        if os.path.isdir(src):
            dst = os.path.join(site_build, name)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            copied.append(dst)
    return copied


def ensure_asset_dirs(parent_dir):
    """Auto-create assets/img/ and assets/file/ under parent_dir if missing.
       Convention:
         <parent>/assets/         site-level files (favicon, logo, etc.)
         <parent>/assets/img/     images referenced by content
         <parent>/assets/file/    non-image downloads (PDFs, archives, etc.)
       parent_dir is typically SRC_DIR or src/<sub-site>/."""
    assets = os.path.join(parent_dir, "assets")
    os.makedirs(os.path.join(assets, "img"),  exist_ok=True)
    os.makedirs(os.path.join(assets, "file"), exist_ok=True)
    return assets
