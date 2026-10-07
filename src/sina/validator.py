"""Üretilen pytest kodunu doğrulayacak modül."""

import ast


_DISALLOWED_CALLS = {
    "exec",
    "eval",
    "compile",
    "os.system",
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "subprocess.check_call",
    "subprocess.check_output",
}


def _strip_code_fence(generated_text: str) -> str:
    stripped_text = generated_text.strip()
    lines = stripped_text.splitlines()

    if (
        len(lines) >= 2
        and lines[0].strip().lower() in {"```", "```python"}
        and lines[-1].strip() == "```"
    ):
        return "\n".join(lines[1:-1]).strip()

    return generated_text


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        return f"{call.func.value.id}.{call.func.attr}"
    return None


def _validate_required_imports(
    tree: ast.Module,
    target_module: str,
    expected_functions: list[str],
) -> None:
    imported_from_target: set[str] = set()
    imported_from_other_modules: set[str] = set()
    expected_names = set(expected_functions)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        imported_names = {
            alias.name
            for alias in node.names
            if alias.name != "*" and alias.name in expected_names
        }
        if node.level == 0 and node.module == target_module:
            imported_from_target.update(imported_names)
        else:
            imported_from_other_modules.update(imported_names)

    wrong_module = [
        name
        for name in expected_functions
        if name in imported_from_other_modules and name not in imported_from_target
    ]
    if wrong_module:
        raise RuntimeError(
            "Generated test code imports expected functions from the wrong module: "
            + ", ".join(dict.fromkeys(wrong_module))
        )

    missing = [
        name for name in expected_functions if name not in imported_from_target
    ]
    if missing:
        raise RuntimeError(
            "Generated test code is missing required imports: "
            + ", ".join(dict.fromkeys(missing))
        )


def validate_generated_tests(
    generated_text: str,
    target_module: str,
    expected_functions: list[str],
) -> str:
    """AI tarafından üretilen pytest metnini temizle ve statik olarak doğrula."""

    if not target_module.strip():
        raise ValueError("target_module must not be empty.")
    if not expected_functions:
        raise ValueError("expected_functions must not be empty.")
    if any(not name.strip() for name in expected_functions):
        raise ValueError("expected_functions must not contain empty names.")

    cleaned_code = _strip_code_fence(generated_text)
    if not cleaned_code.strip():
        raise RuntimeError("Generated test code is empty.")

    try:
        tree = ast.parse(cleaned_code)
    except SyntaxError as exc:
        raise RuntimeError("Generated test code is not valid Python.") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node)
            if call_name in _DISALLOWED_CALLS:
                raise RuntimeError(
                    f"Generated test code contains a disallowed call: {call_name}"
                )

    has_test_function = any(
        isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        for node in tree.body
    )
    if not has_test_function:
        raise RuntimeError("Generated code does not contain a pytest test function.")

    _validate_required_imports(tree, target_module, expected_functions)

    return cleaned_code
