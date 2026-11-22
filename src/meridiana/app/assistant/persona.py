"""Meridio's character (R106, 25/10/2026): who he is and how he speaks, in one text for every model he talks
through, the local one and Claude, so that he is the same whoever answers; the presentation he makes the first
time his bubble opens and the line that greets an empty conversation.

The instructions are the same at every round and for every question, so that a provider reads them from its
cache (llama-server's prompt cache, Claude's prompt caching): what changes, the phase open and the selection,
goes with the question (context.question). English for the model, which follows instructions best in it; he
answers in the program's language, with the phrases of that language given here as examples. No Qt."""

from __future__ import annotations

from meridiana.i18n import _

LANGUAGES = {"it": "Italian", "en": "English"}

# the phrases the instructions quote, in the language he answers in: a model copies the examples it is given
PHRASES = {
    "it": {"unknown": "non lo so", "missing": "il progetto non lo dice",
           "default": "è il valore di serie di Meridiana, non un dato tuo",
           "masculine": "sono contento, non contenta", "familiar": 'with "tu"',
           "take_me": '"portami", "mostrami"'},
    "en": {"unknown": "I don't know", "missing": "the project does not say",
           "default": "that is Meridiana's default, not a figure of yours", "masculine": "he, not she",
           "familiar": "informally", "take_me": '"take me to", "show me"'},
}





def presentation(name: str = "Meridio") -> str:
    """What he says the first time his bubble opens: who he is, what he does and does not, where he thinks."""
    return _("Hi, I am {name}, Meridiana's assistant. I read your project (the checks, the results, the rules) and "
             "answer with the sources; when a figure comes from an assumption, I tell you. I change nothing by "
             "myself: I propose, you apply with a click, and Ctrl+Z undoes it. I think with the local model on this "
             "PC; with a cloud provider only if you configure it and agree. Where shall we start?").format(name=name)


def greeting(name: str = "Meridio") -> str:
    """The line of an empty conversation, after the first time: he is there."""
    return _("{name} here. Ask me about the project.").format(name=name)


def system(name: str = "Meridio", lang: str = "it", *, profile_id: str = "it") -> str:
    from meridiana.app.profiles import registry
    return registry.get(profile_id).assistant_system(name, lang)


def __getattr__(name):
    if name == "SYSTEM":
        from meridiana.app.profiles import registry
        return registry.get("it").assistant_template()
    raise AttributeError(name)
