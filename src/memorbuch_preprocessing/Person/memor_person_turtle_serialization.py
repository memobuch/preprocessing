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
CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
EDTF = Namespace("http://id.loc.gov/datatypes/edtf/")
DERLA = Namespace("https://gams.uni-graz.at/")


# ============================================================================
# SANITIZATION & EDTF DATE HELPERS
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


def _convert_to_edtf(date_str: str) -> Optional[Literal]:
    """
    Parses common date inputs and outputs strict EDTF-level1 literals.
    Handles exact dates (YYYY-MM-DD) and fuzzy dates (YYYY).
    """
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    try:
        if "/" in s:
            day, month, year = s.split("/")
            clean_date = f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        elif "." in s:
            day, month, year = s.split(".")
            clean_date = f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        elif "-" in s:
            clean_date = s  # Already ISO format
        elif len(s) == 4:
            clean_date = s  # Just the year (Valid EDTF)
        else:
            return None

        return Literal(clean_date, datatype=EDTF["EDTF-level1"])
    except Exception:
        logging.warning(f"Could not parse date to EDTF: {date_str}")
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
    g.bind("geo", GEO)
    g.bind("edtf", EDTF)
    g.bind("cidoc", CIDOC)
    g.bind("derla", DERLA)
    g.bind("memor", MEMOR)

    # ------------------------------------------------------------------
    # PERSON
    # ------------------------------------------------------------------
    person_uri = URIRef(f"{MEMOR_BASE_URI}objects/{person.id}")

    g.add((person_uri, RDF.type, MEMOR.victim))
    g.add((person_uri, RDF.type, FOAF.Person))
    g.add((person_uri, RDF.type, SCHEMA.Person))

    full_name = f"{person.first_name} {person.last_name}" if person.first_name and person.last_name else "Unknown"
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
    if person.alternative_spelling:
        g.add((person_uri, SCHEMA.alternateName, _safe_literal(person.alternative_spelling)))

    # --- Gender ---
    if person.gender:
        g.add((person_uri, SCHEMA.gender, _safe_literal(person.gender)))

    # --- Biography ---
    if person.biography_text:
        g.add((person_uri, DCTERMS.description, _safe_literal(person.biography_text, lang="de")))

    # --- Birth ---
    _add_birth_event(g, person_uri, person.birth_date, person.birth_place, lat=None, lon=None)

    # --- Death ---
    _add_death_event(g, person_uri, person.death_date, person.death_place, person.death_latitude,
                     person.death_longitude)

    # --- Voluntary residence ---
    if person.voluntary_address:
        vol_label = MemorVocab.EVENT_TYPES.get("voluntary-residence", {}).get("label", "Letzte Freiwillige Wohnadresse")
        _add_residence_event(
            g, person_uri,
            event_local_name="voluntary-residence",
            ontology_class=MEMOR["voluntary-residence"],
            address=person.voluntary_address,
            lat=person.voluntary_latitude,
            lon=person.voluntary_longitude,
            label=vol_label,
        )

    # --- Forced residence ---
    if person.forced_address:
        forced_label = MemorVocab.EVENT_TYPES.get("forced-residence", {}).get("label", "Erzwungene Wohnadresse")
        _add_residence_event(
            g, person_uri,
            event_local_name="forced-residence",
            ontology_class=MEMOR["forced-residence"],
            address=person.forced_address,
            lat=person.forced_latitude,
            lon=person.forced_longitude,
            label=forced_label,
        )

    # --- Prosecution events (Directly mapped to Vocab Keys) ---
    if person.victim_category:
        for category in person.victim_category:
            category = (category or "").strip()
            if not category: continue
            _add_prosecution_event(g, person_uri, person.id, category)

    # --- Memorial signs ---
    memorial_signs_attr = getattr(person, "memorial_signs", None) or getattr(person, "memorial_sign", None)
    if memorial_signs_attr:
        for sign in memorial_signs_attr:
            if sign and sign.strip():
                # Assuming 'sign' here is a resolvable URI to DERLA or a string identifier.
                # Adjust to URIRef(sign.strip()) if it's an absolute URI
                g.add((person_uri, MEMOR.hasMemorialSign, _safe_literal(sign.strip())))

    # --- Literature ---
    if person.literature:
        g.add((person_uri, MEMOR.hasLiteratureReference, _safe_literal(person.literature)))

    # ------------------------------------------------------------------
    # SOURCES (images + documents)
    # ------------------------------------------------------------------
    for i, image in enumerate(person.images):
        image_dsid = os.path.basename(image.source_path).upper()
        image_uri = URIRef(f"{MEMOR_BASE_URI}api/v1/projects/memor/objects/{person.id}/datastreams/{image_dsid}")
        g.add((person_uri, MEMOR.hasSource, image_uri))
        _add_image_resource(g, image_uri, image.title, image.desc)

    for document in person.documents:
        doc_dsid = os.path.basename(document.source_path).upper()
        doc_uri = URIRef(f"{MEMOR_BASE_URI}api/v1/projects/memor/objects/{person.id}/datastreams/{doc_dsid}")
        g.add((person_uri, MEMOR.hasSource, doc_uri))
        _add_document_resource(g, doc_uri, document.title, document.desc)

    # ------------------------------------------------------------------
    # HAFT / FLUCHT EVENTS
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

    # ------------------------------------------------------------------
    # SERIALIZE
    # ------------------------------------------------------------------
    from memorbuch_preprocessing.MemorStatics import MemorStatics
    ttl_file_path = os.path.join(MemorStatics.OUTPUT_DIR, str(person.id), "SEMANTIC_STATEMENTS.ttl")
    g.serialize(destination=ttl_file_path, format="turtle", encoding="utf-8")
    logging.debug(f"Generated SEMANTIC_STATEMENTS.ttl at: {ttl_file_path}")
    return ttl_file_path


