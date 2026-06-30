from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.definitions.output_fields import collect_output_field_ids


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


class FormMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    formId: str
    version: str


class ValidationRule(BaseModel):
    model_config = ConfigDict(extra="allow")

    rule: str
    message: str | None = None
    value: Any = None


class SelectOption(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    value: str | int | float


class RemoteOptions(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    resultPath: str | None = None
    labelKey: str = "label"
    valueKey: str = "value"
    queryParam: str | None = None
    debounceMs: int | None = None
    minChars: int | None = None
    requires: list[str] = Field(default_factory=list)


class RemoteSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    resultPath: str
    requires: list[str] = Field(default_factory=list)


class Calculation(BaseModel):
    model_config = ConfigDict(extra="allow")

    formula: str

    @field_validator("formula")
    @classmethod
    def formula_max_length(cls, value: str) -> str:
        if len(value) > 500:
            raise ValueError("formula must be at most 500 characters")
        return value


class FieldUiBehavior(BaseModel):
    model_config = ConfigDict(extra="allow")

    closeOnOutsideClick: bool | None = None


class CrossFieldConstraint(BaseModel):
    model_config = ConfigDict(extra="allow")

    logic: str
    target: str
    message: str


class DeclaredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class FormField(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    label: str
    placeholder: str | None = None
    options: list[SelectOption] | None = None
    remoteOptions: RemoteOptions | None = None
    remoteSource: RemoteSource | None = None
    calculation: Calculation | None = None
    readOnly: bool = False
    defaultValue: Any = None
    validation: list[ValidationRule] = Field(default_factory=list)
    ui: FieldUiBehavior | None = None


class FormConfig(BaseModel):
    """Synapse NodeFormConfig — fields plus optional cross-field constraints."""

    model_config = ConfigDict(extra="allow")

    formMeta: FormMeta | None = None
    fields: list[FormField] = Field(default_factory=list)
    crossFieldConstraints: list[CrossFieldConstraint] = Field(default_factory=list)


class TableSummaryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columnId: str
    outputKey: str
    label: str | None = None


class TableConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    columns: list[FormField]
    outputKey: str
    summary: TableSummaryConfig | None = None
    minRows: int = 1
    crossFieldConstraints: list[CrossFieldConstraint] = Field(default_factory=list)


class NodeDefinitionJson(BaseModel):
    """JSON blob stored in node_definition_versions.definition_json."""

    model_config = ConfigDict(extra="allow")

    baseKind: Literal["userInput", "ai", "script", "table"]
    appearance: AppearanceConfig
    description: str | None = None
    output: DeclaredOutput | None = None
    form: FormConfig | None = None
    table: TableConfig | None = None


class NodeDefinitionIngest(BaseModel):
    """Full publish payload from the React Flow frontend."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    slug: str
    status: str
    version: str | int
    baseKind: Literal["userInput", "ai", "script", "table"]
    appearance: AppearanceConfig
    description: str | None = None
    output: DeclaredOutput | None = None
    form: FormConfig | None = None
    table: TableConfig | None = None

    def to_stored_json(self) -> dict:
        if self.baseKind == "table":
            if self.table is None:
                raise ValueError("table baseKind requires a table configuration block")
            payload: dict = {
                "baseKind": self.baseKind,
                "appearance": self.appearance.model_dump(),
                "table": self.table.model_dump(),
            }
            if self.description is not None:
                payload["description"] = self.description
            return payload

        stored = NodeDefinitionJson(
            baseKind=self.baseKind,
            appearance=self.appearance,
            description=self.description,
            output=self.output,
            form=self.form,
        ).model_dump(exclude_none=True)
        if self.baseKind == "userInput" and "form" not in stored:
            stored["form"] = FormConfig().model_dump()
        return stored

    def output_field_ids(self) -> set[str]:
        return collect_output_field_ids(self.to_stored_json())
