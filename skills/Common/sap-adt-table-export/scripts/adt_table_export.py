"""Strictly read-only, bounded SAP ADT Data Preview export runtime."""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import fnmatch
import hashlib
import json
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import quote, urlparse


SKILL_ID = "sap-adt-table-export"
SCHEMA_VERSION = 1
SKILL_ROOT = Path(__file__).resolve().parents[1]
INTERNAL_ENV_FILE = SKILL_ROOT / ".env"
INTERNAL_PROFILES_SETTING = "SAP_ADT_PROFILES_FILE"
MINIMUM_DEPENDENCIES = {"requests": "2.31.0"}
TESTED_DEPENDENCIES = {"requests": "2.34.2"}
ENDPOINT = "/sap/bc/adt/datapreview/freestyle"
TABLE_METADATA_PREFIX = "/sap/bc/adt/ddic/tables/"
STRUCTURE_METADATA_PREFIX = "/sap/bc/adt/ddic/structures/"
CDS_METADATA_PREFIX = "/sap/bc/adt/ddic/ddl/sources/"
DATA_ELEMENT_PREFIX = "/sap/bc/adt/ddic/dataelements/"
ACCEPT = "application/vnd.sap.adt.datapreview.table.v1+xml"
DATA_ELEMENT_ACCEPT = "application/vnd.sap.adt.dataelements.v2+xml"
OBJECT_IDENTIFIER = re.compile(r"^(?=.{1,60}$)(?:[A-Z][A-Z0-9_]*|/[A-Z0-9_]+/[A-Z0-9_/]+)$")
FIELD_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]{0,59}$")
PROFILE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
ALLOWED_TOP_LEVEL = {
    "schema_version",
    "source_type",
    "object",
    "fields",
    "filters",
    "order_by",
    "max_rows",
}
FORBIDDEN_INPUT_KEYS = {
    "connection_profile",
    "profile",
    "profiles",
    "default_profile",
    "url",
    "host",
    "hostname",
    "password",
    "passwd",
    "token",
    "secret",
    "username",
    "user",
    "client",
    "verify_ssl",
    "tls_verify",
    "ca_bundle",
    "sql",
    "query",
    "endpoint",
    "method",
}
ALLOWED_SOURCE_TYPES = {"table", "cds"}
ALLOWED_FILTER_OPTIONS = {"EQ", "NE", "GT", "GE", "LT", "LE", "BT", "IN"}
ALLOWED_FIELD_TYPES = {"string", "integer", "decimal", "date", "time", "boolean"}
MAX_EXPORT_ROWS = 30000
MAX_PREVIEW_PAGE_SIZE = 10000
MAX_INCLUDE_DEPTH = 8
WRITE_TOKENS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "MODIFY",
    "TRUNCATE",
    "DROP",
    "ALTER",
    "CREATE",
    "CALL",
    "EXEC",
    "PROCEDURE",
    "COMMIT",
    "ROLLBACK",
}


class ExportError(Exception):
    """A closed-set, user-facing runtime failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FieldSpec:
    type: str
    sensitive: bool = False


@dataclass(frozen=True)
class ObjectSpec:
    source_type: str
    name: str
    fields: Mapping[str, FieldSpec]
    stable_key: tuple[str, ...]
    bounded_filter_fields: frozenset[str]
    max_rows: int
    page_size: int
    contiguous_key: bool = False


@dataclass(frozen=True)
class Connection:
    base_url: str
    username: str
    password: str
    client: str
    language: str
    verify: bool | str
    system_id: str
    timeout_seconds: int


@dataclass(frozen=True)
class Filter:
    field: str
    option: str
    values: tuple[Any, ...]
    sign: str = "I"


@dataclass(frozen=True)
class PreparedRequest:
    source_type: str
    object_name: str
    fields: tuple[str, ...]
    filters: tuple[Filter, ...]
    order_by: tuple[tuple[str, str], ...]
    max_rows: int
    object_spec: ObjectSpec
    connection: Connection


@dataclass(frozen=True)
class PreviewResult:
    columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class ProfileSpec:
    connection: Connection
    objects: Mapping[str, ObjectSpec]
    dynamic_objects: bool
    max_rows: int
    page_size: int
    deny_object_patterns: tuple[str, ...]
    deny_field_patterns: tuple[str, ...]


@dataclass(frozen=True)
class LiveMetadata:
    fields: Mapping[str, FieldSpec]
    stable_key: tuple[str, ...]
    type_references: Mapping[str, str]
    include_references: tuple[str, ...] = ()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key).lower()
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def _read_json(
    path: Path,
    code: str = "unsupported_system",
    *,
    expose_path: bool = False,
) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        message = f"Cannot read valid JSON from {path}: {exc}" if expose_path else "Internal ADT configuration is unavailable or invalid."
        raise ExportError(code, message) from exc
    if not isinstance(data, dict):
        message = f"JSON root in {path} must be an object." if expose_path else "Internal ADT configuration is unavailable or invalid."
        raise ExportError(code, message)
    return data


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ExportError("unsupported_system", "Internal ADT configuration is unavailable or invalid.") from exc
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            values[key] = value
    return values


def _require_internal_value(name: str, values: Mapping[str, str]) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ExportError("unsupported_system", "Internal ADT configuration is unavailable or invalid.")
    value = values.get(name, "")
    if not value:
        raise ExportError("unsupported_system", "Internal ADT configuration is unavailable or invalid.")
    return value


def _internal_path(value: str, base_directory: Path) -> Path:
    candidate = Path(value.strip())
    if not value.strip():
        raise ExportError("unsupported_system", "Internal ADT configuration is unavailable or invalid.")
    return candidate if candidate.is_absolute() else base_directory / candidate


def load_internal_configuration(env_path: Path | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    """Load only Skill-owned configuration; never consult the caller's environment."""
    env_path = env_path or INTERNAL_ENV_FILE
    internal_values = _load_env_file(env_path)
    profiles_path = _internal_path(internal_values.get(INTERNAL_PROFILES_SETTING, ""), env_path.parent)
    profiles = _read_json(profiles_path, code="unsupported_system")
    return profiles, internal_values


def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
        return True
    if isinstance(value, str) and value.strip().lower() in {"false", "0", "no"}:
        return False
    raise ExportError("unsupported_system", f"Trusted profile field {field} must be boolean.")


