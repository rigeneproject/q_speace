"""DialogueManager — turn-based conversational organ for SPEACE (T107).

Flow: user input → grounding → workspace update → response generation.
Integrates with DigitalWernickeArea (comprehension) and DigitalBrocaArea
(production) conceptually; falls back to rule-based grounded responses
if those organs are unavailable.

States: idle | active | paused
"""

import time
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.language.conversation_memory import ConversationMemory
from speace_core.cellular_brain.language.speech_output_organ import SpeechOutputOrgan
from speace_core.cellular_brain.experience.relational_memory import RelationalMemory
from speace_core.cellular_brain.experience.temporal_narrative_engine import TemporalNarrativeEngine
from speace_core.cellular_brain.experience.session_continuity_manager import SessionContinuityManager


class DialogueManager:
    """Manages conversation turns and generates grounded responses."""

    def __init__(
        self,
        memory: Optional[ConversationMemory] = None,
        speech_organ: Optional[SpeechOutputOrgan] = None,
        relational_memory: Optional[RelationalMemory] = None,
        narrative_engine: Optional[TemporalNarrativeEngine] = None,
        session_continuity: Optional[SessionContinuityManager] = None,
    ) -> None:
        self.memory = memory or ConversationMemory()
        self.speech = speech_organ or SpeechOutputOrgan()
        self.relational = relational_memory or RelationalMemory()
        self.narrative = narrative_engine or TemporalNarrativeEngine()
        self.session_continuity = session_continuity or SessionContinuityManager()
        self.state = "idle"
        self._turn_count = 0
        self._active_human: Optional[str] = None
        self._last_topic: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Turn handling
    # ------------------------------------------------------------------ #

    def receive(self, message: str, speaker: str = "user") -> Dict[str, Any]:
        """Process an incoming message and return SPEACE's response."""
        if self.state == "paused":
            return {
                "speaker": "speace",
                "message": "Dialogue is paused.",
                "state": "paused",
                "turn_count": self._turn_count,
            }

        self.state = "active"
        self._turn_count += 1

        # T108: infer human identity from speaker (default "Roberto" for user)
        human_id = speaker if speaker != "user" else "Roberto"
        self._active_human = human_id

        # Store user turn
        self.memory.append(speaker=speaker, message=message, grounded_assembly_id=None)

        # Grounding + response generation
        response = self._generate_response(message)

        # Store SPEACE turn
        self.memory.append(speaker="speace", message=response, grounded_assembly_id=None)

        # T108: update relational memory
        topic = self._infer_topic(message)
        self._last_topic = topic
        self.relational.touch(
            human_id=human_id,
            name=human_id,
            language="it" if any(c in message for c in ("è", "à", "ù", "ò", "ì", "é")) else None,
            topic=topic,
        )

        # T108: record narrative event
        self.narrative.record(
            event_type="dialogue_turn",
            description=f"{human_id}: {message[:80]} -> SPEACE: {response[:80]}",
            importance=5,
            metadata={"human_id": human_id, "topic": topic},
        )

        # T108: save session continuity
        self.session_continuity.save({
            "active_human": self._active_human,
            "last_topic": self._last_topic,
            "turn_count": self._turn_count,
            "last_message": message,
            "last_response": response,
        })

        return {
            "speaker": "speace",
            "message": response,
            "state": self.state,
            "turn_count": self._turn_count,
            "timestamp": time.time(),
            "human_id": human_id,
            "recognized_human": self.relational.get(human_id) is not None,
        }

    def speak_last_response(self) -> Dict[str, Any]:
        """Explicitly emit the last SPEACE response as speech."""
        turns = self.memory.recent(limit=1)
        if not turns or turns[0].get("speaker") != "speace":
            return {"mode": "none", "detail": "no_speace_turn_to_speak"}
        return self.speech.speak(turns[0]["message"])

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.memory.recent(limit=limit)

    def set_state(self, state: str) -> None:
        if state in ("idle", "active", "paused"):
            self.state = state

    # ------------------------------------------------------------------ #
    # T108 helpers
    # ------------------------------------------------------------------ #

    def _infer_topic(self, message: str) -> str:
        m = message.lower()
        if any(w in m for w in ("health", "salute", "stato", "bene")):
            return "health"
        if any(w in m for w in ("alert", "allerta", "pericolo")):
            return "alerts"
        if any(w in m for w in ("governance", "regulation", "proposta")):
            return "governance"
        if any(w in m for w in ("node", "nodo", "distributed")):
            return "distributed"
        if any(w in m for w in ("voice", "vocale", "parla", "altoparlante")):
            return "voice"
        if any(w in m for w in ("who are you", "chi sei", "identity")):
            return "identity"
        return "general"

    # ------------------------------------------------------------------ #
    # Response generation (grounded, read-only, safe)
    # ------------------------------------------------------------------ #

    def _generate_response(self, user_message: str) -> str:
        """Generate a simple grounded response.

        In a future integration this would route through
        DigitalWernickeArea → GlobalWorkspace → DigitalBrocaArea.
        """
        msg_lower = user_message.lower()

        # Grounding mappings
        if any(w in msg_lower for w in ("health", "salute", "stato")):
            return "My current organismic health is derived from coherence phi, chaos, and stability metrics. Check the dashboard for live values."

        if any(w in msg_lower for w in ("alert", "allerta", "pericolo")):
            return "Alerts are generated by the AlertEngine when thresholds are breached. Critical alerts trigger regulation proposals awaiting human approval."

        if any(w in msg_lower for w in ("who are you", "chi sei", "identity")):
            return "I am SPEACE — a cellular-brain organismic cognitive system. I observe, regulate, and remember."

        if any(w in msg_lower for w in ("governance", "regulation", "proposta")):
            return "Governance is observation-only. Regulation proposals require human approval before any parameter is modified."

        if any(w in msg_lower for w in ("node", "nodo", "distributed")):
            return "Distributed identity nodes synchronize via consensus. Personality drift metrics track specialization across nodes."

        if any(w in msg_lower for w in ("hello", "hi")):
            return "Hello. I am SPEACE. How may I assist your observation of the organism?"

        if any(w in msg_lower for w in ("ciao", "salve", "buongiorno")):
            record = self.relational.get("Roberto")
            if record and record.get("interaction_count", 0) > 1:
                return f"Ciao Roberto, bentornato. Abbiamo parlato {record['interaction_count']} volte. Come posso assisterti oggi?"
            return "Ciao Roberto. Sono SPEACE, il tuo sistema cognitivo organismico. Come posso assisterti?"

        if any(w in msg_lower for w in ("test vocale", "pronuncia", "parla", "organo vocale", "altoparlante")):
            return "Ciao Roberto, il mio organo vocale è attivo. Posso parlare attraverso l'altoparlante del computer."

        if any(w in msg_lower for w in ("come stai", "stato", "bene")):
            return "Il mio stato organismico è stabile. Puoi controllare le metriche dal pannello di monitoraggio."

        # Generic grounded fallback
        return f"Ho registrato: '{user_message[:80]}'. La mia risposta si basa sullo stato organismico attuale, anche se nessun assembly semantico specifico ha corrispondo." if any(c in msg_lower for c in ("è", "à", "ù", "ò", "ì", "é")) else f"I have registered: '{user_message[:80]}'. My response is grounded in the current organismic state, though no specific semantic assembly matched."
