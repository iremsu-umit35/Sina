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


def validate_generated_tests(generated_text: str) -> str:
    """AI tarafından üretilen pytest metnini temizle ve statik olarak doğrula."""

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

    return cleaned_code
