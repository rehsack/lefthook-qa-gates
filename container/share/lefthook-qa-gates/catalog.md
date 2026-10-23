# Catalog cluster: base

The part of the lint/format catalog this image answers for — the filetypes every repository carries, whatever
its language. It ships in the image at `/usr/local/share/lefthook-qa-gates/catalog.md`, beside the tools it
describes, so the statement "this filetype is covered by that tool" and the tool itself move in one release.

Other clusters (C++, Perl, Python, Ruby, AsciiDoc, …) live with the image that answers for them. The audit across
all clusters — which filetypes does a repository carry, which cluster covers each — is `/qa-ready`'s, which
reads this file rather than restating it. No version pins here; those are in the Containerfile.

Moved from `/qa-ready`'s `references/catalog.md` (personal-skills).

## Sourcing preference (order)

**First ask what the tool is.** For a *dependency* the distro is right — it owns the integration, and taking its
build is the whole point of using a distro. For a **gate**, the version is part of what the gate *means*: a finding
class that exists upstream and not in the packaged release changes the verdict, not just the changelog. Measured
case: shellcheck 0.11 split `SC2317` into `SC2317` (unreachable body) and `SC2329` (never-invoked function). A
suppression written against one release is wrong in the other, and neither release is "the" answer — the repo has
to pick one and say so.

So, for gates:

1. **Upstream release, pinned** — with the project's published checksum verified, one digest per architecture.
   The version is a stated decision rather than a property of whatever base image was picked.
2. **Distro package** — where the distro tracks upstream closely enough that the difference cannot produce a
   different verdict, or where no upstream binary exists.
3. **pip/npm** — where neither of the above exists, with the same line pinning (`~= 1.38`).
4. **Never**: tools that pull/build a toolchain at install time on the target. A compiler in a builder stage that
   gets discarded is fine; a compiler in the delivered image is not.

Verify against the *project's* published checksum where there is one. A self-computed digest only proves the file
has not changed since you fetched it — still worth writing down, but say which kind it is.

**One lane may float deliberately.** A developer's brew-installed shellcheck running ahead of the pinned container
one is an *early-warning* lane, not a second opinion — useful precisely because it reports what the next bump will
report. That works only while the binding verdict is stated to come from the pinned lane; otherwise it is two gates
disagreeing with nothing to break the tie.

## Bucket legend

- **base** — this image: mandatory, non-build, self-contained, fast (target < 1 s warm), locally in the hook and
  in CI. Called *mini* in the repositories this image grew out of.
- **domain** — needs the domain toolchain (same version as the build → version integrity); dispatched into its
  own container or environment through a template of its own, not added here.
- **later** — on the radar, not wired yet.
- **security** — misconfig scan (trivy `config`, kics): CI-mandatory, locally optional, blows the local budget.

"IaC" is not one bucket. The recipes nearly every repository carries — a Containerfile, a compose file, a CI
definition — are base: they are linted like any other source, fast and offline (hadolint, dclint, actionlint,
the CI schemas). What is *not* base is the scan that reasons about a deployment — misconfigurations across a
tree, policy, cloud provider rules — and the domain IaC languages (Kubernetes manifests, Helm, Terraform), which
belong to the cluster of the image that carries their toolchain.

## Hygiene checks: framework-free, composed

Composed from single tools instead of a framework bundle (pre-commit-hooks & co.). Left column: common check names
as known from other projects.

| Common check                                                          | Tool                                                                                                                   | Bucket |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------ |
| trailing-whitespace, end-of-file-fixer, mixed-line-ending             | **editorconfig-checker** `--fix` via `.editorconfig` — **one** SSOT for all languages                                  | base   |
| check-merge-conflict (+ whitespace errors)                            | `git diff --cached --check` (git-native)                                                                               | base   |
| detect-private-key                                                    | **gitleaks** (ruleset covers keys)                                                                                     | base   |
| check-added-large-files                                               | **dropped** — size is the wrong criterion                                                                              | —      |
| *(new)* binary/artifact guard                                         | `artifact-guard`: deny-list by **type/extension** (`.jar/.so/.a/.o/.elf/.bin` …); allowlist via `.gitattributes`       | base   |
| check-yaml                                                            | **yamllint** (deeper than check-yaml)                                                                                  | base   |
| check-json                                                            | `check-json` (`jq -e .` per file)                                                                                      | base   |
| check-xml                                                             | `xmllint --noout`                                                                                                      | base   |
| check-toml                                                            | **taplo**                                                                                                              | base   |
| check-executables-have-shebangs, check-shebang-scripts-are-executable | `shebang-exec-match` (mode from git)                                                                                   | base   |
| no-commit-to-branch                                                   | `guard-branch` with the repository's allowlist                                                                         | base   |
| *(range)* secrets anywhere in a series, every message of it           | `range-gates <base>` — gitleaks over `<base>..HEAD` plus the repository's `commit-msg` hook per commit; CI or pre-push | base   |

