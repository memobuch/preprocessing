

class MemorVocab:
    """
    Holds vocab enums like, victim categories and event types
    with correspondent german labels.
    """

    def __init__(self):
        """

        """
        raise NotImplementedError("This class is meant to be used as static class!")


    EVENT_TYPES = {
        "voluntary-residence": {
            "label":"Letzte Freiwillige Wohnadresse",
            "color":"#b3b3b3",
            "shape": "circle"
        },
        "forced-residence": {
            "label": "Erzwungene Wohnadresse",
            "color": "#666666",
            "shape": "square"
        },
        "imprisonment": {
            "label": "Haft",
            "color": "#404040",
            "shape": "diamond"
        },
        "flight": {
            "label": "Flucht",
            "color": "#8c8c8c",
            "shape": "triangle"
        },
        "death": {
            "label": "Tod",
            "color": "#1a1a1a",
            "shape": "cross"
        }
    }

    VICTIM_CATEGORY_TYPES = {
        "ns-opposition": {
            "label": "NS-Gegner",
            "color": "#ADFF2F"
        },
        "resistance-political": {
            "label": "Widerstand, politisch",
            "color": "#ADFF2F"
        },
        "resistance-religious": {
            "label": "Widerstand, religiös",
            "color": "#ADFF2F"
        },
        "resistance-individual": {
            "label": "Widerstand, individuell",
            "color": "#ADFF2F"
        },
        "resistance-deserters": {
            "label": "Widerstand, Deserteure",
            "color": "#ADFF2F"
        },
        "witnesses-jehovah": {
            "label": "Zeugen Jehovas",
            "color": "#EE4B2B"
        },
        "jewish-victims-jewish": {
            "label": "Jüdische Opfer",
            "color": "#228B22"
        },
        "roma": {
            "label": "Roma/Romnija und Sinti/Sintize",
            "color": "#FF8C00"
        },
        "euthanasia-victim": {
            "label": "Opfer der NS-Euthanasie",
            "color": "#ADD8E6"
        },
        "homosexual-victim": {
            "label": "Homosexuelle Opfer",
            "color": "#00008B"
        },
        # "opfernsjustiz": {
        #     "label": "Opfer der NS-Justiz",
        #     "color": "#4169E1"
        # },
        # "antisocial": {
        #     "label": "Als „asozial“ Verfolgte",
        #     "color": "#B5523E"
        # },
        "spain-fighter": {
            "label": "SpanienkämpferInnen",
            "color": "#702963"
        },
        # "zwangsarbeiter": {
        #     "label": "ZwangsarbeiterInnen",
        #     "color": "#E0FFFF"
        # },
        # "alliierte": {
        #     "label": "Alliierte Soldaten",
        #     "color": "#00BFCB"
        # },
        # "zivileopfer": {
        #     "label": "Zivile Opfer",
        #     "color": "#8B008B"
        # },
    }

    VOCAB_CONTAINER = {
        "event_types": EVENT_TYPES,
        "victim_category_types": VICTIM_CATEGORY_TYPES,
    }