"""Read-only source boundary. No live adapter or platform fee defaults."""
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Lot:
    id: str
    title: str
    location: str
    current_bid: float
    expected_resale_gross: float
    buyer_premium: float
    item_vat: float
    premium_vat: float
    is_demo: bool
    source_label: str
    # Required provenance for future real adapters; no guessed listing URLs.
    listing_url: str | None = None
    retrieved_at: str | None = None
    terms_reference: str | None = None


class AuctionSource(Protocol):
    """Future approved API/feed adapter; never place bids here."""
    def fetch_lots(self) -> Sequence[Lot]: ...


class DemoSource:
    def fetch_lots(self) -> Sequence[Lot]:
        from sample_data import LOTS
        return LOTS


def load_lots(mode: str = "demo") -> Sequence[Lot]:
    if mode == "demo":
        return DemoSource().fetch_lots()
    if mode == "live":
        return ()  # Explicit empty state; never substitute demo data.
    raise ValueError("Unbekannter Datenmodus")
