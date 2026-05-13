# plssg - Pretty Lame Static Site Generator

## About

plssg is a static site generator inspired by [werc](http://werc.cat-v.org/) and
[oscean](https://wiki.xxiivv.com/site/oscean.html)). It runs on the
[Python 3](https://www.python.org/) standard library alone — no `pip install`,
no `node_modules`, no build tool to learn — and ships with its JavaScript
virginity intact: every page is plain HTML + CSS, served (or opened via
`file://`) as-is.

Write Markdown under `src/`, run `python3 bin/main.py`, get a navigable
multi-site tree under `build/html/`. Optionally get matching LaTeX books under
`build/tex/` if `xelatex` is around.

## File Structure

```
plssg/
├── bin/                 # the generator itself (one job per file)
│   ├── main.py          # entry point + pipeline orchestration
│   ├── layout.py        # CSS, template, top/side nav, asset copy
│   ├── render.py        # walks src/, dispatches every .md/.html to html.py
│   ├── html.py          # Markdown subset → HTML (pure function)
│   ├── tex.py           # Markdown subset → LaTeX (one book per sub-site)
│   └── rss.py           # build/html/rss.xml from rendered pages, sorted by mtime
│
├── etc/                 # all configuration lives here
│   ├── info.conf        # site title, tagline, favicon, logo, footer, RSS
│   ├── themes.conf      # [global] + per-sub-site CSS variable overrides
│   ├── html.conf        # html.py toggles (paragraph tag, lists, auto-id, …)
│   ├── template.html    # HTML skeleton with {{placeholders}}
│   └── template.tex     # LaTeX skeleton (xeCJK-ready)
│
├── src/                 # your content
│   ├── index.md         # the root pseudo-site (rendered at build root)
│   ├── assets/          # shared favicon / logo / etc.
│   └── 01_Example/      # one sub-site; NN_ prefix only controls nav order
│       ├── index.md     #   → /Example/index.html
│       └── assets/      #   img/  file/  auto-created on first run
│
└── build/               # output, regenerated each run (safe to delete)
    ├── html/            # the static site
    └── tex/             # one xelatex-able book per sub-site (if template.tex exists)
```

Conventions worth remembering:

- A directory name `NN_Name` is stripped to `Name` in URLs and display — the
  prefix exists purely to order top-nav entries.
- Files / directories starting with `.` or `_` are skipped by the generator.
- `index.md` becomes `index.html` in place; everything else
  `NN_thing.md` → `thing.html`.
- A directory without an `index.md` gets a synthesised listing page, so
  navigation never 404s.

## A Brief Walk Through

1. **Clone & write.** Drop Markdown into `src/`. The shipped `src/index.md`
   and `src/01_Example/index.md` are minimal placeholders — overwrite them.
2. **Configure.** Edit [`etc/info.conf`](etc/info.conf) for title / logo /
   footer / RSS, and [`etc/themes.conf`](etc/themes.conf) for colours, fonts,
   sidebar width, etc. Every key in a `themes.conf` section becomes a CSS
   variable (`color_text` → `--color-text`), overlaid on the defaults baked
   into [`bin/layout.py`](bin/layout.py).
3. **Build.**
   ```
   python3 bin/main.py
   ```
   The pipeline, per sub-site:
   - `layout.generate_css` → `build/html/<site>/style.css`
   - `layout.generate_temp_html` → `build/html/<site>/_temp.html` (template
     with everything but `{{article_content}}` filled in)
   - `render.render_site` → one `.html` per source `.md`, with `_temp.html` as
     the wrapper
   - `layout.copy_assets` → mirrors `assets/`, `images/`, `_img/`, `static/`,
     `media/`, `pub/` verbatim

   Then once globally: `rss.generate_rss` writes `build/html/rss.xml`
   (newest-50 by mtime), and `render.post_process_relative_urls` rewrites
   absolute hrefs to relative so each page opens cleanly under `file://`.
4. **(Optional) PDF.** If [`etc/template.tex`](etc/template.tex) is present,
   `bin/tex.py` emits one book per sub-site into `build/tex/<book>/`. Compile
   with `cd build/tex/<book>/ && xelatex <book>.tex`.
5. **Serve.** Anything that serves static files works. For local preview:
   ```
   cd build/html && python3 -m http.server
   ```
   Or just double-click any `.html` — relative URLs make `file://` viable too.

New sub-site? Make a folder under `src/`, run `main.py` again; an empty
`[<site_id>]` section is auto-appended to `themes.conf` for you to fill in
overrides, and `assets/img/` + `assets/file/` skeletons are created
underneath.

## Reference

- [werc](http://werc.cat-v.org/)
- [oscean](https://wiki.xxiivv.com/site/oscean.html)
