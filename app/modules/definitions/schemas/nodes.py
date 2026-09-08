from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.definitions.output_fields import collect_input_field_ids, collect_output_field_ids


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


class TableConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    headerFields: list[FormField] = Field(default_factory=list)
    columns: list[FormField] = Field(default_factory=list)
    crossFieldConstraints: list[CrossFieldConstraint] = Field(default_factory=list)
    minRows: int | None = None
    maxRows: int | None = None
    defaultRows: int | None = None


class TableAggregation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    columnId: str
    operation: Literal["sum", "min", "max", "avg", "count"]


class ConfigTableDataSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    collection: str


class ConfigTableQueryInput(BaseModel):
    """Full Synapse field used as a runtime query parameter.

    Filter binding preferably lives in ``queryFilters``. ``filterField`` /
    ``filterOperator`` remain for backward compatibility with older clients and
    may be empty when filters are declared separately.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    type: str = "text"
    label: str
    placeholder: str | None = None
    readOnly: bool = False
    defaultValue: Any = None
    validation: list[ValidationRule] = Field(default_factory=list)
    filterField: str = ""
    filterOperator: str = "eq"


class ConfigTableQueryFilter(BaseModel):
    """Synapse-style catalog filter bound to a query input or static value."""

    model_config = ConfigDict(extra="allow")

    filterField: str = ""
    filterOperator: str = "eq"
    fieldId: str | None = None
    staticValue: str | None = None


class ConfigTableColumnMapping(BaseModel):
    model_config = ConfigDict(extra="allow")

    dbField: str
    field: FormField


class ConfigTableConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    dataSource: ConfigTableDataSource
    queryInputs: list[ConfigTableQueryInput] = Field(default_factory=list)
    queryFilters: list[ConfigTableQueryFilter] = Field(default_factory=list)
    columnMappings: list[ConfigTableColumnMapping] = Field(default_factory=list)
    extraColumns: list[FormField] = Field(default_factory=list)
    crossFieldConstraints: list[CrossFieldConstraint] = Field(default_factory=list)
    allowEditFetchedRows: bool = False
    allowAddRows: bool = True
    allowDeleteRows: bool = True
    minRows: int | None = None
    maxRows: int | None = None


class NodeDefinitionJson(BaseModel):
    """JSON blob stored in node_definition_versions.definition_json."""

    model_config = ConfigDict(extra="allow")

    baseKind: Literal["userInput", "table", "configTable", "ai", "script"]
    appearance: AppearanceConfig
    description: str | None = None
    output: DeclaredOutput | None = None
    form: FormConfig | None = None
    table: TableConfig | None = None
    configTable: ConfigTableConfig | None = None
    aggregations: list[TableAggregation] | None = None


class NodeDefinitionIngest(BaseModel):
    """Full publish payload from the React Flow frontend."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    slug: str
    status: str
    version: str | int
    baseKind: Literal["userInput", "table", "configTable", "ai", "script"]
    appearance: AppearanceConfig
    description: str | None = None
    output: DeclaredOutput | None = None
    form: FormConfig | None = None
    table: TableConfig | None = None
    configTable: ConfigTableConfig | None = None
    aggregations: list[TableAggregation] | None = None

    def to_stored_json(self) -> dict:
        payload: dict = NodeDefinitionJson(
            baseKind=self.baseKind,
            appearance=self.appearance,
            description=self.description,
            output=self.output,
            form=self.form,
            table=self.table,
            configTable=self.configTable,
            aggregations=self.aggregations,
        ).model_dump(exclude_none=True)
        if self.baseKind == "userInput" and "form" not in payload:
            payload["form"] = FormConfig().model_dump()
        if self.baseKind == "table" and "table" not in payload:
            payload["table"] = TableConfig().model_dump()
        if self.baseKind == "table" and "aggregations" not in payload:
            payload["aggregations"] = []
        if self.baseKind == "configTable" and "configTable" not in payload:
            payload["configTable"] = ConfigTableConfig(
                dataSource=ConfigTableDataSource(collection="")
            ).model_dump()
        if self.baseKind == "configTable" and "aggregations" not in payload:
            payload["aggregations"] = []
        return payload

    def output_field_ids(self) -> set[str]:
        return collect_output_field_ids(self.to_stored_json())

    def input_field_ids(self) -> set[str]:
        return collect_input_field_ids(self.to_stored_json())
