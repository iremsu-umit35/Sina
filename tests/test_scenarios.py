from sina.analyzer import ConditionInfo, ExceptionInfo, FunctionInfo, analyze_source
from sina.scenarios import generate_scenarios


def test_generates_scenario_for_single_exception() -> None:
    function = FunctionInfo(
        name="bol",
        parameters=["a", "b"],
        has_return=True,
        exceptions=[
            ExceptionInfo(
                type="ValueError",
                condition="b == 0",
                message="Sıfıra bölünemez",
            )
        ],
        conditions=[],
    )

    scenarios = generate_scenarios(function)

    assert len(scenarios) == 2
    assert scenarios[0].function_name == "bol"
    assert scenarios[0].kind == "normal"
    assert scenarios[1].kind == "exception"
    assert scenarios[1].description == "b == 0 koşulunda ValueError beklenir"
    assert scenarios[1].condition == "b == 0"
    assert scenarios[1].expected_exception == "ValueError"


def test_generates_scenario_for_unconditional_exception() -> None:
    function = FunctionInfo(
        name="fail",
        parameters=[],
        has_return=False,
        exceptions=[
            ExceptionInfo(type="RuntimeError", condition=None, message="Hata")
        ],
        conditions=[],
    )

    scenarios = generate_scenarios(function)

    assert scenarios[1].condition is None
    assert scenarios[1].description == "RuntimeError beklenir"


def test_generates_normal_scenario_for_function_without_exceptions() -> None:
    function = FunctionInfo(
        name="topla",
        parameters=["a", "b"],
        has_return=True,
        exceptions=[],
        conditions=[],
    )

    scenarios = generate_scenarios(function)

    assert len(scenarios) == 1
    assert scenarios[0].function_name == "topla"
    assert scenarios[0].kind == "normal"
    assert scenarios[0].description == "topla fonksiyonunun normal kullanımı test edilmeli"
    assert scenarios[0].condition is None
    assert scenarios[0].expected_exception is None


def test_preserves_exception_order() -> None:
    function = FunctionInfo(
        name="kontrol",
        parameters=["x"],
        has_return=False,
        exceptions=[
            ExceptionInfo(type="ValueError", condition="x < 0", message="Negatif"),
            ExceptionInfo(type="RuntimeError", condition="x == 0", message="Sıfır"),
        ],
        conditions=[],
    )

    scenarios = generate_scenarios(function)

    assert len(scenarios) == 3
    assert [scenario.kind for scenario in scenarios] == [
        "normal",
        "exception",
        "exception",
    ]
    assert [scenario.expected_exception for scenario in scenarios] == [
        None,
        "ValueError",
        "RuntimeError",
    ]
    assert [scenario.condition for scenario in scenarios] == [
        None,
        "x < 0",
        "x == 0",
    ]


def test_generates_normal_scenario_for_function_without_return() -> None:
    function = FunctionInfo(
        name="yazdir",
        parameters=["deger"],
        has_return=False,
        exceptions=[],
        conditions=[],
    )

    scenarios = generate_scenarios(function)

    assert len(scenarios) == 1
    assert scenarios[0].kind == "normal"
    assert scenarios[0].function_name == "yazdir"


def test_analyzer_output_can_generate_exception_scenario() -> None:
    source_code = """
def bol(a, b):
    if b == 0:
        raise ValueError("Sıfıra bölünemez")
    return a / b
"""

    functions = analyze_source(source_code)
    scenarios = generate_scenarios(functions[0])

    assert len(scenarios) == 2
    assert scenarios[0].function_name == "bol"
    assert scenarios[0].kind == "normal"
    assert scenarios[1].kind == "exception"
    assert scenarios[1].description == "b == 0 koşulunda ValueError beklenir"
    assert scenarios[1].condition == "b == 0"
    assert scenarios[1].expected_exception == "ValueError"


def test_generates_boundary_scenario_for_single_condition() -> None:
    function = FunctionInfo(
        name="kontrol",
        parameters=["age"],
        has_return=True,
        exceptions=[],
        conditions=[ConditionInfo(left="age", operator="<", right=18)],
    )

    scenarios = generate_scenarios(function)

    assert len(scenarios) == 2
    assert scenarios[0].kind == "normal"
    assert scenarios[1].function_name == "kontrol"
    assert scenarios[1].kind == "boundary"
    assert scenarios[1].description == "age için 18 sınırı test edilmeli"
    assert scenarios[1].condition == "age < 18"
    assert scenarios[1].expected_exception is None


def test_preserves_condition_order_for_boundary_scenarios() -> None:
    function = FunctionInfo(
        name="kontrol",
        parameters=["x"],
        has_return=True,
        exceptions=[],
        conditions=[
            ConditionInfo(left="x", operator="<", right=0),
            ConditionInfo(left="x", operator=">=", right=100),
        ],
    )

    scenarios = generate_scenarios(function)

    assert len(scenarios) == 3
    assert [scenario.kind for scenario in scenarios] == [
        "normal",
        "boundary",
        "boundary",
    ]
    assert [scenario.condition for scenario in scenarios[1:]] == [
        "x < 0",
        "x >= 100",
    ]


def test_same_condition_generates_boundary_and_exception_scenarios() -> None:
    source_code = """
def kontrol(x):
    if x < 0:
        raise ValueError("Negatif")
"""

    functions = analyze_source(source_code)
    scenarios = generate_scenarios(functions[0])

    assert len(scenarios) == 3
    assert [scenario.kind for scenario in scenarios] == [
        "normal",
        "boundary",
        "exception",
    ]
    assert scenarios[1].condition == "x < 0"
    assert scenarios[1].expected_exception is None
    assert scenarios[2].condition == "x < 0"
    assert scenarios[2].expected_exception == "ValueError"


def test_preserves_float_boundary() -> None:
    function = FunctionInfo(
        name="fiyat_kontrol",
        parameters=["price"],
        has_return=True,
        exceptions=[],
        conditions=[ConditionInfo(left="price", operator=">=", right=3.5)],
    )

    scenarios = generate_scenarios(function)

    assert scenarios[1].condition == "price >= 3.5"
    assert scenarios[1].description == "price için 3.5 sınırı test edilmeli"
