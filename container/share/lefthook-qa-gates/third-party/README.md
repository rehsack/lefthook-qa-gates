# Bundled third-party software

This image carries software that is not part of lefthook-qa-gates and is licensed by its own authors — some of
it under copyleft licenses (GPL, LGPL, MPL). The lists beside this file name every component, its version and
its license, and say where its source is. They are written while the image is built, so they describe exactly
this image.

| List           | Covers                                       | Written from             | Source                                                                                                                                   |
| -------------- | -------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `rpm.tsv`      | the Fedora base and the packages added to it | the rpm database         | `source-rpm` names the Fedora source package: [src.fedoraproject.org](https://src.fedoraproject.org/), or `dnf download --source <name>` |
| `python.tsv`   | the Python gates and their dependencies      | each package's metadata  | pure-Python packages are installed as source; the files PyPI holds for that version (`source` column)                                    |
| `binaries.tsv` | the gates installed as release binaries      | the Containerfile's pins | the upstream release tag (`source` column)                                                                                               |

Licenses are SPDX expressions where the component states one. Some Python packages state theirs only as a trove
classifier ("BSD License"); the list then carries that text unchanged rather than a guess.

The source is referenced, not mirrored. If a referenced source is no longer available, open an issue at
<https://github.com/rehsack/lefthook-qa-gates/issues> and it will be provided.

lefthook-qa-gates' own files are licensed per file, following REUSE: the wrappers and the schema Apache-2.0, the
catalog and this text CC-BY-SA-4.0, the seeds 0BSD — see the repository's `REUSE.toml`.
