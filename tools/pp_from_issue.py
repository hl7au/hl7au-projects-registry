"""Turn a "Submit a project proposal" issue into a registry entry.

Usage: python tools/pp_from_issue.py --body issue.md [--registry registry.md]

Reads the issue body produced by .github/ISSUE_TEMPLATE/pp-submission.yml,
downloads the attached PDF into PP/ under the registry naming convention, and
adds the project to registry.md with status "Submitted" and the next free
AU#### ID. When the project is already in the registry without a proposal, the
proposal is attached to that entry instead. Writes a markdown summary for the
pull request body to the path given by --summary, if any.
"""

import argparse
import os
import re
import sys

import registry_issue as reg

# The issue form's field labels, mapped to the names used here.
FIELDS = {
    "Project": "project",
    "Work group approval date": "approved",
    "Work group": "workgroup",
    "Project proposal document": "pdf",
    "Notes for the TSC": "notes",
}
REQUIRED = ("project", "approved", "pdf")

PP_FIELD = re.compile(r"^(\s*)PP:\s*(.*?)\s*$", re.IGNORECASE)


def set_pp(lines, start, end, path):
    """Point the project's PP: field at `path`, adding the field if missing."""
    for i in range(start, end):
        field = PP_FIELD.match(lines[i])
        if field:
            if field.group(2):
                reg.fail(
                    "this project already has a proposal on file (%s) - submit a "
                    "scope statement instead, or ask the TSC to replace it"
                    % field.group(2)
                )
            lines[i] = "%sPP: %s" % (field.group(1), path)
            return
    # No PP: line at all: put one after the last field, before any table.
    insert_at = end
    for i in range(start, end):
        if lines[i].lstrip().startswith("|"):
            insert_at = i
            break
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, "PP: %s" % path)


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
        # Auto-incremented from the highest AU#### already in the registry.
        new_id = reg.next_project_id(projects)
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## %s %s" % (new_id, project), "", "Status: Submitted",
                  "Submitted: %s" % approved, "PP:"]
        match = reg.find_project(reg.read_projects(lines), new_id)
    index, pid, title = match

    start, end = reg.section_bounds(lines, index)
    stem, from_file = reg.document_stem(title, lines[start:end])
    path = "PP/%s %s.pdf" % (approved.replace("-", ""), stem)
    if os.path.exists(os.path.join(root, path)):
        reg.fail("%s is already in the registry - is this a resubmission?" % path)

    size = 0
    if not args.no_download:
        size = reg.download_pdf(
            reg.attachment_url(values["pdf"], "Project proposal document"),
            os.path.join(root, path),
        )

    set_pp(lines, start, end, path)
    reg.write_lines(args.registry, lines)

    notes = []
    if new_project:
        notes.append(
            "- **New project.** Added as %s, the next ID after the highest in the "
            "registry." % pid
        )
    else:
        notes.append(
            "- **Existing project.** The proposal was attached to %s, whose status and "
            "submitted date are unchanged." % pid
        )
    if not from_file:
        notes.append(
            "- **Check the file name.** %s has no other documents on file, so the "
            "document name was derived from the project title." % pid
        )

    body = [
        "Adds a work-group-approved project proposal to the registry with status "
        "`Submitted`.",
        "",
    ]
    body += reg.summary_table(
        [
            ("Project", "%s %s" % (pid, title)),
            ("Approved", approved),
            ("Work group", workgroup),
            ("Document", "`%s` (%.1f KB)" % (path, size / 1024.0)),
        ]
    )
    body += [""] + notes + [""]
    submitter_notes = reg.optional(values, "notes")
    if submitter_notes:
        body += ["**Notes from the submitter**", "", submitter_notes, ""]
    summary = "\n".join(body)

    if args.summary:
        with open(args.summary, "w", encoding="utf-8", newline="\n") as f:
            f.write(summary)

    print("project=%s" % pid)
    print("path=%s" % path)
    print("what=PP")
    sys.stderr.write(summary + "\n")


if __name__ == "__main__":
    main()
