"""Host tests for the checker source; tests/host.sh runs them."""
from __future__ import annotations

import contextlib
import io
import pathlib
import re
import tempfile
import unittest

from checker import NAME
from checker.__main__ import main

SUMMARY = re.compile(rf"{re.escape(NAME)}: (PASS|WARNING)( \([ -'*-~]+\))?\n\Z")


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(list(argv))
    return status, out.getvalue(), err.getvalue()


class CheckerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.config = self.workspace / "config.yaml"
        self.config.write_text("config:\n", encoding="utf-8")

    def invoke(self) -> tuple[int, str, str]:
        return run("--workspace", str(self.workspace), "--config", str(self.config), "--format", "text")

    def test_pass_final_line_matches_the_runner_grammar(self) -> None:
        (self.workspace / "README.md").write_text("x\n", encoding="utf-8")
        status, out, err = self.invoke()
        self.assertEqual((status, err), (0, ""))
        self.assertRegex(out.splitlines(keepends=True)[-1], SUMMARY)

    def test_finding_fails_with_exit_1(self) -> None:
        status, out, err = self.invoke()
        self.assertEqual((status, err), (1, ""))
        self.assertEqual(out, f"error: README.md: the repository has no README.md\n{NAME}: FAIL (1 finding)\n")

    def test_missing_config_is_a_tool_error(self) -> None:
        self.config.unlink()
        self.assertEqual(self.invoke(), (2, "", f"{NAME}: error: config_missing: config path is not a regular file\n"))

    def test_usage_error_has_one_grammar(self) -> None:
        self.assertEqual(run(), (2, "", f"{NAME}: error: invalid_usage: invalid command-line arguments\n"))
        self.assertEqual(run("--workspace", "/w", "--config", "/c", "--format", "patch")[0], 2)


if __name__ == "__main__":
    unittest.main()
