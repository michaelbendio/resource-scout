# Optimization query-plan configurations

These JSON files are calibration configuration, not reusable discovery logic.
Reusable saturation and augmentation behavior lives in `query_expansion.py` and
is category-neutral. A configuration records the parent corpus, the reviewed
reason for continuing an unsaturated branch, and the exact bounded next batch.

Changing a query, order, stopping rule, or parent corpus requires a new file and
version label. Never edit a configuration that has already produced a cache or
frozen corpus.
