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


class InvalidTransitionError(WorkflowEngineError):
    code = "INVALID_TRANSITION"


class NodeExecutionError(WorkflowEngineError):
    code = "NODE_EXECUTION_ERROR"


class InputResolutionError(WorkflowEngineError):
    code = "INPUT_RESOLUTION_ERROR"


class FieldValidationError(WorkflowEngineError):
    code = "FIELD_VALIDATION_FAILED"

    def __init__(self, message: str, *, field_errors: list | None = None):
        super().__init__(message, details=field_errors or [])


class UpstreamNotReadyError(WorkflowEngineError):
    code = "UPSTREAM_NOT_READY"
