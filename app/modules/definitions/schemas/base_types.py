from pydantic import BaseModel, ConfigDict, Field


class BaseTypeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        ser_json_by_alias=True,
    )

    id: str
    kind: str
    display_name: str = Field(serialization_alias="displayName")
    description: str
    enabled: bool
    version: str
