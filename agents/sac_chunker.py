def augment_with_summary(clause_type: str, clause_text: str, doc_summary: str) -> str:
    """Summary-Augmented Chunking (SAC): 조항 검색 쿼리에 문서 전체 요약을 덧붙여
    임베딩 시 문서 수준 맥락(Document-Level Context)이 함께 반영되도록 한다.
    이를 통해 조항만 단독으로 임베딩할 때 발생하는 문맥 손실(Document-Level
    Retrieval Mismatch)을 줄인다."""
    return f"[문서 요약] {doc_summary}\n\n[조항 유형: {clause_type}] {clause_text}"
