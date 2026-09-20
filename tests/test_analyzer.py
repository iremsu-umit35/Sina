import pytest

from sina.analyzer import ConditionInfo, ExceptionInfo, FunctionInfo, analyze_source


def test_analyzes_single_function() -> None:
    source_code = """
def topla(a, b):
    return a + b
"""

    result = analyze_source(source_code)

    assert result == [
        FunctionInfo(
            name="topla",
            parameters=["a", "b"],
            has_return=True,
            exceptions=[],
            conditions=[],
        )
    ]


def test_function_without_return() -> None:
    source_code = """
def selamla(isim):
    print(isim)
"""

    result = analyze_source(source_code)

    assert result[0].has_return is False


def test_finds_multiple_top_level_functions() -> None:
    source_code = """
def birinci():
    return 1

def ikinci(deger):
    return deger
"""

    result = analyze_source(source_code)

    assert [function.name for function in result] == ["birinci", "ikinci"]


def test_ignores_nested_function_and_its_return() -> None:
    source_code = """
def outer():
    def inner():
        return 5
"""

    result = analyze_source(source_code)

    assert [function.name for function in result] == ["outer"]
    assert result[0].has_return is False


def test_invalid_source_raises_syntax_error() -> None:
    source_code = "def broken(:\n    pass"

    with pytest.raises(SyntaxError):
        analyze_source(source_code)


def test_extracts_exception_from_if_block() -> None:
    source_code = """
def bol(a, b):
    if b == 0:
        raise ValueError("Sıfıra bölünemez")
    return a / b
"""

    result = analyze_source(source_code)

    assert result[0].exceptions == [
        ExceptionInfo(
            type="ValueError",
            condition="b == 0",
            message="Sıfıra bölünemez",
        )
    ]


def test_extracts_unconditional_exception() -> None:
    source_code = """
def fail():
    raise RuntimeError("Hata")
"""

    result = analyze_source(source_code)

    assert result[0].exceptions == [
        ExceptionInfo(type="RuntimeError", condition=None, message="Hata")
    ]


def test_dynamic_exception_message_is_none() -> None:
    source_code = """
def fail(message):
    raise ValueError(message)
"""

    result = analyze_source(source_code)

    assert result[0].exceptions[0].message is None


def test_preserves_source_order_for_multiple_exceptions() -> None:
    source_code = """
def kontrol(x):
    if x < 0:
        raise ValueError("Negatif")
    if x == 0:
        raise RuntimeError("Sıfır")
"""

    result = analyze_source(source_code)

    assert result[0].exceptions == [
        ExceptionInfo(type="ValueError", condition="x < 0", message="Negatif"),
        ExceptionInfo(type="RuntimeError", condition="x == 0", message="Sıfır"),
    ]


def test_ignores_exception_in_nested_function() -> None:
    source_code = """
def outer():
    def inner():
        raise ValueError("inner")
"""

    result = analyze_source(source_code)

    assert result[0].exceptions == []


def test_extracts_simple_less_than_condition() -> None:
    source_code = """
def kontrol(age):
    if age < 18:
        return False
    return True
"""

    result = analyze_source(source_code)

    assert result[0].conditions == [
        ConditionInfo(left="age", operator="<", right=18)
    ]


@pytest.mark.parametrize(
    ("source_operator", "expected_operator"),
    [("<", "<"), ("<=", "<="), (">", ">"), (">=", ">=")],
)
def test_extracts_supported_comparison_operators(
    source_operator: str,
    expected_operator: str,
) -> None:
    source_code = f"""
def kontrol(value):
    if value {source_operator} 10:
        return True
"""

    result = analyze_source(source_code)

    assert result[0].conditions == [
        ConditionInfo(left="value", operator=expected_operator, right=10)
    ]


def test_extracts_float_boundary() -> None:
    source_code = """
def kontrol(price):
    if price >= 3.5:
        return True
"""

    result = analyze_source(source_code)

    assert result[0].conditions == [
        ConditionInfo(left="price", operator=">=", right=3.5)
    ]


def test_preserves_condition_source_order() -> None:
    source_code = """
def kontrol(x):
    if x < 0:
        return -1
    if x >= 100:
        return 1
    return 0
"""

    result = analyze_source(source_code)

    assert result[0].conditions == [
        ConditionInfo(left="x", operator="<", right=0),
        ConditionInfo(left="x", operator=">=", right=100),
    ]


def test_ignores_equality_condition() -> None:
    source_code = """
def kontrol(age):
    if age == 18:
        return True
"""

    assert analyze_source(source_code)[0].conditions == []


def test_ignores_condition_with_variable_right_side() -> None:
    source_code = """
def kontrol(age, limit):
    if age < limit:
        return True
"""

    assert analyze_source(source_code)[0].conditions == []


def test_ignores_reversed_comparison() -> None:
    source_code = """
def kontrol(age):
    if 18 < age:
        return True
"""

    assert analyze_source(source_code)[0].conditions == []


def test_does_not_treat_bool_as_numeric_constant() -> None:
    source_code = """
def kontrol(value):
    if value < True:
        return True
"""

    assert analyze_source(source_code)[0].conditions == []


def test_ignores_condition_in_nested_function() -> None:
    source_code = """
def outer():
    def inner(age):
        if age < 18:
            return False
"""

    assert analyze_source(source_code)[0].conditions == []


def test_extracts_condition_and_exception_from_same_if() -> None:
    source_code = """
def bol(a, b):
    if b < 1:
        raise ValueError("Geçersiz")
    return a / b
"""

    result = analyze_source(source_code)[0]

    assert result.conditions == [ConditionInfo(left="b", operator="<", right=1)]
    assert result.exceptions == [
        ExceptionInfo(
            type="ValueError",
            condition="b < 1",
            message="Geçersiz",
        )
    ]
