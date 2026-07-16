"""SpeechOutputOrgan — cyber-physical voice emitter for SPEACE (T107).

Tries pyttsx3 for TTS. Falls back to console print.
Safety: no auto-speak, mute switch, volume limit, emission log.
"""

import pathlib
import time
from typing import Any, Dict, Optional


class SpeechOutputOrgan:
    """Emits SPEACE responses as speech or text."""

    def __init__(
        self,
        enabled: bool = True,
        muted: bool = False,
        volume: float = 0.5,
        rate: int = 150,
        log_path: str = "data/dialogue/speech_log.jsonl",
    ) -> None:
        self.enabled = enabled
        self.muted = muted
        self.volume = max(0.0, min(1.0, volume))
        self.rate = rate
        self.log_path = pathlib.Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine: Optional[Any] = None
        self._init_engine()

    def _init_engine(self) -> None:
        if not self.enabled:
            return
        try:
            import pyttsx3  # type: ignore[import-untyped]
            self._engine = pyttsx3.init()
            self._engine.setProperty("volume", self.volume)
            self._engine.setProperty("rate", self.rate)
            # Prefer Italian voice if available
            for voice in self._engine.getProperty("voices"):
                if "it-IT" in voice.id or "Italian" in voice.name:
                    self._engine.setProperty("voice", voice.id)
                    break
        except Exception:
            self._engine = None

    def speak(self, text: str, source: str = "dialogue_manager") -> Dict[str, Any]:
        if not self.enabled or self.muted:
            return self._log("muted", text, source)

        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return self._log("spoken", text, source)
            except Exception as e:
                return self._log("error", text, source, detail=str(e))
        else:
            # Fallback: console (non-blocking, safe)
            print(f"[SPEACE speech] {text}")
            return self._log("printed", text, source)

    def _log(self, mode: str, text: str, source: str, detail: Optional[str] = None) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            "timestamp": time.time(),
            "mode": mode,
            "text": text,
            "source": source,
            "volume": self.volume,
        }
        if detail:
            record["detail"] = detail
        try:
            import json
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return record

    def set_mute(self, muted: bool) -> None:
        self.muted = muted

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))
        if self._engine:
            try:
                self._engine.setProperty("volume", self.volume)
            except Exception:
                pass
