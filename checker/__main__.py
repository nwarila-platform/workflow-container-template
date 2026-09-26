"""Command-line entry point implementing the organization's config-mode container contract.

The runner calls ``--workspace /workspace --config /workspace/.github/.config/<name>.yaml --format text``.
Exit 0 is PASS or WARNING, 1 is a policy failure, and 2 is a tool error. On exit 0 the final stdout line
must match ``<name>: (PASS|WARNING)( \\(<printable ASCII>\\))?`` and end with one line feed (ruling A21);
the runner enforces that grammar independently. A tool error writes one line to stderr and nothing to
stdout. Replace ``check`` with the container's own check; keep the rest.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import NAME


class ToolError(Exception):
    """A bounded, user-visible exit-2 condition."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would print its own usage text and exit 2
        raise ToolError("invalid_usage", "invalid command-line arguments")


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = _Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--format", choices=("text",), default="text")
    return parser.parse_args(argv)


def check(workspace: str, config: str) -> list[tuple[str, str]]:
    """Return (path, message) findings. The example requires a README.md in the workspace."""
    if not os.path.isfile(config):
        raise ToolError("config_missing", "config path is not a regular file")
    if not os.path.isfile(os.path.join(workspace, "README.md")):
        return [("README.md", "the repository has no README.md")]
    return []


def _count(findings: list[tuple[str, str]]) -> str:
    return f"{len(findings)} finding{'' if len(findings) == 1 else 's'}"


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _arguments(argv)
        findings = check(arguments.workspace, arguments.config)
    except ToolError as error:
        sys.stderr.write(f"{NAME}: error: {error.code}: {error.message}\n")
        return 2
    except Exception:  # noqa: BLE001 - every unexpected fault is a tool error, never a result
        sys.stderr.write(f"{NAME}: error: internal_error: unexpected internal error\n")
        return 2
    lines = [f"error: {path}: {message}\n" for path, message in findings]
    status = "FAIL" if findings else "PASS"
    lines.append(f"{NAME}: {status} ({_count(findings)})\n")
    sys.stdout.write("".join(lines))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
