"""Versioned source research, deliberately separated from lot calculation.

Loading this register never fetches URLs and never supplies fee/tax defaults.
Authorization requires an explicit official evidence record; page accessibility
or an API URL does not constitute permission.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_REGISTRY = Path(__file__).parent / "data" / "source_registry.json"
STATUSES = frozenset({"verified", "partially_verified", "unconfirmed", "outdated",
                      "contradictory", "not_verifiable"})


class RegistryError(ValueError):
    """The register violates its versioned contract."""


def _date(value: object) -> None:
    if not isinstance(value, str):
        raise RegistryError("Invalid date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RegistryError("Invalid date") from exc


def _url(value: object) -> None:
    if not isinstance(value, str):
        raise RegistryError("Invalid public HTTPS URL")
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise RegistryError("Invalid public HTTPS URL") from exc
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RegistryError("Invalid public HTTPS URL")


def validate_registry(data: object) -> dict:
    """Validate source identities and fail closed on automated-access permission."""
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise RegistryError("Unsupported source registry schema")
    try:
        _date(data["updated_at"])
        if not isinstance(data["registry_version"], str) or not data["registry_version"]:
            raise RegistryError("Missing registry version")
        sources = data["sources"]
        if not isinstance(sources, list) or not sources:
            raise RegistryError("Missing sources")
        identities = set()
        for source in sources:
            if not isinstance(source, dict):
                raise RegistryError("Invalid source")
            source_id = source["id"]
            if not isinstance(source_id, str) or not source_id or source_id in identities:
                raise RegistryError("Invalid or duplicate source ID")
            identities.add(source_id)
            if not isinstance(source["name"], str) or not source["name"]:
                raise RegistryError("Missing source name")
            _url(source["official_website"])
            _date(source["updated_at"])
            if source["verification_status"] not in STATUSES:
                raise RegistryError("Unknown verification status")
            evidence_ids = set()
            for evidence in source["evidence"]:
                if evidence["id"] in evidence_ids:
                    raise RegistryError("Duplicate evidence ID")
                evidence_ids.add(evidence["id"])
                if evidence["status"] not in STATUSES:
                    raise RegistryError("Unknown evidence status")
                _date(evidence["checked_at"])
                if "url" in evidence:
                    _url(evidence["url"])
            conditions = source["platform_conditions"]
            if conditions["lot_conditions_required"] is not True:
                raise RegistryError("Lot-specific conditions required")
            for field in ("buyer_premium", "vat"):
                if conditions[field]["status"] not in STATUSES:
                    raise RegistryError("Unknown condition status")
                if conditions[field]["calculation_default"] is not None:
                    raise RegistryError("Platform economic defaults are forbidden")
            for field in ("buyer_premium",):
                if not set(conditions[field]["evidence_ids"]).issubset(evidence_ids):
                    raise RegistryError("Unknown evidence reference")
            access = source["data_access"]
            for flag in ("enabled", "automated_access_authorized"):
                if type(access[flag]) is not bool:
                    raise RegistryError("Access flags must be booleans")
            if access["enabled"] or access["automated_access_authorized"]:
                permission = next((e for e in source["evidence"]
                    if e["id"] == access.get("authorization_evidence_id")), None)
                if (not permission or permission.get("kind") != "official_web"
                    or permission.get("status") != "verified"
                    or permission.get("scope") != "commercial_automated_catalog_access"
                    or not access["automated_access_authorized"]
                    or not isinstance(access.get("connector"), str) or not access["connector"]):
                    raise RegistryError("Live connector lacks explicit commercial authorization")
            for assessment in ("economic_priority", "technical_priority"):
                if not isinstance(source[assessment], dict):
                    raise RegistryError("Missing separate priority assessment")
        if "permission_research_order" in data and set(data["permission_research_order"]) != identities:
            raise RegistryError("Research order must cover all sources")
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        if isinstance(exc, RegistryError):
            raise
        raise RegistryError("Incomplete source register") from exc
    return data


def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict:
    """Read a local register (maximum 2 MiB); no network, credentials or writes."""
    try:
        payload = Path(path).read_bytes()
        if len(payload) > 2 * 1024 * 1024:
            raise RegistryError("Source registry too large")
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise RegistryError("Duplicate JSON property")
                result[key] = value
            return result
        data = json.loads(payload, object_pairs_hook=unique_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(RegistryError("Non-finite JSON value")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError("Cannot read source registry") from exc
    return validate_registry(data)


def get_source(source_id: str, path: str | Path = DEFAULT_REGISTRY) -> dict | None:
    """Return independent source metadata; unknown IDs are not auto-registered."""
    return next((source for source in load_registry(path)["sources"]
                 if source["id"] == source_id), None)
