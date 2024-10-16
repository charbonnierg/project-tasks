import io
import unittest  # noqa: E402
from contextlib import redirect_stderr, redirect_stdout

from project_tasks.output import make_capture_output, make_default_output


class TestDefaultOutput(unittest.TestCase):
    def test_write(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            output = make_default_output()
            output.write("hello world")
        self.assertEqual(stdout.getvalue(), "hello world\n")

    def test_write_error(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            output = make_default_output()
            output.write_error("oops something's wrong")
        self.assertEqual(stderr.getvalue(), "oops something's wrong\n")


class TestCaptureOutput(unittest.TestCase):
    def test_write(self) -> None:
        stdout, _, output = make_capture_output()
        output.write("hello world")
        self.assertEqual(stdout.getvalue(), "hello world\n")

    def test_write_error(self) -> None:
        _, stderr, output = make_capture_output()
        output.write_error("oops something's wrong")
        self.assertEqual(stderr.getvalue(), "oops something's wrong\n")
