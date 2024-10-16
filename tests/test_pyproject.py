import os
import tempfile
import typing as t
import unittest
from pathlib import Path

from project_tasks.pyproject import (
    Config,
    InvalidConfigError,
    Task,
    TOMLDecodeError,
    Variable,
    parse_pyproject_content,
    parse_pyproject_document,
    parse_pyproject_file,
    parse_variables,
)


class TestParsePyprojectFileFunc(unittest.TestCase):
    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproject_file = Path(tmpdir) / "pyproject.toml"
            pyproject_file.write_text("# Empty pyproject")
            config = parse_pyproject_file(pyproject_file.as_posix())
        self.assertEqual(
            config,
            Config(tasks={}, variables={}),
        )


class TestParsePyprojectContentFunc(unittest.TestCase):
    def test_success(self) -> None:
        pyproject = "[tool]\n[project-tasks]\n"
        document = parse_pyproject_content(pyproject)
        self.assertEqual(document, Config(tasks={}, variables={}))

    def test_error_without_filename_and_with_location(self) -> None:
        pyproject = "# First line is a comment\n[]\n"
        with self.assertRaises(TOMLDecodeError) as raised:
            parse_pyproject_content(pyproject)
        # Expect default filename to be used
        self.assertEqual(raised.exception.filename, None)
        # Expect error at line 2, column 2, because an empty table name is invalid in TOML
        self.assertEqual(raised.exception.location, "2:2")
        self.assertIn(
            "invalid initial character for a key part (at line 2, column 2)",
            raised.exception.msg,
        )

    def test_error_without_filename_end_of_document(self) -> None:
        pyproject = "# First line is a comment\n["
        with self.assertRaises(TOMLDecodeError) as raised:
            parse_pyproject_content(pyproject)
        # Expect default filename to be used
        self.assertEqual(raised.exception.filename, None)
        # Expect error at line 2, column 2, because key part is missing
        self.assertEqual(raised.exception.location, "2:2")
        self.assertIn(
            "invalid initial character for a key part (at end of document)",
            raised.exception.msg,
        )

    def test_error_with_filename_and_with_location(self) -> None:
        pyproject = "# First line is a comment\n[]\n"
        filename = "pyproject.toml"
        with self.assertRaises(TOMLDecodeError) as raised:
            parse_pyproject_content(pyproject, filename=filename)
        # Expect default filename to be used
        self.assertEqual(raised.exception.filename, filename)
        # Expect error at line 2, column 2, because an empty table name is invalid in TOML
        self.assertEqual(raised.exception.location, "2:2")
        self.assertIn(
            "pyproject.toml:2:2: invalid initial character for a key part (at line 2, column 2)",
            raised.exception.msg,
        )

    def test_error_with_filename_end_of_document(self) -> None:
        pyproject = "# First line is a comment\n["
        filename = "pyproject.toml"
        with self.assertRaises(TOMLDecodeError) as raised:
            parse_pyproject_content(pyproject, filename="pyproject.toml")
        # Expect default filename to be used
        self.assertEqual(raised.exception.filename, filename)
        # Expect error at line 2, column 2, because key part is missing
        self.assertEqual(raised.exception.location, "2:2")
        self.assertIn(
            "pyproject.toml:2:2: invalid initial character for a key part (at end of document)",
            raised.exception.msg,
        )


