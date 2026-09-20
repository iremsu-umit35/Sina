"""Sına'nın mevcut akışını gerçek Gemini ile manuel olarak doğrula."""

from sina.analyzer import analyze_source
from sina.generator import generate_tests
from sina.scenarios import generate_scenarios


SOURCE_CODE = """\
def bol(a, b):
    if b < 1:
        raise ValueError("Geçersiz bölen")
    return a / b
"""


def main() -> None:
    functions = analyze_source(SOURCE_CODE)
    scenarios = [
        scenario
        for function in functions
        for scenario in generate_scenarios(function)
    ]
    generated_tests = generate_tests(
        SOURCE_CODE,
        functions,
        scenarios,
        target_module="calculator",
    )

    print("Analyzer output:")
    for function in functions:
        print(f"- {function}")

    print("\nScenario output:")
    for scenario in scenarios:
        print(f"- {scenario}")

    print("\nFinal generated pytest code:\n")
    print(generated_tests)


if __name__ == "__main__":
    main()
