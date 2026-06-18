class WorkflowEngineError(Exception):
    """Base error for workflow engine domain and persistence layers."""

    code: str = "WORKFLOW_ENGINE_ERROR"

    def __init__(self, message: str, *, details: list | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(WorkflowEngineError):
    code = "NOT_FOUND"


class DuplicateSlugError(WorkflowEngineError):
    code = "DUPLICATE_SLUG"


class VersionConflictError(WorkflowEngineError):
    code = "VERSION_CONFLICT"


class SequenceConflictError(WorkflowEngineError):
    code = "SEQUENCE_CONFLICT"


class ValidationError(WorkflowEngineError):
    code = "VALIDATION_ERROR"