## Catalog by artifact

| Artifact                                         | Lint                                                                            | Format                                                    | Source                              | Bucket           | Follow-up                                                                                                                                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Editorconfig family** (whitespace/EOL/charset) | editorconfig-checker                                                            | editorconfig-checker `--fix` (safe fixes only, since 4.0) | binary                              | base             | github.com/editorconfig-checker/editorconfig-checker                                                                                                                                               |
| **Shell**                                        | shellcheck                                                                      | shfmt (`-i 4`, SSOT for shell style)                      | upstream binary (both); distro lags | base             | MIME selection also catches extensionless scripts                                                                                                                                                  |
| **zsh**                                          | `zsh -n` (interpreter parser — syntax gate, **not** a linter)                   | —                                                         | distro (zsh itself)                 | base             | shellcheck refuses the dialect: `-s zsh` → `Unknown shell: zsh`, upstream #809 open. z-shell/zsh-lint (Go, semantic) is the candidate for real linting — blocked on it publishing a release binary |
| **YAML**                                         | yamllint                                                                        | —                                                         | pip                                 | base             | adrienverge/yamllint                                                                                                                                                                               |
| **Compose**                                      | dclint (compose semantics, complementary to yamllint)                           | dclint `--fix`                                            | binary (standalone)                 | base             | zavoloklom/docker-compose-linter                                                                                                                                                                   |
| **JSON**                                         | `jq -e .`                                                                       | jq                                                        | distro                              | base             | —                                                                                                                                                                                                  |
| **JSON Schema**                                  | `check-jsonschema --check-metaschema`                                           | —                                                         | pip                                 | base             | for repositories that write schemas                                                                                                                                                                |
| **XML**                                          | `xmllint --noout`                                                               | —                                                         | distro (libxml2)                    | base             | —                                                                                                                                                                                                  |
| **TOML**                                         | taplo `lint --no-schema` (offline)                                              | taplo `fmt`                                               | binary                              | base             | tamasfe/taplo                                                                                                                                                                                      |
| **CSV**                                          | —                                                                               | —                                                         | —                                   | base (tool open) | a data format like JSON/YAML/TOML, so it belongs to this cluster; no tool chosen yet                                                                                                               |
| **Dockerfile/Containerfile**                     | hadolint                                                                        | —                                                         | binary                              | base             | hadolint/hadolint                                                                                                                                                                                  |
| **GitHub Actions**                               | check-jsonschema (`vendor.github-workflows`), actionlint                        | —                                                         | pip / binary                        | base             | python-jsonschema/check-jsonschema, rhysd/actionlint                                                                                                                                               |
| **GitLab CI**                                    | check-jsonschema (`vendor.gitlab-ci`, `--data-transform gitlab-ci`)             | —                                                         | pip                                 | base             | resolves `!reference`                                                                                                                                                                              |
| **Markdown**                                     | mdformat                                                                        | mdformat                                                  | pip                                 | base             | markdownlint is node — not in this image                                                                                                                                                           |
| **lefthook.yml**                                 | `check-lefthook` (invariants schema)                                            | —                                                         | this image                          | base             | see `lefthook-invariants.schema.json`                                                                                                                                                              |
| **Commit message**                               | gitlint                                                                         | —                                                         | pip                                 | base             | jorisroovers/gitlint — `.gitlint` = SSOT of valid types                                                                                                                                            |
| **Secrets**                                      | gitleaks                                                                        | —                                                         | binary                              | base             | no baseline upkeep                                                                                                                                                                                 |
| **Copyright/license (REUSE)**                    | `reuse lint-file` per change, `reuse lint` when `REUSE.toml`/`LICENSES/` change | —                                                         | pip                                 | base (opt-in)    | fsfe/reuse-tool. Opt-in, not contract: most repositories are not REUSE-compliant, and no glob says which are. `reuse download` is the one networked command — run once, never in a gate            |

