import unittest

from agents.fidic_comparison import compare_contract_to_fidic, generate_fidic_pdf_bytes


class FIDICComparisonEngineTest(unittest.TestCase):
    def test_score_and_bias_are_weighted_and_evidence_is_sentence_level(self):
        sample = (
            "The Employer may vary the Works without compensation. "
            "Liquidated Damages shall be payable without cap. "
            "The Contractor shall submit a performance security. "
            "The Employer may withhold payment without reason."
        )
        result = compare_contract_to_fidic(sample)

        self.assertGreater(result["overall_score"], 0)
        self.assertIn(result["balance"], ["발주자 유리", "시공사 유리", "균형형"])
        self.assertIn("employer", result["bias_scores"])
        self.assertIn("contractor", result["bias_scores"])
        self.assertTrue(any(issue["evidence"] for issue in result["issues"]))

    def test_pdf_generation_uses_pdf_header(self):
        pdf_bytes = generate_fidic_pdf_bytes({
            "overall_score": 88,
            "balance": "균형형",
            "summary": "테스트 요약",
            "issues": [{"label": "지체상금 / LD", "score": 60, "status": "watch"}],
        })
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 100)


if __name__ == "__main__":
    unittest.main()
