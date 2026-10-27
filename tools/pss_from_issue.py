"""Turn a "Submit a project scope statement" issue into a registry entry.

Usage: python tools/pss_from_issue.py --body issue.md [--registry registry.md]

Reads the issue body produced by .github/ISSUE_TEMPLATE/pss-submission.yml,
downloads the attached PDF into PSS/ under the registry naming convention, and
adds a PSS row (status "Submitted") to the project in registry.md, creating the
project entry if it is not there yet. Writes a markdown summary for the pull
request body to the path given by --summary, if any.

Everything it touches comes from a public issue, so nothing here is trusted:
the attachment host is checked against an allow list, the download is
size-capped and must start with a PDF header, and every value that reaches
registry.md is validated.
"""

import argparse
import os
import re
import sys
import urllib.parse
import urllib.request

ALLOWED_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "user-images.githubusercontent.com",
    "raw.githubusercontent.com",
}
MAX_PDF_BYTES = 25 * 1024 * 1024

SECTION = re.compile(r"^###\s+(.*\S)\s*$")
HEADING = re.compile(r"^##\s+(\S+)\s+(.*\S)\s*$")
PROJECT_ID = re.compile(r"^AU(\d{4})$")
RELEASE = re.compile(r"^R\d+$", re.IGNORECASE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL = re.compile(r"https://[^\s)>\]]+")

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

NO_RESPONSE = "_No response_"


def fail(message):
    raise SystemExit("error: " + message)


def parse_issue(body):
    """Split a rendered issue-form body into {field name: value}."""
    values = {}
    key = None
    buf = []
    for line in body.splitlines():
        section = SECTION.match(line)
        if section:
            if key:
                values[key] = "\n".join(buf).strip()
            key = FIELDS.get(section.group(1).strip())
            buf = []
            continue
        if key:
            buf.append(line)
    if key:
        values[key] = "\n".join(buf).strip()
    for name in ("project", "pss_title", "release", "approved", "pdf"):
        if not values.get(name) or values[name] == NO_RESPONSE:
            fail("the issue is missing a value for %r" % name)
    return values


def clean(value, what):
    """A single line, safe to put in a markdown table cell."""
    value = " ".join(value.split())
    if "|" in value:
        fail("%s may not contain a '|'" % what)
    if not value:
        fail("%s is empty" % what)
    return value


def attachment_url(text):
    """The first allowed GitHub attachment URL in the PSS document field."""
    for candidate in URL.findall(text):
        host = urllib.parse.urlparse(candidate).hostname or ""
        if host in ALLOWED_HOSTS:
            return candidate
    fail(
        "no GitHub attachment found in the PSS document field - drag the PDF "
        "into the box so GitHub uploads it"
    )


def download_pdf(url, dest):
    request = urllib.request.Request(url, headers={"User-Agent": "hl7au-projects-registry"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        fail("the attachment is larger than %d MB" % (MAX_PDF_BYTES // (1024 * 1024)))
    if not data.startswith(b"%PDF-"):
        fail("the attachment is not a PDF - submit the approved PDF, not a Word document")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def read_projects(lines):
    """[(index of the '##' line, id, title)] for each project in registry.md."""
    found = []
    for i, line in enumerate(lines):
        heading = HEADING.match(line)
        if heading:
            found.append((i, heading.group(1), heading.group(2)))
    return found


def find_project(projects, wanted):
    key = wanted.casefold()
    for index, pid, title in projects:
        if pid.casefold() == key or title.casefold() == key:
            return index, pid, title
    return None


def next_project_id(projects):
    numbers = [int(m.group(1)) for _, pid, _ in projects for m in [PROJECT_ID.match(pid)] if m]
    return "AU%04d" % (max(numbers) + 1 if numbers else 1)


def document_stem(title, section):
    """The file-name stem for a project: its last PSS's, else from the title.

    Existing PDFs carry the short form of the name ("AU Core FHIR IG"), which
    is not always derivable from the registry title, so reuse the project's own
    most recent file name when it has one.
    """
    for line in reversed(section):
        match = re.search(r"\|\s*PSS/\d{8}\s+(.*?)\s+R\d+\.pdf\s*\|", line, re.IGNORECASE)
        if match:
            return match.group(1), True
    stem = re.sub(r"\bFHIR Implementation Guide\b", "FHIR IG", title, flags=re.IGNORECASE)
    stem = re.sub(r"\bImplementation Guide\b", "IG", stem, flags=re.IGNORECASE)
    return stem, False


def section_bounds(lines, start):
    """The half-open line range of the project section beginning at `start`."""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEADING.match(lines[i]):
            end = i
            break
    while end > start and not lines[end - 1].strip():
        end -= 1
    return start, end


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
        "| Submitted | Status | Title | PSS |",
        "| --- | --- | --- | --- |",
        row,
    ]


def build_summary(pid, title, pss_title, release, approved, workgroup, path, size, notes, submitter_notes):
    rows = [
        "Adds a work-group-approved scope statement to the registry with status `Submitted`.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Project | %s %s |" % (pid, title),
        "| PSS | %s |" % pss_title,
        "| Release | %s |" % release,
        "| Approved | %s |" % approved,
        "| Work group | %s |" % workgroup,
        "| Document | `%s` (%.1f KB) |" % (path, size / 1024.0),
        "",
    ]
    if notes:
        rows += notes + [""]
    if submitter_notes:
        rows += ["**Notes from the submitter**", "", submitter_notes, ""]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", required=True, help="file holding the issue body")
    parser.add_argument("--registry", default="registry.md")
    parser.add_argument("--summary", help="write a markdown summary here")
    parser.add_argument("--no-download", action="store_true", help="for tests")
    args = parser.parse_args()

    with open(args.body, encoding="utf-8") as f:
        values = parse_issue(f.read())

    project = clean(values["project"], "Project")
    pss_title = clean(values["pss_title"], "PSS title")
    release = clean(values["release"], "Release").upper()
    approved = clean(values["approved"], "Work group approval date")
    workgroup = values.get("workgroup", "")
    workgroup = clean(workgroup, "Work group") if workgroup and workgroup != NO_RESPONSE else "-"
    if not RELEASE.match(release):
        fail("the release must look like R1, R2, R3 - got %r" % release)
    if not DATE.match(approved):
        fail("the approval date must be YYYY-MM-DD - got %r" % approved)

    root = os.path.dirname(os.path.abspath(args.registry)) or "."
    with open(args.registry, encoding="utf-8") as f:
        lines = f.read().splitlines()

    projects = read_projects(lines)
    match = find_project(projects, project)
    new_project = match is None
    if new_project:
        new_id = next_project_id(projects)
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## %s %s" % (new_id, project), "", "Status: Submitted",
                  "Submitted: %s" % approved, "PP:"]
        match = find_project(read_projects(lines), new_id)
    index, pid, title = match

    start, end = section_bounds(lines, index)
    stem, from_file = document_stem(title, lines[start:end])
    path = "PSS/%s %s %s.pdf" % (approved.replace("-", ""), stem, release)

    size = 0
    if not args.no_download:
        size = download_pdf(attachment_url(values["pdf"]), os.path.join(root, path))

    insert_row(lines, start, end, "| %s | Submitted | %s | %s |" % (approved, pss_title, path))
    with open(args.registry, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    notes = []
    if new_project:
        notes.append(
            "- **New project entry.** `%s` was not in the registry, so it was added as %s "
            "with status `Submitted` and no project proposal - check the ID, the title and "
            "whether a PP is needed." % (title, pid)
        )
    if not from_file:
        notes.append(
            "- **Check the file name.** %s has no PSS on file, so the document name was "
            "derived from the project title." % pid
        )
    submitter_notes = values.get("notes", "")
    if submitter_notes == NO_RESPONSE:
        submitter_notes = ""
    summary = build_summary(pid, title, pss_title, release, approved, workgroup,
                            path, size, notes, submitter_notes)
    if args.summary:
        with open(args.summary, "w", encoding="utf-8", newline="\n") as f:
            f.write(summary)

    print("project=%s" % pid)
    print("path=%s" % path)
    print("release=%s" % release)
    sys.stderr.write(summary + "\n")


if __name__ == "__main__":
    main()