class TestParsePyprojectFunc(unittest.TestCase):
    @staticmethod
    def make_pyproject(
        tasks: dict[str, t.Any] | None = None,
        variables: dict[str, t.Any] | None = None,
    ) -> dict[str, t.Any]:
        """A utility to create pyproject document in unit tests."""

        document: dict[str, t.Any] = {"tool": {"project-tasks": {}}}
        document["tool"]["project-tasks"]["tasks"] = tasks or {}
        document["tool"]["project-tasks"]["variables"] = variables or {}
        return document

    def expectConfigEqual(self, config: dict[str, t.Any], expected: Config) -> None:
        """Assertion helper to check that parsed config is equal to expected value."""

        document = self.make_pyproject(**config)
        self.assertEqual(parse_pyproject_document(document), expected)

    def expectConfigError(
        self,
        config: dict[str, t.Any],
        expected_msg: str,
    ) -> None:
        """Assertion helper to check that parsing config raises an error."""

        document = self.make_pyproject(**config)
        with self.assertRaises(InvalidConfigError) as raised:
            parse_pyproject_document(document)
        self.assertEqual(
            raised.exception.msg,
            expected_msg,
        )

    def test_empty(self) -> None:
        self.assertEqual(
            parse_pyproject_document({}),
            Config(tasks={}, variables={}),
        )

    def test_empty_tool_section(self) -> None:
        self.assertEqual(
            parse_pyproject_document({"tool": {}}),
            Config(tasks={}, variables={}),
        )

    def test_empty_project_tasks_section(self) -> None:
        self.assertEqual(
            parse_pyproject_document({"tool": {"project-tasks": {}}}),
            Config(tasks={}, variables={}),
        )

    def test_single_task_as_string(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "test": "python -m unittest discover",
                }
            ),
            Config(
                tasks={
                    "test": Task(["python -m unittest discover"]),
                },
                variables={},
            ),
        )

    def test_single_task_as_list_of_strings(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "test": [
                        "python -m unittest discover",
                        "python -m coverage report",
                    ],
                }
            ),
            Config(
                tasks={
                    "test": Task(
                        [
                            "python -m unittest discover",
                            "python -m coverage report",
                        ]
                    )
                },
                variables={},
            ),
        )

    def test_single_task_as_dict_with_cmd_string(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "test": {"cmd": "python -m unittest discover"},
                }
            ),
            Config(
                tasks={"test": Task(["python -m unittest discover"])},
                variables={},
            ),
        )

    def test_single_task_as_dict_with_cmd_list(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "test": {"cmd": ["python -m unittest discover"]},
                }
            ),
            Config(
                tasks={"test": Task(["python -m unittest discover"])},
                variables={},
            ),
        )

    def test_many_tasks_as_strings(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "A": "python -m module_A",
                    "B": "python -m module_B",
                    "C": "python -m module_C",
                }
            ),
            Config(
                tasks={
                    "A": Task(["python -m module_A"]),
                    "B": Task(["python -m module_B"]),
                    "C": Task(["python -m module_C"]),
                },
                variables={},
            ),
        )

    def test_many_tasks_as_list_of_strings(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "A": ["python -m module_A"],
                    "B": ["python -m module_B"],
                    "C": ["python -m module_C"],
                }
            ),
            Config(
                tasks={
                    "A": Task(["python -m module_A"]),
                    "B": Task(["python -m module_B"]),
                    "C": Task(["python -m module_C"]),
                },
                variables={},
            ),
        )

    def test_many_tasks_as_list_of_dicts(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "A": {"cmd": ["python -m module_A"]},
                    "B": {"cmd": ["python -m module_B"]},
                    "C": {"cmd": ["python -m module_C"]},
                }
            ),
            Config(
                tasks={
                    "A": Task(["python -m module_A"]),
                    "B": Task(["python -m module_B"]),
                    "C": Task(["python -m module_C"]),
                },
                variables={},
            ),
        )

    def test_many_tasks_with_deps(self) -> None:
        self.expectConfigEqual(
            dict(
                tasks={
                    "A": ["python -m module_A"],
                    "B": {"deps": ["A"], "cmd": ["python -m module_B"]},
                    "C": {"deps": ["B"], "cmd": ["python -m module_C"]},
                }
            ),
            Config(
                tasks={
                    "A": Task(["python -m module_A"]),
                    "B": Task(["python -m module_A", "python -m module_B"]),
                    "C": Task(
                        [
                            "python -m module_A",
                            "python -m module_B",
                            "python -m module_C",
                        ]
                    ),
                },
                variables={},
            ),
        )

    def test_error_task_definition_wrong_dep_type(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"deps": 12}},
            ),
            "task 'test': wrong type 'int': deps must be a list of strings.",
        )

    def test_error_task_definition_wrong_dep_item_type(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"deps": [12]}},
            ),
            "task 'test': wrong type 'int': deps list items must be strings.",
        )

    def test_error_task_definition_circle_dependency(self) -> None:
        self.expectConfigError(
            dict(
                tasks={
                    "A": {"deps": ["B"], "cmd": "unused"},
                    "B": {"deps": ["A"], "cmd": "unused"},
                },
            ),
            "task 'A': task 'B' and 'A' introduce a circular dependency.",
        )

    def test_error_task_definition_nested_circle_dependency(self) -> None:
        self.expectConfigError(
            dict(
                tasks={
                    "A": {"deps": ["B"], "cmd": "unused"},
                    "B": {"deps": ["C"], "cmd": "unused"},
                    "C": {"deps": ["A"], "cmd": "unused"},
                },
            ),
            "task 'A': task 'C' and 'A' introduce a circular dependency.",
        )

    def test_error_task_definition_unknown_task_reference(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"deps": ["unknown"]}},
            ),
            "task 'test': task 'unknown' does not exist (used by 'test').",
        )

    def test_error_task_definition_wrong_type(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": 12},
            ),
            "task 'test': wrong type 'int': task must be a string, a dict or a list of strings and dicts.",
        )

    def test_error_task_definition_wrong_step_type(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": [12]},
            ),
            "task 'test': wrong step type 'int': step must be a string or a dict.",
        )

    def test_error_task_definition_wrong_step_type_within_dict(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"cmd": 12}},
            ),
            "task 'test': wrong type 'int': cmd must be a string or a list.",
        )

    def test_error_task_definition_wrong_step_type_within_list_within_dict(
        self,
    ) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"cmd": [12]}},
            ),
            "task 'test': wrong type 'int': cmd list items must be strings.",
        )

    def test_error_task_definition_wrong_step_dict_bad_key(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"invalid-key": "unused"}},
            ),
            "task 'test': wrong key 'invalid-key': task can be defined as dict with keys: ['cmd'].",
        )

    def test_error_task_definition_wrong_step_dict_bad_key_type(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {12: "unused"}},
            ),
            "task 'test': wrong key '12': task can be defined as dict with keys: ['cmd'].",
        )

    def test_error_task_definition_empty_task_step_as_string(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": ""},
            ),
            "task 'test': task step cannot be empty.",
        )

    def test_error_task_definition_empty_task_step_as_string_within_dict(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"cmd": ""}},
            ),
            "task 'test': task step cannot be empty.",
        )

    def test_error_task_definition_empty_task_step_within_list_within_dict(
        self,
    ) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": {"cmd": [""]}},
            ),
            "task 'test': task step cannot be empty.",
        )

    def test_error_task_definition_empty_task_step_within_list(self) -> None:
        self.expectConfigError(
            dict(
                tasks={"test": [""]},
            ),
            "task 'test': task step cannot be empty.",
        )

    def test_error_variable_definition_wrong_type(self) -> None:
        self.expectConfigError(
            dict(
                variables={"test": 12},
            ),
            "variable 'test': wrong type 'int': variable must be a string or a dict.",
        )

    def test_error_variable_definition_wrong_key(self) -> None:
        self.expectConfigError(
            dict(
                variables={"test": {"invalid-key": "unused"}},
            ),
            "variable 'test': wrong key 'invalid-key': variable can be defined as dict with keys: ['default', 'env', 'file', 'secret'].",
        )

    def test_parse_variable_default(self) -> None:
        document = self.make_pyproject(
            variables={
                "test-1": {"default": "default value"},
                "test-2": "other default value",
            }
        )
        config = parse_pyproject_document(document)
        self.assertEqual(list(config.variables), ["test-1", "test-2"])
        self.assertEqual(config.variables["test-1"].get(None), "default value")
        self.assertEqual(config.variables["test-2"].get(None), "other default value")
        self.assertEqual(
            config.variables["test-1"].get("override value"), "override value"
        )
        self.assertEqual(
            config.variables["test-2"].get("override value"), "override value"
        )


