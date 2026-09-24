import hashlib
import unittest
from unittest.mock import patch

import numpy as np

from agents import risk_ontology
from agents.clause_graph import build_clause_graph, evaluate_cross_clause_risks_graph
from agents.document_parser import CLAUSE_TYPES, extract_cross_references, normalize_clauses
from agents.sac_chunker import ContractSACIndex, build_sac_chunk


def _fake_embed(texts):
    """토큰 해시 기반 bag-of-words 임베딩: 같은 단어를 공유할수록 유사도가 높다."""
    vectors = []
    for text in texts:
        vec = np.zeros(64, dtype=np.float32)
        for token in text.lower().split():
            vec[int(hashlib.md5(token.encode()).hexdigest(), 16) % 64] += 1.0
        vectors.append(vec.tolist())
    return vectors


def _clause(cid, number, clause_type, text, refs=None, parent=""):
    return {
        "id": cid,
        "clause_number": number,
        "parent_number": parent,
        "clause_type": clause_type,
        "title": f"Clause {number}",
        "original_text": text,
        "translated_text": text,
        "cross_references": refs or [],
    }


class CrossReferenceExtractionTest(unittest.TestCase):
    def test_english_and_korean_references(self):
        text = "Subject to Sub-Clause 20.1 and Clause 8, and as provided in 제17조 제2항."
        self.assertEqual(extract_cross_references(text), ["20.1", "8", "17.2"])

    def test_normalize_drops_self_reference_and_derives_parent(self):
        clauses = normalize_clauses(
            [{"clause_type": "지체상금", "title": "8.7 Delay Damages",
              "original_text": "Sub-Clause 8.7 Delay Damages. Subject to Sub-Clause 20.1, the Contractor shall pay...",
              "cross_references": ["20.1"]}]
        )
        c = clauses[0]
        self.assertEqual(c["id"], 1)
        self.assertEqual(c["clause_number"], "8.7")
        self.assertEqual(c["parent_number"], "8")
        self.assertEqual(c["cross_references"], ["20.1"])


class OntologyCoverageTest(unittest.TestCase):
    def test_every_parser_type_except_other_reaches_rules(self):
        unmapped = [t for t in CLAUSE_TYPES if t != "기타" and not risk_ontology.get_nodes_for_clause_type(t)]
        self.assertEqual(unmapped, [])

    def test_every_combo_rule_is_reachable_from_parser_types(self):
        reachable = {n.node_id for t in CLAUSE_TYPES for n in risk_ontology.get_nodes_for_clause_type(t)}
        for combo in risk_ontology.RISK_COMBINATIONS:
            missing = [rid for rid in combo.required_node_ids if rid not in reachable]
            self.assertEqual(missing, [], combo.combo_id)

    def test_keyword_trigger_offers_delay_rules_for_misclassified_notice_clause(self):
        text = "The Contractor shall give notice of claim within 7 days, failing which the claim is time-barred."
        ids = {n.node_id for n in risk_ontology.get_nodes_by_keywords(text)}
        self.assertIn("FIDIC-DELAY-NOTICE", ids)
        self.assertIn("FIDIC-DELAY-TIMEBAR", ids)


class SACIndexTest(unittest.TestCase):
    def test_chunk_prepends_document_summary(self):
        chunk = build_sac_chunk(_clause(1, "8.7", "지체상금", "LD text"), "EPC contract summary")
        self.assertTrue(chunk.startswith("[문서 요약] EPC contract summary"))
        self.assertIn("[조항 8.7 | 지체상금", chunk)

    def test_similar_pairs_link_related_clauses(self):
        clauses = [
            _clause(1, "8.7", "지체상금", "delay damages liquidated damages cap percent contract price"),
            _clause(2, "1.14", "손해배상", "total liability cap excludes delay damages liquidated damages"),
            _clause(3, "21", "중재", "arbitration seat singapore icc rules english language"),
        ]
        index = ContractSACIndex(clauses, "EPC summary", embed_fn=_fake_embed)
        pairs = {(a, b) for a, b, _ in index.similar_clause_pairs(top_k=1)}
        self.assertIn((1, 2), pairs)
        self.assertNotIn((1, 3), pairs)
        self.assertEqual(index.search("liquidated damages", top_k=1)[0]["clause_id"], 1)


