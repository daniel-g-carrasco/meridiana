"""Word matching shared by the Meridio knowledge and translated manual guards."""
import re
import unicodedata

STOP = {"della", "delle", "dello", "degli", "dalla", "dalle", "dallo", "dagli", "nella", "nelle", "nello", "negli",
        "sulla", "sulle", "sullo", "sugli", "alla", "alle", "allo", "agli", "come", "quando", "sono", "senza", "anche",
        "dove", "dopo", "prima", "ogni", "tutti", "tutte", "questo", "questa", "quello", "quella", "solo", "oppure"}
ENGLISH_STOP = {'the', 'a', 'an', 'of', 'to', 'from', 'for', 'by', 'with', 'and', 'or', 'it', 'its', 'itself', 'all', 'your'}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def stems(label: str, *, language: str = 'it') -> list[str]:
    out = []
    for token in re.findall(r"\w+", (label or "").replace("&", "")):
        f = fold(token)
        if (token.isupper() and len(token) >= 2) or any(ch.isdigit() for ch in token):
            out.append("=" + f)
        elif ((language == 'it' and len(f) > 3 and f not in STOP)
              or (language == 'en' and len(f) >= 2 and f not in ENGLISH_STOP)):
            out.append(f[:5])
    return list(dict.fromkeys(out))


def explained(label: str, units: list[str], *, language: str = 'it') -> bool:
    """One paragraph must hold every significant word, at least two, as in study 50."""
    words = stems(label, language=language)
    if len(words) < 2:
        return False

    def has(word, text):
        if word.startswith("="):
            return re.search(r"(?<![a-z0-9])" + re.escape(word[1:]) + r"(?![a-z0-9])", text) is not None
        return word in text
    return any(all(has(w, text) for w in words) for text in units)
