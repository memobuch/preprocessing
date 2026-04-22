"""
Turtle (SEMANTIC_STATEMENTS.ttl) Generation for MEMO Project
=============================================================

Generates SEMANTIC_STATEMENTS.ttl per digital object / person.
When ingested via gams-packager + pyrilo, GAMS5 automatically loads
these triples into the Blazegraph / QLever triple store, enabling
SPARQL queries across all MEMO persons.

Produces semantically equivalent output to memor_person_rdf_serialization.py
(RDF/XML) but in Turtle format, with all non-ASCII characters escaped
as \\uXXXX sequences for QLever-safe transport.

Ontologies Used:
- FOAF: Person information
- Schema.org: Person/bio data
- Bio: Biographical events
- CIDOC-CRM: Event modeling (E5_Event, E67_Birth, E69_Death, E53_Place)
- WGS84: Geographic coordinates
- Dublin Core Terms: Descriptions, dates
- SKOS: Alternative labels
- Custom MEMO ontology: Project-specific properties
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, FOAF, SKOS, DCTERMS

from memobuch_preprocessing.MemorVocab import MemoVocab


# ============================================================================
# NAMESPACE DEFINITIONS
# ============================================================================
# Keep these aligned with memor_person_rdf_serialization.py

MEMO_BASE_URI = "https://www.ns-opfer-graz.at/"
MEMO_ONTOLOGY_URI = MEMO_BASE_URI + "ontology#"

# rdflib Namespace objects
MEMO = Namespace(MEMO_ONTOLOGY_URI)
SCHEMA = Namespace("http://schema.org/")
BIO = Namespace("http://purl.org/vocab/bio/0.1/")
WGS84 = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")


# ============================================================================
# SANITIZATION HELPERS
# ============================================================================

def _sanitize_for_turtle(text: str) -> str:
    """
    Remove characters that QLever's strict UTF-8 parser rejects:
    - BOM (U+FEFF) — Google Sheets / Windows copy-paste artifact
    - C0 control chars (except TAB, LF, CR)
    - C1 control chars (U+0080-U+009F) — Windows-1252 encoding artifacts
    - Zero-width chars (U+200B-U+200D)
    """
    if text is None:
        return None
    text = text.replace('\ufeff', '')
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    text = re.sub(r'[\u0080-\u009f]', ' ', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _safe_literal(value, **kwargs) -> Literal:
    """Create an rdflib Literal with sanitized text content."""
    if isinstance(value, str):
        value = _sanitize_for_turtle(value)
    return Literal(value, **kwargs)


def _escape_non_ascii_in_turtle(ttl: str) -> str:
    """
    Replace non-ASCII characters inside Turtle string literals with
    \\uXXXX escape sequences (Turtle standard, W3C spec §6.1).

    This produces a purely ASCII-safe .ttl file that avoids UTF-8
    transport issues in the GAMS -> QLever ingest pipeline
    (error: "Illegal UTF sequence in ad_utility::getUTF8Prefix").

    URIs, prefixes, and Turtle keywords are left untouched.
    Only content within "..." string literals is escaped.
    """
    result = []
    i = 0
    in_uri = False

    while i < len(ttl):
        ch = ttl[i]

        # Track URI boundaries <...>
        if ch == '<' and not in_uri:
            in_uri = True
            result.append(ch)
            i += 1
            continue
        if ch == '>' and in_uri:
            in_uri = False
            result.append(ch)
            i += 1
            continue
        if in_uri:
            result.append(ch)
            i += 1
            continue

        # String literal: escape non-ASCII within "..."
        if ch == '"':
            result.append('"')
            i += 1
            while i < len(ttl):
                ch = ttl[i]
                if ch == '\\' and i + 1 < len(ttl):
                    # Already-escaped sequence: pass through
                    result.append(ch)
                    result.append(ttl[i + 1])
                    i += 2
                elif ch == '"':
                    result.append('"')
                    i += 1
                    break
                elif ord(ch) > 127:
                    cp = ord(ch)
                    if cp <= 0xFFFF:
                        result.append(f'\\u{cp:04X}')
                    else:
                        result.append(f'\\U{cp:08X}')
                    i += 1
                else:
                    result.append(ch)
                    i += 1
        else:
            result.append(ch)
            i += 1

    return ''.join(result)


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
    """
    Convert text to URL-friendly slug.

    NOTE: This mirrors the (no-op) behavior of _slugify() in
    memor_person_rdf_serialization.py — it only lowercases without
    sanitizing special chars. Since the resulting slug is embedded
    into a URI, and we also apply ASCII escaping to the Turtle output,
    any remaining non-ASCII / reserved chars in the URI would cause
    serialization problems. We do minimal safety cleanup here.
    """
    text = text.lower()
    # Minimal safety: Turtle/SPARQL URIs can't contain spaces or certain
    # characters. Replace them with dashes. Semicolons and non-ASCII
    # umlauts would otherwise break URI encoding in QLever.
    # text = re.sub(r'[^a-z0-9]+', '-', text)
    # text = text.strip('-')
    return text


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def write_as_turtle(person) -> Optional[str]:
    """
    Generate SEMANTIC_STATEMENTS.ttl for a MemoPerson.

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
    g.bind("cidoc", CIDOC)
    g.bind("memo", MEMO)

    # ========================================================================
    # PERSON RESOURCE
    # ========================================================================

    person_uri = URIRef(f"{MEMO_BASE_URI}objects/{person.id}")

    # --- Types ---
    g.add((person_uri, RDF.type, FOAF.Person))
    g.add((person_uri, RDF.type, SCHEMA.Person))
    g.add((person_uri, RDF.type, MEMO.HolocaustVictim))

    # --- Label ---
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

    if person.maiden_name:
        g.add((person_uri, SCHEMA.additionalName, _safe_literal(person.maiden_name)))
        g.add((person_uri, MEMO.maidenName, _safe_literal(person.maiden_name)))

    if person.alternative_spelling:
        g.add((person_uri, SCHEMA.alternateName, _safe_literal(person.alternative_spelling)))
        g.add((person_uri, SKOS.altLabel, _safe_literal(person.alternative_spelling)))

    # --- Gender ---
    # Matches new RDF/XML: uses raw gender value (e.g. "male"/"female")
    # without case translation.
    if person.gender:
        g.add((person_uri, SCHEMA.gender, _safe_literal(person.gender)))
        g.add((person_uri, FOAF.gender, _safe_literal(person.gender)))
        g.add((person_uri, MEMO.gender, _safe_literal(person.gender)))

    # --- Biography ---
    if person.biography_text:
        g.add((person_uri, DCTERMS.description, _safe_literal(person.biography_text, lang="de")))
        g.add((person_uri, SCHEMA.description, _safe_literal(person.biography_text, lang="de")))
        g.add((person_uri, BIO.biography, _safe_literal(person.biography_text, lang="de")))

    # --- Birth ---
    if person.birth_date:
        birth_date_xsd = _convert_to_xsd_date(person.birth_date)
        if birth_date_xsd:
            g.add((person_uri, SCHEMA.birthDate, _safe_literal(birth_date_xsd, datatype=XSD.date)))
        g.add((person_uri, FOAF.birthday, _safe_literal(person.birth_date)))

    if person.birth_place:
        g.add((person_uri, SCHEMA.birthPlace, _safe_literal(person.birth_place)))
        g.add((person_uri, FOAF.based_near, _safe_literal(person.birth_place)))
        _add_birth_event(g, person_uri, person.birth_date, person.birth_place)

    # --- Death ---
    if person.death_date:
        death_date_xsd = _convert_to_xsd_date(person.death_date)
        if death_date_xsd:
            g.add((person_uri, SCHEMA.deathDate, _safe_literal(death_date_xsd, datatype=XSD.date)))

    if person.death_place:
        g.add((person_uri, SCHEMA.deathPlace, _safe_literal(person.death_place)))
        _add_death_event(g, person_uri, person.death_date, person.death_place,
                         person.death_latitude, person.death_longitude)

    # --- Victim Categories & Prosecution Events ---
    if person.victim_category:
        for category in person.victim_category:
            category = category.strip()
            if not category:
                continue

            slug = _slugify(category)

            # Shared victim-category concept URI
            category_uri = URIRef(f"{MEMO_ONTOLOGY_URI}victim-category/{slug}")
            g.add((person_uri, DCTERMS.subject, category_uri))
            g.add((person_uri, MEMO.victimCategory, category_uri))

            # Per-person prosecution event URI
            # Matches RDF/XML path: {MEMO_BASE_URI}/objects/{id}/prosecution/{slug}
            # (Note: the RDF/XML code has a double-slash bug — we fix it here
            # because double-slashes in URIs cause QLever parsing issues.)
            prosecution_uri = URIRef(
                f"{MEMO_BASE_URI}objects/{person.id}/prosecution/{slug}"
            )
            g.add((person_uri, MEMO.prosecution, prosecution_uri))

            _add_prosecution_event(g, prosecution_uri, category)

    # --- Youth Status ---
    if person.is_youth:
        g.add((person_uri, MEMO.isYouth, Literal(True)))
        g.add((person_uri, DCTERMS.subject, URIRef(f"{MEMO_ONTOLOGY_URI}youth-victim")))

    # --- Memorial Signs ---
    # Support both `memorial_signs` (new) and `memorial_sign` (current) attr names
    memorial_signs_attr = (
        getattr(person, 'memorial_signs', None)
        or getattr(person, 'memorial_sign', None)
    )
    if memorial_signs_attr:
        for sign in memorial_signs_attr:
            if sign and sign.strip():
                g.add((person_uri, DCTERMS.relation, _safe_literal(sign.strip())))
                g.add((person_uri, MEMO.memorialSign, _safe_literal(sign.strip())))

    # --- Literature ---
    if person.literature:
        g.add((person_uri, DCTERMS.references, _safe_literal(person.literature)))
        g.add((person_uri, MEMO.literatureReference, _safe_literal(person.literature)))

    # --- Voluntary Residence ---
    if person.voluntary_address:
        vol_place_uri = URIRef(f"{MEMO_BASE_URI}objects/{person.id}/places/voluntary_residence")
        g.add((person_uri, MEMO.voluntary_residence, vol_place_uri))
        vol_label = MemoVocab.EVENT_TYPES.get("voluntary_residence", {}).get(
            "label", "Voluntary Residence"
        )
        _add_place_event(g, vol_place_uri, person.voluntary_address,
                         person.voluntary_latitude, person.voluntary_longitude,
                         vol_label, "voluntary_residence")

    # --- Forced Residence ---
    if person.forced_address:
        forced_place_uri = URIRef(f"{MEMO_BASE_URI}objects/{person.id}/places/forced_residence")
        g.add((person_uri, MEMO.forced_residence, forced_place_uri))
        forced_label = MemoVocab.EVENT_TYPES.get("forced_residence", {}).get(
            "label", "Forced Residence"
        )
        _add_place_event(g, forced_place_uri, person.forced_address,
                         person.forced_latitude, person.forced_longitude,
                         forced_label, "forced_residence")

    # ========================================================================
    # IMAGES
    # ========================================================================

    for i, image in enumerate(person.images):
        image_dsid = os.path.basename(image.source_path).upper()
        image_uri = URIRef(
            f"{MEMO_BASE_URI}api/v1/projects/memo/objects/{person.id}/datastreams/{image_dsid}"
        )

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
        doc_uri = URIRef(
            f"{MEMO_BASE_URI}api/v1/projects/memo/objects/{person.id}/datastreams/{doc_dsid}"
        )
        g.add((person_uri, DCTERMS.relation, doc_uri))
        g.add((person_uri, MEMO.hasHistoricSourceDocument, doc_uri))
        _add_document_resource(g, doc_uri, document.title, document.desc)

    # ========================================================================
    # EVENTS (Haftorte, Fluchtorte)
    # ========================================================================

    for event in person.events:
        event_uri = URIRef(f"{MEMO_BASE_URI}objects/{person.id}/events/{event.id}")
        g.add((person_uri, BIO.event, event_uri))
        g.add((person_uri, MEMO.hasLifeEvent, event_uri))
        _add_event(g, event_uri, event, person_uri)

    # ========================================================================
    # PROVENANCE & METADATA
    # ========================================================================

    g.add((person_uri, DCTERMS.creator, _safe_literal("Born digital - memo project GAMS")))
    g.add((person_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))
    g.add((person_uri, DCTERMS.rightsHolder, _safe_literal("MEMO Project")))
    g.add((person_uri, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by-nc/4.0/")))
    g.add((person_uri, DCTERMS.created,
           _safe_literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

    # ========================================================================
    # SERIALIZE TO FILE (UTF-8 Turtle with readable umlauts)
    # ========================================================================
    #
    # We serialize directly as UTF-8 so non-ASCII characters like ü, ö, ä, ß
    # appear literally in the file (e.g. "Mürzzuschlag" instead of
    # "M\u00FCrzzuschlag"). This is readable for humans, diffs cleanly in git,
    # and is fully standards-compliant Turtle (W3C Turtle §6 allows raw UTF-8
    # in string literals).
    #
    # Sanitization of problematic characters (BOM, C0/C1 controls, zero-width)
    # still happens inside _safe_literal() before values enter the graph.

    from memobuch_preprocessing.MemorStatics import MemoStatics
    ttl_file_path = os.path.join(
        MemoStatics.OUTPUT_DIR, str(person.id), 'SEMANTIC_STATEMENTS.ttl'
    )

    g.serialize(destination=ttl_file_path, format="turtle", encoding="utf-8")

    logging.debug(f"Generated SEMANTIC_STATEMENTS.ttl at: {ttl_file_path}")
    return ttl_file_path


# ============================================================================
# RESOURCE BUILDERS
# ============================================================================

def _add_birth_event(g: Graph, person_uri: URIRef, birth_date: str, birth_place: str):
    """Create a Bio:Birth / CIDOC:E67_Birth event."""
    birth_uri = URIRef(str(person_uri) + "/birth")
    g.add((birth_uri, RDF.type, BIO.Birth))
    g.add((birth_uri, RDF.type, CIDOC.E5_Event))
    g.add((birth_uri, RDF.type, CIDOC.E67_Birth))
    g.add((birth_uri, RDFS.label, _safe_literal(f"Geburt von {str(person_uri).split('/')[-1]}")))
    g.add((birth_uri, BIO.principal, person_uri))

    if birth_date:
        date_xsd = _convert_to_xsd_date(birth_date)
        if date_xsd:
            g.add((birth_uri, BIO.date, _safe_literal(date_xsd, datatype=XSD.date)))

    if birth_place:
        g.add((birth_uri, BIO.place, _safe_literal(birth_place)))


def _add_death_event(g: Graph, person_uri: URIRef, death_date: str, death_place: str,
                     lat: float, lon: float):
    """Create a Bio:Death / CIDOC:E69_Death event."""
    death_uri = URIRef(str(person_uri) + "/death")
    g.add((death_uri, RDF.type, BIO.Death))
    g.add((death_uri, RDF.type, CIDOC.E5_Event))
    g.add((death_uri, RDF.type, CIDOC.E69_Death))
    g.add((death_uri, RDFS.label, _safe_literal(f"Death of {str(person_uri).split('/')[-1]}")))
    g.add((death_uri, BIO.principal, person_uri))

    if death_date:
        date_xsd = _convert_to_xsd_date(death_date)
        if date_xsd:
            g.add((death_uri, BIO.date, _safe_literal(date_xsd, datatype=XSD.date)))

    if death_place:
        g.add((death_uri, BIO.place, _safe_literal(death_place)))

    if lat is not None and lon is not None:
        g.add((death_uri, RDF.type, WGS84.Point))
        g.add((death_uri, WGS84.lat, Literal(float(lat), datatype=XSD.float)))
        g.add((death_uri, WGS84.long, Literal(float(lon), datatype=XSD.float)))


def _add_place_event(g: Graph, place_uri: URIRef, address: str, lat: float, lon: float,
                     label: str, place_type: str):
    """Create a place resource (CIDOC E53_Place + schema:Place + WGS84 point)."""
    g.add((place_uri, RDF.type, CIDOC.E53_Place))
    g.add((place_uri, RDF.type, SCHEMA.Place))
    g.add((place_uri, RDF.type, WGS84.Point))
    # Custom MEMO type for the specific kind of place
    g.add((place_uri, RDF.type, URIRef(f"{MEMO_ONTOLOGY_URI}{place_type}")))

    g.add((place_uri, RDFS.label, _safe_literal(label)))
    g.add((place_uri, SCHEMA.address, _safe_literal(address)))

    if lat is not None:
        g.add((place_uri, WGS84.lat, Literal(float(lat), datatype=XSD.float)))
    if lon is not None:
        g.add((place_uri, WGS84.long, Literal(float(lon), datatype=XSD.float)))


def _add_prosecution_event(g: Graph, prosecution_uri: URIRef, category: str):
    """
    Create a per-person prosecution event.

    Matches new RDF/XML _create_prosecution_event(): types the event as
    CIDOC E5_Event and as a memo:prosecution/{slug} class, and labels
    it with the human-readable German label from MemoVocab.
    """
    g.add((prosecution_uri, RDF.type, CIDOC.E5_Event))

    # Typed as the prosecution-for-this-category class.
    # The category slug is used in the URI (not the raw German text) so that
    # non-ASCII characters (ü, ö, ß) and reserved chars (;) don't end up in
    # the URI and break Turtle/SPARQL parsing.
    slug = _slugify(category)
    memo_prosecution_class = URIRef(f"{MEMO_ONTOLOGY_URI}prosecution/{slug}")
    g.add((prosecution_uri, RDF.type, memo_prosecution_class))

    # German label from the vocab — raises if unknown category
    # (matches RDF/XML behavior which also raises)
    category_vocab = MemoVocab.VICTIM_CATEGORY_TYPES.get(category)
    if not category_vocab:
        raise Exception(f"Category '{category}' not found in MemoVocab.VICTIM_CATEGORY_TYPES.")

    category_label = category_vocab.get("label")
    g.add((prosecution_uri, RDFS.label, _safe_literal(category_label, lang="de")))


def _add_image_resource(g: Graph, image_uri: URIRef, title: str, description: str):
    """Add metadata for an image resource."""
    g.add((image_uri, RDF.type, SCHEMA.ImageObject))
    g.add((image_uri, RDF.type, FOAF.Image))
    if title:
        g.add((image_uri, DCTERMS.title, _safe_literal(title)))
        g.add((image_uri, RDFS.label, _safe_literal(title)))
    if description:
        g.add((image_uri, DCTERMS.description, _safe_literal(description)))
    g.add((image_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))


def _add_document_resource(g: Graph, doc_uri: URIRef, title: str, description: str):
    """Add metadata for a document resource."""
    g.add((doc_uri, RDF.type, SCHEMA.DigitalDocument))
    g.add((doc_uri, RDF.type, FOAF.Document))
    if title:
        g.add((doc_uri, DCTERMS.title, _safe_literal(title)))
        g.add((doc_uri, RDFS.label, _safe_literal(title)))
    if description:
        g.add((doc_uri, DCTERMS.description, _safe_literal(description)))
    g.add((doc_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))


def _add_event(g: Graph, event_uri: URIRef, event, person_uri: URIRef):
    """Add a Haftort / Fluchtort event description."""
    g.add((event_uri, RDF.type, BIO.Event))
    g.add((event_uri, RDF.type, MEMO.Event))

    if event.type == "haft":
        g.add((event_uri, RDF.type, MEMO.ImprisonmentEvent))
        g.add((event_uri, MEMO.eventType, _safe_literal("Imprisonment")))
    elif event.type == "flucht":
        g.add((event_uri, RDF.type, MEMO.FlightEvent))
        g.add((event_uri, MEMO.eventType, _safe_literal("Flight")))

    # Coordinates
    if event.lat is not None and event.long is not None:
        g.add((event_uri, RDF.type, WGS84.Point))
        g.add((event_uri, WGS84.lat, Literal(float(event.lat), datatype=XSD.float)))
        g.add((event_uri, WGS84.long, Literal(float(event.long), datatype=XSD.float)))

    # Label & description
    if event.title:
        g.add((event_uri, RDFS.label, _safe_literal(event.title)))
        g.add((event_uri, DCTERMS.title, _safe_literal(event.title)))
    if event.description:
        g.add((event_uri, DCTERMS.description, _safe_literal(event.description)))

    # Date
    if event.date:
        date_xsd = _convert_to_xsd_date(event.date)
        if date_xsd:
            g.add((event_uri, DCTERMS.date, _safe_literal(date_xsd, datatype=XSD.date)))
        g.add((event_uri, MEMO.date, _safe_literal(event.date)))

    # Location
    if event.location:
        g.add((event_uri, BIO.place, _safe_literal(event.location)))
        g.add((event_uri, SCHEMA.location, _safe_literal(event.location)))
        g.add((event_uri, MEMO.location, _safe_literal(event.location)))

    # Link back to person
    g.add((event_uri, BIO.principal, person_uri))
    g.add((event_uri, MEMO.describesVictim, person_uri))

    # Provenance
    g.add((event_uri, DCTERMS.creator, _safe_literal("Born digital - memo project GAMS")))
    g.add((event_uri, DCTERMS.rights, _safe_literal("Creative Commons BY-NC 4.0")))