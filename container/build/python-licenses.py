# SPDX-FileCopyrightText: 2026 Jens Rehsack <sno@netbsd.org>
# SPDX-License-Identifier: Apache-2.0
#
# python-licenses.py — every installed Python distribution with its version, license and
# source, as TSV on stdout. Build-time only: the Containerfile mounts it, runs it once
# and keeps the output, not the script.
#
# The license comes from the package's own metadata: License-Expression (PEP 639) where
# the package states one, the License field where it is a valid SPDX expression, the
# trove classifiers otherwise. The License field is free text — a whole license, or
# "Dual License" — so it is only taken once SPDX says it is an expression.
# license-expression is in the image as a dependency of reuse; without it, the field is
# never trusted and the classifiers answer.

import importlib.metadata

try:
    from license_expression import get_spdx_licensing

    _spdx = get_spdx_licensing()
except ImportError:
    _spdx = None


def is_spdx(text):
    if _spdx is None or not text or "\n" in text:
        return False
    return not _spdx.validate(text).errors


def license_of(md):
    expression = md.get("License-Expression")
    if expression:
        return expression
    field = (md.get("License") or "").strip()
    if is_spdx(field):
        return field
    classifiers = [
        c.split(" :: ")[-1]
        for c in (md.get_all("Classifier") or [])
        if c.startswith("License ::")
    ]
    return "; ".join(classifiers) or "UNKNOWN"


print("name\tversion\tlicense\tsource")
for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
    md = dist.metadata
    name, version = md["Name"], md["Version"]
    print(f"{name}\t{version}\t{license_of(md)}\thttps://pypi.org/project/{name}/{version}/#files")
