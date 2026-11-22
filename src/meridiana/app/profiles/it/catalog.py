"""Catalogue records and separately declared market scope, without changing raw data."""
from copy import deepcopy


def context(records):
    return {"records": deepcopy(records),
            "market_scope": {key: "it" if isinstance(value, dict) and value.get("market_scope") == "it" else None
                             for key, value in records.items()}}