def _compile_field_specs(raw: Any) -> dict[str, FieldSpec]:
    if not isinstance(raw, dict) or not raw:
        raise ExportError("metadata_unavailable", "Trusted object metadata has no fields.")
    result: dict[str, FieldSpec] = {}
    for raw_name, raw_spec in raw.items():
        name = str(raw_name).upper()
        if not FIELD_IDENTIFIER.fullmatch(name):
            raise ExportError("metadata_unavailable", f"Invalid trusted field identifier {raw_name!r}.")
        if isinstance(raw_spec, str):
            type_name = raw_spec.lower()
            sensitive = False
        elif isinstance(raw_spec, dict):
            type_name = str(raw_spec.get("type", "")).lower()
            sensitive = bool(raw_spec.get("sensitive", False))
        else:
            raise ExportError("metadata_unavailable", f"Invalid metadata for field {name}.")
        if type_name not in ALLOWED_FIELD_TYPES:
            raise ExportError("metadata_unavailable", f"Unsupported trusted type {type_name!r} for field {name}.")
        result[name] = FieldSpec(type=type_name, sensitive=sensitive)
    return result


def _resolve_profile(raw_profiles: dict[str, Any], internal_values: Mapping[str, str]) -> ProfileSpec:
    if raw_profiles.get("schema_version") != SCHEMA_VERSION:
        raise ExportError("unsupported_system", "Trusted profiles schema_version must be 1.")
    name = raw_profiles.get("default_profile")
    if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
        raise ExportError("unsupported_system", "Internal default ADT profile is unavailable or invalid.")
    profiles = raw_profiles.get("profiles")
    raw = profiles.get(name) if isinstance(profiles, dict) else None
    if not isinstance(raw, dict) or not raw.get("enabled", True):
        raise ExportError("unsupported_system", "Internal default ADT profile is unavailable or invalid.")
    if raw.get("supported", True) is not True:
        raise ExportError("unsupported_system", "Internal default ADT profile is unavailable or invalid.")

    connection_raw = raw.get("connection")
    if not isinstance(connection_raw, dict):
        raise ExportError("unsupported_system", "Trusted profile connection settings are missing.")
    forbidden_direct = {"base_url", "username", "password", "token", "verify_ssl"}.intersection(connection_raw)
    if forbidden_direct:
        raise ExportError("unsupported_system", "Trusted profiles must reference environment variables, not inline credentials or URLs.")
    env_values = dict(internal_values)
    env_file = raw.get("env_file")
    if env_file:
        env_values.update(_load_env_file(_internal_path(str(env_file), SKILL_ROOT)))

    base_url = _require_internal_value(str(connection_raw.get("base_url_env", "")), env_values).rstrip("/")
    username = _require_internal_value(str(connection_raw.get("username_env", "")), env_values)
    password = _require_internal_value(str(connection_raw.get("password_env", "")), env_values)
    client = _require_internal_value(str(connection_raw.get("client_env", "")), env_values)
    language_env = str(connection_raw.get("language_env", ""))
    language = (env_values.get(language_env) or raw.get("language") or "EN") if language_env else str(raw.get("language", "EN"))
    verify_env = str(connection_raw.get("verify_ssl_env", ""))
    verify_value: Any = env_values.get(verify_env) if verify_env else True
    if not _parse_bool(verify_value, "verify_ssl_env"):
        raise ExportError("tls_validation_failed", "TLS certificate verification cannot be disabled.")
    ca_env = str(connection_raw.get("ca_bundle_env", ""))
    ca_bundle = env_values.get(ca_env) if ca_env else ""
    verify: bool | str = ca_bundle or True

    parsed_url = urlparse(base_url)
    if parsed_url.scheme.lower() != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        raise ExportError("tls_validation_failed", "Trusted ADT base URL must be credential-free HTTPS.")
    if not re.fullmatch(r"\d{3}", client):
        raise ExportError("unsupported_system", "Trusted SAP client must be a three-digit value.")
    timeout_seconds = int(raw.get("timeout_seconds", 30))
    if not 1 <= timeout_seconds <= 300:
        raise ExportError("unsupported_system", "Trusted timeout_seconds must be between 1 and 300.")

    deny_objects = tuple(str(item).upper() for item in raw.get("deny_object_patterns", []))
    deny_fields = tuple(str(item).upper() for item in raw.get("deny_field_patterns", []))
    dynamic_objects = bool(raw.get("dynamic_objects", False))
    profile_max_rows = int(raw.get("max_rows", MAX_EXPORT_ROWS if dynamic_objects else 1000))
    profile_page_size = int(raw.get("page_size", min(profile_max_rows, 200)))
    if not 1 <= profile_page_size <= min(profile_max_rows, MAX_PREVIEW_PAGE_SIZE) or not 1 <= profile_max_rows <= MAX_EXPORT_ROWS:
        raise ExportError("metadata_unavailable", "Invalid profile row policy.")
    raw_objects = raw.get("objects", {})
    if not isinstance(raw_objects, dict) or (not dynamic_objects and not raw_objects):
        raise ExportError("metadata_unavailable", "Trusted profile object allowlist is missing.")
    objects: dict[str, ObjectSpec] = {}
    for raw_key, value in raw_objects.items():
        if not isinstance(value, dict) or ":" not in raw_key:
            raise ExportError("metadata_unavailable", f"Invalid trusted object entry {raw_key!r}.")
        source_type, object_name = raw_key.split(":", 1)
        source_type = source_type.lower()
        object_name = object_name.upper()
        if source_type not in ALLOWED_SOURCE_TYPES or not OBJECT_IDENTIFIER.fullmatch(object_name):
            raise ExportError("metadata_unavailable", f"Invalid trusted object key {raw_key!r}.")
        fields = _compile_field_specs(value.get("fields"))
        stable_key = tuple(str(item).upper() for item in value.get("stable_key", []))
        bounded = frozenset(str(item).upper() for item in value.get("bounded_filter_fields", []))
        if not stable_key or any(item not in fields for item in stable_key):
            raise ExportError("stable_paging_key_unavailable", f"Trusted object {raw_key} has no valid stable key.")
        if not bounded or any(item not in fields for item in bounded):
            raise ExportError("filter_not_allowed", f"Trusted object {raw_key} has no bounded filter policy.")
        max_rows = int(value.get("max_rows", 1000))
        page_size = int(value.get("page_size", min(max_rows, 200)))
        if not 1 <= page_size <= min(max_rows, MAX_PREVIEW_PAGE_SIZE) or not 1 <= max_rows <= MAX_EXPORT_ROWS:
            raise ExportError("metadata_unavailable", f"Invalid row policy for trusted object {raw_key}.")
        objects[f"{source_type}:{object_name}"] = ObjectSpec(
            source_type=source_type,
            name=object_name,
            fields=fields,
            stable_key=stable_key,
            bounded_filter_fields=bounded,
            max_rows=max_rows,
            page_size=page_size,
            contiguous_key=bool(value.get("contiguous_key", False)),
        )

    connection = Connection(
        base_url=base_url,
        username=username,
        password=password,
        client=client,
        language=str(language).upper(),
        verify=verify,
        system_id=str(raw.get("system_id", name)).upper(),
        timeout_seconds=timeout_seconds,
    )
    return ProfileSpec(
        connection=connection,
        objects=objects,
        dynamic_objects=dynamic_objects,
        max_rows=profile_max_rows,
        page_size=profile_page_size,
        deny_object_patterns=deny_objects,
        deny_field_patterns=deny_fields,
    )


