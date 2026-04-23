"""Rhythmscape metrics layer.

Downstream of the ``ingest`` layer. Reads the parquet artifacts produced by
the TAGO batch and emits quantitative indicators — currently RDI
(Rhythmic Discordance Index) and the ``critique_flag`` post-processor.
ARDI and PRM are deferred to later sessions.
"""
