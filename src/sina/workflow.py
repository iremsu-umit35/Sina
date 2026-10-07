"""Sına'nın test üretme ve çalıştırma akışlarını koordine et."""

from dataclasses import dataclass

from sina.analyzer import FunctionInfo, analyze_source
from sina.generator import generate_tests
from sina.runner import TestRunResult, run_generated_tests
from sina.scenarios import TestScenario, generate_scenarios


@dataclass
class GenerationResult:
    functions: list[FunctionInfo]
    scenarios: list[TestScenario]
    generated_test_code: str


def generate_test_workflow(
    source_code: str,
    target_module: str,
) -> GenerationResult:
    """Kaynak kodu analiz et ve doğrulanmış pytest kodu üret."""

    functions = analyze_source(source_code)
    scenarios = [
        scenario
        for function in functions
        for scenario in generate_scenarios(function)
    ]
    generated_test_code = generate_tests(
        source_code,
        functions,
        scenarios,
        target_module,
    )

    return GenerationResult(
        functions=functions,
        scenarios=scenarios,
        generated_test_code=generated_test_code,
    )


def run_test_workflow(
    source_code: str,
    generated_test_code: str,
    target_module: str,
    timeout_seconds: float = 5.0,
) -> TestRunResult:
    """Doğrulanmış pytest kodunu runner katmanına ilet."""

    return run_generated_tests(
        source_code=source_code,
        generated_test_code=generated_test_code,
        target_module=target_module,
        timeout_seconds=timeout_seconds,
    )