class TestVariableGetter(unittest.TestCase):
    def test_variable_with_default(self) -> None:
        vars = parse_variables({"foo": "bar"})
        self.assertEqual(vars["foo"].get(None), "bar")
        self.assertEqual(vars["foo"].get("value"), "value")

    def test_variable_with_env_var_and_default(self) -> None:
        vars = parse_variables({"foo": {"env": "ENV_VAR", "default": "bar"}})
        self.assertEqual(vars["foo"].get(None), "bar")
        self.assertEqual(vars["foo"].get("override value"), "override value")
        os.environ["ENV_VAR"] = "env value"
        try:
            self.assertEqual(vars["foo"].get(None), "env value")
            self.assertEqual(vars["foo"].get("override value"), "override value")
        finally:
            del os.environ["ENV_VAR"]

    def test_variable_with_env_file_and_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            varfile = Path(tmpdir) / "varfile"
            varfile.write_text("file value")
            vars = parse_variables(
                {
                    "foo": {
                        "file": varfile.as_posix(),
                        "default": "bar",
                        "env": "ENV_VAR",
                    }
                }
            )
            self.assertEqual(vars["foo"].get(None), "file value")
            os.environ["ENV_VAR"] = "env value"
            try:
                self.assertEqual(vars["foo"].get(None), "env value")
            finally:
                del os.environ["ENV_VAR"]
        self.assertEqual(vars["foo"].get(None), "bar")

    def test_variable_without_default(self) -> None:
        vars = parse_variables({"foo": {}})
        with self.assertRaises(ValueError) as raised:
            vars["foo"].get(None)
        self.assertEqual(
            raised.exception.args[0], "variable 'foo': value is not defined."
        )
        self.assertEqual(vars["foo"].get("value"), "value")

    def test_secret_variable(self) -> None:
        vars = parse_variables({"foo": {"secret": True, "default": "bar"}})
        self.assertEqual(vars["foo"].get(None), "bar")
        self.assertEqual(vars["foo"].get(None, dry_run=True), "***")


class TestConfig(unittest.TestCase):
    def test_get_task(self) -> None:
        def default_or(value: str | None) -> str:
            if value is not None:
                return value
            return "default value"

        config = Config(
            tasks={"test": Task(["echo '${var.foo}'"])},
            variables={"foo": Variable(getter=default_or)},
        )

        self.assertEqual(
            config.get_task("test", {}),
            Task(["echo 'default value'"]),
        )
        self.assertEqual(
            config.get_task("test", override_variables={"foo": "other value"}),
            Task(["echo 'other value'"]),
        )
