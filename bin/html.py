"""
plssg html backend - Markdown subset -> HTML
Pure function, zero third-party dependencies.

Supports:
- # / ## / ### headings (with optional auto-id slug)
- Paragraphs (blank line separates)
- ``` fenced code blocks (HTML escaped inside)
- ` inline code
- - unordered lists (single level, blank line closes)
- [text](url) inline links
- ![alt](url) inline images
- HTML entity escape for &, <, >
"""
import os
import re
import configparser

DEFAULT_CONF = {
    "wrap_article":  False,
    "paragraph_tag": "p",
    "code_block":    True,
    "inline_code":   True,
    "lists":         True,
    "auto_id":       True,
}


def load_html_conf(path):
    cfg = dict(DEFAULT_CONF)
    if not os.path.exists(path):
        return cfg
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    if "html" in parser:
        for k in list(cfg):
            if k in parser["html"]:
                v = parser["html"][k].strip().strip('"').strip("'")
                if isinstance(cfg[k], bool):
                    cfg[k] = v.lower() not in ("false", "0", "no", "off")
                else:
                    cfg[k] = v
    return cfg


def escape_html(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


# URL pattern: non-whitespace, non-quote characters
INLINE_IMG_RE  = re.compile(r'!\[([^\]]*)\]\(([^\s"\)]+)(?:\s+"[^"]*")?\)')
INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^\s"\)]+)(?:\s+"[^"]*")?\)')
INLINE_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
INLINE_EM_RE   = re.compile(r"\*([^*\s][^*]*?)\*")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def process_inline(text, conf):
    """Apply inline transforms in order: image > link > bold > em > code.
       Order matters: image is link-with-bang, bold is em-with-double-asterisk."""
    text = INLINE_IMG_RE.sub(r'<img src="\2" alt="\1">', text)
    text = INLINE_LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = INLINE_BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = INLINE_EM_RE.sub(r"<em>\1</em>", text)
    if conf.get("inline_code", True):
        text = INLINE_CODE_RE.sub(r"<code>\1</code>", text)
    return text


NON_WORD_RE = re.compile(r"[^\w一-鿿]+")


def slugify(text):
    """Generate a heading id slug. Preserves CJK chars, replaces others with '-'."""
    s = NON_WORD_RE.sub("-", text.lower()).strip("-")
    return s


def heading(tag, text, conf):
    text_html = process_inline(escape_html(text), conf)
    if conf.get("auto_id", True):
        _id = slugify(text)
        return f'<{tag} id="{_id}">{text_html}</{tag}>'
    return f"<{tag}>{text_html}</{tag}>"


def render_markdown(text, conf=None):
    """Markdown subset -> HTML string."""
    if conf is None:
        conf = dict(DEFAULT_CONF)

    out = []
    in_code = False
    in_list = False

    for raw in text.splitlines():
        line = raw.rstrip()

        # fenced code block
        if conf.get("code_block", True) and line.startswith("```"):
            if not in_code:
                out.append("<pre><code>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue
        if in_code:
            out.append(escape_html(line))
            continue

        # unordered list
        if conf.get("lists", True) and line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = process_inline(escape_html(line[2:]), conf)
            out.append(f"<li>{content}</li>")
            continue
        elif in_list and line.strip() == "":
            out.append("</ul>")
            in_list = False
            out.append("")
            continue
        elif in_list:
            out.append("</ul>")
            in_list = False

        # headings
        if line.startswith("### "):
            out.append(heading("h3", line[4:], conf))
        elif line.startswith("## "):
            out.append(heading("h2", line[3:], conf))
        elif line.startswith("# "):
            out.append(heading("h1", line[2:], conf))
        # blank line
        elif line.strip() == "":
            out.append("")
        # 4-space indented block: treat as <pre> code (markdown convention)
        elif raw.startswith("    ") and not in_list:
            out.append(f"<pre><code>{escape_html(raw[4:])}</code></pre>")
        # Raw HTML line (starts with <): pass through unchanged
        elif line.lstrip().startswith("<") and not line.lstrip().startswith("<!--"):
            out.append(line)
        # paragraph
        else:
            tag = conf.get("paragraph_tag", "p")
            content = process_inline(escape_html(line), conf)
            out.append(f"<{tag}>{content}</{tag}>")

    if in_list:
        out.append("</ul>")
    if in_code:
        out.append("</code></pre>")

    result = "\n".join(out)
    if conf.get("wrap_article", False):
        result = f"<article>{result}</article>"
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            print(render_markdown(f.read()))
    else:
        print(render_markdown(sys.stdin.read()))
