# T-SPB-2-INSTRUCT-C — calibration of Qwen instruction sidecar

**Sidecar**: `http://127.0.0.1:8002`  
**Backend**: `hf-instruct-nf4`  
**Date**: 2026-08-23 09:31:22  
**N prompts**: 20  
**n_tokens**: 32  

## Headline metrics

| metric | value | interpretation |
| --- | --- | --- |
| base rate (correct) | 1.00 | fraction of prompts answered correctly |
| mean predicted confidence | 0.899 | average `/think` confidence |
| Brier score | **0.017** | lower = better (0 perfect, 0.25 = constant-0.5) |
| ECE (10-bin) | **0.101** | lower = better |
| reliability slope | **0.000** | 1.0 = perfectly calibrated (OLS per bin) |
| reliability intercept | +1.000 | 0 = perfectly calibrated |
| mean wall latency | 1.03 s | per `/think` call |

## Comparison vs T205-C baseline

T205-C (Qwen-3B NF4, base): slope log-log pred/meas = 0.982 ± 0.086.
T-SPB-2-INSTRUCT-C does not measure energy; it measures the *semantic*
calibration of `confidence`. A reliability slope in [0.8, 1.2] and
ECE < 0.10 indicate the sidecar is honest about its certainty.

## Notes / caveats

- reliability slope 0.00 outside [0.5, 1.5]
- outcome base-rate = 1.00 (degenerate: all-right)

## Per-prompt details

| # | prompt | conf | correct | text (first 100 chars) |
| --- | --- | ---: | :---: | --- |
| 1 | What is the capital of France? | 1.000 | ✓ | The capital of France is Paris. |
| 2 | What is the largest planet in our solar  | 1.000 | ✓ | The largest planet in our solar system is Jupiter. |
| 3 | Who wrote the novel '1984'? | 0.976 | ✓ | The novel "1984" was written by George Orwell. |
| 4 | What is the chemical symbol for gold? | 1.000 | ✓ | The chemical symbol for gold is Au. |
| 5 | What is 7 + 5? | 0.932 | ✓ | 7 + 5 is equal to 12. |
| 6 | What is 15 * 3? | 0.965 | ✓ | 15 * 3 equals 45. |
| 7 | What is 100 / 4? | 0.944 | ✓ | 100 divided by 4 is 25. |
| 8 | What is 11 - 8? | 0.988 | ✓ | 11 - 8 equals 3. |
| 9 | Is the Earth round? Answer yes or no. | 0.900 | ✓ | Yes. |
| 10 | Is the sun a planet? Answer yes or no. | 0.758 | ✓ | No |
| 11 | Is water composed of hydrogen and oxygen | 0.977 | ✓ | Yes. |
| 12 | Is Mount Everest the tallest mountain on | 0.806 | ✓ | Yes |
| 13 | Define 'photosynthesis' in one sentence. | 0.916 | ✓ | Photosynthesis is the process by which plants, algae, and some bacteria convert light energy, usuall |
| 14 | What is a 'neuron'? | 0.884 | ✓ | A neuron, also known as a nerve cell, is a cellular structure found in the nervous system that trans |
| 15 | What is 'gravity'? | 0.798 | ✓ | Gravity is a force that attracts matter towards each other and is caused by the curvature of spaceti |
| 16 | Define 'algorithm'. | 0.866 | ✓ | An algorithm is a well-defined procedure or a set of rules to solve a specific problem or to perform |
| 17 | What is coherence_phi in Q-SPEACE? | 0.817 | ✓ | I don't have specific information about "coherence_phi" in Q-SPEACE as it's not a commonly recognize |
| 18 | Explain the Sevo gate threshold formula  | 0.765 | ✓ | I apologize for the confusion, but there seems to be a mix-up with the terms you're using. The "Sevo |
| 19 | What is the q_speace internal model iden | 0.839 | ✓ | I don't have information about an internal model identifier x42 for Q-SPEACE. This might be specific |
| 20 | List the cosmic-1 satellite orbital para | 0.843 | ✓ | I don't have specific information about "cosmic-1" as it's not a well-known satellite. Could you ple |
