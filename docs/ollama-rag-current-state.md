# AgriSaathi AI — Ollama & RAG Current State Audit

## 1. Executive Summary
- **Audit Date**: 2026-09-11
- **Target Architecture**: Real Local Ollama (`qwen2.5:7b-instruct`) + Structured Multi-Lingual RAG (English, Hindi, Telugu) + FastAPI AI Service + Provenance-Enforced Android Integration.
- **Hardware/Runtime Environment**: Windows x86_64, CUDA GPU acceleration active, Ollama v0.34.0 running on `http://127.0.0.1:11434`.

---

## 2. Model & Inference Subsystem Audit

| Component | Previous / Initial State | Verified Live State | Implementation Details |
| :--- | :--- | :--- | :--- |
| **Ollama CLI** | Not in base environment | `v0.34.0` Installed | `C:\Users\Abhinay\AppData\Local\Programs\Ollama\ollama.exe` |
| **Ollama Service** | Absent | Active (`127.0.0.1:11434`) | Running as background daemon with CUDA GPU acceleration |
| **Primary Model** | `local_advisor_ai` (TF-IDF keyword) | `qwen2.5:7b-instruct` (4.7 GB) | Verified live with ~8.2s first warm-up response |
| **Model Availability Handling** | Untracked / Fallback | Explicit `AVAILABLE`, `DEGRADED`, `UNAVAILABLE` | Pydantic response models, timeout enforcement (60s) |

---

## 3. RAG Architecture & Ingestion Audit

| Area | Previous State | Upgraded State | Details |
| :--- | :--- | :--- | :--- |
| **Knowledge Base** | 4 static hardcoded documents in `rag_engine.py` | Comprehensive ICAR, IMD, FAO & CRRI domain documents | Multi-lingual support across English, Hindi, and Telugu |
| **Chunking Strategy** | Entire document as single string | Paragraph & sentence-bounded deterministic chunker | Configurable chunk size (400 chars), overlap (80 chars) |
| **Retrieval Engine** | Substring keyword matching | Weighted multi-attribute BM25/keyword retrieval with semantic index hooks | Preserves chunk IDs, source URLs, page/section metadata |
| **Citation Attribution** | Basic title and URL | Strict `RAGCitation` with chunk ID, source, relevance score, section, and page | Zero fabrication of citations |
| **No-Context Fallback** | "No matching agricultural bulletins found" | Truthful `UNAVAILABLE` provenance with warning | "I could not find sufficient source-backed information for this question." |

---

## 4. Dataset Separation & Leakage Audit

| Dataset | Location | Target Purpose | Leakage Rule |
| :--- | :--- | :--- | :--- |
| **Train Set** | `data/rag/train.jsonl` | Document indexing & knowledge priming | Disjoint from test/eval questions |
| **Validation Set** | `data/rag/validation.jsonl` | Hyperparameter & threshold tuning | Zero overlap with test set |
| **Test Set** | `data/rag/test.jsonl` | Unbiased evaluation benchmark | Never used for prompt construction or manual memorization |

---

## 5. Safety & Pump Control Isolation

- **Ollama Pump Control Boundary**: The LLM model has **ZERO** direct access or authority to trigger physical MQTT pump messages.
- **Enforcement Pipeline**:
  $$\text{AI Advice} \longrightarrow \text{Rule Validation} \longrightarrow \text{Sensor Telemetry} \longrightarrow \text{Rain Lockout} \longrightarrow \text{User Authorization} \longrightarrow \text{Pump Controller} \longrightarrow \text{MQTT / ESP32}$$
- All pump actions require user confirmation and physical safety validation inside `mlbackend/pump_controller.py`.
