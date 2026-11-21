"""Industry definitions: what to ask public sources, and what counts as a match."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Industry:
    id: str
    label: str
    web_queries: tuple[str, ...]
    nominatim_terms: tuple[str, ...]
    photon_terms: tuple[str, ...]
    overpass_tags: tuple[tuple[str, str], ...]
    keep: tuple[str, ...]
    reject: tuple[str, ...]
    always_categories: tuple[str, ...]
    person_titles: tuple[str, ...]


INDUSTRIES: dict[str, Industry] = {
    "security": Industry(
        id="security",
        label="Security agencies",
        web_queries=("security agency {place}", "security company office {place}"),
        nominatim_terms=("security agency", "security company"),
        photon_terms=("security",),
        overpass_tags=(("office", "security"), ("shop", "security")),
        keep=("security", "guard", "surveillance"),
        reject=("social security",),
        always_categories=("security",),
        person_titles=("Head of Security", "Chief Security Officer", "Security Manager"),
    ),
    "two_way_radio": Industry(
        id="two_way_radio",
        label="Two-way radio dealers / system integrators",
        web_queries=(
            "two way radio dealer {place}",
            "walkie talkie dealer {place}",
            "wireless communication system integrator {place}",
        ),
        nominatim_terms=("wireless communication", "walkie talkie", "radio communication"),
        photon_terms=("wireless", "walkie"),
        overpass_tags=(("shop", "radiotechnics"), ("shop", "communication")),
        keep=(
            "wireless",
            "walkie",
            "two-way",
            "two way",
            "radiotechnics",
            "motorola",
            "kenwood",
            "hytera",
            "icom",
            "tetra",
            "radio communication",
            "communication system",
        ),
        reject=(
            "radiology",
            "radiologist",
            "all india radio",
            "fm radio",
            "community radio",
            "radio station",
        ),
        always_categories=("radiotechnics",),
        person_titles=("Managing Director", "Proprietor", "Sales Head", "General Manager"),
    ),
    "manufacturing": Industry(
        id="manufacturing",
        label="Manufacturing plants",
        web_queries=("manufacturing plant {place}", "factory {place}"),
        nominatim_terms=("factory", "manufacturing plant"),
        photon_terms=("factory",),
        overpass_tags=(("industrial", "factory"), ("man_made", "works")),
        keep=("factory", "manufactur", "plant", "works"),
        reject=(),
        always_categories=("factory", "works"),
        person_titles=("Plant Head", "Plant Manager", "Works Manager", "Operations Director"),
    ),
    "oil_gas": Industry(
        id="oil_gas",
        label="Oil & gas",
        web_queries=("oil gas company {place}", "petroleum depot {place}"),
        nominatim_terms=("oil depot", "petroleum", "gas company"),
        photon_terms=("petroleum", "oil"),
        overpass_tags=(("industrial", "oil"), ("industrial", "gas"), ("man_made", "petroleum_well")),
        keep=("oil", "gas", "petroleum", "refinery", "lng"),
        reject=("gas station", "fuel station", "petrol pump"),
        always_categories=("oil", "petroleum_well"),
        person_titles=("Plant Head", "Terminal Manager", "Operations Director"),
    ),
    "mining": Industry(
        id="mining",
        label="Mining",
        web_queries=("mining company {place}", "quarry {place}"),
        nominatim_terms=("mine", "quarry"),
        photon_terms=("mine", "quarry"),
        overpass_tags=(("industrial", "mine"), ("man_made", "mineshaft")),
        keep=("mine", "mining", "quarry", "mineral"),
        reject=(),
        always_categories=("mine", "mineshaft", "quarry"),
        person_titles=("Mine Manager", "Plant Head", "General Manager"),
    ),
    "logistics": Industry(
        id="logistics",
        label="Logistics / warehouses",
        web_queries=("logistics warehouse {place}", "freight company {place}"),
        nominatim_terms=("warehouse", "logistics"),
        photon_terms=("warehouse", "logistics"),
        overpass_tags=(("building", "warehouse"), ("industrial", "warehouse")),
        keep=("warehouse", "logistics", "freight", "cargo"),
        reject=(),
        always_categories=("warehouse",),
        person_titles=("Warehouse Manager", "Operations Director", "Logistics Head"),
    ),
    "airports_ports": Industry(
        id="airports_ports",
        label="Airports / ports",
        web_queries=("airport {place}", "sea port {place}"),
        nominatim_terms=("airport", "seaport"),
        photon_terms=("airport", "port"),
        overpass_tags=(("aeroway", "aerodrome"), ("industrial", "port")),
        keep=("airport", "aerodrome", "seaport", "harbour", "harbor", "port"),
        reject=("passport", "airport road"),
        always_categories=("aerodrome", "port"),
        person_titles=("Airport Director", "Port Officer", "Head of Security", "Operations Director"),
    ),
    "construction": Industry(
        id="construction",
        label="Construction / EPC",
        web_queries=("EPC contractor {place}", "construction company office {place}"),
        nominatim_terms=("construction company", "engineering contractor"),
        photon_terms=("construction",),
        overpass_tags=(("office", "construction"), ("office", "engineering")),
        keep=("construction", "contractor", "epc", "engineering"),
        reject=(),
        always_categories=("construction",),
        person_titles=("Project Director", "Project Manager", "General Manager"),
    ),
    "hotels": Industry(
        id="hotels",
        label="Hotels / venues / events",
        web_queries=("hotel {place}", "conference venue {place}"),
        nominatim_terms=("hotel", "conference centre"),
        photon_terms=("hotel",),
        overpass_tags=(("tourism", "hotel"), ("amenity", "conference_centre")),
        keep=("hotel", "resort", "venue", "conference", "banquet"),
        reject=(),
        always_categories=("hotel", "conference_centre"),
        person_titles=("General Manager", "Security Manager", "Operations Manager"),
    ),
    "hospitals": Industry(
        id="hospitals",
        label="Hospitals",
        web_queries=("hospital {place}",),
        nominatim_terms=("hospital",),
        photon_terms=("hospital",),
        overpass_tags=(("amenity", "hospital"),),
        keep=("hospital", "medical college"),
        reject=("veterinary", "animal"),
        always_categories=("hospital",),
        person_titles=("Medical Superintendent", "Hospital Administrator", "Head of Security"),
    ),
    "colleges": Industry(
        id="colleges",
        label="Colleges / language training",
        web_queries=("college {place}", "language training institute {place}"),
        nominatim_terms=("college", "language school"),
        photon_terms=("college", "university"),
        overpass_tags=(("amenity", "college"), ("amenity", "university"), ("amenity", "language_school")),
        keep=("college", "university", "institute", "language"),
        reject=(),
        always_categories=("college", "university", "language_school"),
        person_titles=("Principal", "Director", "Dean", "Registrar"),
    ),
    "bpo": Industry(
        id="bpo",
        label="BPOs",
        web_queries=("BPO company {place}", "call center {place}"),
        nominatim_terms=("call center", "BPO"),
        photon_terms=("call center",),
        overpass_tags=(("office", "telecommunication"),),
        keep=("bpo", "call cent", "call centre", "business process"),
        reject=(),
        always_categories=(),
        person_titles=("Center Head", "Operations Director", "Site Head"),
    ),
    "government": Industry(
        id="government",
        label="Government / public safety",
        web_queries=("district collector office {place}", "police commissionerate {place}"),
        nominatim_terms=("police", "municipal office", "collector office"),
        photon_terms=("police", "municipal"),
        overpass_tags=(("amenity", "police"), ("office", "government"), ("amenity", "fire_station")),
        keep=("police", "fire", "municipal", "collector", "government", "nagar palika"),
        reject=(),
        always_categories=("police", "fire_station", "government"),
        person_titles=("Superintendent of Police", "Commissioner", "Chief Officer", "Head of Security"),
    ),
}


def get_industry(industry_id: str) -> Industry:
    try:
        return INDUSTRIES[industry_id]
    except KeyError as exc:
        raise ValueError(f"Unknown industry: {industry_id}") from exc


def industry_options() -> list[dict[str, str]]:
    return [{"id": item.id, "label": item.label} for item in INDUSTRIES.values()]
