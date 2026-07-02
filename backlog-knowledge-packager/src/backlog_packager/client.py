"""ReadOnlyBacklogClient — GET / download only (design §9.1).

post / put / patch / delete are intentionally NOT defined so that the
read-only requirement (FR-11) is enforced by structure. Do not add
write methods to this module.

TODO(#3): get() / download() with apiKey query auth, BACKLOG_DOMAIN
support, 429 retry, apiKey masking in logs.
"""