class ClauseGraphTest(unittest.TestCase):
    def setUp(self):
        self.clauses = [
            _clause(1, "8", "지체상금", "Commencement, delays and suspension."),
            _clause(2, "8.5", "지체상금", "Extension of time, subject to Sub-Clause 20.1.", refs=["20.1"], parent="8"),
            _clause(3, "8.7", "지체상금", "Delay damages up to 10%.", parent="8"),
            _clause(4, "20.1", "분쟁해결", "Notice of claim within 7 days or time-barred."),
            _clause(5, "15.2", "계약해지", "Termination by Employer."),
            _clause(6, "17.3", "면책", "Indemnities."),
        ]

    def test_hierarchy_and_cross_reference_edges(self):
        graph = build_clause_graph(self.clauses)
        explicit = {(e.source, e.target, e.kind) for e in graph.edges if e.kind != "type_dependency"}
        self.assertIn((1, 2, "hierarchy"), explicit)
        self.assertIn((1, 3, "hierarchy"), explicit)
        self.assertIn((2, 4, "cross_reference"), explicit)

    def test_reference_resolves_to_nearest_ancestor(self):
        clauses = [_clause(1, "20", "분쟁해결", "Claims."), _clause(2, "8.5", "지체상금", "see Sub-Clause 20.1.4", refs=["20.1.4"])]
        graph = build_clause_graph(clauses)
        self.assertIn(1, graph.neighbors(2, {"cross_reference"}))

    def test_combo_confidence_levels(self):
        graph = build_clause_graph(self.clauses)
        rules = {2: {"FIDIC-DELAY-EOT"}, 3: {"FIDIC-DELAY-LD"}, 4: {"FIDIC-DELAY-NOTICE"},
                 5: {"FIDIC-TERMINATION"}, 6: {"FIDIC-INDEMNITY"}}
        by_id = {m["combo_id"]: m for m in evaluate_cross_clause_risks_graph(rules, graph)}

        eot_combo = by_id["COMBO-EOT-NOTICE-LD-CAP-TERMINATION"]
        self.assertEqual(eot_combo["confidence"], "explicit")  # 8.5 -> 20.1 참조 + 8 하위조항
        self.assertEqual(eot_combo["clause_ids"], [2, 3, 4])
        self.assertFalse(eot_combo["requires_expert_review"])

        ld_combo = by_id["COMBO-LD-INDEMNITY-TERMINATION"]
        self.assertEqual(ld_combo["confidence"], "co_occurrence")  # 15.2, 17.3은 참조 연결 없음
        self.assertTrue(ld_combo["requires_expert_review"])

    def test_semantic_edge_upgrades_confidence(self):
        graph = build_clause_graph(self.clauses, similar_pairs=[(3, 5, 0.9), (5, 6, 0.8)])
        rules = {3: {"FIDIC-DELAY-LD"}, 5: {"FIDIC-TERMINATION"}, 6: {"FIDIC-INDEMNITY"}}
        by_id = {m["combo_id"]: m for m in evaluate_cross_clause_risks_graph(rules, graph)}
        self.assertEqual(by_id["COMBO-LD-INDEMNITY-TERMINATION"]["confidence"], "semantic")

    def test_rules_in_single_clause_are_explicit(self):
        graph = build_clause_graph(self.clauses)
        rules = {3: {"FIDIC-DELAY-LD", "FIDIC-LIABILITY-CAP"}}
        by_id = {m["combo_id"]: m for m in evaluate_cross_clause_risks_graph(rules, graph)}
        self.assertEqual(by_id["COMBO-LD-CAP-CARVEOUT"]["confidence"], "explicit")


class PipelineGraphWiringTest(unittest.TestCase):
    def test_pipeline_passes_linked_clauses_and_survives_sac_failure(self):
        import pipeline

        parsed = {"clauses": [
            _clause(1, "8.5", "지체상금", "Extension of time subject to Sub-Clause 20.1.", refs=["20.1"]),
            _clause(2, "20.1", "분쟁해결", "Notice of claim within 7 days."),
        ]}
        seen = {}

        def fake_analyze(clause_type, text, summary, language="ko", related_clauses=None, related_clause_types=None):
            seen[text] = ([c["id"] for c in related_clauses or []], related_clause_types)
            rules = ["FIDIC-DELAY-EOT", "FIDIC-DELAY-LD"] if "Extension" in text else ["FIDIC-DELAY-NOTICE"]
            return {"risk_score": 4, "rules_applied": rules}

        class FailingIndex:
            def __init__(self, *args, **kwargs):
                raise PermissionError("embeddings blocked")

        with patch.object(pipeline, "parse_contract", return_value=parsed), \
             patch.object(pipeline, "translate_clause", side_effect=lambda t, language="ko": {"translated_text": t, "confidence": 1.0, "notes": ""}), \
             patch.object(pipeline, "summarize_document", return_value="summary"), \
             patch.object(pipeline, "ContractSACIndex", FailingIndex), \
             patch.object(pipeline, "analyze_clause", side_effect=fake_analyze):
            report = pipeline.run_pipeline("raw")

        self.assertEqual(seen["Extension of time subject to Sub-Clause 20.1."], ([2], ["분쟁해결"]))
        self.assertTrue(report["clause_graph"]["sac_status"].startswith("unavailable"))
        combo = next(m for m in report["cross_clause_risks"] if m["combo_id"] == "COMBO-EOT-NOTICE-LD-CAP-TERMINATION")
        self.assertEqual(combo["confidence"], "explicit")


if __name__ == "__main__":
    unittest.main()
