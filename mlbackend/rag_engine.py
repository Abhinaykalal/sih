"""Repository-backed agricultural knowledge retrieval.

The engine never seeds synthetic or unverified agricultural advice.  Documents must
be supplied explicitly by the application or loaded from a reviewed corpus.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
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
    verification_status: str = "UNVERIFIED"
    citation_id: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)


class RAGCitation(BaseModel):
    title: str
    organization: str
    url: str
    excerpt: str
    verification_status: str = "UNVERIFIED"
    citation_id: Optional[str] = None


class RAGSearchResult(BaseModel):
    query: str
    retrieval_mode: str
    matched_documents_count: int
    citations: List[RAGCitation]
    assembled_context: str


class RAGSearchEngine:
    """Small keyword retriever over explicitly loaded knowledge documents."""

    def __init__(self) -> None:
        self._documents: List[KnowledgeDocument] = []

    def add_document(self, doc: KnowledgeDocument) -> None:
        self._documents.append(doc)

    def search(
        self,
        query: str,
        crop: Optional[str] = None,
        region: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 3,
    ) -> List[KnowledgeDocument]:
        query_words = {word for word in query.lower().split() if len(word) > 3}
        ranked = []

        for doc in self._documents:
            score = 0
            if crop and crop.lower() in doc.crop.lower():
                score += 3
            if topic and topic.lower() in doc.topic.lower():
                score += 4
            if region and any(word in doc.region.lower() for word in region.lower().split()):
                score += 2

            searchable = f"{doc.title} {doc.content} {doc.topic} {doc.crop}".lower()
            score += sum(1 for word in query_words if word in searchable)
            if score > 0:
                ranked.append((score, doc))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in ranked[:limit]]

    def search_with_citations(
        self,
        query: str,
        crop: Optional[str] = None,
        region: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 3,
    ) -> RAGSearchResult:
        docs = self.search(query, crop=crop, region=region, topic=topic, limit=limit)
        citations = [
            RAGCitation(
                title=doc.title,
                organization=doc.source_organization,
                url=doc.url,
                excerpt=doc.content[:180] + ("..." if len(doc.content) > 180 else ""),
                verification_status=doc.verification_status,
                citation_id=doc.citation_id,
            )
            for doc in docs
        ]
        return RAGSearchResult(
            query=query,
            retrieval_mode="KEYWORD_FILTER" if docs else "UNAVAILABLE",
            matched_documents_count=len(docs),
            citations=citations,
            assembled_context="\n\n".join(f"[{doc.source}] {doc.content}" for doc in docs),
        )


# Empty by design until a reviewed corpus is explicitly loaded.
rag_engine = RAGSearchEngine()
