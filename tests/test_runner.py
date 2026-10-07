from pathlib import Path
import subprocess
import tempfile

import pytest

import sina.runner as runner
from sina.runner import run_generated_tests


SOURCE_CODE = """\
def add(a, b):
    return a + b
"""

PASSING_TEST_CODE = """\
from calculator import add


def test_add():
    assert add(2, 3) == 5
"""


def test_returns_passed_for_successful_pytest_run() -> None:
    result = run_generated_tests(SOURCE_CODE, PASSING_TEST_CODE, "calculator")

    assert result.status == "passed"
    assert result.return_code == 0
    assert result.timed_out is False
    assert "1 passed" in result.stdout


def test_returns_failed_for_assertion_failure() -> None:
    generated_test_code = """\
from calculator import add


def test_add():
    assert add(2, 3) == 99
"""

    result = run_generated_tests(SOURCE_CODE, generated_test_code, "calculator")

    assert result.status == "failed"
    assert result.return_code == 1
    assert result.timed_out is False
    assert "1 failed" in result.stdout


def test_returns_error_for_collection_problem() -> None:
    generated_test_code = """\
from missing_module import add


def test_add():
    assert add(2, 3) == 5
"""

    result = run_generated_tests(SOURCE_CODE, generated_test_code, "calculator")

    assert result.status == "error"
    assert result.return_code not in {None, 0, 1}
    assert result.timed_out is False


def test_returns_timeout_for_long_running_test() -> None:
    generated_test_code = """\
from calculator import add


def test_never_finishes():
    while True:
        pass
"""

    result = run_generated_tests(
        SOURCE_CODE,
        generated_test_code,
        "calculator",
        timeout_seconds=0.5,
    )

    assert result.status == "timeout"
    assert result.return_code is None
    assert result.timed_out is True
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)


@pytest.mark.parametrize(
    ("field", "source_code", "generated_test_code", "target_module", "message"),
    [
        (
            "source_code",
            "  \n\t",
            PASSING_TEST_CODE,
            "calculator",
            "source_code must not be empty",
        ),
        (
            "generated_test_code",
            SOURCE_CODE,
            "  \n\t",
            "calculator",
            "generated_test_code must not be empty",
        ),
        (
            "target_module",
            SOURCE_CODE,
            PASSING_TEST_CODE,
            "  \n\t",
            "target_module must not be empty",
        ),
    ],
)
def test_rejects_empty_required_input(
    field: str,
    source_code: str,
    generated_test_code: str,
    target_module: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        run_generated_tests(source_code, generated_test_code, target_module)


@pytest.mark.parametrize("timeout_seconds", [0, -1.0])
def test_rejects_non_positive_timeout(timeout_seconds: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be greater than zero"):
        run_generated_tests(
            SOURCE_CODE,
            PASSING_TEST_CODE,
            "calculator",
            timeout_seconds=timeout_seconds,
        )


def test_rejects_dotted_target_module() -> None:
    with pytest.raises(
        ValueError,
        match="runner does not support dotted target modules yet",
    ):
        run_generated_tests(SOURCE_CODE, PASSING_TEST_CODE, "package.calculator")


@pytest.mark.parametrize("target_module", ["../calculator", "calculator/test"])
def test_rejects_path_like_target_module(target_module: str) -> None:
    with pytest.raises(ValueError):
        run_generated_tests(SOURCE_CODE, PASSING_TEST_CODE, target_module)


def test_invokes_pytest_without_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "pytest output", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = run_generated_tests(SOURCE_CODE, PASSING_TEST_CODE, "calculator")

    assert result.status == "passed"
    assert captured["shell"] is False
    assert captured["command"] == [
        runner.sys.executable,
        "-m",
        "pytest",
        "test_generated.py",
        "-q",
    ]


def test_temporary_directory_is_removed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created_paths: list[Path] = []
    real_temporary_directory = tempfile.TemporaryDirectory

    def tracking_temporary_directory() -> tempfile.TemporaryDirectory[str]:
        context = real_temporary_directory(dir=tmp_path)
        created_paths.append(Path(context.name))
        return context

    monkeypatch.setattr(
        runner.tempfile,
        "TemporaryDirectory",
        tracking_temporary_directory,
    )

    result = run_generated_tests(SOURCE_CODE, PASSING_TEST_CODE, "calculator")

    assert result.status == "passed"
    assert len(created_paths) == 1
    assert not created_paths[0].exists()


def test_does_not_forward_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-parent-secret")
    generated_test_code = """\
import os
from calculator import add


def test_secret_is_not_forwarded():
    assert os.getenv("GEMINI_API_KEY") is None
"""

    result = run_generated_tests(SOURCE_CODE, generated_test_code, "calculator")

    assert result.status == "passed"


def test_result_model_stores_execution_details() -> None:
    result = runner.TestRunResult(
        status="error",
        return_code=2,
        stdout="captured stdout",
        stderr="captured stderr",
        timed_out=False,
    )

    assert result.status == "error"
    assert result.return_code == 2
    assert result.stdout == "captured stdout"
    assert result.stderr == "captured stderr"
    assert result.timed_out is False
