# HL7 AU Project Registry

A simple registry of HL7 Australia projects: each project proposal (PP) with its child
project scope statements (PSS), rendered as a single HTML page with the source PDFs.

## Contents

| Path | What it holds |
| --- | --- |
| `registry.md` | The source of truth — projects, scope statements, statuses and document links |
| `build.py` | Generates `index.html` from `registry.md` (standard library only) |
| `SUBMITTING.md` | The guide for work group co-chairs submitting a PP or PSS |
| `tools/` | The scripts behind the submission workflow |
| `PP/` | Project proposal PDFs |
| `PSS/` | Project scope statement PDFs |
| `NIB/` | Notice of intent to ballot PDFs |
| `TEMPLATES/` | The blank HL7 AU forms (`.docx`, so they stay fillable) |

`index.html` is generated and is not committed — CI builds it, and you build it locally
when you want to look at it.

## Editing the registry

Edit `registry.md`, then:

```bash
python build.py
```

Open `index.html` in a browser. Clicking a project row expands its scope statements, and
clicking a document icon previews that PDF in the right-hand pane.

`build.py` prints a warning for any status outside the allowed list and for any PP/PSS
link that does not resolve to a file in the repository. CI fails the build on either.

### registry.md format

One `##` heading per project, `## <Project ID> <Title>`, followed by its fields and an
optional table of scope statements:

```markdown
## AU0010 AU eRequesting FHIR Implementation Guide

Status: Approved
Submitted: 2023-11-27
PP: PP/20231123 AU eRequesting FHIR IG.pdf

| Submitted | Status | Title | PSS |
| --- | --- | --- | --- |
| R1 | 2025-04-17 | Published | AU eRequesting FHIR IG R1 PSS | PSS/20250430 AU eRequesting FHIR IG R1.pdf |
```

The release is a short token with no spaces — `R1`, `R2` by convention, but any
scheme a project uses — and must be unique within the project: with the project ID it is
what identifies a scope statement, and it shows as a small pill under the project ID in
the view. Leave `PP:` empty for a project with no proposal on file, and leave the last
table cell empty for a scope statement whose PDF is not in the repository. Projects
appear in the view in the order they appear in the file.

Allowed statuses: `Proposed`, `Submitted`, `Approved`, `Active`, `Inactive`, `Withdrawn`,
and `Published` for PSS rows only.

## Submitting to the TSC

Work groups submit an approved document to the AU TSC by opening an issue.
[SUBMITTING.md](SUBMITTING.md) is the guide for co-chairs doing that; what
follows is how it works underneath.

| Form | What it adds |
| --- | --- |
| [**Submit a PP**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=1-pp-submission.yml) | A project, with the proposal PDF in `PP/` |
| [**Submit a PSS**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=2-pss-submission.yml) | A scope statement under a project, with the PSS PDF in `PSS/` |
| [**Add or update a PP PDF**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=3-pp-pdf.yml) | A new document for a proposal already listed, found by project ID |
| [**Add or update a PSS PDF**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=4-pss-pdf.yml) | A new document for a scope statement already listed, found by project ID and release |

Each form links the blank `.docx` template to write on, and asks for the
project, the work group, the work group's approval date and the approved PDF
dragged into the form; the scope statement form also asks for the PSS title and
the release. The attachment must be a PDF — a `.docx` is rejected — and those
answers are what the file name is built from, so the submitter's own file name
does not matter.

Blank issues are turned off, so every issue starts from a form and a submission
always arrives with the metadata the registry needs; the fields themselves are
required, so a half-filled form cannot be sent. Anything that is not a
submission goes through the **Something else** form, which the workflow ignores.

`.github/workflows/submission.yml` then turns the issue into a pull request — it
files the PDF under the naming convention, adds the entry to `registry.md` with
status `Submitted`, and checks that the registry still builds. The TSC reviews
and merges the pull request; changing the status later is an ordinary edit to
`registry.md`.

Project IDs are allocated by the workflow: a new project gets the next `AU####`
after the highest already in the registry. Two submissions for the same new
project — a PP and its first PSS, sent together — are each allocated that ID
against `main`, so both claim it until one is merged. Merge the proposal first,
then re-run the scope statement's issue from the Actions tab: it rebuilds its
branch against the updated registry and finds the project by name. `build.py`
warns if two entries ever end up sharing an ID, so CI stops it landing. A proposal for a project that is
already listed without one is attached to that entry instead, leaving its status
and submitted date alone; a project that already has a proposal is refused.
Submitting a scope statement for a project that is not listed yet creates the
project entry with no proposal, and the pull request says so.

When the submission is malformed — a date that is not `YYYY-MM-DD`, a release
with spaces in it, an attachment that is not a PDF — the workflow comments the
error on the issue. The submitter edits the issue and a maintainer re-runs the
workflow from the Actions tab with the issue number.

`tools/check_issue_forms.py` checks the forms the way GitHub parses them — it
is stricter than a plain YAML load, because GitHub rejects a form containing an
unquoted date and then simply leaves it out of the new-issue chooser with no
error anywhere. CI runs it.

The two PDF forms change an existing entry rather than adding one. They point it at
the new file, named from the document date they are given, and delete the superseded
file once nothing in `registry.md` references it — the pull request shows that deletion.
A scope statement that is not listed is refused, with the project's known releases in
the message.

`tools/pp_from_issue.py`, `tools/pss_from_issue.py` and `tools/pdf_from_issue.py`
(`--kind pp|pss`) do the work, sharing `tools/registry_issue.py`, and run locally too:

```bash
python tools/pss_from_issue.py --body issue.md --summary pr-body.md
```

The workflow can only open the pull request while **Settings > Actions > General >
Allow GitHub Actions to create and approve pull requests** stays on.

GitHub does not run `pull_request` workflows for a pull request opened by a
workflow, so `build.yml` does not fire on these. The submission workflow builds
the registry itself before pushing and reports the result on the pull request as
a `registry build` commit status; a later push to the branch by a reviewer is an
ordinary push and does trigger CI.

## File naming

Documents are named `YYYYMMDD <Project> [<Release>].pdf`, where the date is the date on the
document (when the work group approved it), not the date it was emailed to the TSC.
FHIR implementation guides are written as "FHIR IG". PSS and NIB filenames carry the
release as `R1`, `R2` and so on.

## View options

| URL | Effect |
| --- | --- |
| `index.html` | Content centred in the window (the default) |
| `index.html?align=left` | Content pinned to the left edge — use this when embedding in a page that does its own centring |

## Publishing

The workflow in `.github/workflows/build.yml` builds the site on every push and uploads
it as a build artifact. Deployment to GitHub Pages only runs when the repository variable
`PUBLISH_PAGES` is set to `true`, because **a GitHub Pages site is served publicly even
when the repository is private** — see the deployment notes before turning it on.
