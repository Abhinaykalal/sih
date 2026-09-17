"""
AgriSaathi AI — Advanced Deterministic Multilingual RAG Service
===============================================================
Indexes verified extension documentation from ICAR, IMD, FAO, CRRI, and TNAU.
Supports English, Hindi, and Telugu queries with deterministic paragraph chunking,
metadata preservation, citation attribution, and Ollama grounded synthesis.
"""

import os
import re
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

try:
    from .llm_provider import hybrid_provider, LLMInferenceResponse, LLMProviderName
except ImportError:
    from llm_provider import hybrid_provider, LLMInferenceResponse, LLMProviderName

# Backwards-compat alias for existing code that imports ollama_service
try:
    from .ollama_service import ollama_service
except ImportError:
    try:
        from ollama_service import ollama_service
    except ImportError:
        ollama_service = None

logger = logging.getLogger("agrisaathi.rag")

# RAG Configuration
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "350"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "70"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "8.0"))

class DocumentSourceMetadata(BaseModel):
    doc_id: str
    title: str
    organization: str
    url: str
    section: Optional[str] = None
    page: Optional[int] = None
    crop: str
    topic: str # irrigation | pest_control | disease | fertilizer | climate_resilience
    language: str # en | hi | te
    publication_year: int = 2025
    growth_stage: Optional[str] = None

class KnowledgeChunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    organization: str
    url: str
    section: Optional[str] = None
    page: Optional[int] = None
    crop: str
    topic: str
    language: str
    text: str
    tokens_count: int
    # Extended provenance fields
    growth_stage: Optional[str] = None
    verification_status: str = "VERIFIED_GOVERNMENT_EXTENSION"

class CitationInfo(BaseModel):
    chunk_id: str
    title: str
    source: str
    section: Optional[str] = None
    page: Optional[int] = None
    relevance_score: float

class RAGQueryResponse(BaseModel):
    answer: str
    provenance: str # SOURCE_BACKED_KNOWLEDGE | RULE_BASED | UNAVAILABLE
    citations: List[CitationInfo]
    retrieved_chunks: int
    model_name: str
    model_status: str # AVAILABLE | UNAVAILABLE | DEGRADED | EXPERIMENTAL
    request_id: Optional[str] = None
    generated_at: str
    warnings: List[str] = Field(default_factory=list)