## Tool lessons (universal, grows)

- **Know the gitleaks modes**: since 8.19 `git` scans history and `dir` a tree; `detect`/`protect` still work but
  are deprecated. `git` = whole history (findings carry a commit SHA, the file may be gone/renamed);
  `git --log-opts="<range>"` = a commit range (scans the patch of **every** commit in it);
  `git --pre-commit --staged` = staged changes only (**this** is the local hook mode); `dir` = working tree only
  (descends into submodules/gitignored trees → vendor false positives, allowlist those paths).
- **Drop detect-secrets**: the "audited `.secrets.baseline`" is more a running gag than an audit; constant false
  positives (e.g. `COMMIT_EDITMSG` during `rebase -i`) that you do *not* want to whitelist. Prefer gitleaks.
- **Formatter exit-code trap**: fixers write and exit `0`. Measured on mdformat 1.x: `mdformat FILE` rewrites and
  returns 0, only `--check` returns non-zero (and then writes nothing). A bare fixer in a hook therefore commits
  the *unformatted* index while the working tree holds the fix — the two drift apart silently.
- **lefthook's answer is `fail_on_changes`**, and it is a **hook-level** key, not per job: `always` | `ci` |
  `non-ci` | `never` (default). It compares git-tracked files before and after and fails with *"files were
  modified by a hook"*. Pair it with `fail_on_changes_diff: true` to print what changed. This is what lets
  formatters run in **fix mode** while the correction stays **unstaged** for review. Deliberately *not*
  `stage_fixed: true`, which puts the correction into the commit unseen. Unknown keys are silently ignored, so a
  typo like `no_stage_fixed` never announces itself.
- **`.editorconfig` = whitespace SSOT**, **not** style: `indent_style/size` belong in the formatter (shfmt,
  clang-format, …); a second place violates SPOT and drifts apart.
- **A gate every repository could use is not yet a gate every repository can pass.** A contract job must be
  satisfiable by any repository its glob selects. REUSE fails every repository that has not adopted it, and a
  glob cannot express "has adopted", so it ships as a tool plus an opt-in job — not as contract.
- **REUSE: in-file headers where the format allows, `REUSE.toml` by kind where it does not** — JSON (no
  comments), files whose first line belongs to someone else (a `SKILL.md` frontmatter), and seeds that should be
  copied clean. `reuse lint-file` checks headers and that their license texts exist; only `reuse lint` sees an
  unused license text or a broken `REUSE.toml`.
- **Severity belongs to the tool's config**, not to the hook: yamllint runs without `--strict`, and a rule that
  should fail says `level: error` in `.yamllint`. Two severity knobs overrule each other.
- **lefthook selects by MIME, not only by glob**: `file_types:` accepts real media types (lefthook 2.x vendors
  `gabriel-vasile/mimetype`), so `file_types: ["text/x-shellscript"]` catches extensionless scripts like `bin/foo`
  by their shebang — no glob has to enumerate them. Two caveats, both verified: a file *without* a shebang reports
  `text/plain` (a sourced `lib/foo.bash` is missed and needs a glob **plus** an explicit `shellcheck -s bash`,
  since no shebang states the dialect), and lefthook **ANDs** its filters — `glob` + `file_types` on one job is an
  intersection, so a union needs two jobs.
- **Gate host-side shell on macOS too**: scripts that run on the developer's machine rather than in a container
  meet Apple's `/bin/bash` **3.2.57** (GPLv2 freeze) and BSD userland. A Linux-only CI with bash 5 never sees
  `declare -A`, `${var^^}` or `${arr[@]}`-under-`set -u` breakage. A `macos-latest` job costs nothing on public
  repos — but it has no Docker, so it carries only the host-side gates.
- **dclint ↔ yamllint**: dclint checks compose *semantics* (key order, `name`), yamllint the YAML *syntax/style*.
  On flow sequences they may collide (dclint `--fix` adds bracket spaces, yamllint `brackets` forbids them) →
  yamllint wins (no inner spaces), apply dclint's key reordering by hand. Its `--fix` also drops a comment that
  hangs off a service key (zavoloklom/docker-compose-linter#314) — put such comments inside the service or above
  `services:`.
