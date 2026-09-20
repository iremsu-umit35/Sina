"""Python kaynak kodunun statik analizinden sorumlu modül."""

import ast
from dataclasses import dataclass


@dataclass
class ExceptionInfo:
    type: str
    condition: str | None
    message: str | None


@dataclass
class ConditionInfo:
    left: str
    operator: str
    right: int | float


@dataclass
class FunctionInfo:
    name: str
    parameters: list[str]
    has_return: bool
    exceptions: list[ExceptionInfo]
    conditions: list[ConditionInfo]


_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
_TRY_SCOPES = (ast.Try, getattr(ast, "TryStar", ast.Try))
_COMPARISON_OPERATORS = {
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}


def _has_return(function_node: ast.FunctionDef) -> bool:
    """Fonksiyonun kendi kapsamında bir return ifadesi olup olmadığını bul."""

    def contains_return(node: ast.AST) -> bool:
        if isinstance(node, ast.Return):
            return True
        if isinstance(node, _NESTED_SCOPES):
            return False
        return any(contains_return(child) for child in ast.iter_child_nodes(node))

    return any(contains_return(statement) for statement in function_node.body)


def _condition_from_compare(compare: ast.Compare) -> ConditionInfo | None:
    if len(compare.ops) != 1 or len(compare.comparators) != 1:
        return None
    if not isinstance(compare.left, ast.Name):
        return None

    right = compare.comparators[0]
    if not isinstance(right, ast.Constant):
        return None
    if isinstance(right.value, bool) or not isinstance(right.value, (int, float)):
        return None

    operator = _COMPARISON_OPERATORS.get(type(compare.ops[0]))
    if operator is None:
        return None

    return ConditionInfo(
        left=compare.left.id,
        operator=operator,
        right=right.value,
    )


def _extract_conditions(function_node: ast.FunctionDef) -> list[ConditionInfo]:
    """Fonksiyonun kendi kapsamındaki basit sayısal if koşullarını çıkar."""

    conditions: list[ConditionInfo] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, _NESTED_SCOPES):
            return
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare):
                condition = _condition_from_compare(node.test)
                if condition is not None:
                    conditions.append(condition)

            for statement in node.body:
                visit(statement)
            for statement in node.orelse:
                visit(statement)
            return

        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in function_node.body:
        visit(statement)

    return conditions


def _exception_type(raise_node: ast.Raise) -> str | None:
    exception = raise_node.exc
    if not isinstance(exception, ast.Call) or not isinstance(exception.func, ast.Name):
        return None
    return exception.func.id


def _exception_message(raise_node: ast.Raise) -> str | None:
    exception = raise_node.exc
    if not isinstance(exception, ast.Call) or not exception.args:
        return None

    message = exception.args[0]
    if isinstance(message, ast.Constant) and isinstance(message.value, str):
        return message.value
    return None


def _extract_exceptions(function_node: ast.FunctionDef) -> list[ExceptionInfo]:
    """Fonksiyonun kendi kapsamındaki temel raise ifadelerini çıkar."""

    exceptions: list[ExceptionInfo] = []

    def visit(node: ast.AST, condition: str | None = None) -> None:
        if isinstance(node, _NESTED_SCOPES):
            return
        if isinstance(node, _TRY_SCOPES):
            return
        if isinstance(node, ast.Raise):
            exception_type = _exception_type(node)
            if exception_type is not None and node.cause is None:
                exceptions.append(
                    ExceptionInfo(
                        type=exception_type,
                        condition=condition,
                        message=_exception_message(node),
                    )
                )
            return
        if isinstance(node, ast.If):
            direct_condition = ast.unparse(node.test)
            for statement in node.body:
                visit(statement, direct_condition)
            for statement in node.orelse:
                visit(statement)
            return

        for child in ast.iter_child_nodes(node):
            visit(child, condition)

    for statement in function_node.body:
        visit(statement)

    return exceptions


def analyze_source(source_code: str) -> list[FunctionInfo]:
    """Kaynak koddaki top-level fonksiyonları analiz et."""

    module = ast.parse(source_code)
    functions: list[FunctionInfo] = []

    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        functions.append(
            FunctionInfo(
                name=node.name,
                parameters=[argument.arg for argument in node.args.args],
                has_return=_has_return(node),
                exceptions=_extract_exceptions(node),
                conditions=_extract_conditions(node),
            )
        )

    return functions
