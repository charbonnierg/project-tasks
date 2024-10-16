from __future__ import annotations

import os
import re
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# Regular expression to find location in tommlib.TOMLDecodeError
# Example: "(at line 12, column 41)" => (12, 41,)
LOCATION_PATTERN = re.compile(r"\(at line (\d+), column (\d+)\)")
# Regular expression to find variables within tasks tasks
# Example: "${var.the_name}" => ("the_name",)
VARIABLE_PATTERN = re.compile(r"\${var\.([a-zA-Z0-9-_]*)}")


class InvalidConfigError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__(msg)


class TOMLDecodeError(InvalidConfigError):
    """Error raised when failing to decode a TOML file."""

    def __init__(self, origin: Exception, content: str, filename: str | None) -> None:
        # Save filename
        self.filename = filename
        # Save reason (do not capitalize error message)
        error_message: str = origin.args[0]
        self.reason = error_message[0].lower() + error_message[1:]
        # Find location
        match = LOCATION_PATTERN.search(self.reason)
        if match:
            last_line: str | int = match.group(1)
            last_column: str | int = match.group(2)
        else:
            all_lines = content.splitlines()
            last_line = len(all_lines)
            last_column = 0 if not all_lines else len(all_lines[-1]) + 1
        # Save location
        self.location = f"{last_line}:{last_column}"
        # Construct message using all info when there is a filename
        if filename:
            msg = f"{self.filename}:{self.location}: {self.reason}"
        # Else just use reason
        else:
            msg = self.reason
        super().__init__(msg)


class InvalidVariableError(InvalidConfigError):
    """Error raised when failing to parse a variable."""

    def __init__(self, var_name: str, msg: str) -> None:
        self.name = var_name
        self.reason = msg
        msg = f"variable '{var_name}': {self.reason}"
        super().__init__(msg)


class InvalidTaskError(InvalidConfigError):
    """Error raised when failing to parse a task."""

    def __init__(self, task_name: str, msg: str) -> None:
        self.name = task_name
        self.reason = msg
        msg = f"task '{task_name}': {self.reason}"
        super().__init__(msg)


class InvalidTaskDefinitionError(Exception):
    """Error raised when failing to parse a task definition (either a command or a reference)."""

    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__(self.msg)


class InvalidTaskDefinitionTypeError(InvalidTaskDefinitionError):
    def __init__(self, invalid_type: str) -> None:
        super().__init__(
            f"wrong type '{invalid_type}': task must be a string, a dict or a list of strings and dicts."
        )


class EmptyTaskStepError(InvalidTaskDefinitionError):
    def __init__(self) -> None:
        super().__init__("task step cannot be empty.")


class InvalidTaskStepTypeError(InvalidTaskDefinitionError):
    def __init__(self, invalid_type: str) -> None:
        super().__init__(
            f"wrong step type '{invalid_type}': step must be a string or a dict."
        )


class InvalidTaskCmdTypeError(InvalidTaskDefinitionError):
    def __init__(self, invalid_type: str) -> None:
        super().__init__(
            f"wrong type '{invalid_type}': cmd must be a string or a list."
        )


class InvalidTaskCmdItemTypeError(InvalidTaskDefinitionError):
    def __init__(self, invalid_type: str) -> None:
        super().__init__(
            f"wrong type '{invalid_type}': cmd list items must be strings."
        )


class InvalidTaskDictError(InvalidTaskDefinitionError):
    def __init__(self, invalid_key: t.Any) -> None:
        super().__init__(
            f"wrong key '{invalid_key}': task can be defined as dict with keys: ['cmd']."
        )


class CircularDependencyError(InvalidTaskDefinitionError):
    def __init__(self, task_a: str, task_b: str) -> None:
        super().__init__(
            f"task '{task_a}' and '{task_b}' introduce a circular dependency."
        )


class UnknownTaskReferenceError(InvalidTaskDefinitionError):
    def __init__(self, task_name: str, parent: str) -> None:
        super().__init__(f"task '{task_name}' does not exist (used by '{parent}').")


@dataclass
class _TaskCommand:
    """A task command is a list of commands as strings."""

    steps: list[str]


@dataclass
class _TaskReference:
    """A task reference holds the name to the task referenced."""

    name: str


@dataclass
class _TaskDefinition:
    """A task definition is a list of task commands and tasks references."""

    steps: list[_TaskCommand | _TaskReference]


@dataclass
class _VariableDefinition:
    default: str | None = None
    env: str | None = None
    file: Path | None = None
    secret: bool = False


@dataclass
class Task:
    """A task contains a list of commands as strings."""

    steps: list[str]


