# T201 — Q-SPEACE Radio Layer (Strato 2 Fisico-Radio)

**Status**: implementation complete (baseline)
**Scope**: physical EM interaction layer for the SPEACE protocol
**BCEL gate**: `q_speace/bcel/catalog.py` — 4 nuove equivalenze

## 1. Purpose

Implements Strato 2 (Fisico-Radio) and the missing Sense/Act half of Strato 3
(Controllo Cibernetico) of the SPEACE protocol. Enables AI agents to interact
physically with wireless signals via SDR, metasurfaces, and compliance filters.

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Orchestrator                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Spectrum │  │Wavefront │  │  ComplianceFilter  │  │
│  │  Sensor  │  │Modulator │  │  + RadioEmulator   │  │
│  │ (Sense)  │  │(Modulate)│  │  (Validate)        │  │
│  └────┬─────┘  └────┬─────┘  └─────────┬─────────┘  │
│       │             │                  │            │
│       └─────────────┼──────────────────┘            │
│                     │                               │
│              ┌──────┴──────┐                        │
│              │  SDRFrontend │                        │
│              │ (NullSDR ☑)  │                        │
│              └──────┬──────┘                        │
│                     │                               │
│              ┌──────┴──────┐                        │
│              │ Metasurface  │                        │
│              │ Controller   │                        │
│              └─────────────┘                        │
│                                                     │
│  DigitalTwinRF (gemello digitale catena RF)         │
└─────────────────────────────────────────────────────┘
```

## 3. Modules

### `radio/models.py`
Data classes: `Waveform`, `SpectrumReading`, `FrequencyRange`,
`ModulationParams`, `BeamformingConfig`, `TransmissionReport`.

### `radio/sdr_frontend.py`
- `SDRFrontend` (ABC) — transmit/receive/scan_spectrum/close
- `NullSDR` — software simulator (default, always available)
- Future: `HackRFSDR`, `BladeRFSDR`, `USRPSDR` (require `hackrf`/`soapy`)

### `radio/spectrum_sensor.py`
- `SpectrumSensor` — Sense EM environment
- `sense()` → `SpectrumReading` with RSSI, SNR, occupancy, quality_index
- `update_environment_map()` → radio environment MAP

### `radio/wavefront_modulator.py`
- `WavefrontModulator` — encode/decode Q* ILF to/from spread-spectrum waveform
- `encode(state_vector)` → `Waveform` (BPSK + spreading code + carrier)
- `decode(waveform)` → state vector (carrier recovery + despreading)

### `radio/metasurface_controller.py`
- `MetasurfaceController` — programmable beamforming
- `configure(BeamformingConfig)` — set phase/amplitude profile
- `beamform(waveform, azimuth)` → shaped waveform
- `interference_pattern(focal_point)` → focus EM energy at a point

### `radio/compliance_filter.py`
- `ComplianceFilter` — FCC/ETSI pre-transmission validation
- `RadioEmulator` — wraps filter, tracks validation history

### `radio/digital_twin_rf.py`
- `DigitalTwinRF` — device-level model of SDR chain (LNA, mixer, ADC)
- `predict_cascaded_gain()`, `predict_noise_figure()`, `predict_sensitivity()`
- `estimate_link_budget()` — full path loss + margin calculation

## 4. Integration with orchestrator

The `_run_quantum_step()` method now executes a full Sense-Decide-Act cycle:

1. **Sense**: `SpectrumSensor.sense()` → spectrum reading → modulates ILF coherence
2. **Decide** (unchanged): KL update + Sevo/energy gate
3. **Act** (new):
   - Encode updated Q* via `WavefrontModulator.encode_q_star()`
   - Shape via `MetasurfaceController.beamform()` (if active)
   - Validate via `RadioEmulator.validate()`
   - Transmit via `SDRFrontend.transmit()`

## 5. CLI

```bash
qspace quantum run --radio            # enable radio layer
qspace quantum run --radio --metasurface  # enable radio + metasurface
```

## 6. BCEL additions

| Concept | Classification | Digital rule |
|---|---|---|
| Radio wavefront as biological tissue | accidental | EM field is engineered carrier, not tissue |
| Metasurface as artificial skin | functional | Programmable beamforming controller |
| SDR as artificial cochlea/vocal cords | functional | Software-defined transceiver |
| Cognitive radio as neural adaptation | functional | Spectrum sensor + adaptive hopping |
| Regulatory compliance as immune system | functional | ComplianceFilter/RadioEmulator as hard gate |

## 7. Quality gates

- [x] `pytest` passes (88 tests)
- [x] `ruff check` clean
- [x] Coverage > 20% (78.69%)
- [x] New behavior covered by 19 tests in `tests/test_radio.py`
