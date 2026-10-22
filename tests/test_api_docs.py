import re

import pytest

from app.api_docs import TAGS_METADATA
from app.main import app

FRAMEWORK_SCHEMAS = {"HTTPValidationError", "ValidationError"}


@pytest.fixture(scope="module")
def schema():
    return app.openapi()


def _operations(schema):
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            yield method.upper(), path, operation


def test_only_the_api_and_health_are_documented(schema):
    unexpected = [path for path in schema["paths"] if not path.startswith("/api/v1") and path != "/health"]

    assert unexpected == [], "las páginas HTML no deben aparecer en /docs"


def test_every_operation_has_a_summary_and_a_description(schema):
    for method, path, operation in _operations(schema):
        default_summary = operation["operationId"].replace("_", " ").title()
        assert operation.get("summary") not in (None, "", default_summary), f"{method} {path}: falta summary"
        assert operation.get("description"), f"{method} {path}: falta description"


def test_every_operation_belongs_to_one_documented_tag(schema):
    declared = {tag["name"] for tag in TAGS_METADATA}
    assert all(tag["description"] for tag in TAGS_METADATA)

    for method, path, operation in _operations(schema):
        assert len(operation.get("tags", [])) == 1, f"{method} {path}: debe tener exactamente un grupo"
        assert operation["tags"][0] in declared, f"{method} {path}: grupo sin declarar en TAGS_METADATA"


def test_protected_operations_document_the_401_response(schema):
    for method, path, operation in _operations(schema):
        if operation.get("security"):
            assert "401" in operation["responses"], f"{method} {path}: requiere token pero no documenta el 401"


def test_operations_with_a_path_parameter_document_the_404_response(schema):
    for method, path, operation in _operations(schema):
        if "{" in path:
            assert "404" in operation["responses"], f"{method} {path}: no documenta el 404"


def test_documented_error_responses_use_the_error_schema(schema):
    for method, path, operation in _operations(schema):
        for code, response in operation["responses"].items():
            if code in {"400", "401", "404", "409"}:
                ref = response["content"]["application/json"]["schema"]["$ref"]
                assert ref.endswith("/ErrorResponse"), f"{method} {path} {code}"


def test_every_schema_field_has_a_description(schema):
    undocumented = [
        f"{name}.{field}"
        for name, definition in schema["components"]["schemas"].items()
        if name not in FRAMEWORK_SCHEMAS
        for field, spec in definition.get("properties", {}).items()
        if not (spec.get("description") or any("description" in option for option in spec.get("anyOf", [])))
    ]

    assert undocumented == []


def test_every_enum_explains_its_values(schema):
    undocumented = [
        name
        for name, definition in schema["components"]["schemas"].items()
        if "enum" in definition and not definition.get("description")
    ]

    assert undocumented == []


def test_operation_ids_are_clean_and_unique(schema):
    ids = [operation["operationId"] for _, _, operation in _operations(schema)]

    assert len(ids) == len(set(ids))
    assert not [i for i in ids if re.search(r"api_v1|_get$|_post$|_patch$", i)]


def test_title_description_and_version_are_set(schema):
    from app.version import __version__

    assert schema["info"]["version"] == __version__
    assert "Autenticación" in schema["info"]["description"]
