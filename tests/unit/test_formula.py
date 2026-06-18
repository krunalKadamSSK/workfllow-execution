import pytest

from app.domain.executors.formula import FormulaError, evaluate_formula


def test_evaluate_simple_addition():
    result = evaluate_formula(
        "meltLossPercentage+rawWeight",
        {"meltLossPercentage": 3, "rawWeight": 10},
    )
    assert result == 13


def test_evaluate_with_spaces():
    assert evaluate_formula("a + b", {"a": 2, "b": 3}) == 5


def test_unknown_variable_raises():
    with pytest.raises(FormulaError, match="Unknown variable"):
        evaluate_formula("missing+1", {})


def test_unset_variable_raises():
    with pytest.raises(FormulaError, match="Variable not set"):
        evaluate_formula("a+1", {"a": None})


def test_unsupported_syntax_raises():
    with pytest.raises(FormulaError):
        evaluate_formula("__import__('os').system('x')", {})
