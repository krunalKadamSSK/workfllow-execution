from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IconConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["lucide"]
    name: str


class ColorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["token"]
    value: str


class AppearanceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icon: IconConfig
    color: ColorConfig
    shape: Literal["card"]
    badge: str


class ValidationRule(BaseModel):
    model_config = ConfigDict(extra="allow")

    rule: Literal["required", "min", "max", "pattern"]
    message: str | None = None
    value: Any = None


class SelectOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class RemoteOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    labelKey: str
    valueKey: str


class RemoteSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    resultPath: str


class Calculation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula: str


class FormField(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: Literal["text", "number", "select"]
    label: str
    placeholder: str | None = None
    options: list[SelectOption] | None = None
    remoteOptions: RemoteOptions | None = None
    remoteSource: RemoteSource | None = None
    calculation: Calculation | None = None
    readOnly: bool = False
    validation: list[ValidationRule] = Field(default_factory=list)


class FormConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[FormField]


class NodeDefinitionJson(BaseModel):
    """JSON blob stored in node_definition_versions.definition_json."""

    model_config = ConfigDict(extra="forbid")

    baseKind: Literal["userInput"]
    appearance: AppearanceConfig
    description: str | None = None
    form: FormConfig


class NodeDefinitionIngest(BaseModel):
    """Full publish payload from the React Flow frontend."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    slug: str
    status: str
    version: str | int
    baseKind: Literal["userInput"]
    appearance: AppearanceConfig
    description: str | None = None
    form: FormConfig

    def to_stored_json(self) -> dict:
        return NodeDefinitionJson(
            baseKind=self.baseKind,
            appearance=self.appearance,
            description=self.description,
            form=self.form,
        ).model_dump()

    def output_field_ids(self) -> set[str]:
        return {field.id for field in self.form.fields}
