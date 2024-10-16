import sys
import unittest

from project_tasks.executor import Executor, make_default_executor


class TestDefaultExecutor(unittest.TestCase):
    def test_make_default_executor(self) -> None:
        executor = make_default_executor()
        self.assertIsInstance(executor, Executor)

    def test_run(self) -> None:
        executor = make_default_executor()
        return_code = executor.run(f"{sys.executable} -c 'import sys; sys.exit(0)'")
        self.assertEqual(return_code, 0)
