from __future__ import annotations

import ast
import operator
from typing import Any

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


class FormulaError(ValueError):
    pass


def evaluate_formula(formula: str, variables: dict[str, Any]) -> float:
    """Safely evaluate a restricted arithmetic expression. No eval()."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Invalid formula syntax: {formula}") from exc

    result = _evaluate_node(tree.body, variables)
    return float(result)


def _evaluate_node(node: ast.AST, variables: dict[str, Any]) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise FormulaError(f"Unknown variable: {node.id}")
        value = variables[node.id]
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise FormulaError(f"Variable not set: {node.id}")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise FormulaError(f"Variable is not numeric: {node.id}") from exc

    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)
        if operator_type not in _OPERATORS:
            raise FormulaError(f"Unsupported operator: {operator_type.__name__}")
        left = _evaluate_node(node.left, variables)
        right = _evaluate_node(node.right, variables)
        return float(_OPERATORS[operator_type](left, right))

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate_node(node.operand, variables)

    raise FormulaError(f"Unsupported expression node: {type(node).__name__}")
