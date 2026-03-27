

class MemoVocab:
    """
    Holds vocab enums like, victim categories and event types
    with correspondent german labels.
    """

    def __init__(self):
        """

        """
        raise NotImplementedError("This class is meant to be used as static class!")


    EVENT_TYPES = {
        "voluntary_residence": {
            "label":"Letzte Freiwillige Wohnadresse",
            "color":"#b3b3b3",
            "shape": "circle"
        },
        "forced_residence": {
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
        "widerstand;politisch": {
            "label": "Widerstand, politisch",
            "color": "#ADFF2F"
        },
        "widerstand;religiös": {
            "label": "Widerstand, religios",
            "color": "#ADFF2F"
        },
        "widerstand;individuell": {
            "label": "Widerstand, individuell",
            "color": "#ADFF2F"
        },
        "widerstand;deserteure": {
            "label": "Widerstand, Deserteure",
            "color": "#ADFF2F"
        },
        "zeugenjehovas": {
            "label": "Zeugen Jehovas",
            "color": "#EE4B2B"
        },
        "jüdischeopfer;jüdisch": {
            "label": "Jüdische Opfer",
            "color": "#228B22"
        },
        "jüdischeopfer;als Jude verfolgt": {
            "label": "Jüdische Opfer, als Jude verfolgt",
            "color": "#228B22"
        },
        "roma": {
            "label": "Roma",
            "color": "#FF8C00"
        },
        "euthanasieopfer": {
            "label": "Euthanasie Opfer",
            "color": "#ADD8E6"
        },
        "homosexuelleopfer": {
            "label": "Homosexuelle Opfer",
            "color": "#00008B"
        },
        "opfernsjustiz": {
            "label": "Opfer der NS-Justiz",
            "color": "#4169E1"
        },
        "asoziale": {
            "label": "Asoziale",
            "color": "#B5523E"
        },
        "spanienkämpfer": {
            "label": "SpanienkämpferInnen",
            "color": "#702963"
        },
        "zwangsarbeiter": {
            "label": "ZwangsarbeiterInnen",
            "color": "#E0FFFF"
        },
        "alliierte": {
            "label": "Alliierte Soldaten",
            "color": "#00BFCB"
        },
        "zivileopfer": {
            "label": "Zivile Opfer",
            "color": "#8B008B"
        },
    }

    VOCAB_CONTAINER = {
        "event_types": EVENT_TYPES,
        "victim_category_types": VICTIM_CATEGORY_TYPES,
    }