"""Version 1 import contract. Values never acquire certainty through import."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from math import isfinite
import ipaddress
import re
from urllib.parse import urlsplit

FINANCIAL_FIELDS = (
    "current_bid", "expected_resale_gross", "buyer_premium", "item_vat",
    "premium_vat", "transport", "refurbishment", "storage", "disposal",
)
ORIGINS = {"observed", "estimated", "manual", "unknown"}


class ValidationError(ValueError):
    pass


def text(value, name, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValidationError(f"{name}: Text erforderlich, maximal {limit} Zeichen")
    if any(ord(c) < 32 for c in value):
        raise ValidationError(f"{name}: Steuerzeichen unzulässig")
    return value.strip()


def identifier(value, name):
    value = text(value, name, 100)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValidationError(f"{name}: nur Buchstaben, Ziffern, Punkt, _ und -")
    return value


def timestamp(value, name):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ValidationError(f"{name}: ISO-8601 mit Zeitzone erforderlich") from None


def public_url(value):
    value = text(value, "listing_url")
    try:
        u = urlsplit(value)
        host = u.hostname
        if u.scheme != "https" or not host or u.username or u.password or u.port not in (None, 443):
            raise ValueError
        if host == "localhost" or "." not in host or host.endswith((".local", ".internal")):
            raise ValueError
        try:
            if not ipaddress.ip_address(host).is_global:
                raise ValueError
        except ValueError as error:
            # DNS names are permitted; links are never fetched by this application.
            if re.fullmatch(r"[0-9.]+", host) or ":" in host:
                raise error
        if u.fragment:
            raise ValueError
    except ValueError:
        raise ValidationError("listing_url: öffentliche HTTPS-Adresse ohne Zugangsdaten erforderlich") from None
    return value


@dataclass(frozen=True)
class Datum:
    value: float | None
    origin: str
    reference: str

    @classmethod
    def parse(cls, raw, name):
        if not isinstance(raw, dict) or set(raw) != {"value", "origin", "reference"}:
            raise ValidationError(f"{name}: value, origin und reference erforderlich")
        value, origin, reference = raw["value"], raw["origin"], raw["reference"]
        if not isinstance(origin, str) or origin not in ORIGINS:
            raise ValidationError(f"{name}: ungültige Herkunft")
        if value is None:
            if origin != "unknown":
                raise ValidationError(f"{name}: fehlender Wert muss unknown sein")
            return cls(None, origin, text(reference, name + ".reference"))
        if origin == "unknown" or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"{name}: ungültiger Wert")
        if not isfinite(value) or value < 0 or value > 1_000_000_000:
            raise ValidationError(f"{name}: ungültiger Zahlenbereich")
        if name in {"buyer_premium", "item_vat", "premium_vat"} and value > 1:
            raise ValidationError(f"{name}: Rate als Anteil 0–1 eingeben")
        return cls(float(value), origin, text(reference, name + ".reference"))


@dataclass(frozen=True)
class Listing:
    source: str
    source_id: str
    title: str
    location: str
    listing_url: str
    observed_at: str
    ends_at: str | None
    status: str
    bid_basis: str
    currency: str
    bid_kind: str
    fee_model: str
    terms_reference: str
    rights_reference: str
    fields: dict[str, Datum]

    @property
    def key(self):
        return self.source, self.source_id

    def to_dict(self):
        return asdict(self)

    @classmethod
    def parse(cls, raw, now=None):
        required = set(cls.__dataclass_fields__)
        if not isinstance(raw, dict) or set(raw) != required:
            raise ValidationError("Los: Felder entsprechen nicht dem v1-Vertrag")
        now = now or datetime.now(timezone.utc)
        observed = timestamp(raw["observed_at"], "observed_at")
        if observed > now + timedelta(minutes=5):
            raise ValidationError("observed_at: Zeitpunkt liegt in der Zukunft")
        end = timestamp(raw["ends_at"], "ends_at") if raw["ends_at"] is not None else None
        if raw["currency"] != "EUR":
            raise ValidationError("Nur EUR unterstützt; keine automatische Währungsumrechnung")
        if raw["bid_kind"] not in {"current", "starting", "minimum", "manual", "unknown"}:
            raise ValidationError("bid_kind ungültig")
        if raw["fee_model"] not in {"net_hammer_plus_net_premium", "other", "unknown"}:
            raise ValidationError("fee_model ungültig")
        if raw["status"] not in {"active", "ended", "unknown"}:
            raise ValidationError("status ungültig")
        if raw["bid_basis"] not in {"net", "gross", "unknown"}:
            raise ValidationError("bid_basis ungültig")
        if not isinstance(raw["fields"], dict) or set(raw["fields"]) != set(FINANCIAL_FIELDS):
            raise ValidationError("Alle Finanzfelder sind erforderlich; fehlende Werte als unknown markieren")
        fields = {name: Datum.parse(raw["fields"][name], name) for name in FINANCIAL_FIELDS}
        return cls(identifier(raw["source"], "source"), identifier(raw["source_id"], "source_id"),
                   text(raw["title"], "title", 300), text(raw["location"], "location", 300),
                   public_url(raw["listing_url"]), observed.isoformat(),
                   end.isoformat() if end else None, raw["status"], raw["bid_basis"],
                   raw["currency"], raw["bid_kind"], raw["fee_model"],
                   text(raw["terms_reference"], "terms_reference"),
                   text(raw["rights_reference"], "rights_reference"), fields)
