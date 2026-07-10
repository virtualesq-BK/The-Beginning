def compute_drm(retrieved_doc_ids: list[str], relevant_doc_ids: set[str]) -> dict:
    """DRM(Document-Level Retrieval Mismatch) 및 Precision@K/Recall@K 계산.

    relevant_doc_ids: 정답(ground-truth)으로 표시된 문서 id 집합.
    베타 테스트 단계에서 사람이 라벨링한 relevant_doc_ids를 넣어 검색 품질을 측정한다.
    """
    if not retrieved_doc_ids:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "drm": 1.0}

    hit_count = sum(1 for doc_id in retrieved_doc_ids if doc_id in relevant_doc_ids)
    precision_at_k = hit_count / len(retrieved_doc_ids)
    recall_at_k = hit_count / len(relevant_doc_ids) if relevant_doc_ids else 0.0
    drm = 1.0 - precision_at_k  # 검색 결과 중 문서 수준에서 무관한 항목의 비율
    return {"precision_at_k": precision_at_k, "recall_at_k": recall_at_k, "drm": drm}
