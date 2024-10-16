import abc
import platform
import subprocess


class Executor(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self, cmd: str) -> int:
        raise NotImplementedError


class BourneShellExecutor(Executor):
    """BourneShellExecutor executes commands using a bourne shell (sh, bash, dash, ...)."""

    def __init__(self, shell: str = "bash") -> None:
        self.shell = shell

    def run(self, cmd: str) -> int:
        args = [self.shell, "-c", cmd]
        return subprocess.run(args).returncode


class PowerShellExecutor(Executor):
    """PowerShellExecutor executes commands using PowerShell."""

    def __init__(self, shell: str = "powershell.exe") -> None:
        self.shell = shell

    def run(self, cmd: str) -> int:
        args = [self.shell, "-NoProfile", "-Command", cmd]
        return subprocess.run(args).returncode


def make_default_executor() -> Executor:
    if platform.system() == "Windows":  # pyright: ignore[reportUnknownMemberType]
        return PowerShellExecutor()
    return BourneShellExecutor()
