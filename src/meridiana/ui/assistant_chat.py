"""Meridio answers in the window (task 14; study 14, 6.3-6.9): the conversation behind his speech bubble.

- The call to the model runs in a `ChatJob` on the thread pool, as the layouts and the energy do: the window never
  waits. The text comes into the bubble as the model writes it; Stop (in the field) drops the turn at once and
  shuts the connection; a generation number drops what a stopped job still says.
- The tools run on the window's thread between two rounds (assistant/tools.py, through `WindowHost`), at most
  conversation.ROUNDS rounds a question.
- A proposal is a card in the bubble: «Apply» goes through the window's edit() as one step of the undo (Ctrl+Z),
  «Discard» leaves the project as it is; the model hears what the designer chose with the next question.
- The local model is the default. Claude only with a key in the keyring and the designer's consent, asked the first
  time with what would leave (a card); never for a project marked reserved; the names withheld (privacy.py). No
  network: the question goes to the local model, and it is said.
- The mark on the character (a house, a cloud) and the menu of his chip say where the next question goes; the line
  under the conversation, the tokens and the cost.
- His spoken voice (ui/voice.py), off by default: sentence by sentence as the answer comes.
- His character (R106, assistant/persona.py): the presentation the first time the bubble opens, read by his voice,
  his greeting in an empty conversation. The questions ready follow the conversation (R108,
  assistant/suggestions.py), made on the PC after each turn.
- The local models made simple (R105, assistant/local.py): when the local server does not answer, a `Work`
  looks for another on this PC and a card offers it with one click; none, the card leads to the guide in the
  preferences."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout

from .. import assistant as core
from .. import log
from ..assistant import context, conversation, costs, keys, local, persona, privacy, providers, suggestions, tools
from ..i18n import _
from . import tell
from .design import Space
from .style import Group

LOCAL, CLAUDE = "local", "claude"


class ChatSignals(QObject):
    text = Signal(int, str)                 # generation, a piece of the answer
    done = Signal(int, object)              # generation, conversation.Round
    failed = Signal(int, object)            # generation, providers.ProviderError


class ChatJob(QRunnable):
    """One round of the model, away from the window's thread: the provider's stream gathered, each piece told."""

    def __init__(self, generation: int, provider, system: str, messages: list, specs: list):
        super().__init__()
        self.generation, self.provider, self.system, self.messages, self.specs = (generation, provider, system,
                                                                                   messages, specs)
        self.signals = ChatSignals()

    def run(self):
        g = self.generation
        try:
            r = conversation.collect(self.provider, self.system, self.messages, self.specs,
                                     lambda piece: tell(self.signals.text, g, piece))
        except providers.ProviderError as error:
            tell(self.signals.failed, g, error)
            return
        except Exception as error:          # noqa: BLE001  a thread's boundary: said, not lost
            log.complain("assistant", error)
            tell(self.signals.failed, g, providers.ProviderError("bad", str(error)))
            return
        tell(self.signals.done, g, r)


class WorkSignals(QObject):
    done = Signal(object)


class Work(QRunnable):
    """A slow read away from the window's thread: the local models of this PC (a closed port takes two seconds to
    refuse on Windows), the test of a connection. `fn()`'s result told with `done`; what fails is logged and
    `fallback()` told instead."""

    def __init__(self, fn, fallback=lambda: None):
        super().__init__()
        self.fn, self.fallback = fn, fallback
        self.signals = WorkSignals()
        self.over = False

    def run(self):
        try:
            result = self.fn()
        except Exception as error:          # noqa: BLE001  a thread's boundary: said, not lost
            log.complain("assistant", error)
            result = self.fallback()
        tell(self.signals.done, result)
        self.over = True


def port_of(url: str) -> int:
    from urllib.parse import urlparse
    try:
        return urlparse(url).port or 0
    except ValueError:
        return 0


class WindowHost:
    """The window as the tools see it (assistant/tools.py): what it shows, where it goes, how it changes."""

    def __init__(self, win):
        self.win = win

    @property
    def project(self):
        return self.win.project

    @property
    def session(self):
        return self.win.session

    def path(self):
        return self.win.path

    def checks(self):
        return list(self.win.checks_page.items)

    def layouts(self):
        return self.win.results

    def energy(self):
        return self.win.energy

    def plant(self):
        return self.win.plant_state

    def selection(self):
        return tuple(self.win.selection)

    def phase(self) -> str:
        return self.win.phase()

    def phase_title(self) -> str:
        from .. import phases
        try:
            return phases.by_id(self.phase()).title
        except KeyError:
            return self.phase()

    def rules_facts(self):
        return self.win._rules_facts()

    def go_to(self, target) -> None:
        self.win._navigate(tuple(target))

    def bindings(self):
        return getattr(self.win, "bindings", None)

    @staticmethod
    def key_text(keys: str) -> str:
        from PySide6.QtGui import QKeySequence
        return QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)

    def edit(self, text: str, change) -> None:
        self.win.edit(text, change)

    def fix(self, item) -> None:
        self.win._fix(item)

    def set_status(self, tip: str) -> None:
        button = getattr(self.win, "assistant_button", None)
        if button is not None:
            button.setToolTip(tip)

    def preferences(self) -> None:
        self.win._preferences("assistant")


class Card(Group):
    """A card in the bubble: a group with its title, a few lines, the buttons in a row (design system §4)."""

    def __init__(self, title: str, lines: list[str], buttons: list[tuple[str, str]]):
        super().__init__(title)
        self.setObjectName("meridio-card")
        box = QVBoxLayout(self)
        box.setContentsMargins(Space.M, Space.S, Space.M, Space.M)
        box.setSpacing(Space.XS)
        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            box.addWidget(label)
        row = QHBoxLayout()
        row.setSpacing(Space.S)
        row.addStretch(1)
        self.buttons: dict[str, QPushButton] = {}
        for key, text in buttons:
            b = QPushButton(text)
            row.addWidget(b)
            self.buttons[key] = b
        box.addLayout(row)


def _escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Chat(QObject):
    """The conversation behind Meridio's bubble (`widget`, ui/assistant.Assistant) for the window (`host`)."""

    def __init__(self, widget, host, cfg, save_config=lambda: None, parent=None):
        super().__init__(parent)
        self.widget, self.host, self.cfg, self.save_config = widget, host, cfg, save_config
        self.conversation = conversation.Conversation()
        self.pool = QThreadPool.globalInstance()
        self.generation = 0
        self.provider = None                # the one answering this turn
        self.job: ChatJob | None = None
        self.redactor: privacy.Redactor | None = None
        self.cards: dict[str, Card] = {}    # proposal id -> its card
        self.consent_card: Card | None = None
        self.waiting = ""                   # the question waiting for the consent
        self.decisions: list[str] = []      # what the designer did with the proposals since the last question
        self.keys = keys                    # the keyring (a stand-in in the tests)
        self.make_local = self._local
        self.make_cloud = self._cloud
        self.survey = local.survey          # the local models of this PC (a stand-in in the tests)
        self.surveying = False
        self.survey_card: Card | None = None
        self.last_question = ""             # as typed: asked again when another local model is chosen
        self.survey_job = None              # the search running, kept until it tells
        from .voice import Voice
        paths = getattr(getattr(host, "win", None), "paths", None)
        self.voice = Voice(context.language(), settings=cfg, data_dir=getattr(paths, "data", None), parent=self)
        widget.connected = True
        widget.restore = self._restore
        widget.suggest = self.suggestions
        widget.empty = persona.greeting(core.NAME)
        widget.asked.connect(self.ask)
        widget.stopped.connect(self.stop)
        widget.openedChanged.connect(self._opened)
        widget.voice_button.toggled.connect(self._voice_toggled)
        self._menu()
        self.use_voice(self.voice)
        session = getattr(host, "session", None)
        if session is not None:
            session.subscribe(self._session_changed)
        widget.destroyed.connect(self._gone)
        self.refresh()

    # where the questions go

    def _local(self):
        """The local server of the preferences: Ollama through its own API (the context and the reasoning set at each
        request), any other through OpenAI's."""
        if self.cfg.assistant_local_runtime == "ollama":
            return providers.Ollama(model=self.cfg.assistant_local_model, base_url=self.cfg.assistant_local_url)
        return providers.OpenAICompatible(model=self.cfg.assistant_local_model, base_url=self.cfg.assistant_local_url)

    def _cloud(self, key: str):
        model = self.cfg.assistant_cloud_model
        sonnet = model.startswith("claude-sonnet")
        return providers.Anthropic(model=model, key=key, effort="medium" if sonnet else "low", fallbacks=sonnet)

    def wants_cloud(self) -> bool:
        return self.cfg.assistant_provider == CLAUDE

    def goes_to_cloud(self) -> bool:
        """Where the next question would go: the cloud only when chosen and the project is not reserved."""
        return self.wants_cloud() and not getattr(self.host.project, "reserved", False)

    def refresh(self) -> None:
        """The chip, the mark on the character, the menu's ticks, the status bar's tip, the line of the costs."""
        cloud = self.goes_to_cloud()
        names = costs.short_names()
        if cloud:
            label = names.get(self.cfg.assistant_cloud_model, self.cfg.assistant_cloud_model)
            tip = _("{name} answers with {model}, in the cloud, with your consent").format(
                name=core.NAME, model=label)
        else:
            label = _("Local")
            where = ", ".join(v for v in (self.cfg.assistant_local_model, self.cfg.assistant_local_url) if v)
            tip = _("{name} answers with the local model on this PC ({url})").format(name=core.NAME, url=where)
            if self.wants_cloud():
                tip += " " + _("(the project is reserved: never to the cloud)")
        self.widget.set_where("cloud" if cloud else "local", label, tip)
        self.host.set_status(_("{name}, the assistant (Ctrl+L): {where}").format(name=core.NAME, where=tip))
        self.actions["local"].setChecked(not self.wants_cloud())
        for model, action in self.model_actions.items():
            action.setChecked(self.wants_cloud() and self.cfg.assistant_cloud_model == model)
        self.reserve_action.blockSignals(True)
        self.reserve_action.setChecked(bool(getattr(self.host.project, "reserved", False)))
        self.reserve_action.blockSignals(False)
        self._bill()

    def _menu(self) -> None:
        menu = QMenu(self.widget.where_button)
        group = QActionGroup(menu)
        self.actions: dict[str, QAction] = {}
        local = menu.addAction(_("Local model, on this PC"))
        local.setCheckable(True)
        group.addAction(local)
        local.triggered.connect(lambda: self.choose(LOCAL))
        self.actions["local"] = local
        self.model_actions: dict[str, QAction] = {}
        for model, text in costs.models().items():
            a = menu.addAction(text)
            a.setCheckable(True)
            group.addAction(a)
            a.triggered.connect(lambda _c=False, m=model: self.choose(CLAUDE, m))
            self.model_actions[model] = a
        menu.addSeparator()
        self.reserve_action = menu.addAction(_("Reserved project: never to the cloud"))
        self.reserve_action.setCheckable(True)
        self.reserve_action.toggled.connect(self.reserve)
        menu.addSeparator()
        menu.addAction(_("New conversation"), self.new_conversation)
        menu.addAction(_("Settings…"), self.host.preferences)
        self.widget.where_button.setMenu(menu)
        self.menu = menu

    def choose(self, where: str, model: str = "") -> None:
        self.cfg.assistant_provider = where
        if model:
            self.cfg.assistant_cloud_model = model
        self.save_config()
        self.refresh()

    def reserve(self, on: bool) -> None:
        """The project reserved, or not, as one step of the undo (the project's file keeps it)."""
        if bool(getattr(self.host.project, "reserved", False)) == on:
            return
        self.host.edit(_("Mark the project reserved") if on else _("Mark the project not reserved"),
                       lambda p: setattr(p, "reserved", on))
        self.refresh()

    def apply_preferences(self, choice: dict) -> None:
        """Preferences > Assistant: where, the local server, the Claude model, the voice, a consent withdrawn."""
        for key in ("assistant_provider", "assistant_local_url", "assistant_local_model", "assistant_local_runtime",
                    "assistant_cloud_model"):
            if key in choice:
                setattr(self.cfg, key, choice[key])
        if choice.get("withdraw"):
            self.cfg.assistant_consent = {k: v for k, v in self.cfg.assistant_consent.items() if k != "anthropic"}
        speaking = ("assistant_voice_engine", "assistant_voice_name", "assistant_kokoro_dir", "assistant_kokoro_python")
        if any(k in choice and choice[k] != getattr(self.cfg, k) for k in speaking):
            for k in speaking:
                if k in choice:
                    setattr(self.cfg, k, choice[k])
            self.voice.reconfigure()
            self._voice_available(*self.voice.available())
        if "assistant_voice" in choice:
            self.cfg.assistant_voice = choice["assistant_voice"]
            self._set_voice(choice["assistant_voice"] and self.voice.available()[0])
        self.refresh()

    # a question

    def ask_about(self, item) -> None:
        """«Ask Meridio» on a check: the bubble open with the question written, to send or change (as the help
        box does)."""
        self.widget.open_panel()
        self.widget.field.setText(_("About the check «{text}»: why does it matter, and what should I do?").format(
            text=item.text))
        self.widget.field.setFocus(Qt.FocusReason.OtherFocusReason)

    def ask(self, text: str) -> None:
        """The designer asked: to the local model, or to Claude once the key, the reserve and the consent allow."""
        self.voice.stop()
        self._drop_consent()
        if not self.wants_cloud():
            self._start(text, self.make_local())
            return
        why = privacy.allowed(self.host.project, "anthropic", self.cfg.assistant_consent)
        if why == "reserved":
            self.widget.note(_("This project is reserved: the question goes to the local model."))
            self._start(text, self.make_local())
            return
        try:
            key = self.keys.get("anthropic")
        except keys.KeyringMissing:
            key = ""
        if not key:
            self.widget.note(_("No Claude key in the system's keyring (Preferences > Assistant): the question goes "
                               "to the local model."))
            self._start(text, self.make_local())
            return
        if why == "consent":
            self.waiting = text
            self._show_consent()
            return
        self._start(text, self.make_cloud(key))

    def _show_consent(self) -> None:
        """What would leave, said by Meridio in the conversation (it scrolls), and the card that asks: the first
        time a question would go to Claude, nothing leaves before a click."""
        model = costs.short_names().get(self.cfg.assistant_cloud_model, self.cfg.assistant_cloud_model)
        self.widget.note("\n".join(f"- {line}" for line in privacy.what_leaves("anthropic", model)), who="info")
        card = Card(_("Send this question to Claude?"), [],
                    [("local", _("Local model")), ("cancel", _("Not now")), ("allow", _("Allow and send"))])
        card.buttons["allow"].clicked.connect(self._consented)
        card.buttons["local"].clicked.connect(self._local_instead)
        card.buttons["cancel"].clicked.connect(self._not_now)
        self.consent_card = card
        self.widget.add_card(card)
        self.widget.waiting_for_card()

    def _drop_consent(self) -> None:
        if self.consent_card is not None:
            self.widget.remove_card(self.consent_card)
            self.consent_card = None

    def _consented(self) -> None:
        self.cfg.assistant_consent = privacy.consent(self.cfg.assistant_consent, "anthropic", dt.date.today())
        self.save_config()
        text, self.waiting = self.waiting, ""
        self._drop_consent()
        try:
            key = self.keys.get("anthropic")
        except keys.KeyringMissing:
            key = ""
        self._start(text, self.make_cloud(key) if key else self.make_local())

    def _local_instead(self) -> None:
        text, self.waiting = self.waiting, ""
        self._drop_consent()
        self._start(text, self.make_local())

    def _not_now(self) -> None:
        self.waiting = ""
        self._drop_consent()
        self.widget.answer(_("Not sent."), who="note")

    def _start(self, text: str, provider) -> None:
        """The question into the conversation, with where the designer is and what they did with the proposals."""
        self.last_question = text
        self._drop_survey()
        kind, oid = (self.host.selection() + ("",))[:2]
        selection = "" if kind == "site" else f"{kind} {tools.object_name(self.host.project, kind, oid)}"
        if self.decisions:
            text = "(" + " ".join(self.decisions) + ")\n" + text
            self.decisions = []
        self.conversation.ask(context.question(text, self.host.phase_title(), selection))
        self.provider = provider
        # the report's client is a name as the project's (R61): withheld as well
        client = str((getattr(self.host.project, "report", None) or {}).get("client") or "")
        self.redactor = (privacy.Redactor.of(self.host.project, self.host.path(), {"client": client})
                         if provider.cloud else None)
        self._round()

    def _round(self) -> None:
        self.generation += 1
        messages = (self.redactor.messages(self.conversation.messages) if self.redactor is not None
                    else list(self.conversation.messages))
        self.job = ChatJob(self.generation, self.provider, context.system(core.NAME), messages, tools.specs())
        self.job.signals.text.connect(self._text)
        self.job.signals.done.connect(self._done)
        self.job.signals.failed.connect(self._failed)
        self.widget.set_state(core.THINKING)
        self.pool.start(self.job)

    def _restore(self, text: str) -> str:
        return self.redactor.restore(text) if self.redactor is not None else text

    def _text(self, generation: int, piece: str) -> None:
        if generation != self.generation:
            return
        self.widget.stream(piece)
        self.voice.feed(piece)

    def _done(self, generation: int, r) -> None:
        if generation != self.generation:
            return
        self.job = None
        self.conversation.add_round(r, self.provider)
        self._bill()
        if r.done.reason == "stopped":
            return
        if r.done.reason == "length":
            self.widget.note(_("The answer was cut: it was too long."))
        elif r.done.reason == "refusal":
            self.widget.note(_("The model declined to answer this question."))
        if r.calls and r.done.reason not in ("length", "refusal"):
            self.widget.settle()                    # the words of this round stay; the tools come
            self.conversation.run_tools(r.calls, self.host, self._tool_done)
            if self.conversation.rounds < conversation.ROUNDS:
                self._round()
                return
            self.widget.note(_("Too many steps for one question: ask again, more precisely."))
        self.conversation.close_open_calls()
        self.widget.finish()
        self.voice.flush()

    def _tool_done(self, call, outcome) -> None:
        if outcome.note:
            self.widget.note(outcome.note, who="tool")
        if outcome.proposal is not None:
            self._show_proposal(outcome.proposal)

    def _failed(self, generation: int, error) -> None:
        if generation != self.generation:
            return
        self.job = None
        if error.kind == "offline" and self.provider is not None and self.provider.cloud:
            self.widget.note(_("No network: Claude cannot be reached. The question goes to the local model."))
            self.provider, self.redactor = self.make_local(), None
            self._round()
            return
        self.conversation.close_open_calls()
        self.voice.stop()
        self.widget.answer(self.said(error), who="note")
        if error.kind in ("offline", "model", "tools") and (self.provider is None or not self.provider.cloud):
            self.look_for_local()

    def said(self, error) -> str:
        """What went wrong, in words, with what to do."""
        on_pc = self.provider is None or not self.provider.cloud
        if error.kind == "offline" and on_pc:
            return _("The local model does not answer at {url}. I look for another one on this PC…").format(
                url=self.cfg.assistant_local_url)
        if error.kind == "tools":
            return _("The model {model} does not call tools, and Meridio reads the project with them. I look for "
                     "another one on this PC…").format(model=getattr(self.provider, "model", ""))
        if error.kind == "auth":
            return _("Claude refused the key: check it in Preferences > Assistant.")
        if error.kind == "limit":
            return _("The provider's limit is reached: try again in a while.")
        if error.kind == "model":
            model = getattr(self.provider, "model", "")
            if not on_pc:
                return _("The server does not have the model {model}: check its name in Preferences > "
                         "Assistant.").format(model=model)
            if not model:
                return _("No local model chosen for this server. I look for one on this PC…")
            return _("The server does not have the model {model}. I look for one on this PC…").format(model=model)
        if error.kind == "missing":
            return _("The library for Claude is not installed (anthropic): the local model still answers.")
        return _("The model's server failed: {detail}").format(detail=error.detail or error.kind)

    def stop(self) -> None:
        """Stop: the turn dropped now, the connection shut, the voice silent."""
        self.generation += 1
        if self.provider is not None:
            self.provider.cancel()
        self.job = None
        self.conversation.close_open_calls()
        self.voice.stop()
        if self.consent_card is not None:
            self.waiting = ""
            self._drop_consent()

    # the local models of this PC (R105)

    def look_for_local(self) -> None:
        """The local server did not answer, or has not the model: look for another on this PC, away from the
        window's thread, and offer what is found in a card."""
        if self.surveying:
            return
        self.surveying = True
        extra = (port_of(self.cfg.assistant_local_url),)
        job = Work(lambda: self.survey(extra=extra), local.Survey)
        job.signals.done.connect(self._surveyed)
        self.survey_job = job
        self.pool.start(job)

    def _surveyed(self, found) -> None:
        self.surveying = False
        self.survey_job = None
        self._drop_survey()
        choice = found.choice
        if choice is not None:
            same = (choice.runtime.url.rstrip("/"), choice.model.name) == (
                self.cfg.assistant_local_url.rstrip("/"), self.cfg.assistant_local_model)
            if same:
                self.widget.note(_("{runtime} answers now with {model}: ask again.").format(
                    runtime=choice.runtime.name, model=choice.model.name))
                return
            card = Card(_("On this PC: {runtime}").format(runtime=choice.runtime.name),
                        [_escape(choice.reason(found.machine))],
                        [("prefs", _("Preferences…")), ("use", _("Use it and ask again"))])
            card.buttons["use"].clicked.connect(lambda _c=False, c=choice: self.use_local(c, again=True))
            card.buttons["prefs"].clicked.connect(self._survey_preferences)
            self.survey_card = card
            self.widget.add_card(card)
            return
        idle = [rt for rt in found.idle if rt.start()]
        if idle:
            rt = idle[0]
            self.widget.note(_("{runtime} is on this PC but not running: {how}. Then ask again.").format(
                runtime=rt.name, how=rt.start()))
            return
        card = Card(_("No local model on this PC"),
                    [_escape(_("A few steps give {name} a model of his own on this PC: one program and one command. "
                               "The guide is in Preferences > Assistant.").format(name=core.NAME))],
                    [("prefs", _("Show me how"))])
        card.buttons["prefs"].clicked.connect(self._survey_preferences)
        self.survey_card = card
        self.widget.add_card(card)

    def use_local(self, choice, again: bool = False) -> None:
        """A local model found chosen: its server's address, the model, its API; the question asked again."""
        self.cfg.assistant_provider = LOCAL
        self.cfg.assistant_local_url = choice.runtime.url
        self.cfg.assistant_local_model = choice.model.name
        self.cfg.assistant_local_runtime = "ollama" if choice.runtime.api == "ollama" else ""
        self.save_config()
        self._drop_survey()
        self.refresh()
        self.widget.note(_("{name} now thinks with {model} on {runtime}.").format(
            name=core.NAME, model=choice.model.name, runtime=choice.runtime.name))
        if again and self.last_question:
            self.widget.ask(self.last_question)

    def _survey_preferences(self) -> None:
        self._drop_survey()
        self.host.preferences()

    def _drop_survey(self) -> None:
        if self.survey_card is not None:
            self.widget.remove_card(self.survey_card)
            self.survey_card = None

    # the questions ready (R108)

    def suggestions(self, tab: str) -> list[str]:
        """The questions ready for now: what the conversation is about, the project's state, the phase."""
        import dataclasses

        from .. import phases
        try:
            fallback = tuple(phases.by_id(tab).questions)
        except KeyError:
            fallback = tuple(core.questions(tab))
        facts = dataclasses.replace(suggestions.facts_of(self.host), phase=tab)
        return suggestions.suggest(self.conversation.messages, facts, phase_questions=fallback)

    # his presentation (R106)

    def introduce(self) -> None:
        """The first time his bubble opens: who he is, in his words and, when it is on, in his voice."""
        text = persona.presentation(core.NAME)
        self.widget.greet(text)
        self.voice.feed(text)
        self.voice.flush()
        self.cfg.assistant_introduced = True
        self.save_config()

    def new_conversation(self) -> None:
        self.stop()
        self._drop_survey()
        for card in list(self.cards.values()):
            self.widget.remove_card(card)
        self.cards.clear()
        self.conversation.clear()
        self.decisions = []
        self.widget.clear()
        self._bill()

    def _session_changed(self, topics: set) -> None:
        if "file" in topics:                        # another project: the proposals were for the old one
            self.new_conversation()
        if "file" in topics or "project:text" in topics or "restored" in topics:
            self.refresh()
        if self.widget.opened and self.widget.mood.state == core.IDLE:
            self.widget.fill_questions()            # the checks, the results: the questions follow the project

    def _gone(self, *_args) -> None:
        self.generation += 1
        if self.provider is not None:
            self.provider.cancel()
        self.voice.close()                  # the natural voice's process ends with him

    # proposals

    def _show_proposal(self, proposal: tools.Proposal) -> None:
        from .properties import field_label
        lines = []
        for path, before, after in proposal.lines:
            label = field_label(path.split(".")[-1] if proposal.kind in tools.SECTIONS else path, proposal.kind)
            lines.append(_("{field}: from {before} to {after}").format(field=_escape(label), before=_escape(before),
                                                                    after=_escape(after)))
        if proposal.reason and proposal.reason != proposal.title:
            lines.append(f"<i>{_escape(proposal.reason)}</i>")
        if proposal.source:
            lines.append(_("Source: {source}").format(source=_escape(proposal.source)))
        if proposal.network:
            lines.append(_("It computes the year: the weather may be downloaded from PVGIS."))
        card = Card(_("Proposal: {what}").format(what=proposal.title), lines,
                    [("discard", _("Discard")), ("apply", _("Apply"))])
        card.buttons["apply"].clicked.connect(lambda _c=False, p=proposal: self.apply(p))
        card.buttons["discard"].clicked.connect(lambda _c=False, p=proposal: self.discard(p))
        self.cards[proposal.id] = card
        self.widget.add_card(card)

    def apply(self, proposal: tools.Proposal) -> None:
        """«Apply»: one step of the undo, named after Meridio and the proposal."""
        text = _("{name}: {what}").format(name=core.NAME, what=proposal.title)
        try:
            if proposal.change is not None:
                self.host.edit(text, proposal.change)
            else:
                self.host.fix(proposal.item)
        except ValueError as error:
            proposal.state = "failed"
            self.widget.note(_("Not applied: {why}").format(why=error))
        else:
            proposal.state = "applied"
            self.widget.note(_("Applied: {what}. Ctrl+Z undoes it.").format(what=proposal.title))
            self.decisions.append(f"The designer applied {proposal.id}.")
        self._drop_card(proposal)

    def discard(self, proposal: tools.Proposal) -> None:
        proposal.state = "discarded"
        self.widget.note(_("Discarded: {what}.").format(what=proposal.title))
        self.decisions.append(f"The designer discarded {proposal.id}.")
        self._drop_card(proposal)

    def _drop_card(self, proposal) -> None:
        card = self.cards.pop(proposal.id, None)
        if card is not None:
            self.widget.remove_card(card)

    # costs and voice

    def _bill(self) -> None:
        """The line of the tokens and the cost, from the first answer on."""
        bill = self.conversation.bill
        cloud = bill.dollars > 0 or (self.provider is not None and self.provider.cloud)
        self.widget.set_cost(costs.line(bill, cloud) if bill.usage.total else "")

    def _opened(self, on: bool) -> None:
        """The bubble opened: the first time ever he presents himself, and the questions ready are those of now;
        closed (Esc, its button, Ctrl+L): he stops reading."""
        if on:
            if not self.cfg.assistant_introduced and not self.widget.messages:
                self.introduce()
            if self.widget.mood.state == core.IDLE:
                self.widget.fill_questions()
        else:
            self.voice.stop()

    def use_voice(self, voice) -> None:
        """The speaker's engine (the tests give Qt's mock one): the setting applied, its availability shown."""
        if voice is not self.voice:
            self.voice.stop()
            self.voice = voice
        voice.restore = self._restore
        voice.availableChanged.connect(self._voice_available)
        self._voice_available(*voice.available())
        self._set_voice(self.cfg.assistant_voice and voice.available()[0])

    def _voice_toggled(self, on: bool) -> None:
        """The speaker clicked: remembered in the settings."""
        self.cfg.assistant_voice = on
        self.voice.set_on(on)
        self.save_config()

    def _set_voice(self, on: bool) -> None:
        """The speaker set from the settings: not a choice to save again."""
        button = self.widget.voice_button
        button.blockSignals(True)
        button.setChecked(on)
        button.blockSignals(False)
        self.widget._voice_icon(on)
        self.voice.set_on(on)

    def _voice_available(self, available: bool, why: str) -> None:
        """No engine, or no voice of the program's language: the speaker off and greyed, the setting kept (another
        day, with a voice installed, it speaks again)."""
        self.widget.set_voice(available, why)
        if not available and self.widget.voice_button.isChecked():
            self._set_voice(False)
