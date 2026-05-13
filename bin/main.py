#!/usr/bin/env python3
"""
plssg main entry point
Usage:  python3 bin/main.py
Pipeline:
  1. Walk src/ to enumerate sub-sites
  2. For each site:
     a. layout.generate_css         -> build/html/<site>/style.css
     b. layout.generate_temp_html   -> build/html/<site>/_temp.html
     c. render.render_site          -> build/html/<site>/...*.html
     d. layout.copy_assets          -> build/html/<site>/assets/...
  3. rss.generate_rss               -> build/html/rss.xml
  4. (optional) tex.generate_site_tex per site -> build/tex/<site>.tex
"""
import os
import shutil
import sys

BIN_DIR      = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BIN_DIR, ".."))
sys.path.insert(0, BIN_DIR)

SRC_DIR       = os.path.join(PROJECT_ROOT, "src")
BUILD_DIR     = os.path.join(PROJECT_ROOT, "build")
HTML_DIR      = os.path.join(BUILD_DIR, "html")
TEX_DIR       = os.path.join(BUILD_DIR, "tex")
ETC_DIR       = os.path.join(PROJECT_ROOT, "etc")
TEMPLATE_HTML = os.path.join(ETC_DIR, "template.html")
TEMPLATE_TEX  = os.path.join(ETC_DIR, "template.tex")
THEMES_CONF   = os.path.join(ETC_DIR, "themes.conf")
INFO_CONF     = os.path.join(ETC_DIR, "info.conf")
HTML_CONF     = os.path.join(ETC_DIR, "html.conf")

import layout
import render
import rss
import tex


def main():
    if not os.path.exists(TEMPLATE_HTML):
        print(f"[plssg] FATAL: missing {TEMPLATE_HTML}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(SRC_DIR):
        print(f"[plssg] FATAL: missing {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(HTML_DIR, exist_ok=True)

    info  = layout.read_info_conf(INFO_CONF)
    sites = layout.list_sites(SRC_DIR)
    root_has = layout.has_root_content(SRC_DIR)

    # Auto-create assets/img/ and assets/file/ under src/ and each sub-site.
    # First run creates empty skeleton; subsequent runs are no-ops.
    layout.ensure_asset_dirs(SRC_DIR)
    for site in sites:
        layout.ensure_asset_dirs(os.path.join(SRC_DIR, site))

    # Auto-append empty [<site_id>] sections to themes.conf for any new sub-site,
    # so the user can drop overrides in without hand-typing the section header.
    added = layout.ensure_themes_sections(THEMES_CONF, sites)
    if added:
        print(f"[plssg] added themes.conf sections: {', '.join(added)}")

    if not sites and not root_has:
        print(f"[plssg] no content found under {SRC_DIR}")
        return

    if root_has:
        print("[plssg] sites: <root>, " + ", ".join(sites))
    else:
        print(f"[plssg] sites: {', '.join(sites)}")

    # Always copy root-level src/assets/ (and any other root asset dirs) to the
    # build root, so favicons / shared resources are served at /assets/...
    layout.copy_assets(SRC_DIR, HTML_DIR)
    # Mirror favicon to build root so the browser's default /favicon.ico probe hits 200.
    # Returned int(mtime) is used as a ?v=... cache-buster on the explicit <link rel="icon">.
    fav_ver = layout.mirror_favicon(info, HTML_DIR)
    if fav_ver is not None:
        info["favicon_version"] = str(fav_ver)

    # Root pseudo-site: render src/index.md (and any other src/*.md) at the build root.
    # The root's sidebar lists only top-level files (sub-site dirs belong to top nav).
    if root_has:
        print("[plssg] building <root>")
        layout.generate_css("", HTML_DIR, THEMES_CONF, info)
        layout.generate_temp_html(
            site_name="",
            site_src=SRC_DIR,
            site_build=HTML_DIR,
            sites=sites,
            template_path=TEMPLATE_HTML,
            info=info,
            themes_conf_path=THEMES_CONF,
        )
        render.render_site(
            site_name="",
            site_src=SRC_DIR,
            site_build=HTML_DIR,
            html_conf_path=HTML_CONF,
        )

    for site in sites:
        # site == "" means flat mode (single site at the build root)
        # site_src uses the raw dir name (with NN_ prefix); URLs/build paths
        # use the stripped id (NN_ removed).
        site_src   = os.path.join(SRC_DIR, site) if site else SRC_DIR
        site_id    = layout.site_id_for(site)
        site_build = os.path.join(HTML_DIR, site_id) if site_id else HTML_DIR
        os.makedirs(site_build, exist_ok=True)

        label = site if site else "(flat)"
        print(f"[plssg] building {label}")
        layout.generate_css(site, site_build, THEMES_CONF, info)
        layout.generate_temp_html(
            site_name=site,
            site_src=site_src,
            site_build=site_build,
            sites=sites,
            template_path=TEMPLATE_HTML,
            info=info,
            themes_conf_path=THEMES_CONF,
        )
        render.render_site(
            site_name=site,
            site_src=site_src,
            site_build=site_build,
            html_conf_path=HTML_CONF,
        )
        layout.copy_assets(site_src, site_build)

    print("[plssg] generating rss")
    rss.generate_rss(HTML_DIR, sites, info)

    # Rewrite absolute hrefs/srcs to relative so pages open via file:// too.
    n = render.post_process_relative_urls(HTML_DIR)
    print(f"[plssg] rewrote URLs to relative in {n} html files")

    if os.path.exists(TEMPLATE_TEX):
        print("[plssg] generating tex")
        # Wipe build/tex so stale books from renamed/removed sub-sites don't linger.
        shutil.rmtree(TEX_DIR, ignore_errors=True)
        os.makedirs(TEX_DIR, exist_ok=True)
        if root_has:
            root_book = info.get("site_title", "site")
            out = tex.generate_site_tex(
                book_name=root_book,
                site_src=SRC_DIR,
                tex_root=TEX_DIR,
                template_path=TEMPLATE_TEX,
                info=info,
                is_root=True,
            )
            if out:
                print(f"  [tex] {os.path.relpath(out, PROJECT_ROOT)}")
        for site in sites:
            site_src = os.path.join(SRC_DIR, site)
            book_name = layout.display_name(site)
            out = tex.generate_site_tex(
                book_name=book_name,
                site_src=site_src,
                tex_root=TEX_DIR,
                template_path=TEMPLATE_TEX,
                info=info,
                is_root=False,
            )
            if out:
                print(f"  [tex] {os.path.relpath(out, PROJECT_ROOT)}")

    print(f"[plssg] done -> {HTML_DIR}")


if __name__ == "__main__":
    main()
