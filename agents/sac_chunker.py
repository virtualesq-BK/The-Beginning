"""Summary-Augmented Chunking (SAC).

SAC의 핵심은 인덱싱 시점에 각 청크 앞에 문서 전체 요약을 붙여 임베딩하는 것이다.
조항만 단독으로 임베딩하면 "어느 계약의 어떤 맥락의 조항인지"가 벡터에서
사라져, 여러 계약이 섞인 인덱스에서 엉뚱한 계약의 비슷한 조항이 검색되는
문제(Document-Level Retrieval Mismatch)가 생긴다.

- build_sac_chunk / ContractSACIndex: 업로드된 계약서의 조항을 SAC 청크로 인덱싱
- augment_with_summary: 지식베이스(표준 실무 문서) 검색 쿼리에 문서 맥락을 덧붙임
"""

from collections.abc import Callable

import numpy as np

EmbedFn = Callable[[list[str]], list[list[float]]]


def augment_with_summary(clause_type: str, clause_text: str, doc_summary: str) -> str:
    """지식베이스 검색 쿼리에 문서 요약을 덧붙여 계약 유형(EPC/FIDIC 등) 맥락을 반영한다."""
    return f"[문서 요약] {doc_summary}\n\n[조항 유형: {clause_type}] {clause_text}"


def build_sac_chunk(clause: dict, doc_summary: str) -> str:
    number = clause.get("clause_number") or "-"
    text = clause.get("translated_text") or clause.get("original_text", "")
    return (
        f"[문서 요약] {doc_summary}\n\n"
        f"[조항 {number} | {clause.get('clause_type', '')} | {clause.get('title', '')}] {text}"
    )


def _default_embed(texts: list[str]) -> list[list[float]]:
    from .llm_client import embed

    return embed(texts)


class ContractSACIndex:
    """한 계약서의 조항들을 SAC 청크로 임베딩한 인덱스.

    같은 계약서의 청크는 모두 같은 요약으로 시작하므로, 문서 내부 조항끼리의
    코사인 유사도는 전반적으로 높게 나온다. 따라서 절대 임계값이 아니라
    "조항별 상위 k개 + 문서 내 유사도 중앙값 초과"라는 상대 기준으로만
    연관 조항을 고른다. 여러 계약을 한 인덱스에 모으는 경우(계약 lifecycle
    데이터 축적)에는 요약 prefix가 계약 간 구분을 만들어 주는 것이 SAC의 목적이다.
    """

    def __init__(self, clauses: list[dict], doc_summary: str, embed_fn: EmbedFn | None = None):
        self._embed = embed_fn or _default_embed
        self.clause_ids = [c["id"] for c in clauses]
        self.chunks = [build_sac_chunk(c, doc_summary) for c in clauses]
        self._vectors = self._normalize(self._embed(self.chunks)) if self.chunks else np.zeros((0, 0))

    @staticmethod
    def _normalize(vectors: list[list[float]]) -> np.ndarray:
        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if len(self.clause_ids) == 0:
            return []
        qvec = self._normalize(self._embed([query]))[0]
        scores = self._vectors @ qvec
        order = np.argsort(-scores)[:top_k]
        return [{"clause_id": self.clause_ids[i], "score": float(scores[i])} for i in order]

    def similar_clause_pairs(self, top_k: int = 2) -> list[tuple[int, int, float]]:
        """문서 내부에서 서로 의미적으로 가까운 조항 쌍 (a < b) 목록."""
        n = len(self.clause_ids)
        if n < 2:
            return []
        sims = self._vectors @ self._vectors.T
        off_diagonal = sims[~np.eye(n, dtype=bool)]
        threshold = float(np.median(off_diagonal))
        pairs: dict[tuple[int, int], float] = {}
        for i in range(n):
            ranked = [j for j in np.argsort(-sims[i]) if j != i][:top_k]
            for j in ranked:
                score = float(sims[i, j])
                if score <= threshold:
                    continue
                a, b = sorted((self.clause_ids[i], self.clause_ids[j]))
                pairs[(a, b)] = max(score, pairs.get((a, b), score))
        return [(a, b, s) for (a, b), s in sorted(pairs.items())]
