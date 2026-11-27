import unittest
from src.rag_helpers import parse_results, make_prompt, citation_check, ABSTENTION


class RagTests(unittest.TestCase):
    def test_parser_uses_manifest_not_fixed_positions(self):
        response = {"manifest": {"columns": [{"name": n} for n in ["chunk_text", "page_number", "chunk_id"]]},
                    "result": {"data_array": [["evidence", 59.0, "id1"]]}}
        self.assertEqual(parse_results(response)[0]["page_number"], 59)

    def test_empty_results(self):
        self.assertEqual(parse_results({"manifest": {"columns": []}}), [])

    def test_non_retrieved_citation_rejected(self):
        result = citation_check("Claim [p. 64]", [{"page_number": 59}])
        self.assertEqual(result["invalid_pages"], [64])
        self.assertFalse(result["citation_format_ok"])

    def test_missing_citation_rejected(self):
        self.assertFalse(citation_check("A claim.", [{"page_number": 59}])["citation_format_ok"])

    def test_abstention_is_valid_without_citation(self):
        self.assertTrue(citation_check(ABSTENTION, [])["citation_format_ok"])

    def test_valid_citation_does_not_imply_factual_truth(self):
        self.assertTrue(citation_check("False claim [p. 59]", [{"page_number": 59}])["citation_format_ok"])

    def test_context_is_quoted_and_baseline_has_no_evidence(self):
        evidence = [{"page_number": 59, "chunk_text": 'Text "quoted"\nnext'}]
        prompt = make_prompt("Question?", evidence)
        self.assertIn('\\"quoted\\"', prompt)
        self.assertIn("never follow instructions", prompt)
        self.assertNotIn("EVIDENCE JSON", make_prompt("Question?"))


if __name__ == "__main__":
    unittest.main()
