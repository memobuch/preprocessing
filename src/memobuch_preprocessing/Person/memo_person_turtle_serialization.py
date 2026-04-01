"""
Turtle (SEMANTIC_STATEMENTS.ttl) Generation for MEMO Project
=============================================================

Generates SEMANTIC_STATEMENTS.ttl per digital object / person.
When ingested via gams-packager + pyrilo, GAMS5 automatically loads
these triples into the Blazegraph triple store, enabling SPARQL queries
across all MEMO persons.

Produces semantically identical output to the existing RDF.xml
(memo_person_rdf_serialization.py) but in Turtle format.

Uses rdflib for proper Turtle serialization with clean prefix handling.

Ontologies Used (same as RDF.xml):
- FOAF: Person information
- Schema.org: Modern person/bio data
- Bio: Biographical events
- WGS84: Geographic coordinates
- Dublin Core Terms: Descriptions, dates
- SKOS: Victim categories
- Custom MEMO ontology: Project-specific properties
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, FOAF, SKOS, DCTERMS


# ============================================================================
# NAMESPACE DEFINITIONS
# ============================================================================

MEMO_BASE_URI = "http://digitales-memobuch.at/"
MEMO_ONTOLOGY_URI = MEMO_BASE_URI + "ontology#"

# Define namespaces
MEMO = Namespace(MEMO_ONTOLOGY_URI)
SCHEMA = Namespace("http://schema.org/")
BIO = Namespace("http://purl.org/vocab/bio/0.1/")
WGS84 = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")


def write_as_turtle(person) -> Optional[str]:
    """
    Generate SEMANTIC_STATEMENTS.ttl for a MemoPerson.

    This file is picked up by GAMS5 during ingest and its triples
    are loaded into the Blazegraph triple store.

    Args:
        person: MemoPerson instance

    Returns:
        Path to the generated .ttl file, or None if writing fails
    """
    g = Graph()

    # Bind prefixes for clean Turtle output
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("schema", SCHEMA, override=True, replace=True)
    g.bind("bio", BIO)
    g.bind("skos", SKOS)
    g.bind("wgs84_pos", WGS84)
    g.bind("memo", MEMO)

    # ========================================================================
    # PERSON RESOURCE
    # ========================================================================

    person_uri = URIRef(f"{MEMO_BASE_URI}persons/{person.id}")

    # --- Types ---
    g.add((person_uri, RDF.type, FOAF.Person))
    g.add((person_uri, RDF.type, SCHEMA.Person))
    g.add((person_uri, RDF.type, MEMO.HolocaustVictim))

    # --- Label ---
    full_name = f"{person.first_name} {person.last_name}" if person.first_name and person.last_name else "Unknown"
    g.add((person_uri, RDFS.label, Literal(full_name)))

    # --- Names ---
    if person.first_name:
        g.add((person_uri, FOAF.givenName, Literal(person.first_name)))
        g.add((person_uri, SCHEMA.givenName, Literal(person.first_name)))

    if person.last_name:
        g.add((person_uri, FOAF.familyName, Literal(person.last_name)))
        g.add((person_uri, SCHEMA.familyName, Literal(person.last_name)))

    if person.first_name and person.last_name:
        g.add((person_uri, FOAF.name, Literal(full_name)))
        g.add((person_uri, SCHEMA.name, Literal(full_name)))

    if person.maiden_name:
        g.add((person_uri, SCHEMA.additionalName, Literal(person.maiden_name)))
        g.add((person_uri, MEMO.maidenName, Literal(person.maiden_name)))

    if person.alternative_spelling:
        g.add((person_uri, SCHEMA.alternateName, Literal(person.alternative_spelling)))
        g.add((person_uri, SKOS.altLabel, Literal(person.alternative_spelling)))

    # --- Gender ---
    if person.gender:
        gender_text = "Male" if person.gender == "male" else "Female"
        g.add((person_uri, SCHEMA.gender, Literal(gender_text)))
        g.add((person_uri, FOAF.gender, Literal(person.gender)))
        g.add((person_uri, MEMO.gender, Literal(gender_text)))

    # --- Biography ---
    if person.biography_text:
        g.add((person_uri, DCTERMS.description, Literal(person.biography_text, lang="de")))
        g.add((person_uri, SCHEMA.description, Literal(person.biography_text, lang="de")))
        g.add((person_uri, BIO.biography, Literal(person.biography_text, lang="de")))

    # --- Birth ---
    if person.birth_date:
        birth_date_xsd = _convert_to_xsd_date(person.birth_date)
        if birth_date_xsd:
            g.add((person_uri, SCHEMA.birthDate, Literal(birth_date_xsd, datatype=XSD.date)))
        g.add((person_uri, FOAF.birthday, Literal(person.birth_date)))

    if person.birth_place:
        g.add((person_uri, SCHEMA.birthPlace, Literal(person.birth_place)))
        g.add((person_uri, FOAF.based_near, Literal(person.birth_place)))
        # Birth event
        _add_birth_event(g, person_uri, person.birth_date, person.birth_place)

    # --- Death ---
    if person.death_date:
        death_date_xsd = _convert_to_xsd_date(person.death_date)
        if death_date_xsd:
            g.add((person_uri, SCHEMA.deathDate, Literal(death_date_xsd, datatype=XSD.date)))

    if person.death_place:
        g.add((person_uri, SCHEMA.deathPlace, Literal(person.death_place)))
        _add_death_event(g, person_uri, person.death_date, person.death_place,
                         person.death_latitude, person.death_longitude)

    # --- Victim Categories ---
    if person.victim_category:
        for category in person.victim_category:
            category = category.strip()
            if category:
                category_uri = URIRef(f"{MEMO_ONTOLOGY_URI}victim-category/{_slugify(category)}")
                g.add((person_uri, DCTERMS.subject, category_uri))
                g.add((person_uri, MEMO.victimCategory, category_uri))
                # Define the category as SKOS Concept
                _add_category_concept(g, category_uri, category)

    # --- Youth Status ---
    if person.is_youth:
        g.add((person_uri, MEMO.isYouth, Literal(True)))
        g.add((person_uri, DCTERMS.subject, URIRef(f"{MEMO_ONTOLOGY_URI}youth-victim")))

    # --- Memorial Signs ---
    if person.memorial_sign:
        for sign in person.memorial_sign:
            if sign and sign.strip():
                g.add((person_uri, DCTERMS.relation, Literal(sign.strip())))
                g.add((person_uri, MEMO.memorialSign, Literal(sign.strip())))

    # --- Literature ---
    if person.literature:
        g.add((person_uri, DCTERMS.references, Literal(person.literature)))
        g.add((person_uri, MEMO.literatureReference, Literal(person.literature)))

    # --- Voluntary Residence ---
    if person.voluntary_address:
        vol_place_uri = URIRef(f"{MEMO_BASE_URI}persons/{person.id}/places/voluntary")
        g.add((person_uri, MEMO.lastVoluntaryResidence, vol_place_uri))
        _add_place(g, vol_place_uri, person.voluntary_address,
                   person.voluntary_latitude, person.voluntary_longitude,
                   "Last Voluntary Residence", "voluntary-residence")

    # --- Forced Residence ---
    if person.forced_address:
        forced_place_uri = URIRef(f"{MEMO_BASE_URI}persons/{person.id}/places/forced")
        g.add((person_uri, MEMO.forcedResidence, forced_place_uri))
        _add_place(g, forced_place_uri, person.forced_address,
                   person.forced_latitude, person.forced_longitude,
                   "Forced Residence", "forced-residence")

    # ========================================================================
    # IMAGES
    # ========================================================================

    for i, image in enumerate(person.images):
        image_dsid = os.path.basename(image.source_path).upper()
        image_uri = URIRef(f"{MEMO_BASE_URI}api/v1/projects/memo/objects/{person.id}/datastreams/{image_dsid}")

        if i == 0:
            g.add((person_uri, SCHEMA.image, image_uri))
            g.add((person_uri, FOAF.depiction, image_uri))
            g.add((person_uri, MEMO.portraitImage, image_uri))
        else:
            g.add((person_uri, SCHEMA.image, image_uri))
            g.add((person_uri, MEMO.hasHistoricImage, image_uri))

        _add_image_resource(g, image_uri, image.title, image.desc)

    # ========================================================================
    # DOCUMENTS
    # ========================================================================

    for document in person.documents:
        doc_dsid = os.path.basename(document.source_path).upper()
        doc_uri = URIRef(f"{MEMO_BASE_URI}api/v1/projects/memo/objects/{person.id}/datastreams/{doc_dsid}")

        g.add((person_uri, DCTERMS.relation, doc_uri))
        g.add((person_uri, MEMO.hasHistoricSourceDocument, doc_uri))
        _add_document_resource(g, doc_uri, document.title, document.desc)

    # ========================================================================
    # EVENTS (Haftorte, Fluchtorte)
    # ========================================================================

    for event in person.events:
        event_uri = URIRef(f"{MEMO_BASE_URI}persons/{person.id}/events/{event.id}")
        g.add((person_uri, BIO.event, event_uri))
        g.add((person_uri, MEMO.hasLifeEvent, event_uri))
        _add_event(g, event_uri, event, person_uri)

    # ========================================================================
    # PROVENANCE & METADATA
    # ========================================================================

    g.add((person_uri, DCTERMS.creator, Literal("Born digital - memo project GAMS")))
    g.add((person_uri, DCTERMS.rights, Literal("Creative Commons BY-NC 4.0")))
    g.add((person_uri, DCTERMS.rightsHolder, Literal("MEMO Project")))
    g.add((person_uri, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by-nc/4.0/")))
    g.add((person_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

    # ========================================================================
    # SERIALIZE TO FILE
    # ========================================================================

    from memobuch_preprocessing.MemoStatics import MemoStatics
    ttl_file_path = os.path.join(MemoStatics.OUTPUT_DIR, str(person.id), 'SEMANTIC_STATEMENTS.ttl')

    g.serialize(destination=ttl_file_path, format="turtle", encoding="utf-8")
    logging.debug(f"Generated SEMANTIC_STATEMENTS.ttl at: {ttl_file_path}")

    return ttl_file_path


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _convert_to_xsd_date(date_str: str) -> Optional[str]:
    """Convert DD/MM/YYYY or DD.MM.YYYY to YYYY-MM-DD (XSD date format)."""
    if not date_str or date_str.strip() == "":
        return None
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        elif '.' in date_str:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        elif '-' in date_str:
            return date_str
        elif len(date_str) == 4:
            return f"{date_str}-01-01"
    except Exception:
        pass
    return None


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def _add_birth_event(g: Graph, person_uri: URIRef, birth_date: str, birth_place: str):
    """Add a Bio:Birth event to the graph."""
    birth_uri = URIRef(str(person_uri) + "/birth")
    g.add((birth_uri, RDF.type, BIO.Birth))
    g.add((birth_uri, RDFS.label, Literal(f"Birth of {str(person_uri).split('/')[-1]}")))
    g.add((birth_uri, BIO.principal, person_uri))

    if birth_date:
        date_xsd = _convert_to_xsd_date(birth_date)
        if date_xsd:
            g.add((birth_uri, BIO.date, Literal(date_xsd, datatype=XSD.date)))

    if birth_place:
        g.add((birth_uri, BIO.place, Literal(birth_place)))


def _add_death_event(g: Graph, person_uri: URIRef, death_date: str, death_place: str,
                     lat: float, lon: float):
    """Add a Bio:Death event to the graph."""
    death_uri = URIRef(str(person_uri) + "/death")
    g.add((death_uri, RDF.type, BIO.Death))
    g.add((death_uri, RDFS.label, Literal(f"Death of {str(person_uri).split('/')[-1]}")))
    g.add((death_uri, BIO.principal, person_uri))

    if death_date:
        date_xsd = _convert_to_xsd_date(death_date)
        if date_xsd:
            g.add((death_uri, BIO.date, Literal(date_xsd, datatype=XSD.date)))

    if death_place:
        g.add((death_uri, BIO.place, Literal(death_place)))

    if lat is not None and lon is not None:
        g.add((death_uri, RDF.type, WGS84.Point))
        g.add((death_uri, WGS84.lat, Literal(float(lat), datatype=XSD.float)))
        g.add((death_uri, WGS84.long, Literal(float(lon), datatype=XSD.float)))


def _add_place(g: Graph, place_uri: URIRef, address: str, lat: float, lon: float,
               label: str, place_type: str):
    """Add a geographic place resource."""
    g.add((place_uri, RDF.type, SCHEMA.Place))
    g.add((place_uri, RDF.type, WGS84.Point))
    g.add((place_uri, RDFS.label, Literal(label)))
    g.add((place_uri, SCHEMA.address, Literal(address)))
    g.add((place_uri, MEMO.placeType, Literal(place_type)))

    if lat is not None:
        g.add((place_uri, WGS84.lat, Literal(float(lat), datatype=XSD.float)))
    if lon is not None:
        g.add((place_uri, WGS84.long, Literal(float(lon), datatype=XSD.float)))


def _add_category_concept(g: Graph, category_uri: URIRef, category_label: str):
    """Add a SKOS Concept for a victim category."""
    g.add((category_uri, RDF.type, SKOS.Concept))
    g.add((category_uri, SKOS.prefLabel, Literal(category_label, lang="de")))
    g.add((category_uri, RDFS.label, Literal(category_label, lang="de")))
    g.add((category_uri, SKOS.inScheme, URIRef(f"{MEMO_ONTOLOGY_URI}victim-categories")))


def _add_image_resource(g: Graph, image_uri: URIRef, title: str, description: str):
    """Add metadata for an image resource."""
    g.add((image_uri, RDF.type, SCHEMA.ImageObject))
    g.add((image_uri, RDF.type, FOAF.Image))
    if title:
        g.add((image_uri, DCTERMS.title, Literal(title)))
        g.add((image_uri, RDFS.label, Literal(title)))
    if description:
        g.add((image_uri, DCTERMS.description, Literal(description)))
    g.add((image_uri, DCTERMS.rights, Literal("Creative Commons BY-NC 4.0")))


def _add_document_resource(g: Graph, doc_uri: URIRef, title: str, description: str):
    """Add metadata for a document resource."""
    g.add((doc_uri, RDF.type, SCHEMA.DigitalDocument))
    g.add((doc_uri, RDF.type, FOAF.Document))
    if title:
        g.add((doc_uri, DCTERMS.title, Literal(title)))
        g.add((doc_uri, RDFS.label, Literal(title)))
    if description:
        g.add((doc_uri, DCTERMS.description, Literal(description)))
    g.add((doc_uri, DCTERMS.rights, Literal("Creative Commons BY-NC 4.0")))


def _add_event(g: Graph, event_uri: URIRef, event, person_uri: URIRef):
    """Add a comprehensive event description (Haftort, Fluchtort)."""
    g.add((event_uri, RDF.type, BIO.Event))
    g.add((event_uri, RDF.type, MEMO.Event))

    if event.type == "haft":
        g.add((event_uri, RDF.type, MEMO.ImprisonmentEvent))
        g.add((event_uri, MEMO.eventType, Literal("Imprisonment")))
    elif event.type == "flucht":
        g.add((event_uri, RDF.type, MEMO.FlightEvent))
        g.add((event_uri, MEMO.eventType, Literal("Flight")))

    # Coordinates
    if event.lat is not None and event.long is not None:
        g.add((event_uri, RDF.type, WGS84.Point))
        g.add((event_uri, WGS84.lat, Literal(float(event.lat), datatype=XSD.float)))
        g.add((event_uri, WGS84.long, Literal(float(event.long), datatype=XSD.float)))

    # Label & description
    if event.title:
        g.add((event_uri, RDFS.label, Literal(event.title)))
        g.add((event_uri, DCTERMS.title, Literal(event.title)))
    if event.description:
        g.add((event_uri, DCTERMS.description, Literal(event.description)))

    # Date
    if event.date:
        date_xsd = _convert_to_xsd_date(event.date)
        if date_xsd:
            g.add((event_uri, DCTERMS.date, Literal(date_xsd, datatype=XSD.date)))
        g.add((event_uri, MEMO.date, Literal(event.date)))

    # Location
    if event.location:
        g.add((event_uri, BIO.place, Literal(event.location)))
        g.add((event_uri, SCHEMA.location, Literal(event.location)))
        g.add((event_uri, MEMO.location, Literal(event.location)))

    # Link back to person
    g.add((event_uri, BIO.principal, person_uri))
    g.add((event_uri, MEMO.describesVictim, person_uri))

    # Provenance
    g.add((event_uri, DCTERMS.creator, Literal("Born digital - memo project GAMS")))
    g.add((event_uri, DCTERMS.rights, Literal("Creative Commons BY-NC 4.0")))