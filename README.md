# lefthook-qa-gates

The base gate fleet for [lefthook](https://lefthook.dev): one container image with the checks every repository
needs, whatever its language, and the lefthook contract that names them.

## The model: the file names tools, not places

lefthook orchestrates; it does not provision. So the split is: **the container provisions, lefthook
orchestrates.** `lefthook.yml` never names a container. It names tools behind a `{gates}` prefix, and where that
prefix points is a property of the machine:

| Where             | `{gates}`                                                | lefthook runs           |
| ----------------- | -------------------------------------------------------- | ----------------------- |
| developer machine | `docker compose exec -T gates` (in `lefthook-local.yml`) | on the host, beside git |
| CI                | empty                                                    | inside the image        |

Never both, never nested — no Docker socket, no container in a container.

Languages and domains — C++, Perl, Python, Ruby, AsciiDoc — are not added to this image. They are images of their
own beside it, each behind a template of its own (`{cpp}`, `{perl}`, …). Orthogonal rather than `FROM` this one:
clang-tidy has to match the SDK the code is built with, and a base image cannot know which one that is.

## What is in the image

Gates are pinned upstream releases, with one sha256 per architecture; the distribution (Fedora) supplies only the
base.

| Tool                 | Checks                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------ |
| editorconfig-checker | whitespace, EOL, final newline, charset — **fixer** (safe fixes only)                      |
| shellcheck, shfmt    | shell — shfmt is a **fixer**                                                               |
| `zsh -n`             | zsh syntax (shellcheck refuses the dialect)                                                |
| yamllint             | YAML                                                                                       |
| taplo                | TOML — lint (offline) and **fixer**                                                        |
| `jq`, `xmllint`      | JSON, XML well-formedness                                                                  |
| check-jsonschema     | GitHub workflows, dependabot, GitLab CI, JSON Schema metaschema, `lefthook.yml` invariants |
| actionlint           | GitHub workflow semantics                                                                  |
| hadolint             | Containerfile/Dockerfile                                                                   |
| dclint               | compose semantics — **fixer**                                                              |
| mdformat             | Markdown — **fixer**                                                                       |
| gitlint              | commit message (Conventional Commits)                                                      |
| gitleaks             | secrets in the staged change                                                               |
| lefthook             | for CI runners that run lefthook inside the image                                          |
| reuse                | copyright and license of every file (REUSE) — **opt-in**, not in the contract              |

Plus job wrappers in `/usr/local/bin` (`check-json`, `check-lefthook`, `shebang-exec-match`, `artifact-guard`,
`guard-branch`, `range-gates`) and, under `/usr/local/share/lefthook-qa-gates/`, the invariants schema, the
catalog cluster, the seed configs and `third-party/` — what the image bundles, under which license, and where its
source is.

**Fixers as a gate:** fixers write, and `fail_on_changes: "always"` fails the commit when they did — the
correction stays unstaged for review, deliberately not `stage_fixed`. For that, the container user's uid/gid must
match yours, or it cannot rewrite workspace files.

## Using it in a repository

```yaml
# lefthook.yml
remotes:
  - git_url: https://github.com/rehsack/lefthook-qa-gates
    ref: v0.1.0
    configs:
      - lefthook/base.yml
```

Switch a job off or narrow it by its name; add what only your repository knows — see
[`seeds/lefthook.example.yml`](container/share/lefthook-qa-gates/seeds/lefthook.example.yml). Copy
[`compose.yaml`](compose.yaml), drop `build:` and point `image:` at the release that matches `ref`.

Then, once per machine — both files are git-ignored, because they describe *this machine*:

```sh
# Who commits: uid/gid so the fixers may rewrite your files; name and mail because
# gitlint in the container sees no ~/.gitconfig.
printf 'GIT_USER_NAME=%s\nGIT_USER_EMAIL=%s\nUSER_UID=%s\nUSER_GID=%s\n' \
    "$(git config user.name)" "$(git config user.email)" "$(id -u)" "$(id -g)" > .env

# Where the tools come from.
printf 'templates:\n  gates: docker compose exec -T gates\n' > lefthook-local.yml

docker compose up -d gates
lefthook install
```

A warm service costs one container start per session instead of one per job.

### In CI

lefthook runs inside the image, with `{gates}` empty — no `lefthook-local.yml` on the runner. Run it as the
runner's identity, so the fixers write files the job owns, and give git an identity for gitlint:

```sh
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/workspace" \
    -e GIT_CONFIG_COUNT=2 \
    -e GIT_CONFIG_KEY_0=user.name -e GIT_CONFIG_VALUE_0=ci \
    -e GIT_CONFIG_KEY_1=user.email -e GIT_CONFIG_VALUE_1=ci@example.org \
    ghcr.io/rehsack/lefthook-qa-gates:0.1.0 \
    lefthook run pre-commit --all-files --no-auto-install
```

For a merge or pull request, `range-gates <base>` adds what only a range can answer: a secret in any commit of
`<base>..HEAD` — also one removed again later — and every commit message, through the repository's own
`commit-msg` hook. Pass the tip of the target branch as `<base>`.

## Working on this repository

```sh
docker compose build gates
docker compose up -d gates
lefthook run pre-commit --all-files
```

The repository consumes its own contract through `extends:`, so a change to the contract is gated by the changed
contract. Wrapper, schema and Containerfile changes reach the hooks after a rebuild.

[`ci.yml`](.github/workflows/ci.yml) builds the image per architecture and lets it check this repository from
inside, exactly as above. From `main` it publishes what passed as `main`, with an SBOM and provenance attached.

Releases are cut by merging, not by hand. On every push to `main`,
[`next-version`](.github/scripts/next-version) reads the Conventional Commits since the last release — `type!:` or
a `BREAKING CHANGE:` footer is major, `feat` minor, `fix` patch, anything else no release. When there is one, the
checked image is also tagged `X.Y.Z`, `X.Y` and `latest`, and the GitHub release creates the tag `vX.Y.Z`. A
pull request's checks say in their summary which release its merge would cut.

## Project structure

```text
.
├── .github/                         ci.yml (build, self-check, publish, release), next-version, dependabot.yml
├── LICENSES/                        license texts (REUSE)
├── REUSE.toml                       copyright and license for files without a header
├── bin/service-cold                 host-side: is a compose service cold? (for lefthook `skip:`)
├── compose.yaml                     the fleet as a warm service
├── container/                       build context, laid out as the /usr/local prefix
│   ├── Containerfile
│   ├── requirements.txt
│   ├── bin/                         job wrappers
│   ├── build/                       build-time only, not installed
│   └── share/lefthook-qa-gates/     invariants schema, catalog, seeds, third-party/ (lists written at build)
├── lefthook/base.yml                the contract
├── lefthook.yml                     this repository's own hooks
├── skills/lefthook-base-contract/   Claude Code skill for consumers
└── .claude-plugin/plugin.json
```

Dotfiles at the root (`.editorconfig`, `.yamllint`, `.shellcheckrc`, `.hadolint.yaml`, `.dclintrc`, `.gitlint`,
`.gitleaks.toml`) configure the gates for this repository; `.coderabbit.yml` configures review.

## License

The repository follows the [REUSE specification](https://reuse.software): every file states its copyright and
license, in a header or in [`REUSE.toml`](REUSE.toml), and the texts are in [`LICENSES/`](LICENSES/).

- **Code** — scripts, the Containerfile, the contract, configuration: [Apache-2.0](LICENSES/Apache-2.0.txt).
- **Seeds** — the starting configs under `container/share/lefthook-qa-gates/seeds/`: [0BSD](LICENSES/0BSD.txt).
  Copy them, change them, keep no notice.
- **Prose** — README, catalog, skill, documentation: [CC-BY-SA-4.0](LICENSES/CC-BY-SA-4.0.txt).

The published image bundles third-party tools under their own licenses.