def _typed_value(value: Any, field: str, spec: FieldSpec) -> Any:
    kind = spec.type
    if kind == "string":
        if not isinstance(value, str):
            raise ExportError("filter_not_allowed", f"Filter {field} requires a string value.")
        if len(value) > 512 or "\x00" in value:
            raise ExportError("filter_not_allowed", f"Filter {field} contains an invalid string value.")
        return value
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, (int, str)) or not re.fullmatch(r"[+-]?\d+", str(value)):
            raise ExportError("filter_not_allowed", f"Filter {field} requires an integer value.")
        return int(value)
    if kind == "decimal":
        try:
            parsed = decimal.Decimal(str(value))
        except decimal.InvalidOperation as exc:
            raise ExportError("filter_not_allowed", f"Filter {field} requires a decimal value.") from exc
        if not parsed.is_finite():
            raise ExportError("filter_not_allowed", f"Filter {field} requires a finite decimal value.")
        return parsed
    if kind == "date":
        text = str(value)
        for fmt in ("%Y-%m-%d", "%Y%m%d"):
            try:
                return dt.datetime.strptime(text, fmt).strftime("%Y%m%d")
            except ValueError:
                pass
        raise ExportError("filter_not_allowed", f"Filter {field} requires YYYY-MM-DD or YYYYMMDD.")
    if kind == "time":
        text = str(value).replace(":", "")
        try:
            return dt.datetime.strptime(text, "%H%M%S").strftime("%H%M%S")
        except ValueError as exc:
            raise ExportError("filter_not_allowed", f"Filter {field} requires HH:MM:SS or HHMMSS.") from exc
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in {"true", "x", "1"}:
            return True
        if str(value).strip().lower() in {"false", "", "0"}:
            return False
        raise ExportError("filter_not_allowed", f"Filter {field} requires a boolean value.")
    raise ExportError("metadata_unavailable", f"Unsupported type for field {field}.")


def _task_identity(
    task: dict[str, Any],
    profiles: dict[str, Any],
    internal_values: Mapping[str, str],
) -> tuple[str, str, ProfileSpec]:
    unknown = set(task).difference(ALLOWED_TOP_LEVEL)
    forbidden = set(_walk_keys(task)).intersection(FORBIDDEN_INPUT_KEYS)
    if unknown or forbidden:
        names = sorted(unknown.union(forbidden))
        raise ExportError("filter_not_allowed", f"Task input contains unsupported or security-sensitive keys: {', '.join(names)}.")
    if task.get("schema_version") != SCHEMA_VERSION:
        raise ExportError("unsupported_system", "Task input schema_version must be 1.")
    profile = _resolve_profile(profiles, internal_values)

    source_type = str(task.get("source_type", "")).lower()
    object_name = str(task.get("object", "")).upper()
    if source_type not in ALLOWED_SOURCE_TYPES or not OBJECT_IDENTIFIER.fullmatch(object_name):
        raise ExportError("object_not_allowlisted", "source_type or object identifier is invalid.")
    if any(fnmatch.fnmatchcase(object_name, pattern) for pattern in profile.deny_object_patterns):
        raise ExportError("object_not_allowlisted", f"Object {object_name} is denied by trusted policy.")
    return source_type, object_name, profile


def _prepare_request(
    task: dict[str, Any],
    profiles: dict[str, Any],
    live_metadata: LiveMetadata | None = None,
    internal_values: Mapping[str, str] | None = None,
) -> PreparedRequest:
    source_type, object_name, profile = _task_identity(task, profiles, internal_values or {})
    object_spec = profile.objects.get(f"{source_type}:{object_name}")
    if profile.dynamic_objects:
        if live_metadata is None:
            raise ExportError("metadata_unavailable", "Dynamic object mode requires live ADT DDIC metadata.")
        if not live_metadata.stable_key:
            raise ExportError("stable_paging_key_unavailable", "Live ADT metadata does not declare a stable key.")
        object_spec = ObjectSpec(
            source_type=source_type,
            name=object_name,
            fields=live_metadata.fields,
            stable_key=live_metadata.stable_key,
            bounded_filter_fields=frozenset(live_metadata.fields),
            max_rows=profile.max_rows,
            page_size=profile.page_size,
        )
    if object_spec is None:
        raise ExportError("object_not_allowlisted", f"Object {source_type}:{object_name} is not allowlisted.")

    raw_fields = task.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise ExportError("field_unavailable", "fields must be a non-empty array.")
    fields = tuple(str(item).upper() for item in raw_fields)
    if len(set(fields)) != len(fields):
        raise ExportError("field_unavailable", "fields must not contain duplicates.")
    for field in fields:
        spec = object_spec.fields.get(field)
        if spec is None:
            raise ExportError("field_unavailable", f"Field {field} is not available in trusted metadata.")
        if spec.sensitive or any(fnmatch.fnmatchcase(field, pattern) for pattern in profile.deny_field_patterns):
            raise ExportError("field_unavailable", f"Field {field} is denied as sensitive.")

    raw_filters = task.get("filters")
    if not isinstance(raw_filters, list) or not raw_filters:
        raise ExportError("filter_not_allowed", "At least one bounded filter is required.")
    filters: list[Filter] = []
    bounded = False
    for raw_filter in raw_filters:
        if not isinstance(raw_filter, dict) or set(raw_filter).difference({"field", "sign", "option", "operator", "value", "low", "high", "values"}):
            raise ExportError("filter_not_allowed", "Each filter must use only field/sign/option/operator/value/low/high/values.")
        if "option" in raw_filter and "operator" in raw_filter:
            raise ExportError("filter_not_allowed", "A filter cannot contain both option and operator.")
        field = str(raw_filter.get("field", "")).upper()
        field_spec = object_spec.fields.get(field)
        if field_spec is None or field_spec.sensitive or any(fnmatch.fnmatchcase(field, pattern) for pattern in profile.deny_field_patterns):
            raise ExportError("filter_not_allowed", f"Filter field {field or '<empty>'} is unavailable or denied.")
        sign = str(raw_filter.get("sign", "I")).upper()
        option = str(raw_filter.get("option", raw_filter.get("operator", "EQ"))).upper()
        if sign not in {"I", "E"} or option not in ALLOWED_FILTER_OPTIONS:
            raise ExportError("filter_not_allowed", f"Filter {field} has unsupported sign or option.")
        if option == "BT":
            raw_values = (raw_filter.get("low"), raw_filter.get("high"))
            if any(value is None for value in raw_values):
                raise ExportError("filter_not_allowed", f"BT filter {field} requires low and high.")
        elif option == "IN":
            supplied = raw_filter.get("values")
            if not isinstance(supplied, list) or not supplied or len(supplied) > 100:
                raise ExportError("filter_not_allowed", f"IN filter {field} requires 1 to 100 values.")
            raw_values = tuple(supplied)
        else:
            raw_value = raw_filter.get("value", raw_filter.get("low"))
            if raw_value is None:
                raise ExportError("filter_not_allowed", f"Filter {field} requires value.")
            raw_values = (raw_value,)
        values = tuple(_typed_value(value, field, field_spec) for value in raw_values)
        filters.append(Filter(field=field, option=option, values=values, sign=sign))
        if sign == "I" and field in object_spec.bounded_filter_fields and option in {"EQ", "BT", "IN"}:
            bounded = True
    if not bounded:
        raise ExportError("filter_not_allowed", "A trusted bounded filter using EQ, BT, or IN is required.")

    raw_order = task.get("order_by") or [{"field": key, "direction": "asc"} for key in object_spec.stable_key]
    if not isinstance(raw_order, list):
        raise ExportError("stable_paging_key_unavailable", "order_by must be an array.")
    order_by: list[tuple[str, str]] = []
    for item in raw_order:
        if isinstance(item, str):
            field, direction = item.upper(), "ASC"
        elif isinstance(item, dict) and not set(item).difference({"field", "direction"}):
            field = str(item.get("field", "")).upper()
            direction = str(item.get("direction", "asc")).upper()
        else:
            raise ExportError("stable_paging_key_unavailable", "Invalid order_by item.")
        if field not in object_spec.fields or direction not in {"ASC", "DESC"}:
            raise ExportError("stable_paging_key_unavailable", f"Invalid stable ordering field {field}.")
        order_by.append((field, direction))
    expected_order = tuple((key, "ASC") for key in object_spec.stable_key)
    if tuple(order_by) != expected_order:
        raise ExportError("stable_paging_key_unavailable", "order_by must exactly match the trusted stable key in ascending order.")

    raw_max = task.get("max_rows", min(100, object_spec.max_rows))
    if isinstance(raw_max, bool) or not isinstance(raw_max, int) or not 1 <= raw_max <= object_spec.max_rows:
        raise ExportError("row_limit_reached", f"max_rows must be between 1 and {object_spec.max_rows}.")
    return PreparedRequest(
        source_type=source_type,
        object_name=object_name,
        fields=fields,
        filters=tuple(filters),
        order_by=tuple(order_by),
        max_rows=raw_max,
        object_spec=object_spec,
        connection=profile.connection,
    )


