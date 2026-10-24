# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

lefthook-qa-gates — a container image carrying the **base gate fleet** for lefthook's `pre-commit` and
`commit-msg` hooks, plus the **contract** that names those gates (`lefthook/base.yml`), consumed by other
repositories through lefthook's `remotes:`. Not tied to tpo42: the base for C++, Yocto, Kubernetes, Perl and
documentation repositories alike. Languages and domains get images of their own beside this one —
**orthogonal, not `FROM` it** (clang-tidy needs the SDK the code is built with).

The image is to lefthook what `tpo42-asciidoc-container` is to AsciiDoc: one tag, one set of tool versions,
dispatched into through a template.

## Layout

- `container/` — the build context, laid out as the prefix it installs into (`/usr/local`):
  - `Containerfile`, `requirements.txt` — the fleet and its pins.
  - `bin/` — job wrappers, installed to `/usr/local/bin`. POSIX `sh`, `set -eu`.
  - `share/lefthook-qa-gates/` — `lefthook-invariants.schema.json`, `catalog.md` (this image's catalog cluster),
    `seeds/` (starting configs a consumer copies and then owns), `third-party/README.md` (the `*.tsv` lists
    beside it are written at build time, from the rpm database, the Python metadata and the binary pins).
  - `build/` — build-time only, mounted by the Containerfile and not installed.
  - Wrappers find their data as `$(dirname "$0")/../share/lefthook-qa-gates/` — true in a checkout and in the
    image. Keep that layout.
- `lefthook/base.yml` — the contract. Public API: job names are what consumers override, so renaming one is a
  breaking change.
- `lefthook.yml` — this repository's own hooks: `extends:` the contract, then adds jobs. A same-named job can
  only add keys the contract leaves unset (`skip`, `exclude`); where both set one, the contract wins.
- `bin/` (root) — host-side tools that are *not* in the image: `service-cold` asks the host's runtime whether a
  service is warm, which no container can answer. Canonical copy; consumers vendor it.
- `.claude/` — the plugin root: `.claude-plugin/plugin.json` and `skills/lefthook-base-contract/`, the
  consumer-facing skill, beside the image it describes. A subdirectory rather than the repository root, so that
  installing the plugin copies the skill and not the image's build context. **Everything committed under
  `.claude/` ships to every installer** — a `settings.json`, `agents/` or `hooks/` here would land in their
  sessions too; machine-local settings stay in the git-ignored `settings.local.json`. `plugin.json` is
  authoritative for the plugin (skills, license).
- `.claude-plugin/marketplace.json` — makes the repository its own marketplace and points at `./.claude`,
  listing nothing a second time. No `version` here or in `plugin.json`, deliberately: the git tag is the version,
  and a second copy would drift. Check with `claude plugin validate .` and `claude plugin validate .claude` —
  remaining warnings (version, icon) are known and accepted.

## Build & Run

```bash
docker compose build gates     # the image from this checkout, tagged rehsack/lefthook-qa-gates:local
docker compose up -d gates     # warm for the session
lefthook run pre-commit --all-files
```

Machine-local and git-ignored: `.env` (`GIT_USER_NAME`, `GIT_USER_EMAIL`, `USER_UID`, `USER_GID`) and
`lefthook-local.yml` (`templates: { gates: docker compose exec -T gates }`). README.md has the commands. A
change to a wrapper, the schema or the Containerfile reaches the hooks only after a rebuild.

CI is `.github/workflows/ci.yml`: per architecture it builds the image and runs
`lefthook run pre-commit --all-files` *inside* it with `{gates}` empty — the CI case the contract promises — plus
`range-gates` against the target branch. Every push publishes the checked digest (SBOM, provenance) — main as
`latest`, a branch under its name, every push as `sha-…` — because the image is a gate and has to exist under a
name before the merge that needs it; that also runs every publishing step before the merge does. Pull requests
from forks build without publishing, through `ci-fork.yml` — the only `pull_request` trigger, so a pull request
from a branch here shows one skipped entry, not every job twice. Image tag and contract `ref` pair up: `latest` ↔ `ref: main`,
`X.Y.Z`/`X.Y` ↔ `ref: vX.Y.Z`. `ghcr-cleanup.yml` and `.github/scripts/ghcr-*.sh` are tpo42-asciidoc-container's,
unchanged but for one package instead of two — keep it that way, it is a copy #16-style extraction will want to
find identical.

Releases follow tpo42-asciidoc-container's convention: cut on every push to `main`, from the Conventional Commits
since the last tag, as a lightweight tag created by `gh release create` — never by hand, never annotated.
`.github/scripts/next-version` computes it. It is that repository's `release.yml` logic with the two defects of
tpo42/tpo42-asciidoc-container#16 fixed — a malformed previous tag stops the release, and `BREAKING CHANGE:`
counts only as a footer — and therefore the candidate for the single place #16 asks for. Unlike there, nothing is
rebuilt for a release: the publish job tags the digests the same run already checked, so the tag (created with
`GITHUB_TOKEN`) needs to start no workflow. Every branch run checks that the tag its merge would cut is still
free, so a collision fails the pull request rather than main. Work happens on `feature/…` branches and reaches
`main` by pull request; the subject of each commit decides the release.

Not yet: required status checks on `main` (they have to have run there before they can be selected) and a merge
queue with `merge_group` — tpo42-asciidoc-container has the queue in its ruleset, but no workflow listens to
`merge_group`, so it gates on nothing either. Both repositories together.

To reproduce the CI case locally, run the image against a copy of the checkout without `lefthook-local.yml` — the
local one would otherwise be read inside the container.

No tests beyond the hooks yet.

## Key Conventions

- **Executable scripts** in `container/bin/` and `bin/` are POSIX `sh` with `set -eu` — they run in the image
  and, vendored, on any host. No bash-isms.
- **lefthook invariants**, enforced by `check-lefthook` against the schema: one command with arguments per job
  (no multi-line block, `$( … )`, pipe, `&&`, `;`, negation — evilmartians/lefthook#1167); no container name in
  any `lefthook*.yml` that is committed. Logic goes into a wrapper.
- **Gates are pinned upstream releases**, one sha256 per architecture, read from the project's checksum file
  where one exists and marked self-computed where not. The distribution supplies only the base (shells, runtimes,
  git, jq, libxml2). Bump version and digests together; verify asset names, they drift.
- **Fixers + `fail_on_changes: "always"`**, never `stage_fixed`: a correction fails the commit and stays
  unstaged for review.
- **Severity lives in the tool's config** (`.yamllint` `level: error`), not in hook flags.
- **No network at check time** (`taplo lint --no-schema`): a verdict that depends on the network is not a gate.
- **Catalog clusters**: `catalog.md` covers exactly what this image carries. A row moves here when its tool
  enters the image; rows for other clusters stay with `/qa-ready` until their image exists.
- **Licensing follows REUSE 3.3**, checked by the `reuse` and `reuse-repo` jobs. Code is Apache-2.0, seeds 0BSD,
  prose CC-BY-SA-4.0. A new file with comment syntax opens with
  `SPDX-FileCopyrightText: 2026 Jens Rehsack <sno@netbsd.org>` and `SPDX-License-Identifier:` (after the
  shebang in a script); JSON, Markdown and seeds are covered by kind in `REUSE.toml` — do not add headers there. Apache-2.0 §4(b): a file changed from somebody
  else's work says so.
- **Commits** use conventional commit style, always `--signoff`. Docs are English.

## Open questions

- **Third-party licenses in the published image** — answered for v0.1.0 (2026-10-23): the build writes
  `share/lefthook-qa-gates/third-party/{rpm,python,binaries}.tsv` (rpm database, package metadata, the
  Containerfile's pins) with a README on where each source is; CI attaches an SBOM. Source is **referenced, not
  mirrored** — deliberately no infrastructure for it; the README promises to provide a source that went missing,
  on request. Fedora's sources are Fedora's to keep; a future Yocto base could archive its own (`archiver`).
  A binary bump means checking the license stated in `binaries.tsv`. `tpo42/adoc` has the same question.
- **Relicensing tpo42-asciidoc-container** to the same scheme — tpo42/tpo42-asciidoc-container#21, scheduled
  after this image's first release, together with moving its hooks onto it (decided 2026-10-23). Versions
  published until then stay available under CC-BY-SA-4.0. Its skill is prose and stays CC-BY-SA-4.0, so the
  `personal-skills` copy needs no change.
- **SPEC** — `adr/`, `req/` not started. ADR-001 should state why this image exists at all: it reverses the
  "no shared third image until both requirement sets are known" note in tpo42-asciidoc-container's
  `container/mini.Containerfile` — there are three requirement sets now.
- **Merge semantics, measured on lefthook 2.2.2** (scratch repos, 2026-10-23): `remotes:` and `extends:`
  behave identically. Same-named jobs merge; where both set a key the remote/extended config wins; keys only
  the consumer sets (`skip`, `exclude`) are added. `{gates}` from `lefthook-local.yml` expands inside remote
  jobs. `lefthook validate` rejects run-less override jobs (validates the main file alone) while `run`/`dump`
  merge them fine — open whether to report upstream or to change the override pattern.
- **zsh scripts with a shebang** are `text/x-shellscript` and reach the `shellcheck` job, which rejects the
  dialect. The base `zsh-syntax` job only sees `*.zsh`.
- **CSV** — part of the base cluster, no tool chosen.
- **pre-push** — the contract has none yet; `range-gates` against the upstream branch is the candidate.
- **macOS host floor** — `bin/service-cold` and vendored copies of the wrappers run on hosts, under macOS'
  `/bin/sh` and BSD userland. Nothing executes them there yet (tpo42-asciidoc-container's `host-gates` job is the
  model).
- **Image manifest** — `/qa-ready` should be able to ask an image what it carries instead of parsing
  `catalog.md`; format open.

## What exists elsewhere (to be consolidated)

Material this project grew out of. Read it, take what holds, rewrite rather than copy — and record what moved.

- **tpo42-asciidoc-container** (`~/data/Projects/OSS/container/tpo42-asciidoc-container`)
  - `container/mini.Containerfile`, `container/mini.requirements.txt`, `qa-compose.yml` — adc-mini-qa, the
    direct predecessor of `container/`. Keeps rubocop (Ruby domain, see its `issues/`) and its own jobs until it
    consumes this image.
  - `lefthook.yml` — the most commented lefthook config; source of most job rationale in `lefthook/base.yml`.
  - `.coderabbit.yml`, `.gitlint`, `.hadolint.yaml`, `.dclintrc` — models for the ones here.
  - `adr/adr-010.adoc` (BATS owns the harness — test approach), `adr/adr-011.adoc` (CI fan-out),
    `adr/adr-008.adoc` (variant images), `req/uc-007.adoc` (publish the image, hold the wrappers to their gates).
- **personal-skills** (`~/data/Projects/OSS/personal-skills`)
  - `skills/qa-ready/` — the puppeteer. `resources/*` and `assets/*` moved here (`container/bin`,
    `container/share/lefthook-qa-gates/seeds`); the base rows of `references/catalog.md` moved to `catalog.md`.
    Still to be trimmed there.
  - `skills/qa-ready/resources/lint-asciidoc` and `references/technical-debt.md` (TD-QAR-1) — AsciiDoc domain,
    not base; they go to the AsciiDoc image.
- **tpo42-templates** (`~/data/Projects/Architectures/tpo42-templates`)
  - `container/mini.Containerfile` (Debian, distro-first — the older sourcing line), `docker-compose.yml`
    service `tpo42-tpl-mini`. To become a consumer.
- **fedora-qa-barriers** (`~/data/devel/Delphin/infrastructure/docker/fedora-qa-barriers`) — a derivative of
  adc-mini-qa and `/qa-ready` in another context. Usable for **clean-room rewrites only**; its decisions
  (ADR-CT/QA-001…012 in `Docs/arc42-fedora-qa-barriers.adoc`) were taken for that context and do not bind here.
  `.claude/skills/qa-check-contract` and `upgrade-qa-check-contract` show the CI side of a contract.
