"""Notion pages from Markdown, standard library only. Reads NOTION_TOKEN / NOTION_ROOT_PAGE from .env (never printed).
Usage:
  python3 notion.py page "Title" file.md [parent_id]   create (or replace) a sub-page under the root page
  python3 notion.py title "Title"                      rename the root page
Markdown supported: # ## ### headings, - bullets, 1. numbered, - [ ] to-dos, > quotes/callouts, ``` code, | tables |,
--- dividers, **bold**, `code` and [links](url)."""
import json, re, sys, time, urllib.error, urllib.request
from gdrive import env

E = env()
API = "https://api.notion.com/v1"
H = {"Authorization": f"Bearer {E.get('NOTION_TOKEN', '')}", "Notion-Version": "2022-06-28",
     "Content-Type": "application/json"}


def call(method, path, body=None):
    for attempt in range(5):
        req = urllib.request.Request(f"{API}/{path}", json.dumps(body).encode() if body else None, H, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(float(err.headers.get("Retry-After", 2 * (attempt + 1))))
                continue
            raise SystemExit(f"Notion {err.code}: {json.load(err).get('message')}")


def rich(text):
    """Inline markdown -> Notion rich_text (bold, code, links), split under the 2000-char limit."""
    out = []
    for m in re.finditer(r"\*\*(.+?)\*\*|`(.+?)`|\[(.+?)\]\((https?://[^)]+)\)|([^*`\[]+|[*`\[])", text):
        bold, code, ltxt, url, plain = m.groups()
        s = bold or code or ltxt or plain or ""
        for i in range(0, len(s), 1900):
            t = {"type": "text", "text": {"content": s[i:i + 1900]}}
            if url:
                t["text"]["link"] = {"url": url}
            if bold or code:
                t["annotations"] = {"bold": bool(bold), "code": bool(code)}
            out.append(t)
    return out


def block(kind, text, **extra):
    return {"object": "block", "type": kind, kind: {"rich_text": rich(text), **extra}}


def blocks(md):
    lines, incode = [], False
    for l in md.splitlines():  # join indented continuation lines onto their list item
        if l.strip().startswith("```"):
            incode = not incode
        if not incode and lines and l.startswith("   ") and l.strip() and lines[-1].strip():
            lines[-1] += " " + l.strip()
        else:
            lines.append(l)
    out, i = [], 0
    while i < len(lines):
        l = lines[i].rstrip()
        s = l.strip()
        if not s:
            i += 1; continue
        if s.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            out.append({"object": "block", "type": "code", "code": {
                "rich_text": [{"type": "text", "text": {"content": "\n".join(code)[:1900]}}],
                "language": s[3:].strip() or "plain text"}})
            i += 1; continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            w = max(len(r) for r in rows)
            out.append({"object": "block", "type": "table", "table": {
                "table_width": w, "has_column_header": True, "has_row_header": False,
                "children": [{"type": "table_row", "table_row": {"cells": [rich(c) for c in r + [""] * (w - len(r))]}}
                             for r in rows]}})
            continue
        if s == "---":
            out.append({"object": "block", "type": "divider", "divider": {}})
        elif m := re.match(r"(#{1,3}) (.*)", s):
            out.append(block(f"heading_{len(m.group(1))}", m.group(2)))
        elif m := re.match(r"- \[( |x)\] (.*)", s):
            out.append(block("to_do", m.group(2), checked=m.group(1) == "x"))
        elif s.startswith(("- ", "* ")):
            out.append(block("bulleted_list_item", s[2:]))
        elif m := re.match(r"\d+[.)] (.*)", s):
            out.append(block("numbered_list_item", m.group(1)))
        elif s.startswith("> "):
            body = s[2:]
            icon = body[0] if body and not body[0].isascii() else None
            out.append(block("callout", body[1:].strip() if icon else body,
                             icon={"type": "emoji", "emoji": icon or "💡"}))
        else:
            para = [s]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"(#|- |\* |\d+[.)] |> |\||```|---)",
                                                                                   lines[i + 1].strip()):
                i += 1; para.append(lines[i].strip())
            out.append(block("paragraph", " ".join(para)))
        i += 1
    return out


def children(page_id):
    res, cur = [], None
    while True:
        j = call("GET", f"blocks/{page_id}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        res += j["results"]
        if not j.get("has_more"):
            return res
        cur = j["next_cursor"]


def append(page_id, bl):
    for k in range(0, len(bl), 90):
        call("PATCH", f"blocks/{page_id}/children", {"children": bl[k:k + 90]})


def page(title, md, parent=None, icon="📄"):
    """Create sub-page `title` under `parent` (default root). If it exists, its contents are replaced."""
    parent = parent or E["NOTION_ROOT_PAGE"]
    old = next((b for b in children(parent) if b["type"] == "child_page" and b["child_page"]["title"] == title), None)
    if old:
        for b in children(old["id"]):
            call("DELETE", f"blocks/{b['id']}")
        pid = old["id"]
    else:
        pid = call("POST", "pages", {"parent": {"page_id": parent}, "icon": {"type": "emoji", "emoji": icon},
                                     "properties": {"title": {"title": rich(title)}}})["id"]
    append(pid, blocks(md))
    return pid


def set_title(title, page_id=None, icon=None):
    body = {"properties": {"title": {"title": rich(title)}}}
    if icon:
        body["icon"] = {"type": "emoji", "emoji": icon}
    call("PATCH", f"pages/{page_id or E['NOTION_ROOT_PAGE']}", body)


if __name__ == "__main__":
    if sys.argv[1] == "title":
        set_title(sys.argv[2]); print("renamed")
    elif sys.argv[1] == "page":
        pid = page(sys.argv[2], open(sys.argv[3]).read(), sys.argv[4] if len(sys.argv) > 4 else None)
        print("https://www.notion.so/" + pid.replace("-", ""))