@dataclass
class Variable:
    """A variable contains a value which is evaluated dynamically."""

    getter: t.Callable[[str | None], str] = field(compare=False)
    secret: bool = False

    def get(self, override: str | None, dry_run: bool = False) -> str:
        value = self.getter(override)
        if dry_run and self.secret:
            return "*" * len(value)
        return value


@dataclass
class Config:
    """Config contains all configuration found in a pyproject.toml file ready to be used."""

    tasks: dict[str, Task]
    variables: dict[str, Variable]

    def get_task(self, task_name: str, override_variables: dict[str, str]) -> Task:
        """Get a task by name. Variables are replaced with their value when using this function."""
        task = self.tasks[task_name]
        resolved_task = Task([])
        for step in task.steps:
            to_replace = VARIABLE_PATTERN.findall(step)

            for variable_name in to_replace:
                variable_value = self.variables[variable_name].get(
                    override_variables.get(variable_name, None)
                )
                step = step.replace(f"${{var.{variable_name}}}", variable_value)
            resolved_task.steps.append(step)
        return resolved_task


def parse_pyproject_file(pyproject_file: str) -> Config:
    """Read config from a file."""
    filepath = Path(pyproject_file)
    content = filepath.read_text()
    filename = filepath.as_posix()
    return parse_pyproject_content(content=content, filename=filename)


def parse_pyproject_content(content: str, filename: str | None = None) -> Config:
    """Read config from a string."""
    try:
        document = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise TOMLDecodeError(exc, content, filename)
    return parse_pyproject_document(document)


def parse_pyproject_document(document: dict[str, t.Any]) -> Config:
    """Read config from a dict."""

    tool_section = document.get("tool", {})
    project_tasks_section = tool_section.get("project-tasks", {})
    tasks = parse_tasks(values=project_tasks_section.get("tasks", {}))
    variables = parse_variables(values=project_tasks_section.get("variables", {}))
    return Config(tasks=tasks, variables=variables)


def parse_tasks(values: dict[str, t.Any]) -> dict[str, Task]:
    tasks_definitions = _parse_all_tasks_definitions(values)
    return _resolve_all_tasks(tasks_definitions)


def parse_variables(values: dict[str, t.Any]) -> dict[str, Variable]:
    variables_definitions = _parse_all_variables_definitions(values)
    return _resolve_all_variables(variables_definitions)


## Resolver


def _resolve_all_variables(
    variables: dict[str, _VariableDefinition],
) -> dict[str, Variable]:
    vars: dict[str, Variable] = {}
    for name, definition in variables.items():

        def getter_factory(
            name: str, env: str | None, file: Path | None, default: str | None
        ) -> t.Callable[[str | None], str]:
            def getter(override: str | None) -> str:
                if override is not None:
                    return override
                if env is not None:
                    if env in os.environ:
                        return os.environ[env]
                if file is not None:
                    if file.exists():
                        return file.read_text()
                if default is not None:
                    return default
                raise ValueError(f"variable '{name}': value is not defined.")

            return getter

        vars[name] = Variable(
            getter=getter_factory(
                name, definition.env, definition.file, definition.default
            ),
            secret=definition.secret,
        )
    return vars


def _resolve_task(
    graph: dict[str, _TaskDefinition],
    task_name: str,
    parents: tuple[str, ...] | None = None,
) -> Task:
    """Resolve a task definition.

    NOTE: This function assumes that task_name is always a valid task.

    This function resolves a task definition by recursively resolving its dependencies.
    The goal is to unfold all commands to execute in a single task.
    """
    # Make sure parents is a tuple
    parents = parents or tuple()
    # Check for circular dependencies
    if task_name in parents:
        raise CircularDependencyError(parents[-1], task_name)
    # Check for undefined task
    try:
        definition = graph[task_name]
    except KeyError:
        raise UnknownTaskReferenceError(task_name=task_name, parent=parents[-1])
    # Create a new resolved task
    resolved: list[str] = []
    # It task is not a string, then it may have referenced tasks in steps, let's update parents
    parents = parents + (task_name,)
    # Iterate over task steps
    for item in definition.steps:
        if isinstance(item, _TaskReference):
            # Recursive call to get_task to resolve the task dependency
            resolved_dependency = _resolve_task(graph, item.name, parents)
            resolved.extend(resolved_dependency.steps)
        else:
            # Add command to the resolved task
            resolved.extend(item.steps)
    # At this point task is resolved
    return Task(resolved)


def _resolve_all_tasks(graph: dict[str, _TaskDefinition]) -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    for task_name in graph:
        try:
            tasks[task_name] = _resolve_task(graph, task_name)
        except InvalidTaskDefinitionError as exc:
            raise InvalidTaskError(task_name, exc.msg)
    return tasks


