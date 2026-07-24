"""Controller Protocols (one interface per file)."""

from app.api.controllers.interfaces.backup_controller import BackupController
from app.api.controllers.interfaces.definition_command_controller import (
    DefinitionCommandController,
)
from app.api.controllers.interfaces.definition_query_controller import (
    DefinitionQueryController,
)
from app.api.controllers.interfaces.definition_response_mapper import (
    DefinitionResponseMapper,
)
from app.api.controllers.interfaces.instance_command_controller import (
    InstanceCommandController,
)
from app.api.controllers.interfaces.instance_query_controller import (
    InstanceQueryController,
)
from app.api.controllers.interfaces.instance_response_mapper import (
    InstanceResponseMapper,
)

__all__ = [
    "BackupController",
    "DefinitionCommandController",
    "DefinitionQueryController",
    "DefinitionResponseMapper",
    "InstanceCommandController",
    "InstanceQueryController",
    "InstanceResponseMapper",
]