def _sql_literal(value: Any, spec: FieldSpec) -> str:
    if spec.type in {"integer", "decimal"}:
        return str(value)
    if spec.type == "boolean":
        return "'X'" if value else "' '"
    return "'" + str(value).replace("'", "''") + "'"


def _filter_sql(item: Filter, fields: Mapping[str, FieldSpec]) -> str:
    spec = fields[item.field]
    literals = [_sql_literal(value, spec) for value in item.values]
    if item.option == "BT":
        operator = "NOT BETWEEN" if item.sign == "E" else "BETWEEN"
        return f"{item.field} {operator} {literals[0]} AND {literals[1]}"
    elif item.option == "IN":
        operator = "NOT IN" if item.sign == "E" else "IN"
        return f"{item.field} {operator} ({', '.join(literals)})"
    include_operator = {"EQ": "=", "NE": "<>", "GT": ">", "GE": ">=", "LT": "<", "LE": "<="}[item.option]
    exclude_operator = {"EQ": "<>", "NE": "=", "GT": "<=", "GE": "<", "LT": ">=", "LE": ">"}[item.option]
    operator = exclude_operator if item.sign == "E" else include_operator
    return f"{item.field} {operator} {literals[0]}"


def _keyset_branches(last_key: Sequence[Any], key_fields: Sequence[str], fields: Mapping[str, FieldSpec]) -> list[list[str]]:
    branches: list[list[str]] = []
    for index, field in enumerate(key_fields):
        equal_prefix = [f"{key_fields[i]} = {_sql_literal(last_key[i], fields[key_fields[i]])}" for i in range(index)]
        greater = f"{field} > {_sql_literal(last_key[index], fields[field])}"
        branches.append([*equal_prefix, greater])
    return branches


def _mask_literals(sql: str) -> str:
    chars = list(sql)
    index = 0
    while index < len(chars):
        if chars[index] != "'":
            index += 1
            continue
        chars[index] = " "
        index += 1
        while index < len(chars):
            if chars[index] == "'" and index + 1 < len(chars) and chars[index + 1] == "'":
                chars[index] = chars[index + 1] = " "
                index += 2
                continue
            current = chars[index]
            chars[index] = " "
            index += 1
            if current == "'":
                break
    return "".join(chars)


def _validate_compiled_select(sql: str) -> None:
    masked = _mask_literals(sql).upper()
    if not masked.startswith("SELECT ") or ";" in masked or "--" in masked or "/*" in masked or "*/" in masked:
        raise ExportError("filter_not_allowed", "Internal query compiler produced an unsafe statement.")
    tokens = set(re.findall(r"\b[A-Z]+\b", masked))
    if tokens.intersection(WRITE_TOKENS):
        raise ExportError("filter_not_allowed", "Internal query compiler produced a non-read-only statement.")


def compile_select(request: PreparedRequest, last_key: Sequence[Any] | None = None) -> str:
    selected = list(dict.fromkeys([*request.fields, *request.object_spec.stable_key]))
    predicates = [_filter_sql(item, request.object_spec.fields) for item in request.filters]
    if last_key is None:
        where_clause = " AND ".join(predicates)
    else:
        # Some supported ABAP releases reject boolean grouping parentheses in
        # freestyle Data Preview. Duplicate the bounded predicates per OR
        # branch; AND precedence preserves equivalent keyset semantics.
        branches = _keyset_branches(last_key, request.object_spec.stable_key, request.object_spec.fields)
        where_clause = " OR ".join(" AND ".join([*predicates, *branch]) for branch in branches)
    sql = (
        f"SELECT {', '.join(selected)} FROM {request.object_name} "
        f"WHERE {where_clause} "
        f"ORDER BY {', '.join(request.object_spec.stable_key)}"
    )
    _validate_compiled_select(sql)
    return sql


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _flat_attributes(element: ET.Element) -> dict[str, str]:
    return {_local_name(key): value for key, value in element.attrib.items()}


