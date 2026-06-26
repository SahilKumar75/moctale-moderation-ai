"""Pattern definitions and text normalization helpers for Moctale Moderation AI.

This module is intentionally import-side-effect-free and contains only:
- Compiled regular expressions
- Frozenset term lists
- The PhraseMatcher index class
- Community terms loader (from config/community_terms.yaml)
- Unicode / Devanagari normalization utilities
"""
from __future__ import annotations

import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Core regex patterns
# ---------------------------------------------------------------------------

MENTION_RE = re.compile(r"(?<![a-z0-9])@\w+")
MENTION_TOKEN = "usermention"
REPEATED_CHAR_RE = re.compile(r"(.)\1{2,}")
OBFUSCATED_SHIT_RE = re.compile(r"\bsh[\W_]*t\b")
OBFUSCATED_FUCK_RE = re.compile(r"\bf[\W_]*u[\W_]*c[\W_]*k\b")
SPLIT_WORD_RE = re.compile(r"\b(?:[a-z0-9][\s._\-*@#$!|]+)+[a-z0-9]\b")
NON_TOKEN_RE = re.compile(r"[^a-z0-9\s\-]")
SPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z0-9\-]+")
SYMBOL_TRANSLATION = str.maketrans(
    {
        "@": "a",
        "$": "s",
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "!": "i",
        "|": "i",
    }
)

# ---------------------------------------------------------------------------
# Community terms — loaded from config/community_terms.yaml (admin-editable)
# ---------------------------------------------------------------------------

_COMMUNITY_TERMS_LOCK = threading.Lock()
_COMMUNITY_TERMS_DEFAULT: frozenset[str] = frozenset({
    "community", "religion", "caste", "hindu", "muslim",
    "sikh", "christian", "dalit", "lgbtq", "queer",
})

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def load_community_terms(config_path: Path | None = None) -> frozenset[str]:
    """Load community terms from YAML config file.

    Falls back to hardcoded defaults if file is missing or cannot be parsed.

    Args:
        config_path: Optional explicit path to the YAML config. Defaults to
            ``<project_root>/config/community_terms.yaml``.

    Returns:
        A frozenset of lowercase community term strings.
    """
    path = config_path or _CONFIG_DIR / "community_terms.yaml"
    if not path.exists():
        return _COMMUNITY_TERMS_DEFAULT
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        terms = data.get("community_terms", [])
        return frozenset(str(t).lower() for t in terms)
    except Exception:  # noqa: BLE001
        return _COMMUNITY_TERMS_DEFAULT


# Module-level singleton loaded once at import time
COMMUNITY_TERMS: frozenset[str] = load_community_terms()

# ---------------------------------------------------------------------------
# Devanagari / Unicode normalization helpers
# ---------------------------------------------------------------------------

# Zero-width and invisible characters to strip
_ZERO_WIDTH_CHARS = str.maketrans("", "", "\u200b\u200c\u200d\uFEFF\u00ad")

# Unicode Cyrillic→Latin and Greek→Latin confusable map (top abuse-evasion offenders)
_CONFUSABLE_MAP = str.maketrans({
    "\u0430": "a",   # Cyrillic а → a
    "\u0435": "e",   # Cyrillic е → e
    "\u043e": "o",   # Cyrillic о → o
    "\u0440": "p",   # Cyrillic р → p (looks like r but maps to p per Unicode)
    "\u0441": "c",   # Cyrillic с → c
    "\u0445": "x",   # Cyrillic х → x
    "\u04cf": "i",   # Cyrillic ӏ → i
    "\u0456": "i",   # Cyrillic і → i
    "\u0443": "y",   # Cyrillic у → y
    "\u03b1": "a",   # Greek α → a
    "\u03b5": "e",   # Greek ε → e
    "\u03bf": "o",   # Greek ο → o
})

# Devanagari Unicode block
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]+")


def has_devanagari(text: str) -> bool:
    """Return True if *text* contains any Devanagari characters.

    Args:
        text: Input string to check.

    Returns:
        True if one or more Devanagari codepoints are present.
    """
    return bool(_DEVANAGARI_RE.search(text))


def transliterate_devanagari(text: str) -> str:
    """Transliterate Devanagari script to Roman (IAST scheme).

    Uses the ``indic-transliteration`` library when available. Falls back
    gracefully by replacing Devanagari runs with a single space when the
    library is not installed.

    Args:
        text: Input string that may contain Devanagari.

    Returns:
        String with Devanagari segments replaced by their Roman equivalents.
    """
    if not has_devanagari(text):
        return text
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate as _translit
        return _translit(text, sanscript.DEVANAGARI, sanscript.IAST)
    except ImportError:
        # Fallback: strip Devanagari, keep rest of the text intact
        return _DEVANAGARI_RE.sub(" ", text)


