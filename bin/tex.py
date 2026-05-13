"""
plssg tex backend - Markdown subset -> LaTeX

Each book is a directory under build/tex/<book>/ containing:
  <book>.tex  - the LaTeX source
  img/        - copies of any images referenced by the markdown

Books:
  Root pseudo-site -> build/tex/<site_title>/<site_title>.tex
                      (only src/*.md, NO sub-site content)
  Each sub-site   -> build/tex/<sub_id>/<sub_id>.tex
                     (all .md under src/<sub>/, recursive)

Each .md file becomes one \\section (numbered, in the TOC).
index.md is special: rendered as a preface BEFORE \\tableofcontents,
so the TOC starts with the user's named files.

Headings inside a .md are demoted one level (# -> \\subsection,
## -> \\subsubsection, ### -> \\paragraph) since the file itself
already occupies the \\section slot.

This module does NOT invoke xelatex. The user is expected to run:
  cd build/tex/<book>/ && xelatex <book>.tex
"""
import os
import re
import shutil


LATEX_REPLACEMENTS = [
    # Order matters: backslash first
    ("\\", r"\textbackslash{}"),
    ("&",  r"\&"),
    ("%",  r"\%"),
    ("$",  r"\$"),
    ("#",  r"\#"),
    ("_",  r"\_"),
    ("{",  r"\{"),
    ("}",  r"\}"),
    ("~",  r"\textasciitilde{}"),
    ("^",  r"\textasciicircum{}"),
]


def escape_tex(text):
    for src, dst in LATEX_REPLACEMENTS:
        text = text.replace(src, dst)
    return text


NUM_PREFIX_RE  = re.compile(r"^(\d+)_")
INLINE_IMG_RE  = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
INLINE_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
INLINE_EM_RE   = re.compile(r"\*([^*\s][^*]*?)\*")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def strip_num_prefix(name):
    return NUM_PREFIX_RE.sub("", name)


def display_name(name):
    """01_ELSA Station -> ELSA Station"""
    return strip_num_prefix(name).replace("_", " ").replace("-", " ")


def _resolve_image(ref, md_dir, site_src):
    """Resolve a markdown image ref to a local filesystem path.
       Returns absolute path on success, None if external URL or not found.
       - 'http(s)://...'         -> None (skip)
       - '/foo/bar.png'          -> site_src/foo/bar.png
       - 'assets/img/foo.png'    -> md_dir/assets/img/foo.png
       - 'foo.png'               -> md_dir/foo.png"""
    if re.match(r'^[a-zA-Z]+://', ref):
        return None
    if ref.startswith("/"):
        candidate = os.path.join(site_src, ref.lstrip("/"))
    else:
        candidate = os.path.join(md_dir, ref)
    return candidate if os.path.isfile(candidate) else None


def _copy_image(src_path, book_img_dir):
    """Copy src_path into book_img_dir, returning the basename used.
       Resolves name collisions by appending _1, _2, ... to the stem."""
    os.makedirs(book_img_dir, exist_ok=True)
    base = os.path.basename(src_path)
    dst = os.path.join(book_img_dir, base)
    if os.path.exists(dst) and not os.path.samefile(src_path, dst):
        stem, ext = os.path.splitext(base)
        i = 1
        while True:
            base = f"{stem}_{i}{ext}"
            dst = os.path.join(book_img_dir, base)
            if not os.path.exists(dst):
                break
            i += 1
    shutil.copyfile(src_path, dst)
    return base


def process_inline_tex(text, md_dir, site_src, book_img_dir):
    """Inline transform for LaTeX. Extracts images/links/code into
       placeholders BEFORE escape_tex (so URLs and code aren't mangled),
       then restores them after."""
    saved = []

    def save_img(m):
        alt, ref = m.group(1), m.group(2)
        local = _resolve_image(ref, md_dir, site_src)
        if local is None:
            saved.append(("img_missing", alt, ref))
        else:
            new_name = _copy_image(local, book_img_dir)
            saved.append(("img", alt, new_name))
        return f"\x01TOK{len(saved)-1}\x01"

    def save_link(m):
        saved.append(("link", m.group(1), m.group(2)))
        return f"\x01TOK{len(saved)-1}\x01"

    def save_code(m):
        saved.append(("code", m.group(1), None))
        return f"\x01TOK{len(saved)-1}\x01"

    text = INLINE_IMG_RE.sub(save_img, text)
    text = INLINE_LINK_RE.sub(save_link, text)
    text = INLINE_CODE_RE.sub(save_code, text)
    text = escape_tex(text)
    text = INLINE_BOLD_RE.sub(r"\\textbf{\1}", text)
    text = INLINE_EM_RE.sub(r"\\emph{\1}", text)

    def restore(m):
        idx = int(m.group(1))
        kind, a, b = saved[idx]
        if kind == "link":
            return f"\\href{{{b}}}{{{escape_tex(a)}}}"
        if kind == "code":
            return f"\\texttt{{{escape_tex(a)}}}"
        if kind == "img":
            return f"\\includegraphics[width=\\linewidth]{{img/{b}}}"
        if kind == "img_missing":
            return f"[image: {escape_tex(a)}]"
        return ""

    text = re.sub(r"\x01TOK(\d+)\x01", restore, text)
    return text


