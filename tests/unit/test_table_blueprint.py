from app.domain.validation.table_blueprint import validate_table_blueprint

DRAFT_TABLE = {
    "columns": [],
    "outputKey": "rows",
    "minRows": 1,
}

PUBLISHED_TABLE = {
    "columns": [
        {
            "id": "partNo",
            "type": "text",
            "label": "Part number",
            "validation": [{"rule": "required", "message": "required"}],
        }
    ],
    "outputKey": "childParts",
    "minRows": 1,
}


def test_draft_table_allows_empty_columns():
    assert validate_table_blueprint(DRAFT_TABLE, strict=False) == []


def test_published_table_rejects_empty_columns():
    issues = validate_table_blueprint(DRAFT_TABLE, strict=True)
    assert any(issue.code == "MISSING_TABLE_COLUMNS" for issue in issues)


def test_published_table_accepts_valid_columns():
    assert validate_table_blueprint(PUBLISHED_TABLE, strict=True) == []
