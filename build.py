"""Build index.html (the registry view) from registry.md.

Usage: python build.py [registry.md] [index.html]
"""

import html
import os
import re
import sys
import urllib.parse

PROJECT_STATUSES = ["Proposed", "Submitted", "Approved", "Active", "Inactive", "Withdrawn"]
PSS_STATUSES = PROJECT_STATUSES + ["Published"]

HEADING = re.compile(r"^##\s+(\S+)\s+(.*\S)\s*$")
FIELD = re.compile(r"^(Status|Submitted|PP)\s*:\s*(.*?)\s*$", re.IGNORECASE)
TABLE_ROW = re.compile(r"^\|(.*)\|\s*$")
# Any short token, not just R<n>: see tools/registry_issue.py.
RELEASE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,19}$")
TABLE_RULE = re.compile(r"^\|[\s:|-]+\|\s*$")


def parse(path):
    """Read registry.md into a list of project dicts, each with a 'pss' list."""
    projects = []
    current = None
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            heading = HEADING.match(line)
            if heading:
                current = {
                    "id": heading.group(1),
                    "title": heading.group(2),
                    "status": "",
                    "submitted": "",
                    "pp": "",
                    "pss": [],
                }
                projects.append(current)
                continue
            if current is None:
                continue  # preamble before the first project
            field = FIELD.match(line)
            if field:
                key = field.group(1).lower()
                current["pp" if key == "pp" else key] = field.group(2)
                continue
            if TABLE_RULE.match(line):
                continue
            row = TABLE_ROW.match(line)
            if row:
                cells = [c.strip() for c in row.group(1).split("|")]
                if len(cells) != 5:
                    raise SystemExit(
                        "%s:%d: expected 5 PSS columns, found %d" % (path, lineno, len(cells))
                    )
                if cells[0].lower() == "release":
                    continue  # table header
                current["pss"].append(
                    {
                        "release": cells[0],
                        "submitted": cells[1],
                        "status": cells[2],
                        "title": cells[3],
                        "pss": cells[4],
                    }
                )
    return projects


def check(projects, root):
    """Return a list of warnings about statuses and missing PDFs."""
    warnings = []
    # Two submissions for the same new project are each allocated the next free
    # ID against main, so both can claim it until one of them is merged.
    ids = [p["id"] for p in projects]
    for pid in sorted(set(i for i in ids if ids.count(i) > 1)):
        warnings.append("%s: appears %d times - two entries share an ID" % (pid, ids.count(pid)))
    for p in projects:
        if p["status"] not in PROJECT_STATUSES:
            warnings.append("%s: project status %r is not an allowed status" % (p["id"], p["status"]))
        for link in [p["pp"]] + [s["pss"] for s in p["pss"]]:
            if link and not os.path.exists(os.path.join(root, link)):
                warnings.append("%s: file not found: %s" % (p["id"], link))
        for s in p["pss"]:
            if s["status"] not in PSS_STATUSES:
                warnings.append("%s: PSS status %r is not an allowed status" % (p["id"], s["status"]))
            if not RELEASE.match(s["release"]):
                warnings.append(
                    "%s: PSS release %r is empty or has characters that cannot be used"
                    % (p["id"], s["release"])
                )
        seen = set()
        for s in p["pss"]:
            # The project ID and release together address a scope statement, so
            # a duplicate release would make one of them unreachable.
            if s["release"] in seen:
                warnings.append("%s: more than one %s PSS" % (p["id"], s["release"]))
            seen.add(s["release"])
    return warnings


def pill(status):
    slug = re.sub(r"[^a-z]+", "-", status.lower()).strip("-") or "unset"
    return '<span class="pill pill-%s">%s</span>' % (slug, html.escape(status or "—"))


ICON = (
    '<svg class="icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">'
    '<path class="sheet" d="M4 1.6h4.7L12.4 5.3V14a.6.6 0 0 1-.6.6H4a.6.6 0 0 1-.6-.6V2.2a.6.6 0 0 1 .6-.6z"/>'
    '<path class="fold" d="M8.6 1.7v3.8h3.7"/>'
    "</svg>"
)


