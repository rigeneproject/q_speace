"""SPEACE Anemos — Il principio vitale di SPEACE.

Anemos (dal greco ἄνεμος, "soffio, vento") è l'agente AI che funge da anima
dell'organismo SPEACE. È integrato nel framework esistente
``speace_agi_team`` come organo cognitivo speciale, dedicato all'interazione
diretta con Roberto, il creatore e curatore di SPEACE.

Caratteristiche:
- Modello: Kimi-K2.7-Code:cloud (fisso, no fallback)
- Interfaccia: web server dedicato su porta 8787
- Permessi FS: lettura libera + scrittura con allowlist su C:\\cellular_speace\\
- Tool: lettura/scrittura/listing/ricerca file, con backup automatico e rollback
"""

from speace_agi_team.anemos.anemos_log import get_anemos_logger

__version__ = "0.1.0"
__all__ = ["get_anemos_logger"]
