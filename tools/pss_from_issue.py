"""Turn a "Submit a project scope statement" issue into a registry entry.

Usage: python tools/pss_from_issue.py --body issue.md [--registry registry.md]

Reads the issue body produced by .github/ISSUE_TEMPLATE/pss-submission.yml,
downloads the attached PDF into PSS/ under the registry naming convention, and
adds a PSS row (status "Submitted") to the project in registry.md, creating the
project entry if it is not there yet. Writes a markdown summary for the pull
request body to the path given by --summary, if any.
"""

import argparse
import os
import sys

import registry_issue as reg

# The issue form's field labels, mapped to the names used here.
FIELDS = {
    "Project": "project",
    "PSS title": "pss_title",
    "Release": "release",
    "Work group approval date": "approved",
    "Work group": "workgroup",
    "PSS document": "pdf",
    "Notes for the TSC": "notes",
}
REQUIRED = ("project", "pss_title", "release", "approved", "pdf")


def insert_row(lines, start, end, row):
    """Add `row` to the project's PSS table, creating the table if needed."""
    last_row = None
    for i in range(start, end):
        if lines[i].lstrip().startswith("|"):
            last_row = i
    if last_row is not None:
        lines.insert(last_row + 1, row)
        return
    lines[end:end] = [
        "",
        "| Release | Submitted | Status | Title | PSS |",
        "| --- | --- | --- | --- | --- |",
        row,
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", required=True, help="file holding the issue body")
    parser.add_argument("--registry", default="registry.md")
    parser.add_argument("--summary", help="write a markdown summary here")
    parser.add_argument("--no-download", action="store_true", help="for tests")
    args = parser.parse_args()

    with open(args.body, encoding="utf-8") as f:
        values = reg.parse_issue(f.read(), FIELDS, REQUIRED)

    project = reg.clean(values["project"], "Project")
    pss_title = reg.clean(values["pss_title"], "PSS title")
    release = reg.check_release(values["release"])
    approved = reg.check_date(
        reg.clean(values["approved"], "Work group approval date"), "the approval date"
    )
    workgroup = reg.optional(values, "workgroup")
    workgroup = reg.clean(workgroup, "Work group") if workgroup else "-"

    root = os.path.dirname(os.path.abspath(args.registry)) or "."
    lines = reg.read_lines(args.registry)

    projects = reg.read_projects(lines)
    match = reg.find_project(projects, project)
    new_project = match is None
    if new_project:
        new_id = reg.next_project_id(projects)
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## %s %s" % (new_id, project), "", "Status: Submitted",
                  "Submitted: %s" % approved, "PP:"]
        match = reg.find_project(reg.read_projects(lines), new_id)
    index, pid, title = match

    start, end = reg.section_bounds(lines, index)
    stem, from_file = reg.document_stem(title, lines[start:end])
    path = "PSS/%s %s %s.pdf" % (approved.replace("-", ""), stem, release)
    if os.path.exists(os.path.join(root, path)):
        reg.fail("%s is already in the registry - is this a resubmission?" % path)

    size = 0
    if not args.no_download:
        size = reg.download_pdf(
            reg.attachment_url(values["pdf"], "PSS document"), os.path.join(root, path)
        )

    if release in reg.releases(lines[start:end]):
        reg.fail(
            "%s already has a %s scope statement - use the "
            "\"Add or update a PSS PDF\" form to replace its document" % (pid, release)
        )
    insert_row(
        lines, start, end,
        "| %s | %s | Submitted | %s | %s |" % (release, approved, pss_title, path),
    )
    reg.write_lines(args.registry, lines)

    notes = []
    if new_project:
        notes.append(
            "- **New project entry.** `%s` was not in the registry, so it was added as %s "
            "with status `Submitted` and no project proposal - check the ID, the title and "
            "whether a PP is needed." % (title, pid)
        )
    if not from_file:
        notes.append(
            "- **Check the file name.** %s has no documents on file, so the document name "
            "was derived from the project title." % pid
        )

    body = [
        "Adds a work-group-approved scope statement to the registry with status `Submitted`.",
        "",
    ]
    body += reg.summary_table(
        [
            ("Project", "%s %s" % (pid, title)),
            ("PSS", pss_title),
            ("Release", release),
            ("Approved", approved),
            ("Work group", workgroup),
            ("Document", "`%s` (%.1f KB)" % (path, size / 1024.0)),
        ]
    )
    body += [""]
    if notes:
        body += notes + [""]
    submitter_notes = reg.optional(values, "notes")
    if submitter_notes:
        body += ["**Notes from the submitter**", "", submitter_notes, ""]
    summary = "\n".join(body)

    if args.summary:
        with open(args.summary, "w", encoding="utf-8", newline="\n") as f:
            f.write(summary)

    print("project=%s" % pid)
    print("path=%s" % path)
    print("what=%s PSS" % release)
    sys.stderr.write(summary + "\n")


if __name__ == "__main__":
    main()