def link(path, label):
    """A document icon that opens the PDF in the preview pane (or a new tab)."""
    if not path:
        return '<span class="nolink">—</span>'
    href = "/".join(urllib.parse.quote(part) for part in path.split("/"))
    name = path.rsplit("/", 1)[-1]
    return (
        '<a class="doc" href="%s" data-kind="%s" data-name="%s" target="_blank"'
        ' rel="noopener" title="%s" aria-label="%s">%s</a>'
        % (
            href,
            html.escape(label),
            html.escape(name),
            html.escape("%s — %s" % (label, name)),
            html.escape("%s — %s" % (label, name)),
            ICON,
        )
    )


def render(projects):
    rows = []
    for p in projects:
        n = len(p["pss"])
        rows.append(
            '<tr class="project%s" data-project="%s"%s>'
            '<td class="c-toggle"><span class="chevron" aria-hidden="true"></span></td>'
            '<td class="c-id">%s</td>'
            '<td class="c-status">%s</td>'
            '<td class="c-date">%s</td>'
            '<td class="c-title">%s</td>'
            '<td class="c-doc">%s</td></tr>'
            % (
                "" if n else " leaf",
                html.escape(p["id"]),
                ' tabindex="0" role="button" aria-expanded="false"' if n else "",
                html.escape(p["id"]),
                pill(p["status"]),
                html.escape(p["submitted"] or "—"),
                html.escape(p["title"]),
                link(p["pp"], "PP"),
            )
        )
        for s in p["pss"]:
            rows.append(
                '<tr class="pss" data-parent="%s" hidden>'
                '<td></td><td class="c-id"><span class="rel">%s</span></td>'
                '<td class="c-status">%s</td>'
                '<td class="c-date">%s</td>'
                '<td class="c-title">%s</td>'
                '<td class="c-doc">%s</td></tr>'
                % (
                    html.escape(p["id"]),
                    html.escape(s["release"]),
                    pill(s["status"]),
                    html.escape(s["submitted"] or "—"),
                    html.escape(s["title"]),
                    link(s["pss"], "PSS"),
                )
            )

    total_pss = sum(len(p["pss"]) for p in projects)
    return TEMPLATE % {
        "rows": "\n".join(rows),
        "summary": "%d projects · %d project scope statements" % (len(projects), total_pss),
    }


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HL7 AU Project Registry</title>
<script>
  // Runs before first paint so the layout does not shift: ?align=left
  try {
    var align = new URLSearchParams(location.search).get('align');
    if (align === 'left') document.documentElement.setAttribute('data-align', 'left');
  } catch (e) {}
