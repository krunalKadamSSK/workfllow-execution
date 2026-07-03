from app.domain.executors.table_input import TableExecutor
from app.domain.ports.executors import ExecutionContext
from app.modules.executions.schemas import PendingNodeFormResponse


def test_pending_node_form_response_preserves_table_payload():
  raw = {
      "task_name": "tabletask1",
      "formKind": "table",
      "table": {
          "headerFields": [],
          "columns": [
              {"id": "part_name", "type": "select", "label": "Part Name"},
              {"id": "raw_weight", "type": "number", "label": "Raw Weight"},
          ],
          "initialRows": [{"part_name": "", "raw_weight": ""}],
          "lockedKeys": [],
          "columnDefaults": {},
          "minRows": 1,
          "defaultRows": 1,
      },
  }

  model = PendingNodeFormResponse(**raw)
  dumped = model.model_dump()

  assert dumped["formKind"] == "table"
  assert dumped["table"]["columns"][0]["id"] == "part_name"
  assert dumped["task_name"] == "tabletask1"


def test_table_executor_prepare_pending_node_form_includes_columns():
  executor = TableExecutor()
  context = ExecutionContext(
      workflow_instance_id="inst-1",
      workflow_node_instance_id="node-inst-1",
      workflow_node_id="node-1",
      node_definition_version_id="ver-1",
      base_kind="table",
      definition_json={
          "baseKind": "table",
          "table": {
              "columns": [
                  {"id": "part_name", "type": "select", "label": "Part Name"},
              ],
              "minRows": 1,
              "defaultRows": 1,
          },
      },
      resolved_inputs={},
      locked_input_keys=[],
  )

  payload = executor.prepare_pending_node_form(context)

  assert payload["formKind"] == "table"
  assert payload["aggregations"] == []
  assert len(payload["table"]["columns"]) == 1
  assert payload["table"]["initialRows"] == [{"part_name": ""}]

  response = PendingNodeFormResponse(task_name="tabletask1", **payload)
  serialized = response.model_dump()
  assert serialized["formKind"] == "table"
  assert serialized["table"]["columns"][0]["id"] == "part_name"
