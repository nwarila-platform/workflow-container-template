#!/usr/bin/env bash
# The container's image tests. ci.yaml runs them on each architecture's build and publish.yaml on each
# published child digest before promotion. Usage: tests/image.sh <image> <platform>
set -euo pipefail
image=$1
platform=$2
runtime=${CONTAINER_RUNTIME:-docker}
cd "$(dirname "$0")/.."
name=$(sed -n 's/^      name: \([a-z0-9-]*\)$/\1/p' .github/workflows/check.yaml)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
fail() { printf 'image test failed: %s (platform %s)\n' "$1" "$platform" >&2; cat "$work/err" >&2 || true; exit 1; }
run() {
  status=0
  "$runtime" run --quiet --rm --platform "$platform" --network=none --read-only --cap-drop=ALL \
    --security-opt=no-new-privileges "$@" >"$work/out" 2>"$work/err" || status=$?
}
mkdir -p "$work/pass" "$work/fail"
printf 'config:\n' | tee "$work/pass/config.yaml" >"$work/fail/config.yaml"
printf 'example\n' >"$work/pass/README.md"
chmod -R a+rX "$work"

run -v "$work/pass:/workspace:ro" "$image" --workspace /workspace --config /workspace/config.yaml --format text
[[ $status -eq 0 && ! -s "$work/err" ]] || fail "pass: status $status"
printf '%s: PASS (0 findings)\n' "$name" | cmp -s - "$work/out" || fail 'pass: summary line'

run -v "$work/fail:/workspace:ro" "$image" --workspace /workspace --config /workspace/config.yaml --format text
[[ $status -eq 1 && ! -s "$work/err" ]] || fail "finding: status $status"
printf 'error: README.md: the repository has no README.md\n%s: FAIL (1 finding)\n' "$name" \
  | cmp -s - "$work/out" || fail 'finding: report'

run "$image"
[[ $status -eq 2 && ! -s "$work/out" ]] || fail "usage: status $status"
printf '%s: error: invalid_usage: invalid command-line arguments\n' "$name" | cmp -s - "$work/err" \
  || fail 'usage: error line'
printf 'image tests passed: %s on %s\n' "$image" "$platform"
