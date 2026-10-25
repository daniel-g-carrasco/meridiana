"""The conversation with Meridio and its loop (study 14, 6.3): a question, then rounds of model and tools until the
model answers without asking for a tool, at most ROUNDS rounds. A round is one call of the provider (`collect`,
on a worker thread in the window: ui/assistant_chat.ChatJob); the tools of the round run between two rounds on the
window's thread (tools.run), so that they read the project as it is. `answer` runs a whole turn on the calling
thread: the tests and the trials with a real server use it. No Qt."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from . import costs, tools
from .providers import Done, Provider, ProviderError, Text, ToolCall, Usage

ROUNDS = 6                      # model -> tools -> model, at most this many times for one question (study 14, 6.3)


@dataclass
class Round:
    """What one call of the model gave."""
    text: str = ""
    calls: list = field(default_factory=list)          # ToolCall
    usage: Usage = Usage()
    done: Done = Done("end")


def collect(provider: Provider, system: str, messages: list[dict], specs: list[dict],
            on_text: Callable[[str], None] | None = None) -> Round:
    """One round: the provider's stream gathered, each piece of text told to `on_text` as it comes."""
    r = Round()
    parts: list[str] = []
    for event in provider.stream(system, messages, specs):
        if isinstance(event, Text):
            parts.append(event.text)
            if on_text is not None:
                on_text(event.text)
        elif isinstance(event, ToolCall):
            r.calls.append(event)
        elif isinstance(event, Usage):
            r.usage = event
        elif isinstance(event, Done):
            r.done = event
    r.text = "".join(parts)
    return r


class Conversation:
    """The messages in the providers' common shape (providers.py), what the tools remember, the bill."""

    def __init__(self):
        self.messages: list[dict] = []
        self.state = tools.State()
        self.bill = costs.Bill()
        self.rounds = 0

    def clear(self) -> None:
        self.__init__()

    def ask(self, text: str) -> None:
        self.close_open_calls()
        self.messages.append({"role": "user", "content": text})
        self.rounds = 0

    def add_round(self, r: Round, provider: Provider) -> None:
        """The model's answer of one round, with the calls it asked for and its own content to give back."""
        self.rounds += 1
        turn = {"role": "assistant", "content": r.text,
                "calls": [{"id": c.id, "name": c.name, "arguments": c.arguments if c.arguments is not None else {}}
                          for c in r.calls]}
        if r.done.raw is not None:
            turn["raw"] = {provider.family: r.done.raw}
        self.messages.append(turn)
        self.bill.add(r.done.model or provider.model, r.usage, provider.cloud)

    def add_result(self, call: ToolCall, outcome: tools.Outcome) -> None:
        self.messages.append({"role": "tool", "id": call.id, "name": call.name, "content": outcome.content,
                              "error": outcome.error})

    def open_calls(self) -> list[dict]:
        """The calls of the last answer that have no result yet."""
        answered = set()
        for m in reversed(self.messages):
            if m["role"] == "tool":
                answered.add(m["id"])
            elif m["role"] == "assistant":
                return [c for c in m.get("calls") or [] if c["id"] not in answered]
            else:
                return []
        return []

    def close_open_calls(self) -> None:
        """A turn stopped between the model's calls and their results: each call gets a result that says so (a
        provider refuses a call without one)."""
        for c in self.open_calls():
            self.messages.append({"role": "tool", "id": c["id"], "name": c["name"], "error": True,
                                  "content": json.dumps({"error": "stopped by the designer"})})

    def run_tools(self, calls: list[ToolCall], host, apply_each: Callable | None = None) -> list[tools.Outcome]:
        """The calls of a round answered from the project (`host`), in their order."""
        outcomes = []
        for c in calls:
            if c.arguments is None:
                outcome = tools.Outcome(json.dumps({"error": "the arguments are not valid JSON", "got": c.raw[:200]}),
                                        error=True)
            else:
                outcome = tools.run(c.name, c.arguments, host, self.state)
            self.add_result(c, outcome)
            outcomes.append(outcome)
            if apply_each is not None:
                apply_each(c, outcome)
        return outcomes


def answer(conversation: Conversation, provider: Provider, system: str, question: str, host,
           specs: list[dict] | None = None, on_text=None, on_tool=None, prepare=None) -> Round:
    """A whole turn on this thread: the question, then rounds until an answer without calls or ROUNDS. `prepare`
    turns the messages into what leaves (privacy.Redactor.messages for a cloud model). ProviderError goes on."""
    specs = tools.specs() if specs is None else specs
    conversation.ask(question)
    last = Round()
    while conversation.rounds < ROUNDS:
        messages = prepare(conversation.messages) if prepare else conversation.messages
        last = collect(provider, system, messages, specs, on_text)
        conversation.add_round(last, provider)
        if last.done.reason in ("stopped", "length", "refusal") or not last.calls:
            break
        conversation.run_tools(last.calls, host, on_tool)
    return last


__all__ = ["ROUNDS", "Conversation", "ProviderError", "Round", "answer", "collect"]
