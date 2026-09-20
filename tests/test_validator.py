import pytest

from sina.validator import validate_generated_tests


def test_returns_valid_pytest_code_unchanged() -> None:
    generated_text = "import pytest\n\ndef test_example():\n    assert 1 + 1 == 2\n"

    assert validate_generated_tests(generated_text) == generated_text


def test_strips_python_code_fence() -> None:
    generated_text = '''```python
def test_example():
    value = "`backticks are preserved`"
    assert value
```'''

    assert validate_generated_tests(generated_text) == '''def test_example():
    value = "`backticks are preserved`"
    assert value'''


def test_strips_plain_code_fence() -> None:
    generated_text = "```\ndef test_example():\n    assert True\n```"

    assert validate_generated_tests(generated_text) == (
        "def test_example():\n    assert True"
    )


@pytest.mark.parametrize("generated_text", ["", "   \n\t"])
def test_rejects_empty_code(generated_text: str) -> None:
    with pytest.raises(RuntimeError, match="Generated test code is empty"):
        validate_generated_tests(generated_text)


def test_rejects_invalid_python_and_preserves_syntax_error() -> None:
    with pytest.raises(
        RuntimeError,
        match="Generated test code is not valid Python",
    ) as exc_info:
        validate_generated_tests("def test_broken(:\n    pass")

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
    generated_text = f"def test_example():\n    {call_expression}\n"

    with pytest.raises(RuntimeError) as exc_info:
        validate_generated_tests(generated_text)

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
    generated_text = f"def test_example():\n    {call_expression}\n"

    with pytest.raises(RuntimeError) as exc_info:
        validate_generated_tests(generated_text)

    assert str(exc_info.value).endswith(f"disallowed call: {call_name}")


def test_rejects_code_without_top_level_test_function() -> None:
    generated_text = """
class TestGroup:
    def test_nested(self):
        assert True
"""

    with pytest.raises(
        RuntimeError,
        match="does not contain a pytest test function",
    ):
        validate_generated_tests(generated_text)


def test_accepts_safe_pytest_code() -> None:
    generated_text = """
import pytest

def test_invalid_integer():
    with pytest.raises(ValueError):
        int("not-a-number")
"""

    assert validate_generated_tests(generated_text) == generated_text


def test_checks_syntax_after_stripping_code_fence() -> None:
    generated_text = "```python\ndef test_broken(:\n    pass\n```"

    with pytest.raises(
        RuntimeError,
        match="Generated test code is not valid Python",
    ):
        validate_generated_tests(generated_text)
