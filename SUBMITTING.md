# Submitting to the AU TSC

A guide for work group co-chairs. It covers writing a project proposal or scope
statement on the HL7 AU templates, submitting it to the TSC, and replacing the
document afterwards.

Everything goes through this repository. You need a free
[GitHub account](https://github.com/signup); nothing else is installed, and you
never edit the registry directly.

## What goes where

| You have | You want |
| --- | --- |
| A new project | A **project proposal** (PP) — registers the project and gets it an `AU####` ID |
| A release of an existing project | A **project scope statement** (PSS) — one per release: R1, R2, R3 |
| An amended version of either | A **PDF update** against the entry that is already listed |

A project needs a proposal before its scope statements mean much, but the forms
do not force the order: submitting a PSS for an unlisted project creates the
project entry, and the pull request tells the TSC a proposal is still owed.

## 1. Write the document

Templates can be used to complete document submissions.

- [HL7 AU PP Template](TEMPLATES/HL7%20AU%20PP%20Template%201.0.docx)
- [HL7 AU PSS Template](TEMPLATES/HL7%20AU%20PSS%20Template%201.0.docx)

Take the completed document through your work group in the normal way. **Note
the date your work group approved it** — that date goes on the document and into
the submission, and it is the date the registry shows.

When it is approved, **export it to PDF**. Word's *Save as PDF* is fine. The
submission is rejected if you attach the `.docx`.

You do not need to name the file anything in particular. The registry renames it
to `YYYYMMDD <Project> <Release>.pdf` from what you type into the form.

## 2. Submit it

Open the matching form and fill it in:

- [**Submit a PP**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=1-pp-submission.yml)
- [**Submit a PSS**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=2-pss-submission.yml)

Drag the PDF into the document box — GitHub uploads it and leaves a link behind.
Every field marked `*` is required.

For a PSS, give the **project** as its registry ID (`AU0009`) and the
**release** as it appears in the registry — `R1`, `R2` and so on for most
projects, though a project may use another scheme. For a PP, give the project name if the
project is new, or its ID if the project is listed but has no proposal on file.

The project ID for a new project is allocated for you — the next number after
the highest in the [registry](https://hl7au.github.io/hl7au-projects-registry/).

A new project's PP and its first PSS can be submitted at the same time. The
project has no registry ID yet, so give the **project name** in the PSS form —
spelled exactly as you gave it in the PP form, since that is what ties the two
together. Submit the PP first and the TSC will take them in that order: the
proposal is merged, which creates the project and its ID, and the scope
statement is then re-run against it.

## 3. What happens next

Within a minute the submission becomes a **pull request** for the TSC, and a
comment appears on your issue saying so. The registry shows the entry with the
status **Submitted** once the TSC merges that pull request.

The TSC then considers it at a meeting. If it is approved the status becomes
**Approved**, and later **Published** when the release is published. You do not
have to do anything for those status changes.

If the form was filled in wrongly — a date that is not `YYYY-MM-DD`, a release
with spaces in it, a Word document instead of a PDF — no pull request is created
and the reason is commented on your issue instead. Edit the issue to fix it and
ask a TSC maintainer to re-run it; you do not need to open a new one.

## 4. Replacing the document later

Use these when the entry is **already in the registry** and only the document
changes — the TSC asked for amendments, or you have a corrected version:

- [**Add or update a PP PDF**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=3-pp-pdf.yml) — identified by project ID
- [**Add or update a PSS PDF**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=4-pss-pdf.yml) — identified by project ID **and release**

Both ask for a **document date**: the date on *this* version, not the original.
The new file is named from it, the entry is pointed at the new file, and the
superseded one is removed. Say what changed in the form — that text reaches the
TSC in the pull request.

These forms do not change an entry's status, its title or its release. Ask the
TSC if one of those is wrong.

## Finding the ID and release

Both are on the entry's row in the
[registry](https://hl7au.github.io/hl7au-projects-registry/): the project ID
(`AU0009`) on the project row, and the release (`R3`) on each scope statement
underneath it. Click a project row to expand its scope statements.

## Anything else

Something wrong on the site, or a correction to an entry that is not a new
document? Use the
[**Something else**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=5-other.yml)
form, or email the TSC at <projects@hl7.au>.
