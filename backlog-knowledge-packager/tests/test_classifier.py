"""Unit tests for the rule-based classifier (design §6).

TODO(#8): boundary cases such as "規約テンプレート" → template (match order),
each of the 7 categories, and the unclassified fallback.
Currently only guards that the package skeleton imports.
"""

import backlog_packager


def test_package_imports() -> None:
    assert backlog_packager.__version__