def render_markdown_tex(md_text, md_dir, site_src, book_img_dir):
    """Markdown subset -> LaTeX body (no preamble, no section header).
       Headings are demoted: # -> \\subsection, ## -> \\subsubsection,
       ### -> \\paragraph. The enclosing \\section is emitted by the caller."""
    out = []
    in_code = False
    in_list = False
    for raw in md_text.splitlines():
        line = raw.rstrip()

        if line.startswith("```"):
            if not in_code:
                out.append(r"\begin{verbatim}")
                in_code = True
            else:
                out.append(r"\end{verbatim}")
                in_code = False
            continue
        if in_code:
            out.append(line)
            continue

        if line.startswith("- "):
            if not in_list:
                out.append(r"\begin{itemize}")
                in_list = True
            out.append(r"\item " + process_inline_tex(
                line[2:], md_dir, site_src, book_img_dir))
            continue
        elif in_list and line.strip() == "":
            out.append(r"\end{itemize}")
            in_list = False
            out.append("")
            continue
        elif in_list:
            out.append(r"\end{itemize}")
            in_list = False

        # Demoted by one level: file itself is the \section.
        if line.startswith("### "):
            out.append(r"\paragraph{" + escape_tex(line[4:]) + "}")
        elif line.startswith("## "):
            out.append(r"\subsubsection{" + escape_tex(line[3:]) + "}")
        elif line.startswith("# "):
            out.append(r"\subsection{" + escape_tex(line[2:]) + "}")
        elif line.strip() == "":
            out.append("")
        else:
            out.append(process_inline_tex(
                line, md_dir, site_src, book_img_dir))

    if in_list:
        out.append(r"\end{itemize}")
    if in_code:
        out.append(r"\end{verbatim}")
    return "\n".join(out)


def collect_md_files(site_src, recursive):
    """Return ordered list of (md_path, display_name, is_index).
       recursive=False: only top-level .md files (root pseudo-site).
       recursive=True:  walk all .md under site_src (excluding _xxx, assets).
       Ordering within each directory: index.md first, then NN_-prefix sorted."""
    files = []
    if recursive:
        for root, dirs, names in os.walk(site_src):
            dirs[:] = [d for d in sorted(dirs)
                       if not d.startswith(".")
                       and not d.startswith("_")
                       and d.lower() != "assets"]
            for n in sorted(names):
                if n.endswith(".md"):
                    files.append(os.path.join(root, n))
    else:
        for n in sorted(os.listdir(site_src)):
            full = os.path.join(site_src, n)
            if os.path.isfile(full) and n.endswith(".md"):
                files.append(full)

    def sort_key(path):
        rel_dir = os.path.dirname(os.path.relpath(path, site_src))
        name = os.path.basename(path)
        is_index = 0 if name.lower() == "index.md" else 1
        return (rel_dir, is_index, name)

    files.sort(key=sort_key)
    return [
        (p, display_name(os.path.splitext(os.path.basename(p))[0]),
         os.path.basename(p).lower() == "index.md")
        for p in files
    ]


def generate_site_tex(book_name, site_src, tex_root, template_path,
                      info, is_root=False):
    """Generate a complete book at <tex_root>/<book_name>/<book_name>.tex.
       book_name is the on-disk folder + filename (no NN_, no extension).
       Images referenced by markdown are copied to <tex_root>/<book_name>/img/.
       is_root selects scope: True -> only top-level .md, False -> recursive."""
    if not os.path.exists(template_path):
        return None
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    book_dir = os.path.join(tex_root, book_name)
    img_dir  = os.path.join(book_dir, "img")
    os.makedirs(book_dir, exist_ok=True)

    preface_parts = []
    body_parts    = []

    for md_path, sec_title, is_index in collect_md_files(site_src, recursive=not is_root):
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        rendered = render_markdown_tex(
            md_text,
            md_dir=os.path.dirname(md_path),
            site_src=site_src,
            book_img_dir=img_dir,
        )
        if is_index:
            preface_parts.append(rendered)
        else:
            body_parts.append(r"\section{" + escape_tex(sec_title) + "}")
            body_parts.append(rendered)
            body_parts.append("")

    preface = "\n".join(preface_parts).strip()
    body    = "\n".join(body_parts).strip()

    # The template has \tableofcontents BEFORE {{content}}. We want index.md
    # (preface) to appear BEFORE the TOC, so emit it as raw content placed via
    # a {{preface}} placeholder and have the user's template position it. If
    # the template doesn't carry {{preface}}, fall back to emitting preface
    # right before the TOC by injecting it via {{content}} prefixed with a
    # \\thispagestyle{empty}\\newpage trick — but the simpler route is to
    # require {{preface}} in the template. For backwards compat, if {{preface}}
    # isn't present we put preface at the top of {{content}}.
    if "{{preface}}" in template:
        merged = template
        merged = merged.replace("{{preface}}", preface)
        merged = merged.replace("{{content}}", body)
    else:
        combined = preface + ("\n\n" + body if body else "")
        merged = template.replace("{{content}}", combined)

    merged = merged.replace("{{title}}", escape_tex(book_name))
    merged = merged.replace("{{author}}",
                            escape_tex(_strip_html(info.get("footer_center", ""))))
    merged = merged.replace("{{date}}", r"\today")

    out_path = os.path.join(book_dir, book_name + ".tex")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(merged)
    return out_path


_TAG_RE = re.compile(r"<[^>]+>")
_ENT_RE = re.compile(r"&[a-zA-Z0-9#]+;")


def _strip_html(s):
    """Crude HTML strip for embedding info.conf values into LaTeX."""
    s = _TAG_RE.sub("", s)
    s = _ENT_RE.sub("", s)
    return s.strip()