# ============================================================================
# EVENT BUILDERS (GeoSPARQL & EDTF Compliant)
# ============================================================================

def _add_event_base_types(g: Graph, event_uri: URIRef) -> None:
    g.add((event_uri, RDF.type, MEMOR.event))
    g.add((event_uri, RDF.type, CIDOC.E5_Event))


def _add_event_place_geometry(g: Graph, event_uri: URIRef, place_name: Optional[str], lat, lon) -> None:
    """
    Separates the spatial logic: Event -> Place -> Geometry (WKT).
    This complies with GeoSPARQL and avoids CIDOC logic violations.
    """
    if not place_name and (lat is None or lon is None):
        return

    place_uri = URIRef(str(event_uri) + "_place")
    g.add((event_uri, MEMOR["took-place-at"], place_uri))
    g.add((place_uri, RDF.type, MEMOR.place))

    if place_name:
        g.add((place_uri, RDFS.label, _safe_literal(place_name, lang="de")))

    if lat is not None and lon is not None:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            geom_uri = URIRef(str(place_uri) + "_geom")
            g.add((place_uri, GEO.hasGeometry, geom_uri))
            g.add((geom_uri, RDF.type, GEO.Geometry))
            # WKT Standard: LONGITUDE LATITUDE
            wkt_str = f"POINT({lon_f} {lat_f})"
            g.add((geom_uri, GEO.asWKT, Literal(wkt_str, datatype=GEO.wktLiteral)))
        except (TypeError, ValueError):
            logging.warning(f"Invalid coordinates for {event_uri}: lat={lat!r}, lon={lon!r}")


def _add_birth_event(g: Graph, person_uri: URIRef, birth_date: Optional[str], birth_place: Optional[str], lat,
                     lon) -> None:
    birth_uri = URIRef(str(person_uri) + "/events/birth")
    g.add((birth_uri, RDF.type, MEMOR.birth))
    _add_event_base_types(g, birth_uri)

    g.add((birth_uri, RDFS.label, _safe_literal(f"Geburt von {str(person_uri).split('/')[-1]}", lang="de")))
    g.add((person_uri, MEMOR.hasEvent, birth_uri))

    edtf_literal = _convert_to_edtf(birth_date)
    if edtf_literal:
        g.add((birth_uri, MEMOR.hasDate, edtf_literal))

    _add_event_place_geometry(g, birth_uri, birth_place, lat, lon)


