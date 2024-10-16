from __future__ import annotations

import io
import sys
import typing as t
from dataclasses import dataclass


@dataclass
class Output:
    stdout: t.TextIO
    stderr: t.TextIO

    def write(self, content: str) -> None:
        print(content, file=self.stdout)

    def write_error(self, content: str) -> None:
        print(content, file=self.stderr)


def make_default_output() -> Output:
    return Output(stdout=sys.stdout, stderr=sys.stderr)


def make_capture_output() -> tuple[io.StringIO, io.StringIO, Output]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    return stdout, stderr, Output(stdout, stderr)
