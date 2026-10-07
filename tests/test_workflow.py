import pytest

import sina.workflow as workflow
from sina.analyzer import FunctionInfo
from sina.scenarios import TestScenario as Scenario


def _function(name: str) -> FunctionInfo:
    return FunctionInfo(
        name=name,
        parameters=[],
        has_return=False,
        exceptions=[],
        conditions=[],
    )


def _scenario(function_name: str, kind: str) -> Scenario:
    return Scenario(
        function_name=function_name,
        kind=kind,
        description=f"{function_name} {kind} scenario",
        condition=None,
        expected_exception=None,
    )


def test_generate_workflow_coordinates_layers_without_running_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_code = "def first():\n    pass\n\ndef second():\n    pass\n"
    functions = [_function("first"), _function("second")]
    first_scenarios = [_scenario("first", "normal"), _scenario("first", "boundary")]
    second_scenarios = [_scenario("second", "exception")]
    scenario_calls: list[FunctionInfo] = []
    captured_generation: dict[str, object] = {}

    def fake_analyze_source(received_source_code: str) -> list[FunctionInfo]:
        assert received_source_code == source_code
        return functions

    def fake_generate_scenarios(function: FunctionInfo) -> list[Scenario]:
        scenario_calls.append(function)
        if function is functions[0]:
            return first_scenarios
        return second_scenarios

    def fake_generate_tests(
        received_source_code: str,
        received_functions: list[FunctionInfo],
        received_scenarios: list[Scenario],
        received_target_module: str,
    ) -> str:
        captured_generation.update(
            source_code=received_source_code,
            functions=received_functions,
            scenarios=received_scenarios,
            target_module=received_target_module,
        )
        return "from calculator import first, second\n"

    def fail_if_runner_is_called(*args: object, **kwargs: object) -> None:
        pytest.fail("generate_test_workflow must not execute generated tests")

    monkeypatch.setattr(workflow, "analyze_source", fake_analyze_source)
    monkeypatch.setattr(workflow, "generate_scenarios", fake_generate_scenarios)
    monkeypatch.setattr(workflow, "generate_tests", fake_generate_tests)
    monkeypatch.setattr(workflow, "run_generated_tests", fail_if_runner_is_called)

    result = workflow.generate_test_workflow(source_code, "calculator")

    expected_scenarios = [*first_scenarios, *second_scenarios]
    assert scenario_calls == functions
    assert captured_generation == {
        "source_code": source_code,
        "functions": functions,
        "scenarios": expected_scenarios,
        "target_module": "calculator",
    }
    assert result.functions is functions
    assert result.scenarios == expected_scenarios
    assert result.generated_test_code == "from calculator import first, second\n"


def test_generation_workflow_uses_real_analysis_and_scenarios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_code = '''\
def bol(a, b):
    if b < 1:
        raise ValueError("Geçersiz bölen")
    return a / b
'''
    generated_test_code = '''\
from calculator import bol

def test_bol():
    assert bol(10, 2) == 5
'''

    monkeypatch.setattr(
        workflow,
        "generate_tests",
        lambda source, functions, scenarios, target: generated_test_code,
    )

    result = workflow.generate_test_workflow(source_code, "calculator")

    assert [function.name for function in result.functions] == ["bol"]
    assert [scenario.kind for scenario in result.scenarios] == [
        "normal",
        "boundary",
        "exception",
    ]
    assert result.generated_test_code == generated_test_code


def test_run_workflow_delegates_and_returns_same_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_result = workflow.TestRunResult(
        status="passed",
        return_code=0,
        stdout="1 passed",
        stderr="",
        timed_out=False,
    )

    def fake_run_generated_tests(**kwargs: object) -> workflow.TestRunResult:
        captured.update(kwargs)
        return expected_result

    monkeypatch.setattr(workflow, "run_generated_tests", fake_run_generated_tests)

    result = workflow.run_test_workflow(
        source_code="def add(a, b):\n    return a + b\n",
        generated_test_code="from calculator import add\n",
        target_module="calculator",
        timeout_seconds=2.5,
    )

    assert captured == {
        "source_code": "def add(a, b):\n    return a + b\n",
        "generated_test_code": "from calculator import add\n",
        "target_module": "calculator",
        "timeout_seconds": 2.5,
    }
    assert result is expected_result


def test_generation_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_error = RuntimeError("AI provider failed")

    def fake_generate_tests(*args: object, **kwargs: object) -> str:
        raise provider_error

    monkeypatch.setattr(workflow, "generate_tests", fake_generate_tests)

    with pytest.raises(RuntimeError) as exc_info:
        workflow.generate_test_workflow("def example():\n    pass\n", "example")

    assert exc_info.value is provider_error


def test_runner_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner_error = ValueError("invalid runner input")

    def fake_run_generated_tests(**kwargs: object) -> workflow.TestRunResult:
        raise runner_error

    monkeypatch.setattr(workflow, "run_generated_tests", fake_run_generated_tests)

    with pytest.raises(ValueError) as exc_info:
        workflow.run_test_workflow("source", "tests", "module")

    assert exc_info.value is runner_error