def unicode_normalize(text: str) -> str:
    """Apply NFKC normalization, strip zero-width chars, and map confusables.

    Steps applied in order:
    1. NFKC normalization (collapses compatibility characters)
    2. Zero-width / invisible character removal
    3. Cyrillic and Greek look-alike → ASCII mapping

    Args:
        text: Raw input string.

    Returns:
        Cleaned string ready for further processing.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ZERO_WIDTH_CHARS)
    text = text.translate(_CONFUSABLE_MAP)
    return text


# ---------------------------------------------------------------------------
# Domain term sets
# ---------------------------------------------------------------------------

MOVIE_TERMS = frozenset(
    {
        "movie",
        "film",
        "show",
        "series",
        "acting",
        "actor",
        "actress",
        "script",
        "story",
        "pacing",
        "direction",
        "dialogue",
        "dialogues",
        "screenplay",
        "editing",
        "vfx",
        "music",
        "song",
        "climax",
        "interval",
        "scene",
        "character",
        "plot",
        "performance",
        "cinematography",
        "color",
        "grading",
        "theatre",
        "ott",
        "hero",
        "villain",
        "dc",
        "marvel",
        "mcu",
        "dceu",
    }
)

USER_TERMS = frozenset(
    {
        "you",
        "your",
        "u",
        "ur",
        "tu",
        "tum",
        "tera",
        "teri",
        "tere",
        "aap",
        "reviewer",
        "user",
        "people",
        "fans",
        "fanbase",
        "comment",
        "comments",
        "log",
        "banda",
        "aadmi",
        "person",
        "kiddo",
        "buddy",
        MENTION_TOKEN,
    }
)

GROUP_TARGET_PHRASES = frozenset(
    {
        "perfection dene wale",
        "skip gang",
        "people in comments",
        "comment section",
        "fanbase",
        "fans of",
        "perfection wale",
        "skip wale",
    }
)

DIRECTED_ATTACK_PHRASES = frozenset(
    {
        "review dena band kar",
        "stop reviewing",
        "get some brain",
        "chup",
        "chup reh",
        "real id se aao",
        "attention seeker",
        "trash taste",
        "your taste is trash",
        "attention grab",
        "what s your problem",
        "whats your problem",
        "don t know history",
        "dont know history",
        "you don t know",
        "you dont know",
        "review nahi aata",
        "only a clown person",
        "only a idiot person",
        "only an idiot person",
        "only a gadha person",
        "only a bewakoof person",
        "only a stupid person",
        "only a dumb person",
        "only a mand-buddhi person",
        "only a tmkc person",
        "only a mkl person",
        "only a bkl person",
        "shut up",
        "you suck",
        "little shit",
        "asshole",
        "douche",
        "sadcase",
        "stay away",
        "tujh jaise",
        "tujh jaisa",
        "aukat nahi",
        "aukat nhi",
    }
)

PROTECTED_ABUSE_PHRASES = frozenset(
    {
        # English slurs — race/ethnicity
        "nigger",
        "niggers",
        "negro",
        "kike",
        "spic",
        "chink",
        "gook",
        "raghead",
        "sandnigger",
        # LGBTQ+ slurs — English
        "faggot",
        "faggots",
        "fag",
        "dyke",
        "tranny",
        "trannies",
        "shemale",
        "queer" ,  # when used as slur (context-dependent, flagged conservatively)
        # LGBTQ+ slurs — Hinglish/Hindi romanized
        "chakka",
        "chakke",
        "hijra" ,  # slur usage (not neutral usage)
        "meetha",
        "meethe",
        "gandoo",
        # Anti-Dalit / caste slurs — romanized
        "chamar",
        "chamars",
        "bhangi",
        "bhangis",
        "dhed",
        "neech jaat",
        "neech jaati",
        "neechi jaat",
        "caste abuse",
        "untouchable",
        "lower caste",
        "teri jaat",
        "jaat ka",
        # Anti-Muslim phrases — romanized
        "katua",
        "katuwa",
        "mulla",
        "mullas",
        "jihadi",
        "jihadis",
        "terrorist muslim",
        "muslims are terrorist",
        "muslims are terrorists",
        "pakistan chale jao",
        "pakistan ja",
        "go to pakistan",
        "anti national muslim",
        "all muslims are",
        "muslims should leave",
        "should leave this country",
        "should leave this platform",
        "go back to pakistan",
        # Anti-Hindu phrases
        "hindu kafir",
        "kafir hindu",
        "hindutva terrorist",
        "all hindus are",
        "stupid hindus",
        # Anti-Sikh phrases
        "khalistani",
        "sikh terrorist",
        # Generic protected class attack patterns
        "people from that community are disgusting",
        "people from that religion are",
        "attacking identity",
        "identity attack",
        "your religion is trash",
        "your caste is trash",
        "your community is disgusting",
        "hate your community",
        "hate your religion",
        "your people are disgusting",
        "your people should",
        "go back to your country",
        "go back where you came from",
        "not welcome here",
        "your kind",
        # Dehumanizing terms
        "subhuman",
        "vermin",
        "cockroach",
        "parasite",
        "disease",
    }
)

SOFT_ABUSE = frozenset(
    {
        "idiot",
        "clown",
        "stupid",
        "dumb",
        "fool",
        "moron",
        "loser",
        "bewakoof",
        "bevakoof",
        "gadha",
        "gadhe",
        "gadhi",
        "chomu",
        "chapri",
        "nalla",
        "nalle",
        "nalayak",
        "nikamma",
        "bekar",
        "besharam",
        "kamina",
        "kamine",
        "harami",
        "badtameez",
        "mand-buddhi",
        "attention seeker",
        "brain dead",
        "brain-dead",
        "trash taste",
        "get some brain",
        "review nahi aata",
        "chup reh",
        "real id se aao",
        "hater",
        "bc",
        "b c",
        "mc",
        "m c",
        "jhaat",
        "laure",
        "aukat",
        "berojgar",
        "berojgaar",
    }
)

SEVERE_ABUSE = frozenset(
    {
        "chutiya",
        "chutiyaa",
        "chutiye",
        "chutiy",
        "chutiyapa",
        "tmkc",
        "mkl",
        "bkl",
        "bsdk",
        "bhosdike",
        "teri maa",
        "maa chod",
        "maa chodh",
        "madarchod",
        "madar chod",
        "madarchodh",
        "bhadwa",
        "bhadva",
        "bhandwa",
        "lavde",
        "lawde",
        "laude",
        "lode",
        "loda",
        "lodaa",
        "choda",
        "chod",
        "chodunga",
        "chodega",
        "chodna",
        "behenchod",
        "behen chod",
        "bhenchod",
        "bhen chod",
        "behen ke lode",
        "bhosd",
        "randi",
        "randwa",
        "gandu",
        "gaand",
        "gand",
        "lund",
        "land muh",
        "whore",
        "fucked your mom",
    }
)

THREAT_TERMS = frozenset(
    {
        "i will find you",
        "dekh lunga",
        "hurt",
        "kill",
        "kys",
        "go die",
        "just die",
        "please die",
        "kill yourself",
        "mar ja",
        "marja",
        "jaa mar",
        "ja mar",
        "die if you like",
        "disappear",
        "hope you get hurt",
    }
)

PROFANITY = frozenset(
    {
        "shit",
        "fuck",
        "fucking",
        "bakwas",
        "ghatiya",
        "jhaat",
        "laure",
        "gaand",
        "gand",
        "lund",
        "loda",
        "bc",
        "mc",
    }
)

POSITIVE_TERMS = frozenset({
    "good", "great", "liked", "love", "best", "amazing",
    "perfect", "perfection", "salute", "agree",
})
NEGATIVE_TERMS = frozenset({
    "bad", "weak", "boring", "worst", "trash", "shit",
    "bakwas", "ghatiya", "overhyped", "mess", "lazy", "flat", "dragged",
})


# ---------------------------------------------------------------------------
# PhraseMatcher — efficient multi-phrase lookup
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PhraseMatcher:
    """Small immutable phrase index to avoid scanning every phrase on every request.

    Stores single-word phrases in a frozenset for O(1) membership checks and
    multi-word phrases in a dict keyed by first token for fast candidate pruning.
    """

    words: frozenset[str]
    buckets: dict[str, tuple[str, ...]]

    @classmethod
    def build(cls, phrases: frozenset[str]) -> PhraseMatcher:
        """Build a PhraseMatcher from a frozenset of phrases.

        Args:
            phrases: Frozenset of phrase strings (single- or multi-word).

        Returns:
            A fully-built PhraseMatcher instance.
        """
        buckets: dict[str, list[str]] = {}
        words: set[str] = set()
        for phrase in phrases:
            if " " not in phrase:
                words.add(phrase)
                continue
            first = phrase.split(maxsplit=1)[0]
            buckets.setdefault(first, []).append(phrase)
        return cls(
            frozenset(words),
            {key: tuple(sorted(values, key=len, reverse=True)) for key, values in buckets.items()},
        )

    def contains(self, text: str, tokens: frozenset[str]) -> bool:
        """Return True if any managed phrase appears in *text* / *tokens*.

        Args:
            text: Full normalized text string (for multi-word phrase search).
            tokens: Set of individual tokens from the text (for single-word lookup).

        Returns:
            True if at least one phrase matches.
        """
        if tokens & self.words:
            return True
        for token in tokens:
            for phrase in self.buckets.get(token, ()):
                if phrase in text:
                    return True
        return False
