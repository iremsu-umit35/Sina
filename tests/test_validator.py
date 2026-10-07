import pytest

from sina.validator import validate_generated_tests


TARGET_MODULE = "calculator"
EXPECTED_FUNCTIONS = ["bol"]


def _validate(
    generated_text: str,
    *,
    target_module: str = TARGET_MODULE,
    expected_functions: list[str] | None = None,
) -> str:
    if expected_functions is None:
        expected_functions = EXPECTED_FUNCTIONS
    return validate_generated_tests(
        generated_text,
        target_module=target_module,
        expected_functions=expected_functions,
    )


def test_returns_valid_pytest_code_unchanged() -> None:
    generated_text = (
        "import pytest\n"
        "from calculator import bol\n\n"
        "def test_example():\n"
        "    assert bol(4, 2) == 2\n"
    )

    assert _validate(generated_text) == generated_text


def test_strips_python_code_fence() -> None:
    generated_text = '''```python
from calculator import bol

def test_example():
    value = "`backticks are preserved`"
    assert value
```'''

    assert _validate(generated_text) == '''from calculator import bol

def test_example():
    value = "`backticks are preserved`"
    assert value'''


def test_strips_plain_code_fence() -> None:
    generated_text = (
        "```\n"
        "from calculator import bol\n\n"
        "def test_example():\n"
        "    assert True\n"
        "```"
    )

    assert _validate(generated_text) == (
        "from calculator import bol\n\ndef test_example():\n    assert True"
    )


@pytest.mark.parametrize("generated_text", ["", "   \n\t"])
def test_rejects_empty_code(generated_text: str) -> None:
    with pytest.raises(RuntimeError, match="Generated test code is empty"):
        _validate(generated_text)


def test_rejects_invalid_python_and_preserves_syntax_error() -> None:
    with pytest.raises(
        RuntimeError,
        match="Generated test code is not valid Python",
    ) as exc_info:
        _validate("def test_broken(:\n    pass")

    assert isinstance(exc_info.value.__cause__, SyntaxError)


@pytest.mark.parametrize(
    ("call_name", "call_expression"),
    [
        ("exec", 'exec("print(1)")'),
        ("eval", 'eval("1 + 1")'),
        ("compile", 'compile("pass", "<string>", "exec")'),
    ],
)
def test_rejects_disallowed_builtin_calls(
    call_name: str,
    call_expression: str,
) -> None:
    generated_text = (
        "from calculator import bol\n\n"
        f"def test_example():\n    {call_expression}\n"
    )

    with pytest.raises(RuntimeError) as exc_info:
        _validate(generated_text)

    assert str(exc_info.value).endswith(f"disallowed call: {call_name}")


@pytest.mark.parametrize(
    ("call_name", "call_expression"),
    [
        ("os.system", 'os.system("echo unsafe")'),
        ("subprocess.run", 'subprocess.run(["echo", "unsafe"])'),
        ("subprocess.call", 'subprocess.call(["echo", "unsafe"])'),
        ("subprocess.Popen", 'subprocess.Popen(["echo", "unsafe"])'),
        ("subprocess.check_call", 'subprocess.check_call(["echo", "unsafe"])'),
        (
            "subprocess.check_output",
            'subprocess.check_output(["echo", "unsafe"])',
        ),
    ],
)
def test_rejects_disallowed_process_calls(
    call_name: str,
    call_expression: str,
) -> None:
    generated_text = (
        "from calculator import bol\n\n"
        f"def test_example():\n    {call_expression}\n"
    )

    with pytest.raises(RuntimeError) as exc_info:
        _validate(generated_text)

    assert str(exc_info.value).endswith(f"disallowed call: {call_name}")


def test_rejects_code_without_top_level_test_function() -> None:
    generated_text = """
from calculator import bol

class TestGroup:
    def test_nested(self):
        assert True
"""

    with pytest.raises(
        RuntimeError,
        match="does not contain a pytest test function",
    ):
        _validate(generated_text)


def test_accepts_safe_pytest_code() -> None:
    generated_text = """
import pytest
from calculator import bol

def test_invalid_integer():
    with pytest.raises(ValueError):
        int("not-a-number")
"""

    assert _validate(generated_text) == generated_text


def test_checks_syntax_after_stripping_code_fence() -> None:
    generated_text = "```python\ndef test_broken(:\n    pass\n```"

    with pytest.raises(
        RuntimeError,
        match="Generated test code is not valid Python",
    ):
        _validate(generated_text)


def test_accepts_expected_function_from_target_module() -> None:
    generated_text = "from calculator import bol\n\ndef test_bol():\n    assert True\n"

    assert _validate(generated_text) == generated_text


def test_rejects_expected_function_from_wrong_module() -> None:
    generated_text = "from math_tools import bol\n\ndef test_bol():\n    assert True\n"

    with pytest.raises(RuntimeError, match="wrong module: bol"):
        _validate(generated_text)


def test_rejects_missing_expected_function_import() -> None:
    generated_text = "import pytest\n\ndef test_bol():\n    assert True\n"

    with pytest.raises(RuntimeError, match="missing required imports: bol"):
        _validate(generated_text)


def test_accepts_multiple_expected_functions_in_one_import() -> None:
    generated_text = (
        "from calculator import bol, topla\n\n"
        "def test_functions():\n"
        "    assert True\n"
    )

    assert _validate(
        generated_text,
        expected_functions=["bol", "topla"],
    ) == generated_text


def test_rejects_one_missing_expected_function() -> None:
    generated_text = "from calculator import bol\n\ndef test_bol():\n    assert True\n"

    with pytest.raises(RuntimeError, match="missing required imports: topla"):
        _validate(generated_text, expected_functions=["bol", "topla"])


def test_accepts_expected_functions_imported_on_separate_lines() -> None:
    generated_text = (
        "from calculator import bol\n"
        "from calculator import topla\n\n"
        "def test_functions():\n"
        "    assert True\n"
    )

    assert _validate(
        generated_text,
        expected_functions=["bol", "topla"],
    ) == generated_text


def test_star_import_does_not_satisfy_expected_functions() -> None:
    generated_text = "from calculator import *\n\ndef test_bol():\n    assert True\n"

    with pytest.raises(RuntimeError, match="missing required imports: bol"):
        _validate(generated_text)


def test_alias_is_checked_by_original_name() -> None:
    generated_text = (
        "from calculator import bol as divide\n\n"
        "def test_bol():\n"
        "    assert True\n"
    )

    assert _validate(generated_text) == generated_text


@pytest.mark.parametrize("target_module", ["", "  \n\t"])
def test_rejects_empty_target_module(target_module: str) -> None:
    with pytest.raises(ValueError, match="target_module must not be empty"):
        _validate(
            "from calculator import bol\n\ndef test_bol():\n    assert True\n",
            target_module=target_module,
        )


def test_rejects_empty_expected_functions() -> None:
    with pytest.raises(ValueError, match="expected_functions must not be empty"):
        _validate(
            "from calculator import bol\n\ndef test_bol():\n    assert True\n",
            expected_functions=[],
        )


@pytest.mark.parametrize("empty_name", ["", "   \n\t"])
def test_rejects_empty_expected_function_name(empty_name: str) -> None:
    with pytest.raises(
        ValueError,
        match="expected_functions must not contain empty names",
    ):
        _validate(
            "from calculator import bol\n\ndef test_bol():\n    assert True\n",
            expected_functions=["bol", empty_name],
        )
