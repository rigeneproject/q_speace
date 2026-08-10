# T207 — Lightweight instruction-chat sidecar

**Status:** agentic (production)

## Purpose

Provide an instruction-tuned language interface for written dialogue on the
RTX 3060 6 GB, while retaining SpikingBrain-7B solely as an experimental
backend. The selected default is `Qwen/Qwen2.5-3B-Instruct`, loaded in NF4
4-bit in WSL2. It uses the existing `/health` and `/think` HTTP contract so
the `SpikingBrainCortex` continues to apply ILF, Sevo, cost and confidence
gates unchanged.

## Safety and BCEL

Generated text is untrusted. The server cannot mutate Q-SPEACE state; only
the existing client/cortex may submit a gated belief update. Confidence is a
mean greedy-token probability attenuated by ILF coherence; it must be assessed
by T206 calibration data. No claim of
consciousness, subjective thought, or autonomous agency is made.

## Acceptance criteria

- Server imports without torch on Windows.
- Uses `apply_chat_template` and returns non-empty generated text for a
  deterministic smoke prompt when the model is available.
- `Q_SPEACE_BRAIN_ENDPOINT` can select the service without code changes.
- Full test, Ruff, Black, mypy and compile gates pass.
