# plssg

Pretty Lame Static Site Generator.

A walkthrough follows. Read top to bottom; everything builds on the
previous step.

## what you get

You give `plssg` a directory of Markdown. It gives you back a directory
of HTML, a stylesheet, an RSS feed, and (if you ask) a LaTeX book per
site. No server, no JavaScript, no database, no watcher. You run it; it
exits.

## the directory

After you unpack `plssg`, you have this:

    plssg/
        bin/    six python files. the program.
        etc/    five config files. what you edit.
        src/    your writing. starts with a placeholder.
        README.md

There is no `build/`. There will be, after you run it once.

## first run

From inside `plssg/`:

    python3 bin/main.py

You should see something like

    [plssg] sites: <root>, 01_Example
    [plssg] building <root>
        [render] index.html
    [plssg] building 01_Example
        [render] index.html
      [rss] .../build/html/rss.xml (2 items)
    [plssg] rewrote URLs to relative in 2 html files
    [plssg] generating tex
      [tex] build/tex/My Site/My Site.tex
      [tex] build/tex/Example/Example.tex
    [plssg] done -> .../build/html

Now open `build/html/index.html` in a browser. Or, to serve it:

    python3 -m http.server -d build/html 8000

Either works. `plssg` post-processes every page to use relative URLs,
so `file://` and `http://` both behave.

## what just happened

`bin/main.py` walked `src/`. It found one loose `index.md` and one
sub-directory, `01_Example/`. The loose file is the **root pseudo-site**
--- it renders at the build root. The sub-directory is a **sub-site**;
it renders under `build/html/Example/` (the `NN_` prefix is stripped).
Both share `etc/template.html`, both share `etc/template.tex`, both get
listed in `rss.xml`.

You will spend the rest of your time editing `src/` and `etc/`. The rest
of this document is about those two directories.

## writing pages

Drop a `.md` file anywhere under `src/`. Re-run `bin/main.py`. The file
appears in the sidebar of its containing site, alphabetically sorted.

If you want to control the order, prefix filenames with `NN_`:

    src/01_Example/
        index.md         the page at /Example/
        01_intro.md      sidebar: "intro"
        02_install.md    sidebar: "install"
        03_usage.md      sidebar: "usage"

The `NN_` is stripped from the URL and from the display name. `01_intro.md`
becomes `/Example/intro.html` and is shown as `intro`.

`index.md` is special: it is the file served at the directory URL.
Without it, `plssg` synthesises a directory listing so navigation never
404s, but you should write your own.

A file or directory whose name starts with `.` or `_` is skipped. This
is your draft mechanism: `_draft.md` is invisible, `01_draft.md` is
published.

## adding a sub-site

A sub-site is a directory at the top level of `src/`:

    mkdir 'src/02_Notes'
    echo '# Notes' > 'src/02_Notes/index.md'
    python3 bin/main.py

`02_Notes` now appears in the top nav, next to `Example`. Its sidebar
is independent. Its CSS can be overridden separately (see below). You
can have as many sub-sites as you like; they sort by `NN_`.

If you have no sub-sites and want a single flat site, just don't create
any top-level directories under `src/`. Drop `.md` files into `src/`
directly. `plssg` will build a single site at the build root and skip
the top nav entirely.

## assets

Every time you run `plssg`, it creates two empty directories beside any
content tree that lacks them:

    <somewhere>/assets/img/      images
    <somewhere>/assets/file/     downloads (pdfs, archives, etc.)

You don't have to use them. Any directory named `assets`, `images`,
`_img`, `static`, `media`, or `pub` is copied verbatim into the build.
The `img/` and `file/` split is convention, not law.

Reference assets from Markdown the normal way:

    ![diagram](assets/img/diagram.png)
    [the report](assets/file/report.pdf)

For images, `plssg` resolves the path two ways: relative to the `.md`
file, and (if the path begins with `/`) relative to the site root. Both
work.

## logos and favicons

Drop `favicon.ico` and `logo.svg` (or `.png`, `.jpg`, etc.) into
`src/assets/`. Set `etc/info.conf`:

    favicon   = /assets/favicon.ico
    logo      = /assets/logo.svg
    logo_size = 4em

The favicon is mirrored to `build/html/favicon.ico` so the browser's
default probe hits 200. The logo appears on the home button in the top
nav.

A sub-site can have its own logo, shown on the `<h1>` band of its pages.
The shortcut is: drop `logo.{svg,png,...}` into the sub-site's `assets/`
and `plssg` finds it automatically. To override the size, set
`logo_size` in the `[Example]` section of `themes.conf`.

## etc/info.conf

This is the only file that holds site identity. Open it:

    [site]
    title     = My Site
    tagline   = Hello, world.
    favicon   = /assets/favicon.ico
    logo      = /assets/logo.svg
    logo_size = 4em

    [footer]
    left   = <a href="/">Powered by plssg</a>
    center = &copy; 2026 Anonymous
    right  = <a href="/rss.xml">RSS</a>

    [rss]
    title       = My Site
    description = My Site
    link        = /rss.xml

