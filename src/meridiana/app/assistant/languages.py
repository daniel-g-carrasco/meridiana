"""Which of Meridio's languages a text is in (R649, Daniel 15/11/2026: with the program in English the local model
answered in Italian, and the English voice read it «di merda»). A plain count of the short words each language
cannot do without: no model, no network, nothing to install. Only the languages Meridio speaks (persona.LANGUAGES).
No Qt."""

from __future__ import annotations

import re

# the words that carry a sentence and are not words of the other language («a», «in», «come», «per» are left out:
# they are both, or close to)
_WORDS = {
    "it": frozenset("il lo la gli le un una uno di da del della dei delle dello degli al alla ai alle che non è sono "
                    "per con anche più questo questa questi quello quella nel nella nei sul sulla ma se ed tra fra "
                    "dove quando perché ogni deve essere ho hai ha abbiamo hanno puoi può già ancora molto poi "
                    "cosa qui sei mio tuo suo".split()),
    "en": frozenset("the of and is are was were that this these those with for not be by from which when where "
                    "each must should can could would will have has had you your it its there their what why how "
                    "do does than then also only".split()),
}
_WORD = re.compile(r"[a-zàèéìíòóùú']+")


def detect(text: str, least: int = 2) -> str:
    """"it" or "en", the language whose words outnumber the other's, with at least `least` of them; "" when the
    text does not say (too short, a name, a number, a tie)."""
    counts = {lang: 0 for lang in _WORDS}
    for word in _WORD.findall(text.lower()):
        word = word.strip("'")
        for lang, words in _WORDS.items():
            if word in words:
                counts[lang] += 1
    best = max(counts, key=counts.get)
    others = [n for lang, n in counts.items() if lang != best]
    return best if counts[best] >= least and counts[best] > max(others, default=0) else ""
