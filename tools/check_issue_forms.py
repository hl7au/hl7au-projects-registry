"""Check the issue forms the way GitHub does.

Usage: python tools/check_issue_forms.py [.github/ISSUE_TEMPLATE]

GitHub parses issue forms with Ruby's safe YAML loader, which refuses anything
that is not a plain string, number or boolean. Python's loader is happy to turn
an unquoted `2026-08-18` into a date, so a form that loads fine locally can
still be rejected by GitHub with "Tried to load unspecified class: Date" — and
a rejected form simply vanishes from the new-issue chooser, with no failed
build to notice. This catches that before it is pushed.
"""

import datetime
import glob
import os
import sys

import yaml

# Contact links in config.yml must be http(s): GitHub drops anything else,
# a mailto: link included, without reporting an error.
WEB = ("http://", "https://")


def scalars(node, path):
    if isinstance(node, dict):
        for key, value in node.items():
            for found in scalars(value, "%s.%s" % (path, key)):
                yield found
    elif isinstance(node, list):
        for i, value in enumerate(node):
            for found in scalars(value, "%s[%d]" % (path, i)):
                yield found
    else:
        yield path, node


def check(path):
    problems = []
    with open(path, encoding="utf-8") as f:
        try:
            form = yaml.safe_load(f)
        except yaml.YAMLError as error:
            return ["%s: not valid YAML: %s" % (path, error)]

    for where, value in scalars(form, ""):
        if isinstance(value, (datetime.date, datetime.datetime)):
            problems.append(
                "%s:%s is a date (%s) - GitHub refuses it, quote the value"
                % (path, where, value)
            )
        elif value is not None and not isinstance(value, (str, bool, int, float)):
            problems.append(
                "%s:%s is a %s - GitHub only accepts strings, numbers and booleans"
                % (path, where, type(value).__name__)
            )

    if os.path.basename(path) == "config.yml":
        for i, link in enumerate(form.get("contact_links") or []):
            if not str(link.get("url", "")).startswith(WEB):
                problems.append(
                    "%s: contact_links[%d] (%s) is not an http(s) URL - GitHub "
                    "drops it silently" % (path, i, link.get("url"))
                )
        return problems

    for field in form.get("body") or []:
        if field.get("type") != "markdown" and not field.get("id"):
            problems.append(
                "%s: a %s field has no id - the issue body cannot be parsed "
                "without one" % (path, field.get("type"))
            )
    return problems


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else ".github/ISSUE_TEMPLATE"
    problems = []
    forms = sorted(glob.glob(os.path.join(root, "*.yml")))
    if not forms:
        raise SystemExit("no issue forms found in %s" % root)
    for path in forms:
        problems += check(path)
    for problem in problems:
        print("warning: %s" % problem)
    print("checked %d issue forms" % len(forms))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
