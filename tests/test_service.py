import unittest

from project_tasks.executor import Executor
from project_tasks.output import make_capture_output
from project_tasks.pyproject import Config, Task
from project_tasks.service import Request, Service


class SuccessStubExecutor(Executor):
    def __init__(self) -> None:
        self.called_with: list[str] = []

    def run(self, cmd: str) -> int:
        self.called_with.append(cmd)
        return 0


class ErrorStubExecutor(Executor):
    def __init__(self, fail_after: int = 0) -> None:
        self.called_with: list[str] = []
        self.fail_after = fail_after

    def run(self, cmd: str) -> int:
        self.called_with.append(cmd)
        if self.fail_after >= len(self.called_with):
            return 0
        return 1


class TestService(unittest.TestCase):
    def test_execute_unknown_task(self) -> None:
        cfg = Config(tasks={}, variables={})
        stdout, stderr, output = make_capture_output()
        srv = Service(cfg, output, SuccessStubExecutor())
        result = srv.execute(
            request=Request(tasks=["unknown-task"], variables={}, dry_run=False)
        )
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(), "task: error: task do not exist: 'unknown-task'\n"
        )

    def test_execute_unknown_tasks(self) -> None:
        cfg = Config(tasks={}, variables={})
        stdout, stderr, output = make_capture_output()
        srv = Service(cfg, output, SuccessStubExecutor())
        result = srv.execute(
            request=Request(
                tasks=["unknown-task-1", "unknown-task-2"], variables={}, dry_run=False
            )
        )
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "task: error: tasks do not exist: ['unknown-task-1', 'unknown-task-2']\n",
        )

    def test_execute_single_task_success(self) -> None:
        cfg = Config(tasks={"test": Task(["true"])}, variables={})
        stdout, stderr, output = make_capture_output()
        srv = Service(cfg, output, SuccessStubExecutor())
        result = srv.execute(
            request=Request(tasks=["test"], variables={}, dry_run=False)
        )
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_execute_many_tasks_success(self) -> None:
        cfg = Config(tasks={"test": Task(["true"])}, variables={})
        stdout, stderr, output = make_capture_output()
        srv = Service(cfg, output, SuccessStubExecutor())
        result = srv.execute(
            request=Request(tasks=["test"], variables={}, dry_run=False)
        )
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_execute_single_task_dry_run(self) -> None:
        cfg = Config(tasks={"test": Task(["true"])}, variables={})
        stdout, stderr, output = make_capture_output()
        srv = Service(cfg, output, SuccessStubExecutor())
        result = srv.execute(
            request=Request(tasks=["test"], variables={}, dry_run=True)
        )
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "true\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_execute_single_task_error(self) -> None:
        cfg = Config(tasks={"test": Task(["true"])}, variables={})
        stdout, stderr, output = make_capture_output()
        srv = Service(cfg, output, ErrorStubExecutor())
        result = srv.execute(
            request=Request(tasks=["test"], variables={}, dry_run=False)
        )
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(), "task: error: task test failed with exit code 1\n"
        )

    def test_execute_many_tasks_error_first_task(self) -> None:
        cfg = Config(
            tasks={
                "test-1": Task(["do test-1"]),
                "test-2": Task(["do test-2"]),
            },
            variables={},
        )
        stdout, stderr, output = make_capture_output()
        executor = ErrorStubExecutor()
        srv = Service(cfg, output, executor)
        result = srv.execute(
            request=Request(tasks=["test-1", "test-2"], variables={}, dry_run=False)
        )
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(), "task: error: task test-1 failed with exit code 1\n"
        )
        self.assertEqual(executor.called_with, ["do test-1"])

    def test_execute_many_tasks_error_second_task(self) -> None:
        cfg = Config(
            tasks={
                "test-1": Task(["do test-1"]),
                "test-2": Task(["do test-2"]),
            },
            variables={},
        )
        stdout, stderr, output = make_capture_output()
        executor = ErrorStubExecutor(fail_after=1)
        srv = Service(cfg, output, executor)
        result = srv.execute(
            request=Request(tasks=["test-1", "test-2"], variables={}, dry_run=False)
        )
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(), "task: error: task test-2 failed with exit code 1\n"
        )
        self.assertEqual(executor.called_with, ["do test-1", "do test-2"])
