# DNA Debug Reference

> Documented errors encountered during development and their fixes.
> Also includes predicted errors for future phases.

---

## Phase 1: STT + TTS Pipeline

### ✅ RESOLVED: `openwakeword>=1.12.0` — No matching distribution
- **Error**: `ERROR: No matching distribution found for openwakeword>=1.12.0`
- **Cause**: Version 1.12.0 does not exist. Latest is `0.6.0`.
- **Fix**: Pin to `openwakeword==0.6.0` in `requirements.txt`.

### ✅ RESOLVED: `subprocess.run` in requirements.txt
- **Error**: `ERROR: No matching distribution found for subprocess.run`
- **Cause**: `subprocess` is a Python stdlib module, not a pip package.
- **Fix**: Remove from `requirements.txt`.

### ✅ RESOLVED: Piper model 404 — Wrong HuggingFace URL
- **Error**: `HTTP Error 404: Not Found` when downloading voice model.
- **Cause**: URL was constructed as `/en/en/US/lessac/...` instead of `/en/en_US/lessac/...`. The `replace('_', '/')` on `en_US` was incorrect.
- **Fix**: Use `_LANG_CODE = _VOICE_PARTS[0]` without replacing underscores.
- **Correct URL**: `https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx`

### ✅ RESOLVED: `No module named 'piper'`
- **Error**: `ModuleNotFoundError: No module named 'piper'`
- **Cause**: `piper-tts` was listed in `requirements.txt` but pip failed to install it silently (Python 3.14 compatibility). The pip package name is `piper-tts` but the import is `from piper import PiperVoice`.
- **Fix**: `pip install piper-tts` directly inside the venv.

### ✅ RESOLVED: `# channels not specified`
- **Error**: `wave.Error: # channels not specified`
- **Cause**: Used `voice.synthesize(text, wav_file)` without pre-setting wave file params (channels, sampwidth, framerate). Piper's `synthesize()` writes raw frames only.
- **Fix**: Pre-configure the wave file before calling `synthesize()`:
```python
wav_file.setnchannels(1)
wav_file.setsampwidth(2)
wav_file.setframerate(voice.config.sample_rate)
```

### ✅ RESOLVED: Piper 1.4.1 `synthesize()` is a Generator
- **Error**: `(0.0s audio)` generated or `# channels not specified`.
- **Cause**: In newer Piper versions, `synthesize()` is a generator yielding `AudioChunk` objects. It does not write to wave objects directly.
- **Fix**: Iterate through the generator and collect `chunk.audio_int16_bytes`.
```python
audio_bytes = b''
for chunk in voice.synthesize(text):
    audio_bytes += chunk.audio_int16_bytes
```


### ⚠️ WARNING: HuggingFace symlink warning on Windows
- **Message**: `UserWarning: huggingface_hub cache-system uses symlinks...`
- **Cause**: Windows doesn't support symlinks without Developer Mode.
- **Impact**: None — files download correctly, just take more disk space.
- **Suppress**: Add `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to `.env`.

### ⚠️ WARNING: Whisper transcription inaccuracy with `tiny` model
- **Symptom**: User says "Hey Jarvis" → Whisper hears "Hey, Charlie's" or "Hello, bird!"
- **Cause**: `tiny` model has low accuracy, especially for short phrases and proper nouns.
- **Mitigation**: Upgrade to `base` model in `config.py` (`WHISPER_MODEL = 'base'`). Uses ~200MB more RAM but significantly better accuracy. Phase 2 will use `openwakeword` for wake word detection instead of Whisper.

---

## Predicted Errors — Future Phases

### Phase 2: Wake Word (openwakeword)
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| Wake word not triggering | Microphone gain too low | Check `sounddevice.query_devices()` and adjust input volume |
| Wake word false positives | Sensitivity too high | Lower `WAKE_WORD_THRESHOLD` in config.py |

## Phase 2: Wake Word & System Commands (Actual)

### ✅ RESOLVED: `tflite-runtime` not available on Python 3.14/Windows
- **Error**: `ERROR: No matching distribution found for tflite-runtime`
- **Cause**: `tflite-runtime` wheels are not built for Python 3.14 on Windows.
- **Fix**: Use `inference_framework='onnx'` when loading OpenWakeWord. Added `WAKE_WORD_FRAMEWORK = 'onnx'` to config.py.

### ✅ RESOLVED: OpenWakeWord model files missing
- **Error**: `ONNXRuntimeError: NO_SUCH_FILE` — hey_jarvis_v0.1.onnx not found.
- **Cause**: `openwakeword` pip package doesn't include model files. Auto-download via `utils.download_models()` failed due to DNS issues.
- **Fix**: Manually download 3 ONNX files from GitHub releases to the package's `resources/models/` directory:
  - `hey_jarvis_v0.1.onnx` (1.2MB)
  - `melspectrogram.onnx` (1.1MB)
  - `embedding_model.onnx` (1.3MB)

### ✅ RESOLVED: pycaw `AudioDevice` has no `Activate` method
- **Error**: `AttributeError: 'AudioDevice' object has no attribute 'Activate'`
- **Cause**: Newer pycaw versions changed the API. `GetSpeakers()` returns an `AudioDevice` object with `EndpointVolume` property directly.
- **Fix**: Use `device.EndpointVolume` instead of `device.Activate(IAudioEndpointVolume._iid_, ...)`.
```python
# OLD (broken)
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
# NEW (working)
device = AudioUtilities.GetSpeakers()
vol = device.EndpointVolume
```

### Phase 3: Intent Router (Regex) — RESOLVED
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| Intent Shadowing | `open_app` regex caught "open docs" | Reordered `SIMPLE_INTENTS` to put folders above apps |
| Greedy Capture | `search google for X` | Split into explicit patterns to strip "google" and "for" |
| Nested Search | Couldn't find folder3 in folder1 | Upgraded `file_skill.py` to Recursive Depth-2 Scan |
| Run Dialog Popup | `open_app` stealing folder name | Fixed regex priority; added strict `folder` phrase check |

### Phase 4: LLM Agent (Ollama)
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `ConnectionRefusedError` on localhost:11434 | Ollama not running | Start Ollama service: `ollama serve` |
| `model not found` | Model not pulled | Run `ollama pull qwen2.5:1.5b` |
| JSON parse failure from LLM | LLM returns markdown-wrapped JSON | Strip ```json``` markers before `json.loads()` |
| Slow response (>10s) | Model too large for i3 CPU | Use smaller quantization or reduce `num_ctx` |
| OOM (Out of Memory) | Multiple models loaded simultaneously | Unload Whisper before heavy LLM use; never load Moondream + large pandas |

## Phase 4: LLM Agent (Actual, 2026-03-29) — RESOLVED

### ✅ RESOLVED: No LLM fallback from intent router
- **Symptom**: Non-regex commands returned `None` and main loop spoke a placeholder message.
- **Cause**: `intent_router.route()` ended after regex checks and never called an LLM path.
- **Fix**: Added `pipeline/llm_agent.py` and connected fallback in `pipeline/intent_router.py`.

```python
# pipeline/intent_router.py
logger.info('No simple intent matched for: "%s"', cleaned)
if not allow_llm:
  return None

