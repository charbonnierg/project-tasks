import io
import unittest
from contextlib import redirect_stderr

from project_tasks.cli import custom_except_hook


class TestCustomExceptHook(unittest.TestCase):
    def test_keyboard_interrupt(self) -> None:
        error: KeyboardInterrupt | None = None
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt as exc:
            error = exc
        assert error
        assert error.__traceback__
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            custom_except_hook(
                KeyboardInterrupt, KeyboardInterrupt(), error.__traceback__
            )
        self.assertEqual(stderr.getvalue(), "")

    def test_exception(self) -> None:
        error: Exception | None = None
        try:
            raise Exception("test")
        except Exception as exc:
            error = exc
        assert error
        assert error.__traceback__
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            custom_except_hook(Exception, error, error.__traceback__)
        displayed_error = stderr.getvalue()
        self.assertIn("Traceback (most recent call last):", displayed_error)
        self.assertIn("Exception: test", displayed_error)
