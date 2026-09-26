# workflow-container-template

The golden template for the organization's workflow containers. A repository generated from it is a
complete container on its first commit: it builds a two-architecture image, signs it, attaches an SBOM
and SLSA provenance, verifies all of it anonymously before any tag is promoted, and checks itself
against this template and the organization's control plane. Its author writes only the checker.

## Worked example: `workflow-sample`

A container's name is its repository's name without `workflow-`. Here it is `sample`.

1. Create `nwarila-platform/workflow-sample` from this template.
2. Replace the placeholder name. It appears in three files, and CI fails until `check.yaml` names the
   repository:

   ```sh
   sed -i 's/container-template/sample/g' \
     .github/workflows/check.yaml .pre-commit-hooks.yaml checker/__init__.py
   ```

3. Pin the template in the drift lock. The lock names the template commit the repository was created
   from, which the template cannot carry itself:

   ```sh
   printf 'nwarila-platform/workflow-container-template %s\n' "$TEMPLATE_COMMIT" \
     >> .github/.config/template-drift.lock
   ```

4. Write the check in `checker/__main__.py` and its tests under `tests/`, then open a pull request.
   CI runs the host tests and the image tests on `amd64` and `arm64`.
5. Release: set `VERSION`, merge, and push a signed annotated tag `v<VERSION>` on that commit.

A consumer then calls the container from `.github/workflows/workflow-containers.yaml`. The check
appears as `sample / v0.1.0 / check`:

```yaml
jobs:
  sample:
    uses: nwarila-platform/workflow-sample/.github/workflows/check.yaml@<40-hex> # v0.1.0
    permissions: {contents: read, security-events: write}
    with:
      version: 0.1.0
      digest: sha256:<64-hex>
```

To run the same check before a push, the consumer adds the hook and a pin file:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/nwarila-platform/workflow-sample
    rev: <40-hex> # v0.1.0
    hooks: [{id: sample}]
```

```yaml
# .github/.config/sample.yaml
# renovate: datasource=docker depName=ghcr.io/nwarila-platform/workflow-sample
version: 0.1.0
digest: sha256:<64-hex>
fail_on: error
```

## Container contract

The runner and the local launcher both call the image as
`--workspace /workspace --config /workspace/.github/.config/<name>.yaml --format text`, with no
network, a read-only root, every capability dropped, no new privileges and the workspace mounted
read-only. The image runs as `65532:65532`.

| Exit | Meaning | Output |
|---|---|---|
| 0 | pass or warning | findings, then `<name>: PASS` or `<name>: WARNING`, optionally followed by ` (<printable ASCII>)`, ending in one line feed |
| 1 | policy failure | findings as `error: <path>: <message>`, then a summary line |
| 2 | tool error | stderr only: `<name>: error: <code>: <message>` |

The runner checks the exit-0 summary line itself as a trust boundary (ruling A21). A container that
needs writable `/tmp` and `/home/nonroot` declares `LABEL org.nwarila.workflow.scratch="true"` in its
`Containerfile` (ruling A35); nothing it needs at runtime may live under those paths.

## What a repository carries

`template-drift.json` declares how this template governs a generated repository:

| Mode | Files |
|---|---|
| identical to this template | `.editorconfig`, `.gitattributes`, `.github/renovate.json5`, `.github/workflows/ci.yaml`, `.github/workflows/publish.yaml`, `SECURITY.md`, `tools/install-crane.sh`, `tools/workflow-container.sh` |
| present, content the container's own | `.dockerignore`, `.gitignore`, `.github/.config/template-drift.yaml` and `.lock`, `.github/CODEOWNERS`, `.github/workflows/check.yaml`, `.github/workflows/workflow-containers.yaml`, `.pre-commit-hooks.yaml`, `Containerfile`, `LICENSE`, `README.md`, `VERSION`, `tests/host.sh`, `tests/image.sh` |
| absent | `.github/dependabot.yml`, `THIRD_PARTY_NOTICES.md` |

The six records under `docs/decision-records/org/` are governed byte for byte by
`nwarila-platform/.github`. `workflow-containers.yaml` runs the template-drift check against both
templates on every pull request, reading the template list and lock under `.github/.config/`.

`ci.yaml` and `publish.yaml` never name the container: the image, signing identity and provenance
source derive from the repository name. Each container's own tests are two scripts, which both
workflows call:

- `tests/host.sh` runs the checker's tests on the host.
- `tests/image.sh <image> <platform>` runs the built or published image and compares its output
  byte for byte.

## Release

`publish.yaml` runs on a signed annotated `v*` tag whose commit and name match `VERSION`. It pushes an
unaliased two-architecture index by digest, requires one SPDX SBOM per child, signs the index and both
children keylessly, adds SLSA level 3 provenance, then verifies signatures, provenance and
`tests/image.sh` anonymously on each child. Only then does it tag the digest `<version>` and
`sha-<commit>`. There is no `latest` tag. The signing identity is
`https://github.com/nwarila-platform/workflow-<name>/.github/workflows/publish.yaml@refs/tags/v<version>`.

## Local launcher

`tools/workflow-container.sh <name> check|sync` runs a container the way the runner does, from the
digest pinned in the consumer's `.github/.config/<name>.yaml`. It needs Podman or Docker, Python 3,
Git and cosign, and it refuses to run an image whose signature it cannot verify. Network and runtime
operations are bounded by `timeout` or `gtimeout` when either is installed; without both, as on stock
macOS, they run unbounded. `sync` applies a patch only for a container whose wrapper sets
`patch: true`.