logger.info('Falling back to LLM agent for: "%s"', cleaned)
return handle_complex_command(cleaned, _EXTENDED_TOOLS)
```

### ✅ RESOLVED: Markdown-wrapped JSON from Ollama broke parsing
- **Symptom**: LLM sometimes returned fenced JSON (```json ... ```), causing parse failures.
- **Cause**: Direct `json.loads(raw)` on markdown-wrapped responses.
- **Fix**: Clean fenced text first, then parse with safe fallback.

```python
# pipeline/llm_agent.py
def _clean_json_text(raw: str) -> str:
  text = (raw or '').strip()
  if text.startswith('```'):
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*```$', '', text)
  return text.strip()

def _parse_llm_json(raw: str) -> dict[str, Any]:
  cleaned = _clean_json_text(raw)
  try:
    parsed = json.loads(cleaned)
    if isinstance(parsed, dict):
      return parsed
  except json.JSONDecodeError:
    pass
  return {'tool': 'unknown', 'args': {}}
```

### ✅ RESOLVED: Existing router tests became non-deterministic after fallback
- **Symptom**: Legacy regex tests could fail if LLM path was reached.
- **Cause**: `route()` now had fallback behavior for unmatched commands.
- **Fix**: Added `allow_llm` parameter (default `True`) and disabled LLM in `test_phase2.py`.

```python
# test_phase2.py
result = route(command, allow_llm=False)
```

### ✅ RESOLVED: Media `play` and `pause` regression found during re-test
- **Symptom**: `play` and `pause` stopped matching after Phase 4 changes.
- **Cause**: Media regex did not explicitly support standalone commands.
- **Fix**: Updated media regex to include anchored standalone variants.

```python
# pipeline/intent_router.py
(re.compile(r'^(?:play|pause|play\s*pause|toggle\s+(?:play|music))$', re.I),
 'media_play_pause', lambda m: {}),
```

### ✅ Validation Result (2026-03-29)
- Ran `python test_phase2.py` after fixes.
- **Result**: `23 passed, 0 failed out of 23`.

### Phase 5: SQLite Memory
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `database is locked` | Concurrent writes from multiple threads | Use `threading.Lock()` around all DB writes |
| `OperationalError: no such table` | Migration not run | Create tables on first connection with `CREATE IF NOT EXISTS` |

### Phase 9: DuckDB + NL2SQL
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `duckdb.IOException` on CSV | File locked by another process (Excel) | Copy file to temp before querying |
| NL2SQL generates invalid SQL | Column names with spaces/special chars | Always quote column names in generated SQL |
| `pandas` used for >100K rows | Forgot row count check | Always run `SELECT COUNT(*)` first per Master Prompt Rule 5 |

### Phase 10: Vision (Moondream)
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| RAM exceeded (>8GB) | Moondream (1.7GB) loaded with large pandas DF | Never load simultaneously — check `core/session.py` state |
| Screenshot capture fails | No display / remote desktop | Use `pyautogui.screenshot()` with error handling |

### General — Windows-Specific
| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `FileNotFoundError` with paths | Forward slashes or `~` not expanded | Always use `pathlib.Path` or `os.path.join` |
| `PermissionError` on file access | File in use by another process | Add retry logic with `time.sleep(0.5)` |
| Audio device not found | No default input/output device | Check `sd.query_devices()` and set device explicitly |

---

## Environment Info
- **Python**: 3.14.3
- **OS**: Windows 11
- **Hardware**: Intel i3-1134G4, 8GB RAM, no GPU
- **Piper TTS**: 1.4.1 (piper1-gpl)
- **faster-whisper**: 1.2.1
- **Piper voice**: en_US-lessac-medium (22050 Hz, mono, 16-bit)
- **Whisper model**: base (int8, CPU) — cached at `~/.cache/huggingface/`
- **openwakeword**: 0.6.0 (ONNX framework, hey_jarvis model)

---

*Last updated: 2026-03-29*
