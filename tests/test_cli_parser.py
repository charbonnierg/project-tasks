import unittest

from project_tasks.cli import Exit, parse_args
from project_tasks.service import Request

USAGE = "usage: task [--help] [--list] [--file FILE] [--dry-run] [--var.<NAME> VALUE] [task_name ...]"
HELP = f"""{USAGE}

task: run a single or several tasks defined in pyproject.toml.

positional arguments:
  task_name        Task to run

options:
  --help, -h       Show help and exit
  --file, -f FILE  Pyproject file
  --list, -l       List available tasks
  --dry-run        Show task steps instead of executing them

optional key-value arguments:
  --var.<name>     Set variable with value
"""


class TestParseArgs(unittest.TestCase):
    def assertRaisesExit(
        self, args: list[str], expect_code: int, expect_msg: str
    ) -> None:
        with self.assertRaises(Exit) as raised:
            parse_args(args)
        self.assertEqual(raised.exception.return_code, expect_code)
        self.assertEqual(raised.exception.msg, expect_msg)

    def test_error_with_invalid_option(self) -> None:
        self.assertRaisesExit(
            ["--invalid"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: unrecognized arguments: --invalid",
        )

    def test_error_with_invalid_options(self) -> None:
        self.assertRaisesExit(
            ["--invalid", "test", "--other-invalid"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: unrecognized arguments: --invalid --other-invalid",
        )

    def test_parse_help(self) -> None:
        self.assertRaisesExit(
            ["--help"],
            expect_code=0,
            expect_msg=HELP,
        )

    def test_parse_help_short_option(self) -> None:
        self.assertRaisesExit(
            ["-h"],
            expect_code=0,
            expect_msg=HELP,
        )

    def test_parse_help_takes_precedence_with_valid_options(self) -> None:
        self.assertRaisesExit(
            ["--help", "--dry-run", "test", "--var.foo", "bar"],
            expect_code=0,
            expect_msg=HELP,
        )

    def test_parse_help_error_with_invalid_option(self) -> None:
        self.assertRaisesExit(
            ["--help", "--invalid", "test"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: unrecognized arguments: --invalid",
        )

    def test_error_when_variable_value_is_not_provided(self) -> None:
        self.assertRaisesExit(
            ["--var.foo"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: unrecognized arguments: --var.foo",
        )

    def test_error_when_variable_value_is_not_provided_and_other_variable_is_defined(
        self,
    ) -> None:
        self.assertRaisesExit(
            ["--var.foo", "--var.other", "bar"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: unrecognized arguments: --var.foo --var.other",
        )

    def test_error_when_no_task_is_provided(self) -> None:
        self.assertRaisesExit(
            [],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: at least one task name is required",
        )

    def test_error_invalid_variable_overrides(self) -> None:
        self.assertRaisesExit(
            ["--var.foo", "--var.bar=baz"],
            1,
            f"{USAGE}\ntask: error: unrecognized arguments: --var.foo --var.bar=baz",
        )

    def test_error_list_with_dry_run(self) -> None:
        self.assertRaisesExit(
            ["--list", "--dry-run"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: --list option cannot be used together with tasks and variables arguments or --dry-run option",
        )

    def test_error_list_with_tasks(self) -> None:
        self.assertRaisesExit(
            ["--list", "task_A"],
            expect_code=1,
            expect_msg=f"{USAGE}\ntask: error: --list option cannot be used together with tasks and variables arguments or --dry-run option",
        )

    def test_parse_list(self) -> None:
        filename, should_list, request = parse_args(["--list"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, True)
        self.assertEqual(request, Request([], variables={}, dry_run=False))

    def test_parse_list_with_filename(self) -> None:
        filename, should_list, request = parse_args(["-f", "other.toml", "--list"])
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, True)
        self.assertEqual(request, Request([], variables={}, dry_run=False))

    def test_parse_single_task_without_option(self) -> None:
        filename, should_list, request = parse_args(["task_A"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(request, Request(["task_A"], variables={}, dry_run=False))

    def test_parse_single_task_dry_run_after_task(self) -> None:
        filename, should_list, request = parse_args(["task_A", "--dry-run"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(request, Request(["task_A"], variables={}, dry_run=True))

    def test_parse_single_task_dry_run_before_task(self) -> None:
        filename, should_list, request = parse_args(["--dry-run", "task_A"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(request, Request(["task_A"], variables={}, dry_run=True))

    def test_parse_many_tasks_dry_run_before_task(self) -> None:
        filename, should_list, request = parse_args(["--dry-run", "task_A", "task_B"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A", "task_B"], variables={}, dry_run=True)
        )

    def test_parse_many_tasks_dry_run_after_task(self) -> None:
        filename, should_list, request = parse_args(["task_A", "task_B", "--dry-run"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A", "task_B"], variables={}, dry_run=True)
        )

    def test_parse_many_tasks_dry_run_between_task(self) -> None:
        filename, should_list, request = parse_args(["task_A", "--dry-run", "task_B"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A", "task_B"], variables={}, dry_run=True)
        )

    def test_parse_single_task_custom_file_before_task(self) -> None:
        filename, should_list, request = parse_args(["-f", "other.toml", "task_A"])
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(request, Request(["task_A"], variables={}, dry_run=False))

    def test_parse_many_tasks_custom_file_before_task(self) -> None:
        filename, should_list, request = parse_args(
            ["-f", "other.toml", "task_A", "task_B"]
        )
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A", "task_B"], variables={}, dry_run=False)
        )

    def test_parse_single_task_custom_file_after_task(self) -> None:
        filename, should_list, request = parse_args(["task_A", "-f", "other.toml"])
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(request, Request(["task_A"], variables={}, dry_run=False))

    def test_parse_many_tasks_custom_file_after_task(self) -> None:
        filename, should_list, request = parse_args(
            ["task_A", "task_B", "-f", "other.toml"]
        )
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A", "task_B"], variables={}, dry_run=False)
        )

    def test_parse_many_tasks_custom_file_between_tasks(self) -> None:
        filename, should_list, request = parse_args(
            ["task_A", "-f", "other.toml", "task_B"]
        )
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A", "task_B"], variables={}, dry_run=False)
        )

    def test_parse_single_task_dry_run_custom_file(self) -> None:
        filename, should_list, request = parse_args(
            ["task_A", "-f", "other.toml", "--dry-run"]
        )
        self.assertEqual(filename, "other.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(request, Request(["task_A"], variables={}, dry_run=True))

    def test_parse_single_task_variable_override(self) -> None:
        filename, should_list, request = parse_args(["task_A", "--var.foo=bar"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A"], variables={"foo": "bar"}, dry_run=False)
        )

    def test_parse_single_task_variable_override_splitted(self) -> None:
        filename, should_list, request = parse_args(["task_A", "--var.foo", "bar"])
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request, Request(["task_A"], variables={"foo": "bar"}, dry_run=False)
        )

    def test_parse_many_tasks_variable_overrides(self) -> None:
        filename, should_list, request = parse_args(
            ["task_A", "task_B", "--var.foo=bar", "--var.other=baz"]
        )
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request,
            Request(
                ["task_A", "task_B"],
                variables={"foo": "bar", "other": "baz"},
                dry_run=False,
            ),
        )

    def test_parse_many_tasks_variable_overrides_splitted(self) -> None:
        filename, should_list, request = parse_args(
            ["--var.foo", "bar", "--var.other", "baz", "task_A", "task_B"]
        )
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request,
            Request(
                ["task_A", "task_B"],
                variables={"foo": "bar", "other": "baz"},
                dry_run=False,
            ),
        )

    def test_parse_many_tasks_variable_overrides_splitted_between_tasks(self) -> None:
        filename, should_list, request = parse_args(
            ["task_A", "--var.foo", "bar", "task_B", "--var.other", "baz"]
        )
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request,
            Request(
                ["task_A", "task_B"],
                variables={"foo": "bar", "other": "baz"},
                dry_run=False,
            ),
        )

    def test_parse_many_tasks_dry_run_variable_overrides_splitted_between_tasks(
        self,
    ) -> None:
        filename, should_list, request = parse_args(
            ["task_A", "--var.foo", "bar", "--dry-run", "task_B", "--var.other", "baz"]
        )
        self.assertEqual(filename, "pyproject.toml")
        self.assertEqual(should_list, False)
        self.assertEqual(
            request,
            Request(
                ["task_A", "task_B"],
                variables={"foo": "bar", "other": "baz"},
                dry_run=True,
            ),
        )
