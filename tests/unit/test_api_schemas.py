from app.api.schemas import ApiErrorBody, ApiErrorResponse


def test_api_error_response_schema():
    payload = ApiErrorResponse(
        error=ApiErrorBody(
            code="NOT_FOUND",
            message="Resource not found",
            details=[{"field": "id"}],
            request_id="req-123",
        )
    )
    body = payload.model_dump()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"] == "req-123"
