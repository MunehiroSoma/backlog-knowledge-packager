"""Rule-based classification into 7 categories + unclassified (design §6).

Keyword match on title/path, evaluated top-down, first match wins
(template before rule — see design §6.2 for the order rationale).

TODO(#8): keyword table constant and classify() implementation.
"""