def parse_preview_xml(xml_text: str) -> PreviewResult:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ExportError("metadata_unavailable", f"ADT Data Preview returned invalid XML: {exc}") from exc
    columns: list[tuple[str, list[str]]] = []
    for element in root.iter():
        if _local_name(element.tag) != "columns":
            continue
        metadata = next((child for child in element if _local_name(child.tag) == "metadata"), None)
        if metadata is None:
            continue
        name = _flat_attributes(metadata).get("name", "").upper()
        if not name:
            continue
        dataset = next((child for child in element if _local_name(child.tag) == "dataSet"), None)
        values = [] if dataset is None else [(child.text or "") for child in dataset if _local_name(child.tag) == "data"]
        columns.append((name, values))
    if not columns:
        for element in root.iter():
            if _local_name(element.tag) != "column":
                continue
            name = _flat_attributes(element).get("name", "").upper()
            if not name:
                continue
            values = [(child.text or "") for child in element.iter() if child is not element and _local_name(child.tag) in {"row", "cell", "value", "data"}]
            columns.append((name, values))
    if not columns:
        raise ExportError("metadata_unavailable", "ADT response did not include column metadata.")
    if len({name for name, _ in columns}) != len(columns):
        raise ExportError("metadata_unavailable", "ADT response contains duplicate column metadata.")
    row_count = max((len(values) for _, values in columns), default=0)
    rows = tuple(
        {name: values[index] if index < len(values) else "" for name, values in columns}
        for index in range(row_count)
    )
    return PreviewResult(columns=tuple(name for name, _ in columns), rows=rows)


class AdtClient:
    """Narrow client exposing only live metadata and read-only Data Preview endpoints."""

    def __init__(self, connection: Connection):
        try:
            import requests
        except ImportError as exc:
            raise ExportError("unsupported_system", "The requests package is required.") from exc
        installed = tuple(int(part) for part in requests.__version__.split(".")[:3])
        minimum = tuple(int(part) for part in MINIMUM_DEPENDENCIES["requests"].split("."))
        if installed < minimum:
            raise ExportError(
                "unsupported_system",
                f"requests>={MINIMUM_DEPENDENCIES['requests']} is required; reproduce with scripts/requirements.txt.",
            )
        self._requests = requests
        self._connection = connection
        self._session = requests.Session()
        self._session.auth = (connection.username, connection.password)
        self._url = connection.base_url + ENDPOINT

    def metadata(self, source_type: str, object_name: str) -> tuple[str, str]:
        encoded = quote(object_name.lower(), safe="")
        if source_type == "table":
            path = f"{TABLE_METADATA_PREFIX}{encoded}/source/main"
        elif source_type == "cds":
            path = f"{CDS_METADATA_PREFIX}{encoded}/source/main"
        else:
            raise ExportError("unsupported_system", "Unsupported ADT metadata source type.")
        return self._metadata_get(path, "text/plain")

    def structure_metadata(self, name: str) -> tuple[str, str]:
        if not FIELD_IDENTIFIER.fullmatch(name.upper()):
            raise ExportError("metadata_unavailable", "Live DDIC returned an invalid include reference.")
        path = f"{STRUCTURE_METADATA_PREFIX}{quote(name.lower(), safe='')}/source/main"
        return self._metadata_get(path, "text/plain")

    def data_element(self, name: str) -> tuple[str, str]:
        if not OBJECT_IDENTIFIER.fullmatch(name.upper()):
            raise ExportError("metadata_unavailable", "Live DDIC returned an invalid data-element reference.")
        path = f"{DATA_ELEMENT_PREFIX}{quote(name.lower(), safe='')}"
        return self._metadata_get(path, DATA_ELEMENT_ACCEPT)

    def _metadata_get(self, path: str, accept: str) -> tuple[str, str]:
        try:
            response = self._session.get(
                self._connection.base_url + path,
                headers={
                    "Accept": accept,
                    "X-SAP-Client": self._connection.client,
                    "Accept-Language": self._connection.language,
                },
                verify=self._connection.verify,
                timeout=self._connection.timeout_seconds,
                allow_redirects=False,
            )
            if 300 <= response.status_code < 400:
                raise ExportError("metadata_unavailable", "Redirects are not allowed for ADT metadata.")
            if response.status_code == 401:
                raise ExportError("authentication_failed", "SAP ADT authentication failed.")
            if response.status_code == 403:
                raise ExportError("authorization_denied", "SAP denied the ADT metadata request.")
            if response.status_code in {404, 405, 501, 503}:
                raise ExportError("metadata_unavailable", f"SAP ADT metadata is unavailable (HTTP {response.status_code}).")
            if response.status_code >= 400:
                raise ExportError("metadata_unavailable", f"SAP rejected the metadata request (HTTP {response.status_code}).")
            if not response.text.strip():
                raise ExportError("metadata_unavailable", "SAP ADT metadata response is empty.")
            return response.text, path
        except ExportError:
            raise
        except self._requests.exceptions.SSLError as exc:
            raise ExportError("tls_validation_failed", "SAP ADT TLS certificate validation failed.") from exc
        except self._requests.exceptions.Timeout as exc:
            raise ExportError("timeout", "SAP ADT metadata request timed out.") from exc
        except self._requests.exceptions.RequestException as exc:
            raise ExportError("adt_service_unavailable", f"SAP ADT metadata request failed: {type(exc).__name__}.") from exc

    def _request(self, method: str, *, row_number: int, sql: str, token: str | None = None):
        if method not in {"GET", "POST"}:
            raise ExportError("filter_not_allowed", "Only read-only ADT Data Preview submission methods are reachable.")
        headers = {
            "Accept": ACCEPT,
            "X-SAP-Client": self._connection.client,
            "Accept-Language": self._connection.language,
        }
        if token:
            headers["x-csrf-token"] = token
        kwargs: dict[str, Any] = {
            "headers": headers,
            "verify": self._connection.verify,
            "timeout": self._connection.timeout_seconds,
            "allow_redirects": False,
        }
        if method == "GET":
            kwargs["params"] = {"rowNumber": row_number, "sqlCommand": sql}
        else:
            headers["Content-Type"] = "text/plain; charset=utf-8"
            kwargs["params"] = {"rowNumber": row_number}
            kwargs["data"] = sql.encode("utf-8")
        return self._session.request(method, self._url, **kwargs)

    def preview(self, sql: str, row_number: int) -> PreviewResult:
        if not 1 <= row_number <= 10001:
            raise ExportError("row_limit_reached", "Internal ADT row limit is invalid.")
        _validate_compiled_select(sql)
        try:
            response = self._request("GET", row_number=row_number, sql=sql)
            if response.status_code == 405:
                response = self._request("POST", row_number=row_number, sql=sql)
                if response.status_code == 403 and "csrf" in response.text.lower():
                    token_response = self._session.get(
                        self._url,
                        headers={
                            "Accept": ACCEPT,
                            "X-SAP-Client": self._connection.client,
                            "x-csrf-token": "fetch",
                        },
                        verify=self._connection.verify,
                        timeout=self._connection.timeout_seconds,
                        allow_redirects=False,
                    )
                    token = token_response.headers.get("x-csrf-token")
                    if token:
                        response = self._request("POST", row_number=row_number, sql=sql, token=token)
            if 300 <= response.status_code < 400:
                raise ExportError("adt_service_unavailable", "Redirects are not allowed for the ADT endpoint.")
            if response.status_code == 401:
                raise ExportError("authentication_failed", "SAP ADT authentication failed.")
            if response.status_code == 403:
                raise ExportError("authorization_denied", "SAP denied the ADT Data Preview request.")
            if response.status_code in {404, 405, 501, 503}:
                raise ExportError("adt_service_unavailable", f"SAP ADT Data Preview is unavailable (HTTP {response.status_code}).")
            if response.status_code >= 400:
                raise ExportError("metadata_unavailable", f"SAP rejected the structured query (HTTP {response.status_code}).")
            return parse_preview_xml(response.text)
        except ExportError:
            raise
        except self._requests.exceptions.SSLError as exc:
            raise ExportError("tls_validation_failed", "SAP ADT TLS certificate validation failed.") from exc
        except self._requests.exceptions.Timeout as exc:
            raise ExportError("timeout", "SAP ADT request timed out.") from exc
        except self._requests.exceptions.RequestException as exc:
            raise ExportError("adt_service_unavailable", f"SAP ADT request failed: {type(exc).__name__}.") from exc