def _add_death_event(g: Graph, person_uri: URIRef, death_date: Optional[str], death_place: Optional[str], lat,
                     lon) -> None:
    death_uri = URIRef(str(person_uri) + "/events/death")
    g.add((death_uri, RDF.type, MEMOR.death))
    _add_event_base_types(g, death_uri)

    g.add((death_uri, RDFS.label, _safe_literal(f"Tod von {str(person_uri).split('/')[-1]}", lang="de")))
    g.add((person_uri, MEMOR.hasEvent, death_uri))

    edtf_literal = _convert_to_edtf(death_date)
    if edtf_literal:
        g.add((death_uri, MEMOR.hasDate, edtf_literal))

    _add_event_place_geometry(g, death_uri, death_place, lat, lon)


def _add_residence_event(g: Graph, person_uri: URIRef, *, event_local_name: str, ontology_class: URIRef,
                         address: Optional[str], lat, lon, label: str) -> None:
    event_uri = URIRef(str(person_uri) + f"/events/{event_local_name}")
    g.add((event_uri, RDF.type, ontology_class))
    _add_event_base_types(g, event_uri)

    g.add((event_uri, RDFS.label, _safe_literal(label, lang="de")))
    g.add((person_uri, MEMOR.hasEvent, event_uri))

    _add_event_place_geometry(g, event_uri, address, lat, lon)


def _add_prosecution_event(g: Graph, person_uri: URIRef, person_id: str, category_key: str) -> None:
    """
    Directly leverages the strictly aligned vocabulary. The category_key 
    maps 1:1 to the ontology class (e.g., ns-opposition -> memor:ns-opposition).
    """
    category_vocab = MemorVocab.VICTIM_CATEGORY_TYPES.get(category_key)
    if not category_vocab:
        logging.warning(f"Category '{category_key}' not found in MemorVocab. Skipping.")
        return

    prosecution_uri = URIRef(f"{MEMOR_BASE_URI}objects/{person_id}/events/prosecution_{category_key}")

    # Use dict lookup to safely inject the kebab-case key into the Namespace
    g.add((prosecution_uri, RDF.type, MEMOR[category_key]))
    g.add((prosecution_uri, RDF.type, MEMOR.prosecution))
    _add_event_base_types(g, prosecution_uri)

    label = category_vocab.get("label", category_key)
    g.add((prosecution_uri, RDFS.label, _safe_literal(label, lang="de")))
    g.add((person_uri, MEMOR.hasEvent, prosecution_uri))


def _add_haft_flucht_event(g: Graph, event_uri: URIRef, event, person_uri: URIRef) -> None:
    _add_event_base_types(g, event_uri)

    # Aligning legacy string identifiers with modern vocab keys
    if event.type == "haft" or event.type == "imprisonment":
        g.add((event_uri, RDF.type, MEMOR.imprisonment))
    elif event.type == "flucht" or event.type == "flight":
        g.add((event_uri, RDF.type, MEMOR.flight))

    if event.title:
        g.add((event_uri, RDFS.label, _safe_literal(event.title)))
    if event.description:
        g.add((event_uri, DCTERMS.description, _safe_literal(event.description)))

    edtf_literal = _convert_to_edtf(event.date)
    if edtf_literal:
        g.add((event_uri, MEMOR.hasDate, edtf_literal))

    _add_event_place_geometry(g, event_uri, getattr(event, "location", None), event.lat,
                              getattr(event, "long", getattr(event, "lon", None)))

    g.add((person_uri, MEMOR.hasEvent, event_uri))


# ============================================================================
# RESOURCE BUILDERS
# ============================================================================

def _add_image_resource(g: Graph, image_uri: URIRef, title: Optional[str], description: Optional[str]) -> None:
    g.add((image_uri, RDF.type, MEMOR.image))
    g.add((image_uri, RDF.type, SCHEMA.ImageObject))
    if title:
        g.add((image_uri, RDFS.label, _safe_literal(title)))
    if description:
        g.add((image_uri, DCTERMS.description, _safe_literal(description)))


def _add_document_resource(g: Graph, doc_uri: URIRef, title: Optional[str], description: Optional[str]) -> None:
    g.add((doc_uri, RDF.type, MEMOR.source))
    g.add((doc_uri, RDF.type, SCHEMA.DigitalDocument))
    if title:
        g.add((doc_uri, RDFS.label, _safe_literal(title)))
    if description:
        g.add((doc_uri, DCTERMS.description, _safe_literal(description)))