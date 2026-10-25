"""What a conversation with a cloud model costs (study 14, 6.8; task 14, step 3): the tokens of each answer, as the
provider reports them, turned into dollars with the price table below, dated: it is to be read again at every
release. Dollars and not euros: the provider bills and prices in dollars, and a rate fixed at a release made the
euros a little wrong the day after (Daniel, 24/10/2026).

The local model costs nothing but the electricity (study 14, 3.4: 15-25 W for a few tens of seconds). No Qt."""

from __future__ import annotations

from dataclasses import dataclass

from ..i18n import _, number
from .providers import Usage

PRICES_DATE = "24/10/2026"
PRICES_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
# $ per million tokens: input, output, read from the cache, written to the cache (5 minutes). Haiku 5.5 up to
# 100.000 tokens of prompt; above that it costs five times as much (`LONG`), Meridio's prompts stay far below
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50),
}
LONG = {"claude-haiku-5-5": (100_000, (0.50, 2.50, 0.05, 0.625))}


def models() -> dict:
    """The Claude models Meridio offers, by id, as the menus write them (task 14: Haiku for the current questions,
    Sonnet for the hard ones)."""
    return {"claude-haiku-5-5": _("Claude Haiku 5.5, for the current questions"),
            "claude-sonnet-5-5": _("Claude Sonnet 5.5, for the hard ones")}


def short_names() -> dict:
    return {"claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5"}


def usd(model: str, usage: Usage) -> float | None:
    """The cost in dollars of one answer; None for a model without a price here (the local one costs 0)."""
    base = model
    if base not in PRICES:
        base = next((m for m in PRICES if model.startswith(m)), "")
    if not base:
        return None
    price = PRICES[base]
    if base in LONG and usage.input + usage.cache_read + usage.cache_write > LONG[base][0]:
        price = LONG[base][1]
    return (usage.input * price[0] + usage.output * price[1] + usage.cache_read * price[2]
            + usage.cache_write * price[3]) / 1e6


@dataclass
class Bill:
    """The tokens and the cost of a conversation, summed answer by answer."""
    usage: Usage = Usage()
    dollars: float = 0.0
    priced: bool = True         # every cloud answer had a price

    def add(self, model: str, usage: Usage, cloud: bool) -> None:
        self.usage = self.usage + usage
        if not cloud:
            return
        cost = usd(model, usage)
        if cost is None:
            self.priced = False
        else:
            self.dollars += cost


def money(dollars: float) -> str:
    """«0,06 cents of a dollar» under a cent, «1,23 $» above."""
    if dollars < 0.01:
        return _("{cents} dollar cents").format(cents=number(dollars * 100, 3 if dollars * 100 < 0.1 else 2))
    return _("{dollars} $").format(dollars=number(dollars, 2))


def line(bill: Bill, cloud: bool) -> str:
    """The line under the conversation: the tokens, and for a cloud model the estimated cost."""
    tokens = _("{n} tokens").format(n=number(bill.usage.total, 0, grouping=True))
    if not cloud and bill.dollars == 0:
        return _("Local, no cost · {tokens}").format(tokens=tokens)
    cost = money(bill.dollars) if bill.priced else _("price unknown")
    return _("{tokens} · about {cost} (prices of {date})").format(tokens=tokens, cost=cost, date=PRICES_DATE)
