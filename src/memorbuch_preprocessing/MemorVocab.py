

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
        "nsopposition": {
            "label": "NS-Gegner",
            "color": "#ADFF2F"
        },
        "resistance_political": {
            "label": "Widerstand, politisch",
            "color": "#ADFF2F"
        },
        "resistance_religious": {
            "label": "Widerstand, religiös",
            "color": "#ADFF2F"
        },
        "resistance_individual": {
            "label": "Widerstand, individuell",
            "color": "#ADFF2F"
        },
        "resistance_deserters": {
            "label": "Widerstand, Deserteure",
            "color": "#ADFF2F"
        },
        "witnessesjehovah": {
            "label": "Zeugen Jehovas",
            "color": "#EE4B2B"
        },
        "jewishvictims_jewish": {
            "label": "Jüdische Opfer",
            "color": "#228B22"
        },
        "jewishvictims_persecutedasjew": {
            "label": "Jüdische Opfer, als Jude verfolgt",
            "color": "#228B22"
        },
        "roma": {
            "label": "Roma/Romnija und Sinti/Sintize",
            "color": "#FF8C00"
        },
        "euthanasiavictim": {
            "label": "Opfer der NS-Euthanasie",
            "color": "#ADD8E6"
        },
        "homosexualvictim": {
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
        "spainfighter": {
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