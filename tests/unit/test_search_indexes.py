from app.infrastructure.persistence.indexes import (
    AlembicIndexMigrator,
    IndexSpec,
    SearchListIndexCatalog,
)


def test_search_list_index_catalog_has_expected_indexes() -> None:
    catalog = SearchListIndexCatalog()
    specs = catalog.list_index_specs()
    names = {spec.name for spec in specs}

    assert "ix_workflow_node_executions_instance_started" in names
    assert "ix_workflow_node_projections_instance_id" in names
    assert "ix_workflow_instances_created_at" in names
    assert "ix_workflow_instances_status_created" in names
    assert "ix_workflow_instances_definition_id" in names
    assert "ix_workflow_instances_definition_version_id" in names
    assert "ix_workflow_events_instance_type_seq" in names
    assert all(isinstance(spec, IndexSpec) for spec in specs)
    assert len(specs) == 7


def test_alembic_index_migrator_binds_catalog() -> None:
    catalog = SearchListIndexCatalog()
    migrator = AlembicIndexMigrator(catalog=catalog)
    assert migrator.list_index_specs() == catalog.list_index_specs()