</script>
<style>
  :root {
    --bg: #ffffff;
    --surface: #f7f8fa;
    --text: #1a1d21;
    --muted: #6b7280;
    --border: #e3e6ea;
    --accent: #0b5fa5;
    --child-bg: #fafbfc;
    --pill-bg: #eceff3;
    --pill-text: #3b4350;
    --accent-soft: #e4eefa;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #15181c;
      --surface: #1d2126;
      --text: #e8eaed;
      --muted: #9aa3af;
      --border: #2c3138;
      --accent: #6db3ef;
      --child-bg: #191d22;
      --pill-bg: #2a2f36;
      --pill-text: #c6cdd6;
      --accent-soft: #1b2f44;
    }
    :root:not([data-theme="light"]) .pill-proposed  { background: #1c3250; color: #a8c9ee; }
    :root:not([data-theme="light"]) .pill-submitted { background: #43340f; color: #e8c879; }
    :root:not([data-theme="light"]) .pill-approved  { background: #1b3b24; color: #8fd4a0; }
    :root:not([data-theme="light"]) .pill-active    { background: #10364f; color: #8ecbf2; }
    :root:not([data-theme="light"]) .pill-published { background: #2e2a52; color: #bdb4ef; }
    :root:not([data-theme="light"]) .pill-inactive  { background: #2a2f36; color: #a7afbb; }
    :root:not([data-theme="light"]) .pill-withdrawn { background: #4a2222; color: #efa7a7; }
  }
  :root[data-theme="dark"] {
    --bg: #15181c;
    --surface: #1d2126;
    --text: #e8eaed;
    --muted: #9aa3af;
    --border: #2c3138;
    --accent: #6db3ef;
    --child-bg: #191d22;
    --pill-bg: #2a2f36;
    --pill-text: #c6cdd6;
    --accent-soft: #1b2f44;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 28px 16px 64px;
    background: var(--bg);
    color: var(--text);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  .wrap { max-width: 1670px; margin: 0 auto; }
  /* ?align=left pins the content to the left edge, for embedding in a page
     that does its own centering. The default is centred. */
  :root[data-align="left"] .wrap { margin-left: 0; margin-right: auto; }
  h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
  .summary { color: var(--muted); font-size: 13px; margin: 0 0 20px; }
  .controls { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
  button {
    font: inherit; font-size: 13px; padding: 6px 12px; border-radius: 7px;
    border: 1px solid var(--border); background: var(--surface); color: var(--text);
    cursor: pointer;
  }
  button:hover { border-color: var(--accent); color: var(--accent); }
  table { width: 100%%; border-collapse: collapse; }
  thead th {
    text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--muted); font-weight: 600; padding: 8px 10px;
    border-bottom: 1px solid var(--border); white-space: nowrap;
  }
  td { padding: 9px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr.project { cursor: pointer; }
  tr.project.leaf { cursor: default; }
  tr.project:hover:not(.leaf) td { background: var(--surface); }
  tr.pss td { background: var(--child-bg); }
  tr.pss .c-title { padding-left: 26px; color: var(--text); }
  .c-toggle { width: 26px; padding-right: 0; }
  .c-id { font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--muted); }
  tr.project .c-id { color: var(--text); font-weight: 600; }
  /* The release sits under the project ID: together they identify a PSS. */
  .rel {
    display: inline-block; padding: 1px 7px; border-radius: 999px;
    border: 1px solid var(--border); background: var(--surface);
    font-size: 11.5px; font-weight: 600; letter-spacing: .02em; color: var(--muted);
  }
  .c-date { white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--muted); }
  .c-doc { text-align: right; white-space: nowrap; }
  .chevron {
    display: inline-block; width: 0; height: 0; margin-left: 2px;
    border-left: 5px solid var(--muted); border-top: 4px solid transparent;
    border-bottom: 4px solid transparent; transition: transform 0.12s ease;
  }
  tr.project.leaf .chevron { visibility: hidden; }
  tr.project.open .chevron { transform: rotate(90deg) translateX(-1px); }
  .pill {
    display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px;
    background: var(--pill-bg); color: var(--pill-text); white-space: nowrap;
  }
  .pill-proposed  { background: #e6eef9; color: #1d4f8b; }
  .pill-submitted { background: #fff3d6; color: #7a5300; }
  .pill-approved  { background: #e2f1e4; color: #1f6b33; }
  .pill-active    { background: #dbefff; color: #0d5a8f; }
  .pill-published { background: #e6e3fa; color: #43338c; }
  .pill-inactive  { background: #ebedf0; color: #5a6270; }
  .pill-withdrawn { background: #fae3e3; color: #8c2f2f; }
  a.doc {
    display: inline-flex; align-items: center; gap: 5px; padding: 3px 7px;
    border-radius: 6px; color: var(--muted); text-decoration: none;
    font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
  }
  a.doc .icon { fill: none; stroke: currentColor; stroke-width: 1.1; stroke-linejoin: round; }
  a.doc:hover { color: var(--accent); background: var(--surface); }
  a.doc.active { color: var(--accent); background: var(--accent-soft); }
  a.doc.active .icon .sheet { fill: var(--accent-soft); }
  a.doc.active .icon { stroke-width: 1.5; }
  .nolink { color: var(--muted); }

  .layout { display: flex; gap: 20px; align-items: flex-start; }
  .list { flex: 1 1 520px; min-width: 0; }
  .viewer {
    flex: 1 1 750px; min-width: 0; position: sticky; top: 24px;
    height: calc(100vh - 140px); min-height: 360px;
    border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
    display: flex; flex-direction: column; overflow: hidden;
  }
  .viewer-head {
    display: flex; align-items: center; gap: 10px; padding: 9px 12px;
    border-bottom: 1px solid var(--border); font-size: 12px; color: var(--muted);
  }
  .viewer-name {
    flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: var(--text); font-weight: 600;
  }
  .viewer-head a { color: var(--accent); text-decoration: none; white-space: nowrap; }
  .viewer-head a:hover { text-decoration: underline; }
  .viewer-body { flex: 1; position: relative; background: #ffffff; }
  .viewer-body iframe { width: 100%%; height: 100%%; border: 0; display: block; }
  .viewer-empty {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    text-align: center; padding: 24px; color: var(--muted); font-size: 13px;
    background: var(--surface);
  }
  .viewer[hidden], .viewer-empty[hidden], .viewer-body iframe[hidden] { display: none; }
  @media (max-width: 900px) {
    .layout { flex-direction: column; }
    .viewer { position: static; width: 100%%; height: 70vh; }
  }
  @media (max-width: 640px) {
    .c-id, thead .c-id { display: none; }
    body { padding: 20px 16px 48px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <h1>HL7 AU Project Registry</h1>
  <p class="summary">%(summary)s</p>
  <div class="controls">
    <button type="button" id="expand-all">Expand all</button>
    <button type="button" id="collapse-all">Collapse all</button>
  </div>
  <div class="layout">
    <div class="list">
      <table>
        <thead>
          <tr>
            <th class="c-toggle"></th>
            <th class="c-id">Project&nbsp;ID&thinsp;/&thinsp;Release</th>
            <th>Status</th>
            <th>Submitted</th>
            <th>Title</th>
            <th class="c-doc">Document</th>
          </tr>
        </thead>
        <tbody>
%(rows)s
        </tbody>
      </table>
    </div>
    <aside class="viewer" id="viewer">
      <div class="viewer-head">
        <span class="viewer-name" id="viewer-name">Preview</span>
        <a id="viewer-open" href="#" target="_blank" rel="noopener" hidden>Open in new tab</a>
        <a id="viewer-close" href="#" hidden>Close</a>
      </div>
      <div class="viewer-body">
        <iframe id="viewer-frame" title="Document preview" hidden></iframe>
        <div class="viewer-empty" id="viewer-empty">Select a PP or PSS document to preview it here.</div>
      </div>
    </aside>
  </div>
</div>
<script>
  function setOpen(row, open) {
    if (row.classList.contains('leaf')) return;
    row.classList.toggle('open', open);
    row.setAttribute('aria-expanded', open ? 'true' : 'false');
    var id = row.dataset.project;
    document.querySelectorAll('tr.pss[data-parent="' + id + '"]').forEach(function (child) {
      child.hidden = !open;
    });
  }

  document.querySelectorAll('tr.project').forEach(function (row) {
    row.addEventListener('click', function (event) {
      if (event.target.closest('a')) return;
      setOpen(row, !row.classList.contains('open'));
    });
    row.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        setOpen(row, !row.classList.contains('open'));
      }
    });
  });

  function setAll(open) {
    document.querySelectorAll('tr.project').forEach(function (row) { setOpen(row, open); });
  }
  document.getElementById('expand-all').addEventListener('click', function () { setAll(true); });
  document.getElementById('collapse-all').addEventListener('click', function () { setAll(false); });

  var frame = document.getElementById('viewer-frame');
  var empty = document.getElementById('viewer-empty');
  var nameEl = document.getElementById('viewer-name');
  var openEl = document.getElementById('viewer-open');
  var closeEl = document.getElementById('viewer-close');

  function clearPreview() {
    document.querySelectorAll('a.doc.active').forEach(function (el) { el.classList.remove('active'); });
    frame.hidden = true;
    frame.removeAttribute('src');
    openEl.hidden = true;
    closeEl.hidden = true;
    nameEl.textContent = 'Preview';
    empty.hidden = false;
    empty.textContent = 'Select a PP or PSS document to preview it here.';
  }

  document.querySelectorAll('a.doc').forEach(function (anchor) {
    anchor.addEventListener('click', function (event) {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      if (anchor.classList.contains('active')) { clearPreview(); return; }
      document.querySelectorAll('a.doc.active').forEach(function (el) { el.classList.remove('active'); });
      anchor.classList.add('active');
      nameEl.textContent = anchor.dataset.name;
      openEl.href = anchor.href;
      openEl.hidden = false;
      closeEl.hidden = false;
      empty.hidden = true;
      frame.hidden = false;
      frame.src = anchor.getAttribute('href');
    });
  });

  closeEl.addEventListener('click', function (event) {
    event.preventDefault();
    clearPreview();
  });
</script>
</body>
</html>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "registry.md"
    dst = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    root = os.path.dirname(os.path.abspath(src)) or "."
    projects = parse(src)
    warnings = check(projects, root)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(projects))
    total_pss = sum(len(p["pss"]) for p in projects)
    print("%s -> %s (%d projects, %d PSS)" % (src, dst, len(projects), total_pss))
    for w in warnings:
        print("warning: %s" % w)


if __name__ == "__main__":
    main()
