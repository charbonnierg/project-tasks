import tempfile
import unittest
from pathlib import Path

from project_tasks.cli import run
from project_tasks.output import make_capture_output

from .test_cli_parser import HELP, USAGE


class TestCLIRun(unittest.TestCase):
    def test_file_does_not_exist(self) -> None:
        stdout, stderr, output = make_capture_output()
        code = run(output, ["task1", "-f", "does-not-exist.toml"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "task: error: pyproject file not found: does-not-exist.toml\n",
        )

    def test_list(self) -> None:
        stdout, stderr, output = make_capture_output()
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject_file = Path(tmpdir) / "pyproject.toml"
            pyproject_file.write_text(
                "\n".join(
                    [
                        "[tool.project-tasks.tasks]",
                        "task1 = \"python -c 'import sys; sys.exit(0)'\"",
                        "task2 = \"python -c 'import sys; sys.exit(1)'\"",
                    ]
                )
            )
            code = run(output, ["--list", "-f", pyproject_file.as_posix()])
        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue(), "task1\ntask2\n")

    def test_dry_run(self) -> None:
        stdout, stderr, output = make_capture_output()
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject_file = Path(tmpdir) / "pyproject.toml"
            pyproject_file.write_text(
                "\n".join(
                    [
                        "[tool.project-tasks.tasks]",
                        "task1 = \"python -c 'import sys; sys.exit(0)'\"",
                        "task2 = \"python -c 'import sys; sys.exit(1)'\"",
                    ]
                )
            )
            code = run(output, ["--dry-run", "task1", "-f", pyproject_file.as_posix()])
        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue(), "python -c 'import sys; sys.exit(0)'\n")

    def test_help(self) -> None:
        stdout, stderr, output = make_capture_output()
        code = run(output, ["--help"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), HELP + "\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_invalid_arg(self) -> None:
        stdout, stderr, output = make_capture_output()
        code = run(output, ["--invalid"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            f"{USAGE}\ntask: error: unrecognized arguments: --invalid\n",
        )

    def test_no_task(self) -> None:
        stdout, stderr, output = make_capture_output()
        code = run(output, [])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            f"{USAGE}\ntask: error: at least one task name is required\n",
        )

    def test_invalid_config(self) -> None:
        stdout, stderr, output = make_capture_output()
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject_file = Path(tmpdir) / "pyproject.toml"
            pyproject_file.write_text(
                "\n".join(
                    [
                        "[tool.project-tasks.tasks]",
                        "task1 = ",
                    ]
                )
            )
            code = run(output, ["task2", "-f", pyproject_file.as_posix()])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            f"task: error: {pyproject_file.as_posix()}:2:9: invalid value (at end of document)\n",
        )
