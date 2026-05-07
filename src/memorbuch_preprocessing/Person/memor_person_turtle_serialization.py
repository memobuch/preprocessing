"""
Turtle (SEMANTIC_STATEMENTS.ttl) Generation for MEMOR Project
=============================================================

REFACTORED to match the new MEMOR ontology
(https://www.ns-opfer-graz.at/ontology#).

Key changes vs. the previous version
------------------------------------
- Person typed as `memor:victim` (was: `memor:HolocaustVictim`).
- All event linking goes through `memor:hasEvent` — the canonical
  ontology property.
- `memor:voluntary_residence` is now an EVENT class
  (subClassOf `memor:event`), NOT a property pointing at a Place.
  Address and coordinates sit directly on the event resource.
  `forced_residence` is modeled symmetrically (flagged: not yet in
  ontology — see notes at the bottom of this file).
- Birth and death events are explicitly typed `memor:birth` /
  `memor:death` in addition to the inherited `bio:` / `cidoc:` types.
- Prosecution events are typed with their specific subclass
  (e.g. `memor:widerstand_politisch`) instead of a generic
  `memor:prosecution/{slug}` URI. A name map handles the gap between
  vocab keys and ontology class names.
- Literature uses the canonical `memor:hasLiteratureReference`.
- Images typed as `memor:image` and linked via `memor:hasSource`.

When ingested via gams-packager + pyrilo, GAMS5 loads these triples into
the QLever triple store, enabling SPARQL queries across all MEMOR
persons.
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, SKOS, XSD

from memorbuch_preprocessing.MemorVocab import MemorVocab


# ============================================================================
# NAMESPACES
# ============================================================================

MEMOR_BASE_URI = "https://www.ns-opfer-graz.at/"
MEMOR_ONTOLOGY_URI = MEMOR_BASE_URI + "ontology#"

MEMOR = Namespace(MEMOR_ONTOLOGY_URI)
SCHEMA = Namespace("http://schema.org/")
BIO = Namespace("http://purl.org/vocab/bio/0.1/")
WGS84 = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")


# ============================================================================
# PROSECUTION CATEGORY -> ONTOLOGY CLASS MAP
# ============================================================================
# Maps the keys used in MemorVocab.VICTIM_CATEGORY_TYPES to the local part
# of the corresponding `memor:*` prosecution subclass in the ontology.
#
# WARNING: Several vocab keys have NO matching ontology class. They are
# listed below the active map, commented out. Decide per category:
#   - add the class to the ontology (preferred), or
#   - drop the category from the vocab.
PROSECUTION_CLASS_MAP = {
    "widerstand;politisch":             "widerstand_politisch",
    "widerstand;religiös":              "widerstand_religioes",
    "widerstand;individuell":           "widerstand_individuell",
    "widerstand;deserteure":            "widerstand_deserteure",
    "zeugenjehovas":                    "zeugenjehovas",
    "jüdischeopfer;jüdisch":            "juedischeopfer_juedisch",
    "jüdischeopfer;als Jude verfolgt":  "juedischeopfer_als-Jude-verfolgt",
    "roma":                             "roma",
    "euthanasieopfer":                  "euthanasieopfer",
    "homosexuelleopfer":                "homosexuelleopfer",
    "asoziale":                         "asoziale",
    "spanienkämpfer":                   "spanienkaempfer",
    # NOT IN ONTOLOGY YET — add classes (or drop from vocab) before enabling:
    # "opfernsjustiz":   "opfer_ns_justiz",
    # "zwangsarbeiter":  "zwangsarbeiter",
    # "alliierte":       "alliierte_soldaten",
    # "zivileopfer":     "zivile_opfer",
}


# ============================================================================
# SANITIZATION & DATE HELPERS
# ============================================================================

def _sanitize_for_turtle(text: str) -> Optional[str]:
    """Strip BOM, C0/C1 control chars, zero-width chars (Google Sheets junk)."""
    if text is None:
        return None
    text = text.replace("\ufeff", "")
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"[\u0080-\u009f]", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _safe_literal(value, **kwargs) -> Literal:
    """Create an rdflib Literal with sanitized text content."""
    if isinstance(value, str):
        value = _sanitize_for_turtle(value)
    return Literal(value, **kwargs)


def _convert_to_xsd_date(date_str: str) -> Optional[str]:
    """DD/MM/YYYY or DD.MM.YYYY -> YYYY-MM-DD; pass-through for ISO; YYYY -> YYYY-01-01."""
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    try:
        if "/" in s:
            day, month, year = s.split("/")
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        if "." in s:
            day, month, year = s.split(".")
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        if "-" in s:
            return s
        if len(s) == 4:
            return f"{s}-01-01"
    except Exception:
        pass
    return None


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def write_as_turtle(person) -> Optional[str]:
    """Generate SEMANTIC_STATEMENTS.ttl for a MemorPerson."""
    g = Graph()

    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("schema", SCHEMA, override=True, replace=True)
    g.bind("bio", BIO)
    g.bind("skos", SKOS)
    g.bind("wgs84_pos", WGS84)
    g.bind("cidoc", CIDOC)
    g.bind("memor", MEMOR)

    # ------------------------------------------------------------------
    # PERSON
    # ------------------------------------------------------------------
    person_uri = URIRef(f"{MEMOR_BASE_URI}objects/{person.id}")

    # memor:victim is canonical; foaf:Person + schema:Person stay for
    # cross-vocabulary interop (federated queries, generic clients).
    g.add((person_uri, RDF.type, MEMOR.victim))
    g.add((person_uri, RDF.type, FOAF.Person))
    g.add((person_uri, RDF.type, SCHEMA.Person))

    full_name = (
        f"{person.first_name} {person.last_name}"
        if person.first_name and person.last_name
        else "Unknown"
    )
    g.add((person_uri, RDFS.label, _safe_literal(full_name)))

    # --- Names ---
    if person.first_name:
        g.add((person_uri, FOAF.givenName, _safe_literal(person.first_name)))
        g.add((person_uri, SCHEMA.givenName, _safe_literal(person.first_name)))
    if person.last_name:
        g.add((person_uri, FOAF.familyName, _safe_literal(person.last_name)))
        g.add((person_uri, SCHEMA.familyName, _safe_literal(person.last_name)))
    if person.first_name and person.last_name:
        g.add((person_uri, FOAF.name, _safe_literal(full_name)))
        g.add((person_uri, SCHEMA.name, _safe_literal(full_name)))
    if person.maiden_name:
        g.add((person_uri, SCHEMA.additionalName, _safe_literal(person.maiden_name)))
    if person.alternative_spelling:
        g.add((person_uri, SCHEMA.alternateName, _safe_literal(person.alternative_spelling)))
        g.add((person_uri, SKOS.altLabel, _safe_literal(person.alternative_spelling)))

    # --- Gender ---
    if person.gender:
        g.add((person_uri, SCHEMA.gender, _safe_literal(person.gender)))
        g.add((person_uri, FOAF.gender, _safe_literal(person.gender)))

    # --- Biography ---
    if person.biography_text:
        g.add((person_uri, DCTERMS.description, _safe_literal(person.biography_text, lang="de")))
        g.add((person_uri, SCHEMA.description, _safe_literal(person.biography_text, lang="de")))
        g.add((person_uri, BIO.biography, _safe_literal(person.biography_text, lang="de")))

    # --- Birth (literal data on person + memor:birth event) ---
    if person.birth_date:
        d = _convert_to_xsd_date(person.birth_date)
        if d:
            g.add((person_uri, SCHEMA.birthDate, _safe_literal(d, datatype=XSD.date)))
        g.add((person_uri, FOAF.birthday, _safe_literal(person.birth_date)))
    if person.birth_place:
        g.add((person_uri, SCHEMA.birthPlace, _safe_literal(person.birth_place)))
        # NOTE: birth coords not yet captured in the data model.
        _add_birth_event(g, person_uri, person.birth_date, person.birth_place,
                         lat=None, lon=None)

    # --- Death (literal data on person + memor:death event) ---
    if person.death_date:
        d = _convert_to_xsd_date(person.death_date)
        if d:
            g.add((person_uri, SCHEMA.deathDate, _safe_literal(d, datatype=XSD.date)))
    if person.death_place:
        g.add((person_uri, SCHEMA.deathPlace, _safe_literal(person.death_place)))
        _add_death_event(g, person_uri, person.death_date, person.death_place,
                         person.death_latitude, person.death_longitude)

    # --- Voluntary residence (NOW AN EVENT) ---
    if person.voluntary_address:
        vol_label = MemorVocab.EVENT_TYPES.get("voluntary_residence", {}).get(
            "label", "Letzte Freiwillige Wohnadresse"
        )
        _add_residence_event(
            g, person_uri,
            event_local_name="voluntary_residence",
            ontology_class=MEMOR.voluntary_residence,
            address=person.voluntary_address,
            lat=person.voluntary_latitude,
            lon=person.voluntary_longitude,
            label=vol_label,
        )

    # --- Forced residence (event, modeled symmetrically) ---
    # NOTE: memor:forced_residence is not yet declared in the ontology.
    if person.forced_address:
        forced_label = MemorVocab.EVENT_TYPES.get("forced_residence", {}).get(
            "label", "Erzwungene Wohnadresse"
        )
        _add_residence_event(
            g, person_uri,
            event_local_name="forced_residence",
            ontology_class=MEMOR.forced_residence,
            address=person.forced_address,
            lat=person.forced_latitude,
            lon=person.forced_longitude,
            label=forced_label,
        )

    # --- Prosecution events (one per victim category) ---
    if person.victim_category:
        for category in person.victim_category:
            category = (category or "").strip()
            if not category:
                continue
            _add_prosecution_event(g, person_uri, person.id, category)

    # --- Youth status (kept as a flat boolean for now; not in ontology) ---
    if person.is_youth:
        g.add((person_uri, MEMOR.isYouth, Literal(True)))

    # --- Memorial signs (kept; not in ontology yet) ---
    memorial_signs_attr = (
        getattr(person, "memorial_signs", None)
        or getattr(person, "memorial_sign", None)
    )
    if memorial_signs_attr:
        for sign in memorial_signs_attr:
            if sign and sign.strip():
                g.add((person_uri, DCTERMS.relation, _safe_literal(sign.strip())))
                g.add((person_uri, MEMOR.memorialSign, _safe_literal(sign.strip())))

    # --- Literature (canonical ontology property) ---
    if person.literature:
        g.add((person_uri, MEMOR.hasLiteratureReference, _safe_literal(person.literature)))

    # ------------------------------------------------------------------
    # SOURCES (images + documents) — linked via memor:hasSource
    # ------------------------------------------------------------------
    for i, image in enumerate(person.images):
        image_dsid = os.path.basename(image.source_path).upper()
        image_uri = URIRef(
            f"{MEMOR_BASE_URI}api/v1/projects/memor/objects/{person.id}/datastreams/{image_dsid}"
        )
        g.add((person_uri, MEMOR.hasSource, image_uri))
        # Cross-vocab links — useful for generic image clients.
        g.add((person_uri, SCHEMA.image, image_uri))
        if i == 0:
            g.add((person_uri, FOAF.depiction, image_uri))
        _add_image_resource(g, image_uri, image.title, image.desc)

    for document in person.documents:
        doc_dsid = os.path.basename(document.source_path).upper()
        doc_uri = URIRef(
            f"{MEMOR_BASE_URI}api/v1/projects/memor/objects/{person.id}/datastreams/{doc_dsid}"
        )
        g.add((person_uri, MEMOR.hasSource, doc_uri))
        g.add((person_uri, DCTERMS.relation, doc_uri))
        _add_document_resource(g, doc_uri, document.title, document.desc)

    # ------------------------------------------------------------------
    # HAFT / FLUCHT EVENTS (from MemorEvent objects)
    # ------------------------------------------------------------------
    for event in person.events:
        event_uri = URIRef(f"{MEMOR_BASE_URI}objects/{person.id}/events/{event.id}")
        _add_haft_flucht_event(g, event_uri, event, person_uri)

    # ------------------------------------------------------------------
    # PROVENANCE
    # ------------------------------------------------------------------
    g.add((person_uri, DCTERMS.creator, _safe_literal("Born digital - memor project GAMS")))
    g.add((person_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))
    g.add((person_uri, DCTERMS.rightsHolder, _safe_literal("MEMOR Project")))
    g.add((person_uri, DCTERMS.license,
           URIRef("https://creativecommons.org/licenses/by-nc/4.0/")))
    g.add((person_uri, DCTERMS.created,
           _safe_literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

    # ------------------------------------------------------------------
    # SERIALIZE (UTF-8 — readable umlauts, no \uXXXX escaping)
    # ------------------------------------------------------------------
    from memorbuch_preprocessing.MemorStatics import MemorStatics
    ttl_file_path = os.path.join(
        MemorStatics.OUTPUT_DIR, str(person.id), "SEMANTIC_STATEMENTS.ttl"
    )
    g.serialize(destination=ttl_file_path, format="turtle", encoding="utf-8")
    logging.debug(f"Generated SEMANTIC_STATEMENTS.ttl at: {ttl_file_path}")
    return ttl_file_path


# ============================================================================
# EVENT BUILDERS
# ============================================================================

def _add_event_base_types(g: Graph, event_uri: URIRef) -> None:
    """Types every memor:event subclass should carry."""
    g.add((event_uri, RDF.type, MEMOR.event))
    g.add((event_uri, RDF.type, CIDOC.E5_Event))


def _add_geo_point(g: Graph, event_uri: URIRef, lat, lon) -> None:
    """Attach WGS84 coordinates to an event/place when present and parseable."""
    if lat is None or lon is None:
        return
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        logging.warning(f"Invalid coordinates for {event_uri}: lat={lat!r}, lon={lon!r}")
        return
    g.add((event_uri, RDF.type, WGS84.Point))
    g.add((event_uri, WGS84.lat, Literal(lat_f, datatype=XSD.float)))
    g.add((event_uri, WGS84.long, Literal(lon_f, datatype=XSD.float)))


def _add_birth_event(g: Graph, person_uri: URIRef,
                     birth_date: Optional[str], birth_place: Optional[str],
                     lat, lon) -> None:
    """memor:birth — subclass of memor:event, bio:Birth, cidoc:E67_Birth."""
    birth_uri = URIRef(str(person_uri) + "/events/birth")
    g.add((birth_uri, RDF.type, MEMOR.birth))
    _add_event_base_types(g, birth_uri)
    g.add((birth_uri, RDF.type, BIO.Birth))
    g.add((birth_uri, RDF.type, CIDOC.E67_Birth))

    g.add((birth_uri, RDFS.label,
           _safe_literal(f"Geburt von {str(person_uri).split('/')[-1]}")))
    g.add((birth_uri, BIO.principal, person_uri))

    if birth_date:
        d = _convert_to_xsd_date(birth_date)
        if d:
            g.add((birth_uri, BIO.date, _safe_literal(d, datatype=XSD.date)))
    if birth_place:
        g.add((birth_uri, BIO.place, _safe_literal(birth_place)))
    _add_geo_point(g, birth_uri, lat, lon)

    g.add((person_uri, MEMOR.hasEvent, birth_uri))


def _add_death_event(g: Graph, person_uri: URIRef,
                     death_date: Optional[str], death_place: Optional[str],
                     lat, lon) -> None:
    """memor:death — subclass of memor:event, cidoc:E69_Death."""
    death_uri = URIRef(str(person_uri) + "/events/death")
    g.add((death_uri, RDF.type, MEMOR.death))
    _add_event_base_types(g, death_uri)
    g.add((death_uri, RDF.type, BIO.Death))
    g.add((death_uri, RDF.type, CIDOC.E69_Death))

    g.add((death_uri, RDFS.label,
           _safe_literal(f"Tod von {str(person_uri).split('/')[-1]}")))
    g.add((death_uri, BIO.principal, person_uri))

    if death_date:
        d = _convert_to_xsd_date(death_date)
        if d:
            g.add((death_uri, BIO.date, _safe_literal(d, datatype=XSD.date)))
    if death_place:
        g.add((death_uri, BIO.place, _safe_literal(death_place)))
    _add_geo_point(g, death_uri, lat, lon)

    g.add((person_uri, MEMOR.hasEvent, death_uri))


def _add_residence_event(g: Graph, person_uri: URIRef, *,
                         event_local_name: str,
                         ontology_class: URIRef,
                         address: Optional[str],
                         lat, lon,
                         label: str) -> None:
    """
    Voluntary or forced residence as a first-class event.

    Per the new ontology, voluntary_residence is a subclass of memor:event,
    so address + coordinates live directly on the event resource.
    No separate Place node is created.
    """
    event_uri = URIRef(str(person_uri) + f"/events/{event_local_name}")
    g.add((event_uri, RDF.type, ontology_class))
    _add_event_base_types(g, event_uri)

    g.add((event_uri, RDFS.label, _safe_literal(label, lang="de")))
    if address:
        g.add((event_uri, SCHEMA.address, _safe_literal(address)))
        g.add((event_uri, BIO.place, _safe_literal(address)))

    _add_geo_point(g, event_uri, lat, lon)
    g.add((person_uri, MEMOR.hasEvent, event_uri))


def _add_prosecution_event(g: Graph, person_uri: URIRef,
                           person_id: str, category_key: str) -> None:
    """
    Per-person prosecution event, typed as the specific ontology subclass
    (e.g. memor:widerstand_politisch) AND as memor:prosecution + memor:event.
    """
    category_vocab = MemorVocab.VICTIM_CATEGORY_TYPES.get(category_key)
    if not category_vocab:
        # Unknown vocab key — fail loudly, this is a data error.
        raise ValueError(
            f"Category '{category_key}' not found in MemorVocab.VICTIM_CATEGORY_TYPES."
        )

    class_local = PROSECUTION_CLASS_MAP.get(category_key)
    if not class_local:
        # Vocab key exists but no matching ontology class. Soft-fail to avoid
        # blocking ingest while the ontology is being filled in.
        logging.warning(
            f"No memor:* prosecution class mapped for category '{category_key}'. "
            f"Skipping prosecution event. Add the class to the ontology and to "
            f"PROSECUTION_CLASS_MAP."
        )
        return

    prosecution_uri = URIRef(
        f"{MEMOR_BASE_URI}objects/{person_id}/events/prosecution_{class_local}"
    )

    # Specific subclass + parent + base event types
    g.add((prosecution_uri, RDF.type, URIRef(MEMOR_ONTOLOGY_URI + class_local)))
    g.add((prosecution_uri, RDF.type, MEMOR.prosecution))
    _add_event_base_types(g, prosecution_uri)

    label = category_vocab.get("label", category_key)
    g.add((prosecution_uri, RDFS.label, _safe_literal(label, lang="de")))

    g.add((person_uri, MEMOR.hasEvent, prosecution_uri))


def _add_haft_flucht_event(g: Graph, event_uri: URIRef, event, person_uri: URIRef) -> None:
    """
    Imprisonment / flight events.

    NOTE: There are no dedicated `memor:imprisonment` or `memor:flight`
    classes in the ontology yet. We mint local subclasses here. Recommend
    adding them to the ontology so the SPARQL graph stays self-describing.
    """
    _add_event_base_types(g, event_uri)

    if event.type == "haft":
        g.add((event_uri, RDF.type, MEMOR.imprisonment))
    elif event.type == "flucht":
        g.add((event_uri, RDF.type, MEMOR.flight))

    if event.title:
        g.add((event_uri, RDFS.label, _safe_literal(event.title)))
        g.add((event_uri, DCTERMS.title, _safe_literal(event.title)))
    if event.description:
        g.add((event_uri, DCTERMS.description, _safe_literal(event.description)))
    if event.date:
        d = _convert_to_xsd_date(event.date)
        if d:
            g.add((event_uri, DCTERMS.date, _safe_literal(d, datatype=XSD.date)))
        g.add((event_uri, MEMOR.date, _safe_literal(event.date)))
    if event.location:
        g.add((event_uri, BIO.place, _safe_literal(event.location)))
        g.add((event_uri, SCHEMA.location, _safe_literal(event.location)))

    _add_geo_point(g, event_uri, event.lat, event.long)

    g.add((event_uri, BIO.principal, person_uri))
    g.add((event_uri, DCTERMS.creator, _safe_literal("Born digital - memor project GAMS")))
    g.add((event_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))

    # Person -> event linkage uses the canonical property
    g.add((person_uri, MEMOR.hasEvent, event_uri))


# ============================================================================
# RESOURCE BUILDERS (sources)
# ============================================================================

def _add_image_resource(g: Graph, image_uri: URIRef,
                        title: Optional[str], description: Optional[str]) -> None:
    """memor:image (subclass of memor:source) + cross-vocab types."""
    g.add((image_uri, RDF.type, MEMOR.image))
    g.add((image_uri, RDF.type, MEMOR.source))
    g.add((image_uri, RDF.type, SCHEMA.ImageObject))
    g.add((image_uri, RDF.type, FOAF.Image))
    if title:
        g.add((image_uri, DCTERMS.title, _safe_literal(title)))
        g.add((image_uri, RDFS.label, _safe_literal(title)))
    if description:
        g.add((image_uri, DCTERMS.description, _safe_literal(description)))
    g.add((image_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))


def _add_document_resource(g: Graph, doc_uri: URIRef,
                           title: Optional[str], description: Optional[str]) -> None:
    """Document typed as memor:source (no dedicated subclass yet)."""
    g.add((doc_uri, RDF.type, MEMOR.source))
    g.add((doc_uri, RDF.type, SCHEMA.DigitalDocument))
    g.add((doc_uri, RDF.type, FOAF.Document))
    if title:
        g.add((doc_uri, DCTERMS.title, _safe_literal(title)))
        g.add((doc_uri, RDFS.label, _safe_literal(title)))
    if description:
        g.add((doc_uri, DCTERMS.description, _safe_literal(description)))
    g.add((doc_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))


# ============================================================================
# OPEN ITEMS — ontology gaps surfaced by this refactor
# ============================================================================
# The following items are written into the .ttl by this module but are NOT
# yet declared in the MEMOR ontology. Each should either (a) be added to the
# ontology, or (b) reconsidered here:
#
#   memor:forced_residence       subClassOf memor:event
#   memor:imprisonment           subClassOf memor:event   (Haft)
#   memor:flight                 subClassOf memor:event   (Flucht)
#   memor:isYouth                rdfs:Property            (or use dcterms:subject)
#   memor:memorialSign           rdfs:Property
#   memor:date                   rdfs:Property            (raw, non-XSD date string)
#   memor:gender                 rdfs:Property            (currently only literal)
#
# Vocab keys without a prosecution class:
#   opfernsjustiz, zwangsarbeiter, alliierte, zivileopfer
#
# Ontology issues spotted:
#   - `memor:euthanasieopfer a owl:Classs` — typo (extra "s").
#   - `memor:victim a owl:Class, foaf:Person, schema:Person` likely intends
#     `rdfs:subClassOf foaf:Person, schema:Person` instead.
#   - `memor:event` is `rdfs:subClassOf wgs84_pos:Point` — this forces every
#     event (including prosecution, which is abstract) to be a geo point.
#     Consider relaxing: only attach wgs84_pos:Point on instances that have
#     coordinates.