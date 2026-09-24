import unittest

from fastapi.testclient import TestClient

from agents.regulatory_ontology import build_default_graph
from agents.regulatory_analyzer import run_regulatory_pipeline
from server import app


class RegulatoryOntologyTest(unittest.TestCase):
    def test_requirements_are_ordered_by_dependency(self):
        g = build_default_graph()
        reqs = g.requirements("KR", "chemical")
        self.assertEqual(reqs[0]["permit"], "화학물질 등록 (K-REACH)")
        self.assertEqual(reqs[1]["permit"], "환경영향평가")

    def test_prerequisites_and_impact_are_inverse(self):
        g = build_default_graph()
        self.assertEqual(g.prerequisites("KR:chemical:1"), ["KR:chemical:0"])
        self.assertEqual(g.impacted_by("KR:chemical:0"), ["KR:chemical:1"])

    def test_unsupported_sector_returns_empty(self):
        g = build_default_graph()
        self.assertEqual(g.requirements("FR", "aerospace"), [])


class RegulatoryPipelineTest(unittest.TestCase):
    def test_gap_analysis_flags_missing_and_short_documents(self):
        g = build_default_graph()
        result = run_regulatory_pipeline(
            "Plant X", "KR", "chemical", {"등록 신청서": "짧음"}, g,
        )
        statuses = {(gap["document"], gap["status"]) for gap in result["gaps"]}
        self.assertIn(("등록 신청서", "insufficient"), statuses)
        self.assertIn(("물질 안전성 정보", "missing"), statuses)
        self.assertIn("법률 자문이 아닙니다", result["disclaimer"])

    def test_drafts_cover_every_requirement(self):
        g = build_default_graph()
        result = run_regulatory_pipeline("Plant X", "KR", "chemical", {}, g)
        self.assertEqual(set(result["drafts"]), {r["permit"] for r in result["requirements"]})


class RegulatoryEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_analyze_endpoint(self):
        r = self.client.post("/api/v1/regulatory/analyze", json={
            "project_name": "Plant X", "country": "KR", "sector": "chemical",
            "submitted": {"등록 신청서": "짧음"},
        })
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(len(body["requirements"]) >= 2)
        self.assertTrue(any(gap["status"] == "missing" for gap in body["gaps"]))

    def test_analyze_endpoint_rejects_unsupported_sector(self):
        r = self.client.post("/api/v1/regulatory/analyze", json={
            "project_name": "X", "country": "FR", "sector": "aerospace",
        })
        self.assertEqual(r.status_code, 400)

    def test_requirements_endpoint_returns_ordered_permits(self):
        r = self.client.get("/api/v1/regulatory/requirements", params={"country": "KR", "sector": "chemical"})
        self.assertEqual(r.status_code, 200)
        permits = [item["permit"] for item in r.json()["items"]]
        self.assertEqual(permits, ["화학물질 등록 (K-REACH)", "환경영향평가"])

    def test_requirements_endpoint_rejects_unsupported_sector(self):
        r = self.client.get("/api/v1/regulatory/requirements", params={"country": "FR", "sector": "aerospace"})
        self.assertEqual(r.status_code, 400)

    def test_sectors_endpoint_lists_seeded_pairs(self):
        r = self.client.get("/api/v1/regulatory/sectors")
        self.assertEqual(r.status_code, 200)
        pairs = {(i["country"], i["sector"]) for i in r.json()["items"]}
        self.assertIn(("KR", "chemical"), pairs)


if __name__ == "__main__":
    unittest.main()