def _comparison_value(value: str, spec: FieldSpec) -> Any:
    try:
        if spec.type == "integer":
            return int(value)
        if spec.type == "decimal":
            return decimal.Decimal(value)
        if spec.type == "boolean":
            return value.upper() in {"X", "TRUE", "1"}
    except (ValueError, decimal.InvalidOperation) as exc:
        raise ExportError("metadata_unavailable", "ADT returned a value incompatible with trusted key metadata.") from exc
    return value


def _infer_live_field_type(type_expression: str) -> str:
    """Map an ADT/DDIC type expression to the small safe literal type set."""
    normalized = re.sub(r"\s+", "", type_expression).lower()
    if re.search(r"(?:^|\.)(?:int1|int2|int4|int8|integer)(?:\W|$)", normalized):
        return "integer"
    if re.search(r"(?:^|\.)(?:dec|curr|quan|fltp|decfloat16|decfloat34)(?:\W|$)", normalized):
        return "decimal"
    if re.search(r"(?:^|\.)(?:dats|date)(?:\W|$)", normalized):
        return "date"
    if re.search(r"(?:^|\.)(?:tims|time)(?:\W|$)", normalized):
        return "time"
    if re.search(r"(?:^|\.)(?:boolean|boole_d|xfeld)(?:\W|$)", normalized):
        return "boolean"
    # Named DDIC data elements do not expose their primitive domain in source
    # text. Treating them as strings keeps literals quoted and fail-closed; SAP
    # remains the authority and rejects incompatible comparisons.
    return "string"


