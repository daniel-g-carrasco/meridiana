"""The data: how things are written on disk and where the products come from (docs/studio/43).

atomic (a file written whole or not at all), project_archive (the .mer container), registry (the clients and the
jobs in SQLite), year_store (the years computed, in the cache), catalog/ (the products and their data), tables/
(tables made by a tool). data imports only itself: never core, app or gui; the folders it works in are given by
whoever calls (tests/nucleo/test_strati.py)."""
