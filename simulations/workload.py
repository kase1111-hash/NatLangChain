"""Synthetic economy that generates a year of natural-language ledger traffic.

The population is a small supply-chain economy: foundries and fabricators
selling to integrators, freelancers logging work, auditors filing findings,
and a municipal registry recording permits. Every entry is prose a human could
have written, because prose is the substrate the chain is supposed to validate.

Four traffic classes are generated deliberately:

1. ``clean``      — well-formed prose that should be accepted.
2. ``flagged``    — legitimate business language that trips the validator's
                    heuristics (e.g. "non-refundable deposit"). Used to measure
                    the false-rejection rate over a year.
3. ``ambiguous``  — vague prose that should land in NEEDS_CLARIFICATION.
4. ``adversarial``— attacks, generated separately by the scenario driver.

All randomness is seeded, so a run is reproducible from ``(seed, days)``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Population
# --------------------------------------------------------------------------

SUPPLIERS = [
    "northwind_foundry", "cascade_machining", "harbor_plastics", "granite_tooling",
    "meridian_castings", "blue_ridge_fabrication", "kestrel_optics", "tallgrass_textiles",
    "ironwood_millwork", "solstice_electronics", "delta_bearings", "quarry_composites",
]

BUYERS = [
    "halcyon_robotics", "verdant_agritech", "lumen_medical", "atlas_transit",
    "orchard_appliance", "seabright_marine", "pinnacle_aerospace", "juniper_furniture",
    "coastal_energy", "redwood_instruments", "starling_avionics", "brightline_rail",
    "copperfield_hvac", "wavelength_audio", "foxglove_labs", "silverpine_packaging",
    "aurora_diagnostics", "keystone_construction", "nimbus_drones", "pelican_logistics",
]

FREELANCERS = [
    "ivy_chen", "marcus_odell", "priya_raman", "tomas_brenner", "leah_whitfield",
    "kwame_asante", "sofia_marino", "daniel_okafor", "hana_kobayashi", "elias_vance",
    "rosa_delgado", "arthur_pemberton", "nadia_haddad", "gregor_lindqvist", "mei_tanaka",
]

AUDITORS = [
    "cornerstone_assurance", "fairmont_audit", "beacon_compliance", "thornhill_review",
    "sentinel_quality", "ledgerworks_audit", "trueline_inspection", "vantage_controls",
]

REGISTRARS = ["city_of_ashford", "port_of_calloway", "greenfield_county", "dockside_authority"]

ALL_ACTORS = SUPPLIERS + BUYERS + FREELANCERS + AUDITORS + REGISTRARS

GOODS = [
    "machined brackets", "injection-molded housings", "precision bearings",
    "carbon fiber panels", "optical lenses", "control boards", "hydraulic fittings",
    "steel weldments", "anodized enclosures", "wiring harnesses", "gasket sets",
    "titanium fasteners", "ceramic substrates", "linear actuators", "cooling manifolds",
]

DEPOTS = [
    "Portland depot", "Ashford yard", "Calloway pier", "Greenfield warehouse",
    "Dockside terminal", "Riverbend hub", "Northgate receiving dock",
]

WORK_KINDS = [
    "firmware integration", "mechanical drafting", "test fixture assembly",
    "supplier qualification", "packaging design", "thermal analysis",
    "wiring diagram revision", "field calibration", "documentation cleanup",
]

AUDIT_TOPICS = [
    "incoming inspection records", "calibration certificates", "material traceability",
    "packing slip reconciliation", "batch numbering", "storage temperature logs",
]

PERMIT_KINDS = [
    "loading dock access", "night freight movement", "hazardous material storage",
    "temporary crane placement", "harbor berth reservation",
]


@dataclass
class MinedRef:
    """Where an accepted entry ended up once mined, so derivatives can cite it."""

    block_index: int
    entry_index: int
    author: str
    intent: str
    kind: str
    day: int


@dataclass
class Draft:
    """A prepared entry awaiting submission."""

    content: str
    author: str
    intent: str
    kind: str
    traffic_class: str
    metadata: dict = field(default_factory=dict)
    parent_refs: list = field(default_factory=list)
    derivative_type: str | None = None
    expectation: str = "accepted"


class WorkloadGenerator:
    """Produces the day-to-day prose traffic of the simulated economy."""

    def __init__(self, seed: int = 20260101):
        self.rng = random.Random(seed)
        self._counter = 0
        self.assets: dict[str, str] = {}  # asset_id -> current owner (our own book)

    # -- helpers -----------------------------------------------------------
    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:06d}"

    def _money(self, low: int, high: int) -> str:
        return f"{self.rng.randrange(low, high, 25):,} dollars"

    def _qty(self) -> int:
        return self.rng.randrange(50, 8000, 25)

    def _date(self, day: int) -> str:
        # A human-readable target date some weeks out from the current day.
        offset = self.rng.randint(7, 60)
        total = day + offset
        month = (total // 30) % 12 + 1
        dom = total % 28 + 1
        return f"2026-{month:02d}-{dom:02d}"

    # -- clean traffic -----------------------------------------------------
    def supply_agreement(self, day: int) -> Draft:
        supplier = self.rng.choice(SUPPLIERS)
        buyer = self.rng.choice(BUYERS)
        good = self.rng.choice(GOODS)
        qty = self._qty()
        order = self._next_id("PO")
        content = (
            f"{supplier} agreed to supply {qty} {good} to {buyer} under purchase "
            f"order {order}. Delivery is due on {self._date(day)} at the "
            f"{self.rng.choice(DEPOTS)}. The agreed total is {self._money(2000, 90000)}, "
            f"payable within thirty days of receipt."
        )
        return Draft(
            content=content,
            author=supplier,
            intent=f"Supply agreement signed with {buyer} for purchase order {order}",
            kind="supply_agreement",
            traffic_class="clean",
            metadata={"purchase_order": order, "counterparty": buyer},
        )

    def delivery_receipt(self, day: int, parent: MinedRef | None = None) -> Draft:
        buyer = self.rng.choice(BUYERS)
        good = self.rng.choice(GOODS)
        qty = self._qty()
        content = (
            f"{buyer} confirmed receipt of {qty} {good} at the "
            f"{self.rng.choice(DEPOTS)} on {self._date(day)}. Incoming inspection "
            f"recorded {self.rng.randint(0, 4)} units held for rework, and the "
            f"remainder moved into finished goods inventory."
        )
        draft = Draft(
            content=content,
            author=buyer,
            intent="Delivery receipt confirmed by the receiving buyer",
            kind="delivery_receipt",
            traffic_class="clean",
        )
        if parent is not None:
            draft.parent_refs = [
                {"block_index": parent.block_index, "entry_index": parent.entry_index}
            ]
            draft.derivative_type = "fulfillment"
        return draft

    def payment(self, day: int, parent: MinedRef | None = None) -> Draft:
        buyer = self.rng.choice(BUYERS)
        supplier = self.rng.choice(SUPPLIERS)
        invoice = self._next_id("INV")
        content = (
            f"{buyer} paid {self._money(2000, 90000)} to {supplier} in settlement of "
            f"invoice {invoice}. The payment covers the full balance and closes the "
            f"account for that shipment."
        )
        draft = Draft(
            content=content,
            author=buyer,
            intent=f"Payment record for invoice {invoice} settlement",
            kind="payment",
            traffic_class="clean",
            metadata={"invoice": invoice, "counterparty": supplier},
        )
        if parent is not None:
            draft.parent_refs = [
                {"block_index": parent.block_index, "entry_index": parent.entry_index}
            ]
            draft.derivative_type = "fulfillment"
        return draft

    def work_log(self, day: int) -> Draft:
        who = self.rng.choice(FREELANCERS)
        client = self.rng.choice(BUYERS)
        kind = self.rng.choice(WORK_KINDS)
        hours = self.rng.randint(3, 40)
        content = (
            f"{who} completed {hours} hours of {kind} work for {client} during "
            f"week {day // 7 + 1} of the engagement. The deliverables were handed "
            f"over through the shared project folder and logged against the "
            f"retainer balance."
        )
        return Draft(
            content=content,
            author=who,
            intent=f"Work log covering {kind} hours for {client}",
            kind="work_log",
            traffic_class="clean",
        )

    def audit_finding(self, day: int) -> Draft:
        auditor = self.rng.choice(AUDITORS)
        target = self.rng.choice(SUPPLIERS + BUYERS)
        topic = self.rng.choice(AUDIT_TOPICS)
        content = (
            f"{auditor} reviewed the {topic} held by {target} for the quarter ending "
            f"{self._date(day)}. The review sampled {self.rng.randint(12, 120)} records "
            f"and found {self.rng.randint(0, 6)} gaps, each logged with a corrective "
            f"action owner and a closure date."
        )
        return Draft(
            content=content,
            author=auditor,
            intent=f"Audit finding on {topic} at {target}",
            kind="audit_finding",
            traffic_class="clean",
        )

    def permit(self, day: int) -> Draft:
        registrar = self.rng.choice(REGISTRARS)
        holder = self.rng.choice(SUPPLIERS + BUYERS)
        kind = self.rng.choice(PERMIT_KINDS)
        permit_id = self._next_id("PMT")
        content = (
            f"{registrar} registered permit {permit_id} granting {holder} the right to "
            f"conduct {kind} through {self._date(day)}. The permit carries a filing fee "
            f"of {self._money(100, 4000)} and the standard inspection schedule."
        )
        return Draft(
            content=content,
            author=registrar,
            intent=f"Register new permit {permit_id} for {kind}",
            kind="permit",
            traffic_class="clean",
            metadata={"permit_id": permit_id, "holder": holder},
        )

    def asset_transfer(self, day: int) -> Draft | None:
        """Transfer a tracked asset. Returns None if nothing is transferable."""
        if not self.assets:
            return None
        asset_id = self.rng.choice(list(self.assets))
        owner = self.assets[asset_id]
        recipient = self.rng.choice([a for a in SUPPLIERS + BUYERS if a != owner])
        content = (
            f"{owner} transferred title in equipment {asset_id} to {recipient} "
            f"following the sale agreed on {self._date(day)}. The unit ships from the "
            f"{self.rng.choice(DEPOTS)} once the final inspection is countersigned."
        )
        return Draft(
            content=content,
            author=owner,
            intent=f"Transfer of ownership in asset {asset_id}",
            kind="asset_transfer",
            traffic_class="clean",
            metadata={"asset_id": asset_id, "recipient": recipient},
        )

    def asset_registration(self, day: int) -> tuple[Draft, str, str]:
        owner = self.rng.choice(SUPPLIERS + BUYERS)
        asset_id = self._next_id("EQ")
        content = (
            f"{owner} registered equipment {asset_id}, a "
            f"{self.rng.choice(['press brake', 'CNC lathe', 'reflow oven', 'coating line', 'test bench'])} "
            f"commissioned on {self._date(day)} and held at the "
            f"{self.rng.choice(DEPOTS)}. The unit carries serial "
            f"{self.rng.randint(100000, 999999)} and a five year service plan."
        )
        draft = Draft(
            content=content,
            author=owner,
            intent=f"Register new equipment asset {asset_id}",
            kind="asset_registration",
            traffic_class="clean",
            metadata={"asset_id": asset_id},
        )
        return draft, asset_id, owner

    # -- derivative traffic ------------------------------------------------
    def amendment(self, day: int, parent: MinedRef) -> Draft:
        content = (
            f"{parent.author} amended the terms recorded in block {parent.block_index}, "
            f"entry {parent.entry_index}. The revised schedule moves delivery to "
            f"{self._date(day)} and adjusts the balance by {self._money(100, 9000)}. "
            f"All other terms of the original record stand unchanged."
        )
        return Draft(
            content=content,
            author=parent.author,
            intent="Amendment revising the recorded delivery schedule and balance",
            kind="amendment",
            traffic_class="clean",
            parent_refs=[
                {"block_index": parent.block_index, "entry_index": parent.entry_index}
            ],
            derivative_type="amendment",
        )

    # -- legitimate-but-flagged traffic ------------------------------------
    def flagged_business_prose(self, day: int) -> Draft:
        """Ordinary commercial language the heuristic validator treats as hostile."""
        supplier = self.rng.choice(SUPPLIERS)
        buyer = self.rng.choice(BUYERS)
        phrase, note = self.rng.choice(
            [
                ("a non-refundable deposit", "non-refundable"),
                ("a minimum order of 500 units", "minimum order"),
                ("a perpetual license to the design files", "perpetual"),
                ("an irrevocable letter of credit", "irrevocable"),
            ]
        )
        content = (
            f"{supplier} agreed to hold production capacity for {buyer} against "
            f"{phrase}, as set out in the master terms dated {self._date(day)}. "
            f"Both parties countersigned the schedule at the quarterly review."
        )
        return Draft(
            content=content,
            author=supplier,
            intent="Supply agreement signed covering reserved production capacity",
            kind="flagged_business_prose",
            traffic_class="flagged",
            metadata={"trigger_phrase": note},
            expectation="rejected_invalid",
        )

    def ambiguous_prose(self, day: int) -> Draft:
        who = self.rng.choice(BUYERS)
        content = (
            f"{who} will settle the outstanding balance soon, once the paperwork "
            f"reaches an acceptable state. The final payment figure still looks "
            f"reasonable to both sides and will be fixed later."
        )
        return Draft(
            content=content,
            author=who,
            intent="Payment record for an outstanding balance settlement",
            kind="ambiguous_prose",
            traffic_class="ambiguous",
            expectation="needs_clarification",
        )

    # -- daily mix ---------------------------------------------------------
    def day_drafts(self, day: int, count: int, parents: list[MinedRef]) -> list[Draft]:
        """Build one day's worth of drafts."""
        drafts: list[Draft] = []
        for _ in range(count):
            roll = self.rng.random()
            if roll < 0.24:
                drafts.append(self.supply_agreement(day))
            elif roll < 0.42:
                parent = self._pick_parent(parents, {"supply_agreement"})
                drafts.append(self.delivery_receipt(day, parent))
            elif roll < 0.58:
                parent = self._pick_parent(parents, {"delivery_receipt"})
                drafts.append(self.payment(day, parent))
            elif roll < 0.70:
                drafts.append(self.work_log(day))
            elif roll < 0.78:
                drafts.append(self.audit_finding(day))
            elif roll < 0.84:
                drafts.append(self.permit(day))
            elif roll < 0.89:
                parent = self._pick_parent(parents, {"supply_agreement", "permit"})
                if parent is not None:
                    drafts.append(self.amendment(day, parent))
                else:
                    drafts.append(self.work_log(day))
            elif roll < 0.94:
                transfer = self.asset_transfer(day)
                drafts.append(transfer if transfer else self.work_log(day))
            elif roll < 0.97:
                drafts.append(self.flagged_business_prose(day))
            else:
                drafts.append(self.ambiguous_prose(day))
        return drafts

    def _pick_parent(self, parents: list[MinedRef], kinds: set[str]) -> MinedRef | None:
        if not parents:
            return None
        # Prefer a recent entry of a matching kind; fall back to any recent entry.
        window = parents[-400:]
        candidates = [p for p in window if p.kind in kinds]
        pool = candidates or window
        return self.rng.choice(pool) if pool else None
