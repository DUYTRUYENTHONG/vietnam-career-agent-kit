import copy
import json
from pathlib import Path
import tempfile
import unittest

from core.evidence_pairing import checked, lexical_answer, messages, packet_from_workspace, preview, strict_json
from core.workflow import Preparation, WorkflowError
from scripts.evidence_bench import FIXTURE, load_cases, metrics
from test_contracts import job, profile


class EvidenceTests(unittest.TestCase):
    def test_checkpoint_binding_tracks_bytes_and_does_not_claim_origin(self):
        from adapters.qwen35_pairing import checkpoint_binding
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                checkpoint_binding(root)
            weight = root / 'model.safetensors'
            weight.write_bytes(b'fictional-weights-v1')
            first = checkpoint_binding(root)
            self.assertFalse(first['upstream_origin_verified'])
            weight.write_bytes(b'fictional-weights-v2')
            self.assertNotEqual(first['files'], checkpoint_binding(root)['files'])

    def test_workspace_packet_requires_current_confirmation_and_preserves_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            work = Preparation(root / "private", repo)
            work.init("vi")
            cv = root / "cv.md"
            cv.write_text("Used SQL in a fictional project.", encoding="utf-8")
            work.import_cv(cv, "CV1")
            jd = work.import_job(job()).data["job"]["id"]
            source = profile()
            source["contacts"] = {"phone": "fictional phone"}
            pending = dict(source["facts"][0], id="P", status="pending")
            source["facts"].append(pending)
            fingerprint = work.import_profile(source).data["fingerprint"]
            with self.assertRaises(WorkflowError):
                packet_from_workspace(work, jd)
            proof = work.data_dir / "proof.txt"
            proof.write_text("CONFIRM PROFILE " + fingerprint, encoding="utf-8")
            work.confirm_profile(fingerprint, proof)
            packet = packet_from_workspace(work, jd)
            self.assertEqual([f["id"] for f in packet["facts"]], ["F1"])
            self.assertNotIn("fictional phone", str(packet))
            output = preview(packet, lexical_answer)
            self.assertTrue(output["review_required"])
            self.assertEqual(output["source_binding"]["profile_hash"], fingerprint)
            self.assertEqual(output["cv_suggestions"][0], {"fact_id": "F1", "quote": cv.read_text(),
                             "source_id": "CV1", "locator": "line 3"})
            (work.data_dir / work.inspect_profile().data["sources"][0]["path"]).write_text("changed")
            with self.assertRaises(WorkflowError):
                packet_from_workspace(work, jd)

    def test_citations_and_valid_json(self):
        for pred in ({"label": "unknown", "fact_ids": ["F"]}, {"label": "direct", "fact_ids": []},
                     {"label": "partial", "fact_ids": ["X"]}, {"label": "direct", "fact_ids": ["F","F"]}):
            with self.assertRaises(ValueError):
                checked(pred, {"F": {}})
        with self.assertRaises(ValueError):
            strict_json('{"label":"partial","label":"direct"}')

    def test_conflict_omitted_from_cv_and_grounded_citations_only(self):
        case = load_cases(FIXTURE)[-1]
        result = preview(case["packet"], lambda r, f: case["gold"][r["id"]])
        self.assertEqual(result["job_requirement_coverage"], "review_explicit_conflict")
        self.assertEqual([s["fact_id"] for s in result["cv_suggestions"]], ["F1", "F2"])
        packed = messages(case["packet"]["requirements"][0], {"F": {"text": "one quote", "secret": "x"}})
        self.assertEqual(set(json.loads(packed[-1]["content"])), {"requirement", "facts"})
        self.assertNotIn("secret", str(packed))

    def test_choice_menu_permutation_and_unscored_preview(self):
        from adapters.qwen35_pairing import choice_menu
        case = load_cases(FIXTURE)[-1]
        req = case["packet"]["requirements"][0]
        facts = {f["id"]: f for f in case["packet"]["facts"]}
        menu = choice_menu(req, facts)
        self.assertEqual(len(menu), 19)
        self.assertEqual(menu, choice_menu(req, dict(reversed(list(facts.items())))))
        self.assertTrue(any(len(x["fact_ids"]) == 2 for x in menu.values()))
        with self.assertRaises(ValueError):
            choice_menu(req, {str(i): {} for i in range(5)})
        item = preview(case["packet"], lambda r, f: {"label": "direct"})
        self.assertEqual(item["job_requirement_coverage"], "manual_review_invalid_output")
        self.assertTrue(all(r["status"] == "unscored" for r in item["rows"]))
        self.assertEqual(item["cv_suggestions"], [])

    def test_cross_split_bridge_and_exact_duplicates_rejected(self):
        original = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            for kind in ("group", "text"):
                data = copy.deepcopy(original)
                a, b, c = data["cases"][0], data["cases"][1], data["cases"][-1]
                if kind == "group":
                    b["groups"].append(a["groups"][0])
                    c["groups"].append(b["groups"][0])
                else:
                    c["packet"]["facts"][0]["text"] = a["packet"]["facts"][0]["text"].upper()
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "across splits"):
                    load_cases(path)

    def test_invalid_outputs_count_in_f1_and_wrong_entailment_counts_as_false_support(self):
        pos = {"label": "direct", "fact_ids": ["F"]}
        neg = {"label": "contradicted", "fact_ids": ["F"]}
        result = metrics([{"gold": pos, "prediction": None}, {"gold": neg, "prediction": pos}])
        self.assertEqual((result["n"], result["invalid"], result["false_support_count"]), (2, 1, 1))
        self.assertEqual(result["label_macro_f1"], 0)
        self.assertAlmostEqual(result["citation_micro_f1"], 2/3)
