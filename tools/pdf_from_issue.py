"""Add or replace the PDF behind a registry entry, from an issue.

Usage: python tools/pdf_from_issue.py --kind pp|pss --body issue.md
                                      [--registry registry.md] [--summary pr-body.md]

Reads the issue body produced by .github/ISSUE_TEMPLATE/pp-pdf.yml or
pss-pdf.yml. A project proposal is addressed by project ID; a scope statement
by project ID and release, which is why registry.md carries a Release column.
The new PDF is filed under the naming convention, the entry is pointed at it,
and a superseded file that nothing else references is removed.
"""

import argparse
import os
import sys

import registry_issue as reg

FIELDS = {
    "Project": "project",
    "Release": "release",
    "Document date": "dated",
    "Document": "pdf",
    "What changed": "notes",
}
PP_FIELD_PREFIX = "PP:"


def pp_line(lines, start, end):
    """The index of the project's PP: line, or None."""
    for i in range(start, end):
        if lines[i].strip().lower().startswith("pp:"):
            return i
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=("pp", "pss"))
    parser.add_argument("--body", required=True, help="file holding the issue body")
    parser.add_argument("--registry", default="registry.md")
    parser.add_argument("--summary", help="write a markdown summary here")
    parser.add_argument("--no-download", action="store_true", help="for tests")
    args = parser.parse_args()

    required = ["project", "dated", "pdf"] + (["release"] if args.kind == "pss" else [])
    with open(args.body, encoding="utf-8") as f:
        values = reg.parse_issue(f.read(), FIELDS, required)

    project = reg.clean(values["project"], "Project")
    dated = reg.check_date(reg.clean(values["dated"], "Document date"), "the document date")

    root = os.path.dirname(os.path.abspath(args.registry)) or "."
    lines = reg.read_lines(args.registry)
    match = reg.find_project(reg.read_projects(lines), project)
    if match is None:
        reg.fail(
            "no project %r in the registry - give the project ID as it appears "
            "there, e.g. AU0009" % project
        )
    index, pid, title = match
    start, end = reg.section_bounds(lines, index)
    stem, _ = reg.document_stem(title, lines[start:end])

    if args.kind == "pss":
        release = reg.check_release(values["release"])
        row = reg.find_release(lines, start, end, release)
        if row is None:
            known = reg.releases(lines[start:end])
            reg.fail(
                "%s has no %s scope statement%s - submit it with the scope "
                "statement form first"
                % (pid, release, " (it has %s)" % ", ".join(known) if known else "")
            )
        old = reg.cells(lines[row])[4]
        path = "PSS/%s %s %s.pdf" % (dated.replace("-", ""), stem, release)
        what = "%s %s PSS" % (pid, release)
    else:
        release = ""
        row = pp_line(lines, start, end)
        if row is None:
            reg.fail("%s has no PP: field - fix registry.md by hand" % pid)
        old = lines[row].split(":", 1)[1].strip()
        path = "PP/%s %s.pdf" % (dated.replace("-", ""), stem)
        what = "%s PP" % pid

    size = 0
    if not args.no_download:
        size = reg.download_pdf(
            reg.attachment_url(values["pdf"], "Document"), os.path.join(root, path)
        )

    if args.kind == "pss":
        reg.set_cell(lines, row, 4, path)
    else:
        lines[row] = "PP: %s" % path
    reg.write_lines(args.registry, lines)

    # Drop a superseded file once nothing in the registry points at it. The
    # pull request shows the deletion, so the TSC sees it before it lands.
    removed = ""
    if old and old != path:
        still_used = any(old in line for line in reg.read_lines(args.registry))
        if not still_used and os.path.exists(os.path.join(root, old)):
            os.remove(os.path.join(root, old))
            removed = old

    action = "Replaces" if old else "Adds"
    body = ["%s the document behind %s." % (action, what), ""]
    body += reg.summary_table(
        [
            ("Project", "%s %s" % (pid, title)),
            ("Entry", what),
            ("Document date", dated),
            ("New document", "`%s` (%.1f KB)" % (path, size / 1024.0)),
            ("Replaces", "`%s`" % old if old else "nothing - the entry had no document"),
        ]
    )
    body += [""]
    if removed:
        body += ["- **%s was deleted**, since nothing else in the registry "
                 "references it." % removed, ""]
    elif old and old == path:
        body += ["- The file name is unchanged, so this is an in-place replacement.", ""]
    elif old:
        body += ["- `%s` was kept, because another entry still references it." % old, ""]
    changed = reg.optional(values, "notes")
    if changed:
        body += ["**What changed**", "", changed, ""]
    summary = "\n".join(body)

    if args.summary:
        with open(args.summary, "w", encoding="utf-8", newline="\n") as f:
            f.write(summary)

    print("project=%s" % pid)
    print("path=%s" % path)
    print("what=%s PDF" % (("%s " % release) + "PSS" if release else "PP"))
    sys.stderr.write(summary + "\n")


if __name__ == "__main__":
    main()
