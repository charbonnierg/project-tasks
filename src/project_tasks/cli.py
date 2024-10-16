from __future__ import annotations

import argparse
import sys
import typing as t
from types import TracebackType

from .executor import make_default_executor
from .output import Output, make_default_output
from .pyproject import InvalidConfigError, parse_pyproject_file
from .service import Request, Service


class Exit(Exception):
    """Errors raised by the command line argument parser."""

    def __init__(self, return_code: int, msg: str | list[str]) -> None:
        self.return_code = return_code
        self.msg = "\n".join(msg) if isinstance(msg, list) else msg
        super().__init__(self.msg)


def create_parser() -> argparse.ArgumentParser:
    # At this point we know the tasks, so we can create the main parser
    parser = argparse.ArgumentParser(
        prog="task",
        add_help=False,
        usage="task [--help] [--list] [--file FILE] [--dry-run] [--var.<NAME> VALUE] [task_name ...]\n",
        description=(
            "task: run a single or several tasks defined in pyproject.toml.\n\n"
            "positional arguments:\n"
            "  task_name        Task to run\n"
        ),
        epilog=(
            "optional key-value arguments:\n"
            "  --var.<name>     Set variable with value\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # --help option
    parser.add_argument("--help", "-h", action="store_true", help="Show help and exit")
    # --file option
    parser.add_argument("--file", "-f", default="pyproject.toml", help="Pyproject file")
    # --list option
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available tasks"
    )
    # --dry-run option
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show task steps instead of executing them",
    )
    return parser


def parse_args(args: t.Sequence[str]) -> tuple[str, bool, Request]:
    # Create a new parser
    parser = create_parser()
    # Parse known arguments
    ns, remaining = parser.parse_known_args(args)
    # Parse variables and tasks
    tasks: list[str] = []
    variables: dict[str, str] = {}
    unrecognized_arguments: list[str] = []
    pending_variable: str | None = None
    for arg in remaining:
        if arg.startswith("--var."):
            # Handle case when a new variable is defined while previous does not have a value
            if pending_variable:
                unrecognized_arguments.extend([f"--var.{pending_variable}", arg])
                pending_variable = None
                continue
            # Handle case when variable override is a single string
            if "=" in arg:
                name, value = arg[6:].split("=", 1)
                variables[name] = value
                continue
            # Handle case when variable override is splitted on two arguments
            pending_variable = arg[6:]
            continue
        # Expect a value to override the pending variable
        if pending_variable:
            variables[pending_variable] = arg
            pending_variable = None
            continue
        # Invalid option
        if arg.startswith("--"):
            unrecognized_arguments.append(arg)
            continue
        # Append new task
        tasks.append(arg)
    if pending_variable:
        unrecognized_arguments.append(f"--var.{pending_variable}")
    # Exit with usage and error if unrecognized arguments are provided
    if unrecognized_arguments:
        raise Exit(
            1,
            [
                parser.format_usage().strip(),
                f"task: error: unrecognized arguments: {' '.join(unrecognized_arguments)}",
            ],
        )
    # Exit if --help is specified
    if ns.help:
        raise Exit(0, parser.format_help())
    # Exit with usage and error if no task task is provided and --list is not used
    if not tasks and not ns.list:
        raise Exit(
            1,
            [
                parser.format_usage().strip(),
                "task: error: at least one task name is required",
            ],
        )
    # Exit with usage and error if --list is used with any option
    if ns.list:
        if ns.dry_run or tasks or variables:
            raise Exit(
                1,
                [
                    parser.format_usage().strip(),
                    "task: error: --list option cannot be used together with tasks and variables arguments or --dry-run option",
                ],
            )
    # Return options
    return (
        ns.file,
        ns.list,
        Request(
            tasks=tasks,
            variables=variables,
            dry_run=ns.dry_run,
        ),
    )


def run(output: Output, args: t.Sequence[str]) -> int:
    """Run CLI.

    This function do not call sys.exit(), but instead returns
    an integer indicating the code with which program should exit.

    All function output is written to the output argument.

    Arguments:
        output: the output to write to.
        args: command line arguments and options. Example: ["task1", "task2", "--dry-run"].

    Returns:
        exit_code: 0 indicates success, anything else is an error.
    """
    # Parse command line arguments
    try:
        filename, should_list, request = parse_args(args)
    except Exit as exc:
        if exc.return_code > 0:
            output.write_error(exc.msg)
        else:
            output.write(exc.msg)
        return exc.return_code
    # Parse pyproject file
    try:
        config = parse_pyproject_file(filename)
    # Display nice error message when config is invalid
    except InvalidConfigError as exc:
        output.write_error(f"task: error: {exc.msg}")
        return 1
    # Display nice error message when file is not found
    except FileNotFoundError:
        output.write_error(f"task: error: pyproject file not found: {filename}")
        return 1
    if should_list:
        for task in config.tasks:
            output.write(task)
        return 0
    # Create a new service
    service = Service(config=config, output=output, executor=make_default_executor())
    # Execute the service
    return service.execute(request)


def main() -> t.NoReturn:  # pragma: no cover
    """Command line entry point."""
    # Use custom except hook
    sys.excepthook = custom_except_hook
    sys.exit(run(make_default_output(), sys.argv[1:]))


# Keep a reference to the default except hook
_default_except_hook = sys.excepthook


# Define a new function to handle uncaught exceptions
def custom_except_hook(
    exception_type: type[BaseException],
    exception: BaseException,
    traceback: TracebackType,
):
    # Suppress traceback display on KeyboardInterrupt
    if exception_type is KeyboardInterrupt:
        return
    # use default except hook
    _default_except_hook(exception_type, exception, traceback)