The footer is three columns. HTML is allowed and not escaped. The
`tagline` shows on the `<h1>` band of the root page; sub-site pages
show their own name instead.

To override any of these for one sub-site, put an `info.conf` with the
same `[section]` structure into the sub-site's `assets/`:

    src/01_Example/assets/info.conf

Only the keys you set there override; the rest inherit.

## etc/themes.conf

`plssg` does not have themes. It has CSS variables. `themes.conf` is a
list of variable values:

    [global]
    color_text       = #000
    color_bg         = #fff
    color_border     = #000
    color_hover_bg   = #eee
    color_code_bg    = #f5f5f5

    font_family_body = Helvetica, Verdana, Arial, sans-serif
    font_family_mono = Menlo, Consolas, monospace

    font_body    = 84%
    font_nav     = 1.5em
    font_banner  = 1.9em
    sidebar_width     = 16em
    content_max_width = 70em

INI key `color_text` becomes CSS variable `--color-text`. The defaults
in `bin/layout.py` give you a monochrome page. Override what you want;
omit the rest.

Per sub-site, add an `[Example]` section (the section name is the
sub-site directory name with `NN_` stripped):

    [Example]
    color_bg = #fefae0

`plssg` auto-appends an empty `[Example]` section the first time it
sees a new sub-site, so you never type the section header. The section
just sits there empty until you fill it in.

The full list of recognised keys is in the comment block at the top of
`themes.conf`. Anything not in that list is ignored.

## etc/html.conf

Toggles for the Markdown renderer:

    [html]
    wrap_article  = false
    paragraph_tag = p
    code_block    = true
    inline_code   = true
    lists         = true
    auto_id       = true

You will probably never touch this. The only knob worth knowing is
`auto_id = false`, which turns off the slug-id on every heading.

## the markdown subset

`plssg` understands a small dialect, deliberately:

    # heading             ## sub-heading       ### sub-sub
    paragraph text
    **bold**   *italic*   `inline code`
    ```
    fenced code
    ```
    - list item
    [link](url)   ![image](url)

Headings get auto-generated ids (CJK is preserved). Four-space-indented
lines become a `<pre>` block (Markdown convention). A line that starts
with `<` is passed through unchanged --- so for tables, footnotes,
custom widgets, or any other escape hatch, just write HTML.

If you need more than a paragraph of escape-hatch HTML, write the whole
file as `foo.html` instead of `foo.md`. `plssg` extracts the `<main>` (or
`<body>`) and drops it into the template like any other page. If both
`foo.md` and `foo.html` exist, `.md` wins.

## the tex side

If `etc/template.tex` exists, `plssg` also emits one LaTeX book per
site:

    build/tex/<book>/<book>.tex
    build/tex/<book>/img/...

Each `.md` becomes a `\section`. `index.md` is special: it becomes the
preface, placed before `\tableofcontents`. Headings inside a `.md` are
demoted one level (`#` becomes `\subsection`, etc.) because the file
itself is already a section.

`plssg` does not call `xelatex`. That is your job:

    cd 'build/tex/My Site'
    xelatex 'My Site.tex'

The shipped `template.tex` uses xelatex + xeCJK with Songti SC, fine
for Chinese. Edit it for your own taste. Delete it to skip tex
generation entirely.

## the six bin files

Read them, they're short. In dependency order:

    bin/html.py     Markdown subset -> HTML. one pure function.
    bin/tex.py      Markdown subset -> LaTeX. one pure function.
    bin/layout.py   CSS, template, top nav, sidebar, footer, assets.
    bin/rss.py      build/html walk -> rss.xml.
    bin/render.py   per-site file walker. calls html.py per file.
    bin/main.py     entry point. wires the above together.

No imports outside the standard library. No setup.py. No requirements.
Python 3.6+ should be enough; 3.10+ is what it's tested on.

## conventions that bite

A few things behave in ways that aren't obvious:

- `NN_` prefixes are stripped *everywhere they're shown* but kept on
  disk. `src/01_Example/` is the directory; `/Example/` is the URL.
  When you reference a sub-site in code or config, use the stripped
  name (`[Example]` in `themes.conf`, not `[01_Example]`).
- `_` prefix hides a file or directory from the build. `.` does the
  same. Use either; they are equivalent.
- Both `.md` and `.html` are content. They can coexist; `.md` wins.
- The build is not incremental. Every run regenerates everything.
  Deletions in `src/` are *not* reflected unless you also delete the
  old output --- `plssg` only writes, never sweeps. If a `.md` is
  removed, blow away `build/html/` and rebuild.
- `build/tex/` *is* swept on every run, because stale LaTeX from
  renamed sub-sites was confusing.

## what to do next

Edit `src/index.md`. Edit `etc/info.conf` to set your title and
footer. Run `python3 bin/main.py`. Open the result. Iterate.

When you outgrow it, the answer is not to extend `plssg` --- the answer
is to read the six files in `bin/`, see what they do, and write the
generator you actually need. They are short on purpose.

## see also

werc(1), the spiritual reference. plssg owes it the directory layout
and the disposition.
