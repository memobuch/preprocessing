"""
Improved RDF.xml Generation for MEMO Project
=============================================

This module provides an enhanced write_as_rdf_xml() method that:
1. Fixes the ontology URI typo (onotology -> ontology)
2. Maps ALL MemoPerson data to RDF
3. Uses proper, established ontologies
4. Provides semantic richness for Holocaust victim data

Ontologies Used:
- FOAF: Person information
- Schema.org: Modern person/bio data
- Bio: Biographical events
- WGS84: Geographic coordinates
- Dublin Core Terms: Descriptions, dates
- SKOS: Victim categories
- Custom MEMO ontology: Project-specific properties

Author: Claude (for MEMO project refactoring)
"""

import xml.etree.ElementTree as ET
from typing import Optional
import os


def write_as_rdf_xml_improved(self):
    """
    IMPROVED RDF.xml file generator that creates comprehensive, semantically rich RDF
    using proper ontologies and mapping ALL data from MemoPerson.

    This method should REPLACE the existing write_as_rdf_xml() in MemoPerson class.
    """

    # ============================================================================
    # NAMESPACE DEFINITIONS
    # ============================================================================

    MEMO_BASE_URI = "http://digitales-memobuch.at/"
    MEMO_ONTOLOGY = MEMO_BASE_URI + "ontology#"  # FIXED: was "onotology"

    # Define all namespaces
    namespaces = {
        'xmlns:rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'xmlns:rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema#',
        'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
        'xmlns:dcterms': 'http://purl.org/dc/terms/',
        'xmlns:foaf': 'http://xmlns.com/foaf/0.1/',
        'xmlns:schema': 'http://schema.org/',
        'xmlns:bio': 'http://purl.org/vocab/bio/0.1/',
        'xmlns:skos': 'http://www.w3.org/2004/02/skos/core#',
        'xmlns:wgs84_pos': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'xmlns:memo': MEMO_ONTOLOGY
    }

    # ============================================================================
    # ROOT ELEMENT
    # ============================================================================

    root = ET.Element('rdf:RDF', namespaces)

    # ============================================================================
    # PERSON DESCRIPTION - Main Resource
    # ============================================================================

    person_uri = f"{MEMO_BASE_URI}persons/{self.id}"
    person_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': person_uri})

    # --- Basic Identification ---

    # Label
    full_name = f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else "Unknown"
    ET.SubElement(person_desc, 'rdfs:label').text = full_name

    # Types - Multiple typing for better interoperability
    ET.SubElement(person_desc, 'rdf:type', {'rdf:resource': 'http://xmlns.com/foaf/0.1/Person'})
    ET.SubElement(person_desc, 'rdf:type', {'rdf:resource': 'http://schema.org/Person'})
    ET.SubElement(person_desc, 'rdf:type', {'rdf:resource': f'{MEMO_ONTOLOGY}HolocaustVictim'})

    # --- Names (COMPLETE) ---

    if self.first_name:
        ET.SubElement(person_desc, 'foaf:givenName').text = self.first_name
        ET.SubElement(person_desc, 'schema:givenName').text = self.first_name

    if self.last_name:
        ET.SubElement(person_desc, 'foaf:familyName').text = self.last_name
        ET.SubElement(person_desc, 'schema:familyName').text = self.last_name

    if self.first_name and self.last_name:
        ET.SubElement(person_desc, 'foaf:name').text = full_name
        ET.SubElement(person_desc, 'schema:name').text = full_name

    # NEW: Maiden name
    if self.maiden_name:
        ET.SubElement(person_desc, 'schema:additionalName').text = self.maiden_name
        ET.SubElement(person_desc, 'memo:maidenName').text = self.maiden_name

    # NEW: Alternative spelling
    if self.alternative_spelling:
        ET.SubElement(person_desc, 'schema:alternateName').text = self.alternative_spelling
        ET.SubElement(person_desc, 'skos:altLabel').text = self.alternative_spelling

    # --- Gender (NEW) ---

    if self.gender:
        # Schema.org gender (text)
        gender_text = "Male" if self.gender == "male" else "Female"
        ET.SubElement(person_desc, 'schema:gender').text = gender_text
        # FOAF gender (resource)
        gender_uri = f"http://xmlns.com/foaf/0.1/{gender_text}"
        ET.SubElement(person_desc, 'foaf:gender').text = self.gender
        # Custom property
        ET.SubElement(person_desc, 'memo:gender').text = gender_text

    # --- Biography ---

    if self.biography_text:
        ET.SubElement(person_desc, 'dcterms:description', {'xml:lang': 'de'}).text = self.biography_text
        ET.SubElement(person_desc, 'schema:description', {'xml:lang': 'de'}).text = self.biography_text
        ET.SubElement(person_desc, 'bio:biography', {'xml:lang': 'de'}).text = self.biography_text

    # --- Birth Information ---

    if self.birth_date:
        # Convert date format if needed (DD/MM/YYYY -> YYYY-MM-DD for XSD compliance)
        birth_date_xsd = _convert_to_xsd_date(self.birth_date)
        if birth_date_xsd:
            ET.SubElement(person_desc, 'schema:birthDate',
                          {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#date'}).text = birth_date_xsd
        # Keep original for compatibility
        ET.SubElement(person_desc, 'foaf:birthday').text = self.birth_date

    if self.birth_place:
        ET.SubElement(person_desc, 'schema:birthPlace').text = self.birth_place
        ET.SubElement(person_desc, 'foaf:based_near').text = self.birth_place
        # Create a Birth event (Bio vocabulary)
        birth_event = _create_birth_event(root, person_uri, self.birth_date, self.birth_place)

    # --- Death Information (NEW) ---

    if self.death_date:
        death_date_xsd = _convert_to_xsd_date(self.death_date)
        if death_date_xsd:
            ET.SubElement(person_desc, 'schema:deathDate',
                          {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#date'}).text = death_date_xsd

    if self.death_place:
        ET.SubElement(person_desc, 'schema:deathPlace').text = self.death_place
        # Create a Death event (Bio vocabulary)
        death_event = _create_death_event(root, person_uri, self.death_date,
                                          self.death_place, self.death_latitude,
                                          self.death_longitude)

    # --- Holocaust-Specific: Victim Categories (NEW) ---

    if self.victim_category:
        for category in self.victim_category:
            category = category.strip()
            if category:
                # Create SKOS concept for the category
                category_uri = f"{MEMO_ONTOLOGY}victim-category/{_slugify(category)}"
                ET.SubElement(person_desc, 'dcterms:subject', {'rdf:resource': category_uri})
                ET.SubElement(person_desc, 'memo:victimCategory', {'rdf:resource': category_uri})

                # Define the category concept (in same file for completeness)
                _create_category_concept(root, category_uri, category)

    # --- Youth Status ---

    if self.is_youth:
        ET.SubElement(person_desc, 'memo:isYouth',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#boolean'}).text = 'true'
        ET.SubElement(person_desc, 'dcterms:subject', {'rdf:resource': f'{MEMO_ONTOLOGY}youth-victim'})

    # --- Memorial Signs ---

    if self.memorial_signs:
        for sign in self.memorial_signs:
            if sign and sign.strip():
                ET.SubElement(person_desc, 'dcterms:relation').text = sign.strip()
                ET.SubElement(person_desc, 'memo:memorialSign').text = sign.strip()

    # --- Literature References (NEW) ---

    if self.literature:
        ET.SubElement(person_desc, 'dcterms:references').text = self.literature
        ET.SubElement(person_desc, 'memo:literatureReference').text = self.literature

    # --- Addresses (NEW) ---

    # Voluntary address (last known voluntary residence)
    if self.voluntary_address:
        voluntary_place_uri = f"{person_uri}/places/voluntary"
        ET.SubElement(person_desc, 'memo:lastVoluntaryResidence',
                      {'rdf:resource': voluntary_place_uri})
        _create_place(root, voluntary_place_uri, self.voluntary_address,
                      self.voluntary_latitude, self.voluntary_longitude,
                      "Last Voluntary Residence", "voluntary-residence")

    # Forced address (forced residence during persecution)
    if self.forced_address:
        forced_place_uri = f"{person_uri}/places/forced"
        ET.SubElement(person_desc, 'memo:forcedResidence',
                      {'rdf:resource': forced_place_uri})
        _create_place(root, forced_place_uri, self.forced_address,
                      self.forced_latitude, self.forced_longitude,
                      "Forced Residence", "forced-residence")

    # ============================================================================
    # IMAGES
    # ============================================================================

    for i, image in enumerate(self.images):
        image_dsid = os.path.basename(image.source_path).upper()
        # Use self.id instead of hardcoded person ID
        image_uri = f'{MEMO_BASE_URI}api/v1/projects/memo/objects/{self.id}/datastreams/{image_dsid}'

        if i == 0:
            # First image is portrait
            ET.SubElement(person_desc, 'schema:image', {'rdf:resource': image_uri})
            ET.SubElement(person_desc, 'foaf:depiction', {'rdf:resource': image_uri})
            ET.SubElement(person_desc, 'memo:portraitImage', {'rdf:resource': image_uri})
        else:
            # Additional images
            ET.SubElement(person_desc, 'schema:image', {'rdf:resource': image_uri})
            ET.SubElement(person_desc, 'memo:hasHistoricImage', {'rdf:resource': image_uri})

        # Create image resource description
        _create_image_resource(root, image_uri, image.title, image.desc)

    # ============================================================================
    # DOCUMENTS
    # ============================================================================

    for i, document in enumerate(self.documents):
        document_dsid = os.path.basename(document.source_path).upper()
        # Use self.id instead of hardcoded person ID
        document_uri = f'{MEMO_BASE_URI}api/v1/projects/memo/objects/{self.id}/datastreams/{document_dsid}'

        ET.SubElement(person_desc, 'dcterms:relation', {'rdf:resource': document_uri})
        ET.SubElement(person_desc, 'memo:hasHistoricSourceDocument', {'rdf:resource': document_uri})

        # Create document resource description
        _create_document_resource(root, document_uri, document.title, document.desc)

    # ============================================================================
    # EVENTS (Haftorte, Fluchtorte)
    # ============================================================================

    for event in self.events:
        event_uri = f"{person_uri}/events/{event.id}"

        # Link person to event
        ET.SubElement(person_desc, 'bio:event', {'rdf:resource': event_uri})
        ET.SubElement(person_desc, 'memo:hasLifeEvent', {'rdf:resource': event_uri})

        # Create detailed event description
        _create_event_description(root, event_uri, event, person_uri)

    # ============================================================================
    # PROVENANCE & METADATA
    # ============================================================================

    ET.SubElement(person_desc, 'dcterms:creator').text = "Born digital - memo project GAMS"
    ET.SubElement(person_desc, 'dcterms:rights').text = "Creative Commons BY-NC 4.0"
    ET.SubElement(person_desc, 'dcterms:rightsHolder').text = "MEMO Project"
    ET.SubElement(person_desc, 'dcterms:license',
                  {'rdf:resource': 'https://creativecommons.org/licenses/by-nc/4.0/'})

    # Add creation/modification metadata
    ET.SubElement(person_desc, 'dcterms:created',
                  {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#dateTime'}).text = \
        _get_current_datetime()

    # ============================================================================
    # WRITE TO FILE
    # ============================================================================

    from memobuch_preprocessing.MemoStatics import MemoStatics
    xml_file_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'RDF.xml')

    # Pretty print with proper formatting
    _indent(root)
    tree = ET.ElementTree(root)
    tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)

    return root


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _convert_to_xsd_date(date_str: str) -> Optional[str]:
    """
    Convert DD/MM/YYYY format to YYYY-MM-DD (XSD date format).
    Returns None if conversion fails.
    """
    if not date_str or date_str.strip() == "":
        return None

    try:
        # Try DD/MM/YYYY format
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        # Try YYYY-MM-DD format (already correct)
        elif '-' in date_str:
            return date_str
        # Try YYYY only
        elif len(date_str) == 4:
            return f"{date_str}-01-01"
    except:
        pass

    return None


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def _create_birth_event(root, person_uri: str, birth_date: str, birth_place: str):
    """Create a Bio vocabulary Birth event."""
    birth_uri = f"{person_uri}/birth"
    birth_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': birth_uri})

    ET.SubElement(birth_desc, 'rdf:type', {'rdf:resource': 'http://purl.org/vocab/bio/0.1/Birth'})
    ET.SubElement(birth_desc, 'rdfs:label').text = f"Birth of {person_uri.split('/')[-1]}"
    ET.SubElement(birth_desc, 'bio:principal', {'rdf:resource': person_uri})

    if birth_date:
        date_xsd = _convert_to_xsd_date(birth_date)
        if date_xsd:
            ET.SubElement(birth_desc, 'bio:date',
                          {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#date'}).text = date_xsd

    if birth_place:
        ET.SubElement(birth_desc, 'bio:place').text = birth_place

    return birth_uri


def _create_death_event(root, person_uri: str, death_date: str, death_place: str,
                        lat: float, lon: float):
    """Create a Bio vocabulary Death event."""
    death_uri = f"{person_uri}/death"
    death_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': death_uri})

    ET.SubElement(death_desc, 'rdf:type', {'rdf:resource': 'http://purl.org/vocab/bio/0.1/Death'})
    ET.SubElement(death_desc, 'rdfs:label').text = f"Death of {person_uri.split('/')[-1]}"
    ET.SubElement(death_desc, 'bio:principal', {'rdf:resource': person_uri})

    if death_date:
        date_xsd = _convert_to_xsd_date(death_date)
        if date_xsd:
            ET.SubElement(death_desc, 'bio:date',
                          {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#date'}).text = date_xsd

    if death_place:
        ET.SubElement(death_desc, 'bio:place').text = death_place

    # Add geographic coordinates
    if lat is not None and lon is not None:
        ET.SubElement(death_desc, 'rdf:type',
                      {'rdf:resource': 'http://www.w3.org/2003/01/geo/wgs84_pos#Point'})
        ET.SubElement(death_desc, 'wgs84_pos:lat',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(lat)
        ET.SubElement(death_desc, 'wgs84_pos:long',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(lon)

    return death_uri


def _create_place(root, place_uri: str, address: str, lat: float, lon: float,
                  label: str, place_type: str):
    """Create a geographic place resource."""
    place_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': place_uri})

    ET.SubElement(place_desc, 'rdf:type', {'rdf:resource': 'http://schema.org/Place'})
    ET.SubElement(place_desc, 'rdf:type',
                  {'rdf:resource': 'http://www.w3.org/2003/01/geo/wgs84_pos#Point'})
    ET.SubElement(place_desc, 'rdfs:label').text = label
    ET.SubElement(place_desc, 'schema:address').text = address

    from memobuch_preprocessing.MemoStatics import MemoStatics
    MEMO_BASE_URI = "http://digitales-memobuch.at/"
    MEMO_ONTOLOGY = MEMO_BASE_URI + "ontology#"

    ET.SubElement(place_desc, 'memo:placeType').text = place_type

    if lat is not None:
        ET.SubElement(place_desc, 'wgs84_pos:lat',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(lat)
    if lon is not None:
        ET.SubElement(place_desc, 'wgs84_pos:long',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(lon)


def _create_category_concept(root, category_uri: str, category_label: str):
    """Create a SKOS Concept for a victim category."""
    concept_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': category_uri})

    ET.SubElement(concept_desc, 'rdf:type',
                  {'rdf:resource': 'http://www.w3.org/2004/02/skos/core#Concept'})
    ET.SubElement(concept_desc, 'skos:prefLabel', {'xml:lang': 'de'}).text = category_label
    ET.SubElement(concept_desc, 'rdfs:label', {'xml:lang': 'de'}).text = category_label

    from memobuch_preprocessing.MemoStatics import MemoStatics
    MEMO_BASE_URI = "http://digitales-memobuch.at/"
    MEMO_ONTOLOGY = MEMO_BASE_URI + "ontology#"

    # Link to concept scheme
    ET.SubElement(concept_desc, 'skos:inScheme',
                  {'rdf:resource': f'{MEMO_ONTOLOGY}victim-categories'})


def _create_image_resource(root, image_uri: str, title: str, description: str):
    """Create metadata for an image resource."""
    image_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': image_uri})

    ET.SubElement(image_desc, 'rdf:type', {'rdf:resource': 'http://schema.org/ImageObject'})
    ET.SubElement(image_desc, 'rdf:type', {'rdf:resource': 'http://xmlns.com/foaf/0.1/Image'})

    if title:
        ET.SubElement(image_desc, 'dcterms:title').text = title
        ET.SubElement(image_desc, 'rdfs:label').text = title

    if description:
        ET.SubElement(image_desc, 'dcterms:description').text = description

    ET.SubElement(image_desc, 'dcterms:rights').text = "Creative Commons BY-NC 4.0"


def _create_document_resource(root, doc_uri: str, title: str, description: str):
    """Create metadata for a document resource."""
    doc_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': doc_uri})

    ET.SubElement(doc_desc, 'rdf:type', {'rdf:resource': 'http://schema.org/DigitalDocument'})
    ET.SubElement(doc_desc, 'rdf:type', {'rdf:resource': 'http://xmlns.com/foaf/0.1/Document'})

    if title:
        ET.SubElement(doc_desc, 'dcterms:title').text = title
        ET.SubElement(doc_desc, 'rdfs:label').text = title

    if description:
        ET.SubElement(doc_desc, 'dcterms:description').text = description

    ET.SubElement(doc_desc, 'dcterms:rights').text = "Creative Commons BY-NC 4.0"


def _create_event_description(root, event_uri: str, event, person_uri: str):
    """Create comprehensive event description (Haftort, Fluchtort)."""
    event_desc = ET.SubElement(root, 'rdf:Description', {'rdf:about': event_uri})

    from memobuch_preprocessing.MemoStatics import MemoStatics
    MEMO_BASE_URI = "http://digitales-memobuch.at/"
    MEMO_ONTOLOGY = MEMO_BASE_URI + "ontology#"

    # Type the event
    ET.SubElement(event_desc, 'rdf:type', {'rdf:resource': 'http://purl.org/vocab/bio/0.1/Event'})
    ET.SubElement(event_desc, 'rdf:type', {'rdf:resource': f'{MEMO_ONTOLOGY}Event'})

    # Specific event type based on event.type
    if event.type == "haft":
        ET.SubElement(event_desc, 'rdf:type', {'rdf:resource': f'{MEMO_ONTOLOGY}ImprisonmentEvent'})
        ET.SubElement(event_desc, 'memo:eventType').text = "Imprisonment"
    elif event.type == "flucht":
        ET.SubElement(event_desc, 'rdf:type', {'rdf:resource': f'{MEMO_ONTOLOGY}FlightEvent'})
        ET.SubElement(event_desc, 'memo:eventType').text = "Flight"

    # Geographic point
    if event.lat is not None and event.long is not None:
        ET.SubElement(event_desc, 'rdf:type',
                      {'rdf:resource': 'http://www.w3.org/2003/01/geo/wgs84_pos#Point'})
        ET.SubElement(event_desc, 'wgs84_pos:lat',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(event.lat)
        ET.SubElement(event_desc, 'wgs84_pos:long',
                      {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(event.long)

    # Label
    if event.title:
        ET.SubElement(event_desc, 'rdfs:label').text = event.title
        ET.SubElement(event_desc, 'dcterms:title').text = event.title

    # Description
    if event.description:
        ET.SubElement(event_desc, 'dcterms:description').text = event.description

    # Date
    if event.date:
        date_xsd = _convert_to_xsd_date(event.date)
        if date_xsd:
            ET.SubElement(event_desc, 'dcterms:date',
                          {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#date'}).text = date_xsd
        # Keep original
        ET.SubElement(event_desc, 'memo:date').text = event.date

    # Location
    if event.location:
        ET.SubElement(event_desc, 'bio:place').text = event.location
        ET.SubElement(event_desc, 'schema:location').text = event.location
        ET.SubElement(event_desc, 'memo:location').text = event.location

    # Link back to person
    ET.SubElement(event_desc, 'bio:principal', {'rdf:resource': person_uri})
    ET.SubElement(event_desc, 'memo:describesVictim', {'rdf:resource': person_uri})

    # Provenance
    ET.SubElement(event_desc, 'dcterms:creator').text = "Born digital - memo project GAMS"
    ET.SubElement(event_desc, 'dcterms:rights').text = "Creative Commons BY-NC 4.0"


def _get_current_datetime() -> str:
    """Get current datetime in XSD format."""
    from datetime import datetime
    return datetime.now().isoformat()


def _indent(elem, level=0):
    """
    Pretty print XML by adding whitespace.
    In-place prettyprint formatter.
    """
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            _indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# ============================================================================
# INTEGRATION INSTRUCTIONS
# ============================================================================

"""
TO INTEGRATE INTO MemoPerson CLASS:

1. Copy the write_as_rdf_xml_improved() function
2. Rename it to write_as_rdf_xml() to replace the existing method
3. Copy all helper functions (_convert_to_xsd_date, _create_birth_event, etc.)
4. Add them as methods or module-level functions in MemoPerson.py

ALTERNATIVE (cleaner):
1. Save this file as memo_rdf_improved.py in the memobuch_preprocessing folder
2. In MemoPerson.py, import: from memobuch_preprocessing.memo_rdf_improved import write_as_rdf_xml_improved
3. In MemoPerson class, replace write_as_rdf_xml with:

   def write_as_rdf_xml(self):
       return write_as_rdf_xml_improved(self)

This keeps the improved code separate and maintainable.
"""