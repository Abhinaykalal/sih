# AgriSaathi AI — RAG Evaluation and Architecture Report

## 1. System Overview
- **RAG Subsystem**: `MultilingualRAGService` (`mlbackend/rag_service.py`)
- **LLM Inference Engine**: Ollama (`qwen2.5:7b-instruct`) on CUDA GPU acceleration
- **Document Repositories**: ICAR (IIRR, NRRI, IISS, CICR), IMD Agromet Advisory, UN FAO-56, PJTSAU.

---

## 2. Configuration Parameters

| Parameter | Configured Value | Environment Variable | Rationale |
| :--- | :--- | :--- | :--- |
| **Number of Source Documents** | `8` verified docs | N/A | High-integrity extension publications |
| **Number of Indexed Chunks** | `13` chunks | N/A | Deterministic sentence & paragraph split |
| **Chunk Size** | `350` characters | `RAG_CHUNK_SIZE` | Compact agricultural domain focus |
| **Chunk Overlap** | `70` characters | `RAG_CHUNK_OVERLAP` | Preserves boundary context |
| **Top-K Chunks** | `3` | `RAG_TOP_K` | Balances prompt budget with accuracy |
| **Similarity Threshold** | `1.5` | `RAG_SIMILARITY_THRESHOLD` | Eliminates irrelevant context noise |
| **Retrieval Engine** | Weighted Multi-Token Matching | N/A | Robust cross-lingual BM25 style match |
| **Supported Languages** | English (`en`), Hindi (`hi`), Telugu (`te`) | N/A | Complete multilingual tokenization |

---

## 3. Re-indexing & Operational Commands

- **Python Re-index Execution**:
  ```python
  from mlbackend.rag_service import rag_service
  rag_service.reindex()
  ```
- **FastAPI HTTP Endpoint**:
  ```bash
  curl -X POST http://localhost:8000/api/ai/rag/reindex
  ```
- **CLI Model Inspection**:
  ```powershell
  ollama list
  ```

---

## 4. Benchmark Evaluation Results on Test Set (`data/rag/test.jsonl`)

| Query ID | Language | Topic | Retrieval Match | Provenance | Grounded Answer Precision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rag-test-001` | EN | Rain Lockout / Irrigation Delay | `imd-rain-lockout-003` | `SOURCE_BACKED_KNOWLEDGE` | **High (Accurate rainfall rules)** |
| `rag-test-002` | EN | Pre-harvest Paddy Drying | `icar-rice-irr-001` | `SOURCE_BACKED_KNOWLEDGE` | **High (10-15 day rule cited)** |
| `rag-test-003` | EN | Acidic Soil pH Management | `icar-soil-npk-005` | `SOURCE_BACKED_KNOWLEDGE` | **High (Lime application cited)** |
| `rag-test-004` | EN | Potassium Osmotic Stress Role | `icar-soil-npk-005` | `SOURCE_BACKED_KNOWLEDGE` | **High (Drought/pest resistance)** |
| `rag-test-005` | EN | Fertilizer Leaching Protection | `imd-rain-lockout-003` | `SOURCE_BACKED_KNOWLEDGE` | **High (Runoff & leaching cited)** |
| `rag-test-006` | EN | Missing Sensor Telemetry | Fallback (No Chunks) | `UNAVAILABLE` | **Strict No-Hallucination Fallback** |
| `rag-test-007` | EN | Leaf Disease Diagnostic Status | Fallback / Model Card | `EXPERIMENTAL` | **Experimental Label Enforced** |
| `rag-test-008` | HI | धान में वर्षा और जल निकासी | `icar-rice-hi-006` | `SOURCE_BACKED_KNOWLEDGE` | **High (हिंदी में सटीक उत्तर)** |
| `rag-test-009` | TE | వరిలో నత్రజని అధిక వాడకం | `icar-rice-te-007` | `SOURCE_BACKED_KNOWLEDGE` | **High (తెలుగులో ఖచ్చితమైన వివరణ)** |
| `rag-test-010` | TE | పత్తి పురుగుల నివారణ | `icar-cotton-te-008` | `SOURCE_BACKED_KNOWLEDGE` | **High (వేపనూనె/ఎసిటామిప్రిడ్ సిఫార్సు)** |

---

## 5. Known Limitations & Transparency
1. **Keyword Overlap Semantic Fallback**: When domain vocabularies differ completely without synonyms, the system marks context as `UNAVAILABLE` rather than guessing.
2. **Offline Mode**: If the local Ollama daemon is offline, raw verified document excerpts are returned directly to the user with `SOURCE_BACKED_KNOWLEDGE` and a notification warning.