## Tasks parser


def _parse_str_task_definition(definition: str) -> _TaskDefinition:
    if not definition:
        raise EmptyTaskStepError()
    return _TaskDefinition(steps=[_TaskCommand([definition])])


def _parse_list_task_definition(definition: list[t.Any]) -> _TaskDefinition:
    steps: list[str] = []
    for step in definition:
        if isinstance(step, str):
            if not step:
                raise EmptyTaskStepError()
            steps.append(step)
            continue
        raise InvalidTaskStepTypeError(type(step).__name__)
    return _TaskDefinition(steps=[_TaskCommand(steps)])


def _parse_dict_task_definition(definition: dict[t.Any, t.Any]) -> _TaskDefinition:
    steps: list[_TaskCommand | _TaskReference] = []
    for key, value in definition.items():
        if not isinstance(key, str):
            raise InvalidTaskDictError(key)
        if key == "cmd":
            if isinstance(value, str):
                if not value:
                    raise EmptyTaskStepError()
                steps.append(_TaskCommand([value]))
            elif isinstance(value, list):
                cmd = _TaskCommand([])
                for step in value:  # pyright: ignore[reportUnknownVariableType]
                    if isinstance(step, str):
                        if not step:
                            raise EmptyTaskStepError()
                        cmd.steps.append(step)
                    else:
                        raise InvalidTaskCmdItemTypeError(type(step).__name__)  # pyright: ignore[reportUnknownArgumentType]
                steps.append(cmd)
            else:
                raise InvalidTaskCmdTypeError(type(value).__name__)
            continue
        if key == "deps":
            if isinstance(value, list):
                dependencies: list[str | t.Any] = value
                for dep in dependencies:
                    if isinstance(dep, str):
                        steps.append(_TaskReference(dep))
                    else:
                        raise InvalidTaskDefinitionError(
                            f"wrong type '{type(dep).__name__}': deps list items must be strings."
                        )
            else:
                raise InvalidTaskDefinitionError(
                    f"wrong type '{type(value).__name__}': deps must be a list of strings."
                )
        else:
            raise InvalidTaskDictError(key)
    return _TaskDefinition(steps=steps)


def _parse_task_definition(
    definition: t.Any,
) -> _TaskDefinition:
    # Handle strings
    if isinstance(definition, str):
        return _parse_str_task_definition(definition)
    # Handle lists
    if isinstance(definition, list):
        return _parse_list_task_definition(definition)  # pyright: ignore[reportUnknownArgumentType]
    # Handle dicts
    if isinstance(definition, dict):
        return _parse_dict_task_definition(definition)  # pyright: ignore[reportUnknownArgumentType]
    # Everything else is invalid
    raise InvalidTaskDefinitionTypeError(type(definition).__name__)


def _parse_all_tasks_definitions(
    mapping: dict[str, t.Any],
) -> dict[str, _TaskDefinition]:
    # Create an empty dict of tasks definitions
    tasks_definitions: dict[str, _TaskDefinition] = {}
    # Declare type of raw task definition
    raw_definition: str | list[t.Any] | dict[t.Any, t.Any] | t.Any
    # Iterate over raw tasks definitions
    for task_name, raw_definition in mapping.items():
        try:
            tasks_definitions[task_name] = _parse_task_definition(raw_definition)
        except InvalidTaskDefinitionError as exc:
            raise InvalidTaskError(task_name, exc.msg)
    return tasks_definitions


## Variables parser


def _parse_all_variables_definitions(
    mapping: dict[str, t.Any],
) -> dict[str, _VariableDefinition]:
    variables: dict[str, _VariableDefinition] = {}
    for var_name, raw_definition in mapping.items():
        if isinstance(raw_definition, str):
            variables[var_name] = _VariableDefinition(default=raw_definition)
        elif isinstance(raw_definition, dict):
            raw: dict[str, t.Any] = raw_definition
            for key in raw:
                if key not in ["default", "env", "file", "secret"]:
                    raise InvalidVariableError(
                        var_name,
                        f"wrong key '{key}': variable can be defined as dict with keys: ['default', 'env', 'file', 'secret'].",
                    )
            variables[var_name] = _VariableDefinition(
                default=raw.get("default", None),
                env=raw.get("env", None),
                file=Path(raw["file"]) if "file" in raw else None,
                secret=raw.get("secret", False),
            )
        else:
            raise InvalidVariableError(
                var_name,
                f"wrong type '{type(raw_definition).__name__}': variable must be a string or a dict.",
            )
    return variables
