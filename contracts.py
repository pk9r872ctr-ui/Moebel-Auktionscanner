"""Private, versioned candidate handoff; no ERP transport or accounting model."""
from datetime import datetime, timezone
from listings import Listing, ValidationError, timestamp, identifier


def candidate_export(store, workspace):
    """Export only decisions bound to the current snapshot. Not a buy instruction."""
    identifier(workspace, "workspace")
    return {
        "schema_version": 1,
        "event_type": "opportunity.selected",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection_kind": "manual_not_profit_verified",
        "candidates": [{"offer_key": [row["source"], row["source_id"]],
                        "approved_snapshot_at": row["observed_at"],
                        "approval_status": "manually_selected",
                        "listing": row} for row in store.export_candidates(workspace)],
    }


def validate_candidate_export(raw, now=None):
    required = {"schema_version", "event_type", "generated_at", "selection_kind", "candidates"}
    if not isinstance(raw, dict) or set(raw) != required or type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValidationError("Kandidatenvertrag v1 erforderlich")
    if raw["event_type"] != "opportunity.selected" or raw["selection_kind"] != "manual_not_profit_verified":
        raise ValidationError("Auswahlart unzulässig")
    timestamp(raw["generated_at"], "generated_at")
    if not isinstance(raw["candidates"], list) or len(raw["candidates"]) > 1000:
        raise ValidationError("Maximal 1000 Kandidaten")
    seen = set()
    for candidate in raw["candidates"]:
        if not isinstance(candidate, dict) or set(candidate) != {"offer_key", "approved_snapshot_at", "approval_status", "listing"}:
            raise ValidationError("Kandidat unvollständig")
        lot = Listing.parse(candidate["listing"], now)
        if lot.terms_reference.startswith("P0:"):
            raise ValidationError("Historische P0-Recherche ist kein Einkaufskandidat")
        if candidate["offer_key"] != list(lot.key) or candidate["approval_status"] != "manually_selected":
            raise ValidationError("Kennung oder Freigabestatus widersprüchlich")
        if timestamp(candidate["approved_snapshot_at"], "approved_snapshot_at") != timestamp(lot.observed_at, "observed_at") or lot.key in seen:
            raise ValidationError("Snapshot widersprüchlich oder doppelt")
        seen.add(lot.key)
    return raw