def parse_live_metadata_details(source_type: str, source: str) -> LiveMetadata:
    """Extract live fields, inferred literal types, and ordered declared keys."""
    without_block_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    clean = re.sub(r"//.*?$", "", without_block_comments, flags=re.MULTILINE)
    braces = re.search(r"\{(.*)\}", clean, flags=re.DOTALL)
    if not braces:
        raise ExportError("metadata_unavailable", "ADT metadata source has no parseable field body.")
    body = braces.group(1)
    if source_type in {"table", "structure"}:
        matches = re.findall(
            r"(?im)(?:^|;)\s*(key\s+)?([A-Za-z][A-Za-z0-9_]*)\s*:\s*([^;]+)",
            body,
        )
        fields = {
            name.upper(): FieldSpec(type=_infer_live_field_type(type_expression))
            for _, name, type_expression in matches
        }
        keys = tuple(name.upper() for key, name, _ in matches if key)
        type_references: dict[str, str] = {}
        for _, name, type_expression in matches:
            reference_match = re.match(
                r"\s*((?:[A-Za-z][A-Za-z0-9_]{0,59}|/[A-Za-z0-9_]+/[A-Za-z0-9_/]+))(?=\s|$)",
                type_expression,
            )
            if reference_match and not type_expression.lstrip().lower().startswith("abap."):
                type_references[name.upper()] = reference_match.group(1).upper()
        include_references = tuple(
            name.upper()
            for name in re.findall(
                r"(?im)(?:^|;)\s*include\s+([A-Za-z][A-Za-z0-9_]*)\b",
                body,
            )
        )
    else:
        # CDS projection syntax varies by release. Extract identifiers from the
        # projection body, then require every trusted field and key to occur as
        # an exact token before Data Preview is called. The Data Preview column
        # metadata provides the second, exact validation layer.
        field_names = {name.upper() for name in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", body)}
        fields = {name: FieldSpec(type="string") for name in field_names}
        key_matches = re.findall(
            r"(?is)\bkey\s+(?:[A-Za-z][A-Za-z0-9_]*\.)?([A-Za-z][A-Za-z0-9_]*)(?:\s+as\s+([A-Za-z][A-Za-z0-9_]*))?",
            body,
        )
        keys = tuple((alias or name).upper() for name, alias in key_matches)
        type_references = {}
        include_references = ()
    if not fields:
        raise ExportError("metadata_unavailable", "ADT metadata source contains no parseable fields.")
    return LiveMetadata(
        fields=fields,
        stable_key=keys,
        type_references=type_references,
        include_references=include_references,
    )


def expand_live_metadata(
    client: Any,
    source_type: str,
    source: str,
    *,
    include_stack: tuple[str, ...] = (),
) -> tuple[LiveMetadata, list[str]]:
    """Expand live DDIC includes through the read-only structure source endpoint."""
    metadata = parse_live_metadata_details(source_type, source)
    if not metadata.include_references:
        return metadata, []
    if source_type not in {"table", "structure"}:
        raise ExportError("metadata_unavailable", "Only table and structure metadata may contain DDIC includes.")

    fields = dict(metadata.fields)
    type_references = dict(metadata.type_references)
    structure_hashes: list[str] = []
    for include_name in metadata.include_references:
        if include_name in include_stack:
            chain = " -> ".join([*include_stack, include_name])
            raise ExportError("metadata_unavailable", f"DDIC include cycle detected: {chain}.")
        if len(include_stack) >= MAX_INCLUDE_DEPTH:
            raise ExportError("metadata_unavailable", "DDIC include nesting exceeds the safe depth limit.")
        include_source, _path = client.structure_metadata(include_name)
        expanded, nested_hashes = expand_live_metadata(
            client,
            "structure",
            include_source,
            include_stack=(*include_stack, include_name),
        )
        structure_hashes.append(_sha256(include_source.encode("utf-8")))
        structure_hashes.extend(nested_hashes)
        for field_name, field_spec in expanded.fields.items():
            if field_name in fields:
                raise ExportError(
                    "metadata_unavailable",
                    f"DDIC include {include_name} conflicts with field {field_name}.",
                )
            fields[field_name] = field_spec
        for field_name, reference in expanded.type_references.items():
            existing = type_references.get(field_name)
            if existing is not None and existing != reference:
                raise ExportError(
                    "metadata_unavailable",
                    f"DDIC include {include_name} has conflicting type metadata for {field_name}.",
                )
            type_references[field_name] = reference

    return (
        LiveMetadata(
            fields=fields,
            stable_key=metadata.stable_key,
            type_references=type_references,
            include_references=(),
        ),
        structure_hashes,
    )


def parse_live_metadata(source_type: str, source: str) -> tuple[set[str], set[str]]:
    """Backward-compatible field/key set view of parsed ADT metadata."""
    details = parse_live_metadata_details(source_type, source)
    return set(details.fields), set(details.stable_key)


def parse_data_element_type(xml_text: str, expected_name: str) -> str:
    """Resolve a DDIC data element to the safe literal class used by filters."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ExportError("metadata_unavailable", "ADT data-element metadata is invalid XML.") from exc
    actual_name = _flat_attributes(root).get("name", "").upper()
    if actual_name and actual_name != expected_name.upper():
        raise ExportError("metadata_unavailable", "ADT data-element metadata identity does not match the requested reference.")
    data_type = next(
        ((element.text or "").strip().upper() for element in root.iter() if _local_name(element.tag) == "dataType"),
        "",
    )
    if not data_type:
        raise ExportError("metadata_unavailable", f"ADT data element {expected_name} has no published data type.")
    if data_type in {"INT1", "INT2", "INT4", "INT8"}:
        return "integer"
    if data_type in {"DEC", "CURR", "QUAN", "FLTP", "DF16_DEC", "DF34_DEC", "DECFLOAT16", "DECFLOAT34"}:
        return "decimal"
    if data_type in {"DATS", "DATN"}:
        return "date"
    if data_type in {"TIMS", "TIMN"}:
        return "time"
    if data_type in {"BOOLEAN", "BOOLE"}:
        return "boolean"
    # Character-like and less common DDIC types remain quoted string literals.
    # Their exact live DDIC identity and dataType were still validated above.
    return "string"


def enrich_live_field_types(
    client: Any,
    metadata: LiveMetadata,
    required_fields: Iterable[str],
) -> tuple[LiveMetadata, list[str]]:
    fields = dict(metadata.fields)
    hashes: list[str] = []
    resolved: dict[str, str] = {}
    for field in sorted({str(item).upper() for item in required_fields}):
        reference = metadata.type_references.get(field)
        if not reference:
            continue
        if reference not in resolved:
            source, _path = client.data_element(reference)
            resolved[reference] = parse_data_element_type(source, reference)
            hashes.append(_sha256(source.encode("utf-8")))
        current = fields[field]
        fields[field] = FieldSpec(type=resolved[reference], sensitive=current.sensitive)
    return LiveMetadata(
        fields=fields,
        stable_key=metadata.stable_key,
        type_references=metadata.type_references,
        include_references=metadata.include_references,
    ), hashes


def _row_key(row: Mapping[str, str], request: PreparedRequest) -> tuple[Any, ...]:
    values: list[Any] = []
    for field in request.object_spec.stable_key:
        if field not in row:
            raise ExportError("metadata_unavailable", f"ADT result omitted stable key field {field}.")
        values.append(_comparison_value(row[field], request.object_spec.fields[field]))
    return tuple(values)


def _scope(request: PreparedRequest) -> dict[str, Any]:
    filters = []
    for item in request.filters:
        entry: dict[str, Any] = {"field": item.field, "sign": item.sign, "option": item.option}
        if item.option == "BT":
            entry.update({"low": str(item.values[0]), "high": str(item.values[1])})
        elif item.option == "IN":
            entry["values"] = [str(value) for value in item.values]
        else:
            entry["value"] = str(item.values[0])
        filters.append(entry)
    return {
        "source_type": request.source_type,
        "object": request.object_name,
        "fields": list(request.fields),
        "filters": filters,
        "order_by": [{"field": field, "direction": direction.lower()} for field, direction in request.order_by],
        "max_rows": request.max_rows,
    }


def execute(
    task: dict[str, Any],
    profiles: dict[str, Any],
    client_factory: Callable[[Connection], Any] | None = None,
    run_id: str | None = None,
    started_at: str | None = None,
    internal_values: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    client_factory = client_factory or AdtClient
    run_id = run_id or str(uuid.uuid4())
    started_at = started_at or _utc_now()
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "skill_id": SKILL_ID,
        "run_id": run_id,
        "status": "failed",
        "read_only": True,
        "validated": False,
        "source": {},
        "scope": {},
        "rows": [],
        "row_count": 0,
        "completeness": {
            "source_complete": False,
            "total_count_known": False,
            "truncated": False,
            "paging_complete": False,
            "reason": "validation_failed",
        },
        "validation_issues": [],
        "started_at": started_at,
        "completed_at": started_at,
        "artifacts": [{"type": "input", "sha256": _sha256(_canonical_bytes(task))}],
    }
    try:
        trusted_values = internal_values or {}
        source_type, object_name, profile = _task_identity(task, profiles, trusted_values)
        client = client_factory(profile.connection)
        metadata_source, _metadata_path = client.metadata(source_type, object_name)
        live_metadata, structure_metadata_hashes = expand_live_metadata(
            client,
            source_type,
            metadata_source,
        )
        type_metadata_hashes: list[str] = []
        if profile.dynamic_objects:
            requested_type_fields = [
                *(item for item in task.get("fields", []) if isinstance(item, str)),
                *(
                    item.get("field")
                    for item in task.get("filters", [])
                    if isinstance(item, dict) and isinstance(item.get("field"), str)
                ),
                *live_metadata.stable_key,
            ]
            live_metadata, type_metadata_hashes = enrich_live_field_types(
                client,
                live_metadata,
                requested_type_fields,
            )
        request = _prepare_request(
            task,
            profiles,
            live_metadata=live_metadata if profile.dynamic_objects else None,
            internal_values=trusted_values,
        )
        base["source"] = {
            "type": "sap_adt_data_preview",
            "source_type": request.source_type,
            "object": request.object_name,
            "fields": list(request.fields),
        }
        base["scope"] = _scope(request)
        live_fields = set(live_metadata.fields)
        live_keys = set(live_metadata.stable_key)
        required_fields = set(request.fields).union(request.object_spec.stable_key)
        if not required_fields.issubset(live_fields):
            missing = sorted(required_fields.difference(live_fields))
            raise ExportError("field_unavailable", f"Live ADT metadata does not contain fields: {', '.join(missing)}.")
        if not set(request.object_spec.stable_key).issubset(live_keys):
            raise ExportError("stable_paging_key_unavailable", "Live ADT metadata does not confirm the trusted stable key.")
        metadata_at = _utc_now()
        base["source"]["metadata_validated_at"] = metadata_at
        base["artifacts"].append({"type": "metadata", "sha256": _sha256(metadata_source.encode("utf-8")), "timestamp": metadata_at})
        base["artifacts"].extend(
            {"type": "structure_metadata", "sha256": digest, "timestamp": metadata_at}
            for digest in structure_metadata_hashes
        )
        base["artifacts"].extend(
            {"type": "data_element_metadata", "sha256": digest, "timestamp": metadata_at}
            for digest in type_metadata_hashes
        )
        output_rows: list[dict[str, str]] = []
        seen_keys: set[tuple[Any, ...]] = set()
        last_key: tuple[Any, ...] | None = None
        expected_next_key: tuple[Any, ...] | None = None
        query_hashes: list[str] = []
        complete = False
        while len(output_rows) < request.max_rows:
            remaining = request.max_rows - len(output_rows)
            page_size = min(request.object_spec.page_size, remaining)
            query = compile_select(request, last_key=last_key)
            query_hashes.append(_sha256(query.encode("utf-8")))
            preview = client.preview(query, page_size + 1)
            expected_columns = tuple(dict.fromkeys([*request.fields, *request.object_spec.stable_key]))
            if tuple(name.upper() for name in preview.columns) != expected_columns:
                raise ExportError(
                    "metadata_unavailable",
                    f"Live ADT columns {list(preview.columns)} do not match trusted requested columns {list(expected_columns)}.",
                )
            base["validated"] = True
            if len(preview.rows) > page_size + 1:
                raise ExportError("paging_incomplete", "ADT returned more rows than the requested page bound.")
            if not preview.rows:
                if expected_next_key is not None:
                    raise ExportError("paging_incomplete", "ADT paging omitted the probed next boundary row.")
                complete = True
                break
            keep = preview.rows[:page_size]
            page_keys = [_row_key(row, request) for row in keep]
            if page_keys != sorted(page_keys) or (last_key is not None and page_keys and page_keys[0] <= last_key):
                raise ExportError("paging_incomplete", "ADT page ordering is not strictly monotonic.")
            if expected_next_key is not None and page_keys[0] != expected_next_key:
                raise ExportError("paging_incomplete", "ADT paging produced a missing or changed chunk boundary.")
            if len(set(page_keys)) != len(page_keys) or any(key in seen_keys for key in page_keys):
                raise ExportError("paging_incomplete", "ADT paging produced a duplicate business key.")
            if request.object_spec.contiguous_key and last_key is not None and len(last_key) == 1:
                numeric = [last_key[0], *(key[0] for key in page_keys)]
                if any(isinstance(value, int) for value in numeric) and any(right != left + 1 for left, right in zip(numeric, numeric[1:])):
                    raise ExportError("paging_incomplete", "ADT paging produced a missing contiguous key.")
            seen_keys.update(page_keys)
            output_rows.extend({field: row.get(field, "") for field in request.fields} for row in keep)
            if len(preview.rows) <= page_size:
                complete = True
                break
            expected_next_key = _row_key(preview.rows[page_size], request)
            if expected_next_key <= page_keys[-1]:
                raise ExportError("paging_incomplete", "ADT overflow probe did not advance beyond the page boundary.")
            last_key = page_keys[-1]

        truncated = not complete
        issues = []
        if truncated:
            issues.append({"code": "row_limit_reached", "message": "More rows exist beyond max_rows; returned evidence is bounded and incomplete."})
        base.update(
            {
                "status": "partial" if truncated else "complete",
                "rows": output_rows,
                "row_count": len(output_rows),
                "completeness": {
                    "source_complete": complete,
                    "total_count_known": complete,
                    "truncated": truncated,
                    "paging_complete": complete,
                    "reason": "row_limit_reached" if truncated else "bounded_complete",
                },
                "validation_issues": issues,
            }
        )
        base["artifacts"].extend(
            [
                {"type": "generated_query", "sha256": digest} for digest in query_hashes
            ]
            + [{"type": "rows", "sha256": _sha256(_canonical_bytes(output_rows))}]
        )
    except ExportError as exc:
        base["validation_issues"] = [{"code": exc.code, "message": exc.message}]
    except Exception as exc:  # Defensive fail-closed boundary; never emit credentials or row content.
        base["validation_issues"] = [{"code": "unsupported_system", "message": f"Unexpected runtime failure: {type(exc).__name__}."}]
    if base["status"] == "failed" and base["validation_issues"]:
        base["completeness"]["reason"] = base["validation_issues"][0]["code"]
    base["completed_at"] = _utc_now()
    return base


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(payload.encode("utf-8"))
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = _sha256(payload.encode("utf-8"))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "skill_id": SKILL_ID,
        "run_id": result.get("run_id"),
        "read_only": True,
        "status": result.get("status"),
        "output_file": path.name,
        "output_sha256": digest,
        "created_at": _utc_now(),
    }
    manifest_path = path.with_name(path.name + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strictly read-only bounded SAP ADT table/CDS export")
    parser.add_argument("--input", required=True, type=Path, help="Structured task JSON")
    parser.add_argument("--output", required=True, type=Path, help="Canonical result JSON")
    args = parser.parse_args(argv)
    started_at = _utc_now()
    run_id = str(uuid.uuid4())
    try:
        task = _read_json(args.input, code="filter_not_allowed", expose_path=True)
        profiles, internal_values = load_internal_configuration()
        result = execute(
            task,
            profiles,
            run_id=run_id,
            started_at=started_at,
            internal_values=internal_values,
        )
    except ExportError as exc:
        result = {
            "schema_version": SCHEMA_VERSION,
            "skill_id": SKILL_ID,
            "run_id": run_id,
            "status": "failed",
            "read_only": True,
            "validated": False,
            "source": {},
            "scope": {},
            "rows": [],
            "row_count": 0,
            "completeness": {
                "source_complete": False,
                "total_count_known": False,
                "truncated": False,
                "paging_complete": False,
                "reason": exc.code,
            },
            "validation_issues": [{"code": exc.code, "message": exc.message}],
            "started_at": started_at,
            "completed_at": _utc_now(),
            "artifacts": [],
        }
    write_result(args.output, result)
    return 0 if result["status"] in {"complete", "partial"} else 1


if __name__ == "__main__":
    sys.exit(main())
