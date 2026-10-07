"""Doğrulanmış pytest kodunu ayrı bir subprocess içinde çalıştır."""

import keyword
import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile


@dataclass
class TestRunResult:
    status: str
    return_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


def _build_child_environment() -> dict[str, str]:
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }

    for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP"):
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value

    return environment


def _timeout_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def run_generated_tests(
    source_code: str,
    generated_test_code: str,
    target_module: str,
    timeout_seconds: float = 5.0,
) -> TestRunResult:
    """Kaynak ve test kodunu geçici dizinde pytest ile çalıştır."""

    if not source_code.strip():
        raise ValueError("source_code must not be empty.")
    if not generated_test_code.strip():
        raise ValueError("generated_test_code must not be empty.")
    if not target_module.strip():
        raise ValueError("target_module must not be empty.")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")
    if "." in target_module:
        raise ValueError("runner does not support dotted target modules yet.")
    if not target_module.isidentifier() or keyword.iskeyword(target_module):
        raise ValueError("target_module must be a valid Python module identifier.")

    with tempfile.TemporaryDirectory() as temporary_directory:
        working_directory = Path(temporary_directory)
        source_path = working_directory / f"{target_module}.py"
        test_path = working_directory / "test_generated.py"

        source_path.write_text(source_code, encoding="utf-8")
        test_path.write_text(generated_test_code, encoding="utf-8")

        command = [
            sys.executable,
            "-m",
            "pytest",
            test_path.name,
            "-q",
        ]

        try:
            completed_process = subprocess.run(
                command,
                cwd=working_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                env=_build_child_environment(),
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TestRunResult(
                status="timeout",
                return_code=None,
                stdout=_timeout_output(exc.stdout),
                stderr=_timeout_output(exc.stderr),
                timed_out=True,
            )

    if completed_process.returncode == 0:
        status = "passed"
    elif completed_process.returncode == 1:
        status = "failed"
    else:
        status = "error"

    return TestRunResult(
        status=status,
        return_code=completed_process.returncode,
        stdout=completed_process.stdout,
        stderr=completed_process.stderr,
        timed_out=False,
    )
