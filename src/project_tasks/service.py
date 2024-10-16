from dataclasses import dataclass

from .executor import Executor
from .output import Output
from .pyproject import Config


@dataclass
class Request:
    tasks: list[str]
    variables: dict[str, str]
    dry_run: bool


class Service:
    def __init__(
        self,
        config: Config,
        output: Output,
        executor: Executor,
    ) -> None:
        self.executor = executor
        self.output = output
        self.config = config

    def execute(self, request: Request) -> int:
        # Check that all tasks exist so that we can raise an error with all tasks
        unknown_tasks = [
            task_name
            for task_name in request.tasks
            if task_name not in self.config.tasks
        ]
        if unknown_tasks:
            if len(unknown_tasks) > 1:
                self.output.write_error(
                    f"task: error: tasks do not exist: {unknown_tasks}"
                )
            else:
                self.output.write_error(
                    f"task: error: task do not exist: '{unknown_tasks[0]}'"
                )
            return 1
        # Iterate over tasks
        for task_name in request.tasks:
            task = self.config.get_task(
                task_name=task_name,
                override_variables=request.variables,
            )
            for command in task.steps:
                if request.dry_run:
                    self.output.write(command)
                else:
                    return_code = self.executor.run(command)
                    if return_code != 0:
                        self.output.write_error(
                            f"task: error: task {task_name} failed with exit code {return_code}",
                        )
                        return return_code
        return 0
