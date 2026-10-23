---
name: lefthook-base-contract
description: Wire a repository's lefthook pre-commit and commit-msg hooks onto the lefthook-qa-gates base image — remotes pin, {gates} template, warm compose service, CI case — and extend or override it without forking the contract. Use when onboarding a repo onto the base gates, bumping its contract release, or adding a language image beside it.
user-invocable: true
---

# /lefthook-base-contract — the base gates, consumed

The contract is `lefthook/base.yml` in `rehsack/lefthook-qa-gates`. The image of the same release carries every
tool it names. This skill wires a repository onto both. It does **not** decide which checks a repository is
missing — that is `/qa-ready`, which reads the catalog clusters (this image's is
`/usr/local/share/lefthook-qa-gates/catalog.md`).

## The model

lefthook orchestrates, the container provisions. `lefthook.yml` names tools behind a `{gates}` prefix and never a
container; where the prefix points is a property of the machine:

| Case                                                      | `{gates}`                                              | lefthook runs           |
| --------------------------------------------------------- | ------------------------------------------------------ | ----------------------- |
| developer machine                                         | `docker compose exec -T gates` in `lefthook-local.yml` | on the host, beside git |
| CI (GitLab, Jenkins, any runner that can start the image) | empty                                                  | inside the image        |

Never both, never nested.

## Onboarding a repository

1. **Take the contract by release** — start from `seeds/lefthook.example.yml` in the image
   (`/usr/local/share/lefthook-qa-gates/seeds/`). `remotes:` with a `ref` that is a release tag, never a branch:
   an unpinned remote changes the gate under a commit that changed nothing.
2. **Name the image of the same release** in the repository's compose file — copy `compose.yaml` from this
   repository, drop `build:`, point `image:` at the published tag.
3. **Machine-local files**, both git-ignored: `.env` with `GIT_USER_NAME`, `GIT_USER_EMAIL`, `USER_UID`,
   `USER_GID`; `lefthook-local.yml` with the `gates:` template. The README of `lefthook-qa-gates` has the commands.
4. **Seed what the tools read**: `.editorconfig`, `.yamllint`, `.gitlint`, `.shellcheckrc`, `.gitleaks.toml` from
   `seeds/`. They are starting points; the repository tunes its copy and owns it from then on.
5. `docker compose up -d gates`, `lefthook install`, then `lefthook run pre-commit --all-files` once — the first
   run on an existing tree is where the backlog shows.

## Adjusting without forking

- **Switch a job off** by its name: `- name: mdformat` / `skip: true`. Job names are contract API.
- **Narrow a job**: same name, add `exclude:`.
- **Not rewritable**: jobs merge by name, and where both set a key the contract wins (lefthook 2.2.2,
  `remotes:` and `extends:` alike). A different `glob` or `run` is a new job under its own name — skip the
  contract's one if it would now run twice. Check the result with `lefthook dump`.
- `lefthook validate` rejects the run-less override jobs above (it checks the main file alone);
  `lefthook run` merges them correctly. Do not "fix" that by adding a `run:` — it would be ignored anyway.
- **Add policy** the contract leaves open: `guard-branch` with the repository's allowlist
  (`guard-branch main feature/ fix/` — a trailing `/` is a prefix, no globs).
- **Opt into REUSE** where the repository is (or becomes) REUSE-compliant: the two commented `reuse` jobs in
  the seed. Not contract, because a repository that has not adopted REUSE cannot pass them.
- **Add a language or domain**: a template of its own pointing at its own image (`{cpp}`, `{perl}`, `{adoc}`).
  Not `FROM` this image — clang-tidy needs the SDK the code is built with, and no base image knows which one that
  is. Each such image ships its own contract and catalog cluster.

## Invariants (checked by `check-lefthook`)

One command with arguments per job — no multi-line block, `$( … )`, pipe, `&&`, `;` or negation, in `run:` and
`skip:` (evilmartians/lefthook#1167). No container name in `lefthook.yml`. Logic goes into a wrapper script, which
then sits under shellcheck and shfmt like every other script.

## Bumping

Move `ref` in `remotes:` and the image tag together, in one commit, and run `lefthook run pre-commit --all-files`:
a newer gate may report what the older one did not, and that is the point of pinning it. They come in pairs:
`ref: vX.Y.Z` with image `X.Y.Z` (or `X.Y` to take its fixes), `ref: main` with image `latest`. A mixed pair runs
a contract against tools it was not written for.

## In CI

lefthook runs inside the image with `{gates}` empty — no `lefthook-local.yml` on the runner. Run the container as
the runner's uid/gid (`-u`), give git an identity through `GIT_CONFIG_*`, and call
`lefthook run pre-commit --all-files --no-auto-install`. For a merge or pull request add `range-gates <base>`, with
the tip of the target branch as `<base>`: secrets in every commit of the range, and every message through the
repository's own `commit-msg` hook. The README has the full invocation.

## Not here

- CI pipeline wiring beyond that (stages, publishing, runner setup) — the project's own CI contract.
- Which filetypes need a check — `/qa-ready`.