class MultilingualRAGService:
    """Production multilingual RAG service for precision agricultural extension."""

    def __init__(
        self,
        chunk_size: int = RAG_CHUNK_SIZE,
        chunk_overlap: int = RAG_CHUNK_OVERLAP,
        similarity_threshold: float = RAG_SIMILARITY_THRESHOLD
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        self._raw_documents: List[Dict[str, Any]] = []
        self.chunks_index: List[KnowledgeChunk] = []
        self.corpus_hash: Optional[str] = None
        self._load_from_corpus()
        self.reindex()

    def _load_from_corpus(self):
        """Loads verified agricultural extension documents from data/rag JSON."""
        import json
        import hashlib
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rag", "icar_knowledge.json")
        try:
            with open(data_path, "rb") as f:
                content = f.read()
                self.corpus_hash = hashlib.sha256(content).hexdigest()
                docs = json.loads(content.decode("utf-8"))
                
            self._raw_documents = []
            for d in docs:
                self._raw_documents.append({
                    "meta": DocumentSourceMetadata(**d["meta"]),
                    "content": d["content"]
                })
        except Exception as e:
            logger.warning(f"Failed to load RAG documents from {data_path}: {e}")
            self._raw_documents = []
            self.corpus_hash = None


    def _chunk_text_deterministic(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Splits document text on sentence or paragraph boundaries deterministically."""
        sentences = re.split(r'(?<=[.!?।॥\n])\s+', text.strip())
        chunks = []
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            s_clean = sentence.strip()
            if not s_clean:
                continue
            s_len = len(s_clean)
            if current_len + s_len > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # retain tail for overlap
                overlap_chunk = []
                accum = 0
                for prev in reversed(current_chunk):
                    if accum + len(prev) < overlap:
                        overlap_chunk.insert(0, prev)
                        accum += len(prev)
                    else:
                        break
                current_chunk = overlap_chunk
                current_len = sum(len(x) for x in current_chunk)

            current_chunk.append(s_clean)
            current_len += s_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def reindex(self):
        """Indexes all raw documents into chunks with unique deterministic IDs."""
        self.chunks_index.clear()
        for doc in self._raw_documents:
            meta: DocumentSourceMetadata = doc["meta"]
            raw_content = doc["content"]
            chunk_texts = self._chunk_text_deterministic(raw_content, self.chunk_size, self.chunk_overlap)
            
            for idx, c_text in enumerate(chunk_texts):
                chunk_id = f"{meta.doc_id}-chk-{idx+1:02d}"
                self.chunks_index.append(KnowledgeChunk(
                    chunk_id=chunk_id,
                    doc_id=meta.doc_id,
                    title=meta.title,
                    organization=meta.organization,
                    url=meta.url,
                    section=meta.section,
                    page=meta.page,
                    crop=meta.crop,
                    topic=meta.topic,
                    language=meta.language,
                    text=c_text,
                    tokens_count=len(c_text.split()),
                    growth_stage=meta.growth_stage,
                    verification_status="VERIFIED_GOVERNMENT_EXTENSION"
                ))
        logger.info(f"RAG indexing complete: {len(self._raw_documents)} documents -> {len(self.chunks_index)} chunks")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizes text preserving multilingual script characters and removing common stopwords."""
        STOPWORDS = {
            "in", "the", "is", "of", "to", "and", "for", "at", "on", "by", "or", "an", "as", "it",
            "are", "with", "this", "that", "from", "be", "was", "were", "what", "when", "how", "why",
            "की", "के", "में", "का", "और", "से", "है", "को", "पर", "लिए", "ने", "हो",
            "మరియు", "లో", "యొక్క", "నుండి", "కు", "తో"
        }
        words = re.findall(r'[\w\u0900-\u097F\u0C00-\u0C7F]+', text.lower())
        return [w for w in words if len(w) > 1 and w not in STOPWORDS]

    def retrieve_chunks(
        self,
        query: str,
        crop: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = RAG_TOP_K
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """Scores chunks using multi-attribute token matching with contextual weighting."""
        q_tokens = set(self._tokenize(query))
        if not q_tokens or len(q_tokens) == 0:
            return []

        scored_chunks: List[Tuple[KnowledgeChunk, float]] = []

        for chunk in self.chunks_index:
            score = 0.0
            
            # Content and title token matching
            chunk_tokens = set(self._tokenize(chunk.text + " " + chunk.title + " " + chunk.topic))
            intersection = q_tokens.intersection(chunk_tokens)
            
            # Require at least one meaningful domain token match before applying crop/topic boost
            if intersection:
                score += len(intersection) * 3.0
                
                # Domain topic & crop boost
                if crop and (crop.lower() in chunk.crop.lower() or chunk.crop.lower() in crop.lower()):
                    score += 3.0
                if topic and topic.lower() in chunk.topic.lower():
                    score += 3.0

                # Exact phrase substring bonus
                if query.lower().strip() in chunk.text.lower():
                    score += 5.0

            if score >= self.similarity_threshold:
                scored_chunks.append((chunk, round(score, 2)))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def search(self, query: str, crop: Optional[str] = None, top_k: int = RAG_TOP_K) -> List['KnowledgeDocument']:
        """Backward-compat alias returning a flat list of KnowledgeDocument objects (no scores)."""
        results = []
        for chunk, _ in self.retrieve_chunks(query, crop=crop, top_k=top_k):
            results.append(KnowledgeDocument(
                id=chunk.chunk_id,
                title=chunk.title,
                source=chunk.organization,
                source_organization=chunk.organization,
                url=chunk.url,
                publication_date="2025-01-01",
                crop=chunk.crop,
                growth_stage=chunk.growth_stage,
                region="India",
                topic=chunk.topic,
                language=chunk.language,
                content=chunk.text,
                verification_status=chunk.verification_status,
                citation_id=chunk.doc_id
            ))
        return results

    def search_with_citations(self, query: str, crop: Optional[str] = None, top_k: int = RAG_TOP_K):
        """Backward-compat alias returning (chunk, score) tuples."""
        return self.retrieve_chunks(query, crop=crop, top_k=top_k)

    def query_rag(
        self,
        question: str,
        language: str = "en",
        crop: Optional[str] = None,
        farm_context: Optional[str] = None,
        top_k: int = RAG_TOP_K,
        model_override: Optional[str] = None
    ) -> RAGQueryResponse:
        """Executes full RAG pipeline: retrieval, citation formatting, and hybrid LLM synthesis."""
        import datetime
        now_iso = datetime.datetime.now().isoformat()

        # Detect active provider for status reporting
        provider_status = hybrid_provider.get_status()

        # 1. Retrieve relevant knowledge chunks
        matched = self.retrieve_chunks(question, crop=crop, top_k=top_k)

        # 2. Check if context is sufficient
        if not matched:
            fallback_msg = (
                "I could not find sufficient source-backed information for this question in the verified agricultural knowledge base."
                if language == "en" else
                "सत्यापित कृषि ज्ञानकोष में इस प्रश्न के लिए पर्याप्त प्रामाणिक जानकारी उपलब्ध नहीं हो सकी।"
                if language == "hi" else
                "ధృవీకరించబడిన వ్యవసాయ నాలెడ్జ్ బేస్‌లో ఈ ప్రశ్నకు తగిన ఆధారాలు లభించలేదు."
            )
            return RAGQueryResponse(
                answer=fallback_msg,
                provenance=f"UNAVAILABLE (sha256:{self.corpus_hash})" if self.corpus_hash else "UNAVAILABLE",
                citations=[],
                retrieved_chunks=0,
                model_name=provider_status.model_name,
                model_status="UNAVAILABLE",
                generated_at=now_iso,
                warnings=["No sufficiently relevant knowledge-base context was found."]
            )

        # 3. Assemble Citations
        citations: List[CitationInfo] = []
        context_parts: List[str] = []
        for chk, score in matched:
            citations.append(CitationInfo(
                chunk_id=chk.chunk_id,
                title=chk.title,
                source=f"{chk.organization} ({chk.url})",
                section=chk.section,
                page=chk.page,
                relevance_score=score
            ))
            context_parts.append(f"[{chk.organization} - {chk.title} (Section: {chk.section or 'N/A'})]\n{chk.text}")

        assembled_context = "\n\n".join(context_parts)

        # 4. Construct Grounded Prompt for Ollama
        system_prompt = (
            "You are AgriSaathi AI, an expert agricultural advisor. "
            "Base your answer strictly on the provided Extension Context. "
            "Do NOT hallucinate facts, do NOT claim physical pump activation, and clearly explain rules to the farmer. "
            "If the context is incomplete, acknowledge limitations truthfully."
        )
        if language == "hi":
            system_prompt += " Respond in Hindi (हिंदी)."
        elif language == "te":
            system_prompt += " Respond in Telugu (తెలుగు)."

        user_prompt = (
            f"Extension Context:\n{assembled_context}\n\n"
        )
        if farm_context:
            user_prompt += f"Current Farm Telemetry/Sensor Context:\n{farm_context}\n\n"
        user_prompt += f"Farmer Question: {question}\n\nProvide a concise, practical, and grounded answer:"

        # 5. Call hybrid LLM provider (Ollama local, Groq cloud, or RAG_ONLY honest fallback)
        rag_excerpt = (
            f"Source-backed advisory from {matched[0][0].organization}:\n\n{matched[0][0].text}"
        )
        llm_resp: LLMInferenceResponse = hybrid_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            rag_excerpt=rag_excerpt,
        )

        # 6. Build response — honest labeling for all provider states
        if llm_resp.status == "RAG_ONLY" or not llm_resp.answer:
            direct_summary = (
                "LLM synthesis unavailable — showing source-backed excerpts.\n\n"
                + rag_excerpt
            )
            return RAGQueryResponse(
                answer=direct_summary,
                provenance=f"RAG_ONLY (sha256:{self.corpus_hash})" if self.corpus_hash else "RAG_ONLY",
                citations=citations,
                retrieved_chunks=len(matched),
                model_name=llm_resp.model_name,
                model_status="RAG_ONLY",
                generated_at=now_iso,
                warnings=llm_resp.warnings or [
                    "LLM synthesis unavailable. Displaying raw RAG source excerpts with full citations."
                ]
            )

        return RAGQueryResponse(
            answer=llm_resp.answer,
            provenance=f"SOURCE_BACKED_KNOWLEDGE (sha256:{self.corpus_hash})" if self.corpus_hash else "SOURCE_BACKED_KNOWLEDGE",
            citations=citations,
            retrieved_chunks=len(matched),
            model_name=f"{llm_resp.provider}:{llm_resp.model_name}",
            model_status="AVAILABLE",
            generated_at=now_iso,
            warnings=llm_resp.warnings or []
        )

# Singleton RAG instance
rag_engine = MultilingualRAGService()

# ---------------------------------------------------------------------------
# Backward-compatibility shim
# The old rag_engine.py (before rag_service.py merge) exported KnowledgeDocument
# with a different schema used by test_advisory_provenance.py.
# We provide a thin adapter so those tests keep passing without modification.
# ---------------------------------------------------------------------------
class KnowledgeDocument(BaseModel):
    """Backward-compat document model for tests that still reference the old rag_engine schema."""
    id: str
    title: str
    source: str
    source_organization: str
    url: str
    publication_date: str
    crop: str
    growth_stage: Optional[str] = None
    region: str
    topic: str
    language: str = "en"
    content: str
    verification_status: str = "VERIFIED_GOVERNMENT_EXTENSION"
    citation_id: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)

