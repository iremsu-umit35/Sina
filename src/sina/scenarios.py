"""Analiz sonuçlarından test senaryoları oluşturacak modül."""

from dataclasses import dataclass

from sina.analyzer import FunctionInfo


@dataclass
class TestScenario:
    function_name: str
    kind: str
    description: str
    condition: str | None
    expected_exception: str | None


def generate_scenarios(function: FunctionInfo) -> list[TestScenario]:
    """Fonksiyon için normal, boundary ve exception senaryoları üret."""

    scenarios = [
        TestScenario(
            function_name=function.name,
            kind="normal",
            description=f"{function.name} fonksiyonunun normal kullanımı test edilmeli",
            condition=None,
            expected_exception=None,
        )
    ]

    for condition in function.conditions:
        scenarios.append(
            TestScenario(
                function_name=function.name,
                kind="boundary",
                description=(
                    f"{condition.left} için {condition.right} sınırı test edilmeli"
                ),
                condition=f"{condition.left} {condition.operator} {condition.right}",
                expected_exception=None,
            )
        )

    for exception in function.exceptions:
        if exception.condition is None:
            description = f"{exception.type} beklenir"
        else:
            description = f"{exception.condition} koşulunda {exception.type} beklenir"

        scenarios.append(
            TestScenario(
                function_name=function.name,
                kind="exception",
                description=description,
                condition=exception.condition,
                expected_exception=exception.type,
            )
        )

    return scenarios
