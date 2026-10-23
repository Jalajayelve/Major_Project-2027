"""Run deterministic Agent 7 checks in an independent Python process."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'backend/app/agents'))
from extracurricular_agent.predict import ArtifactError, agent7_full_pipeline, agent7_output_to_state, score_extracurricular
from extracurricular_agent.sop import combine_scores, score_sop


def verify(directory: Path):
    examples = json.loads((Path(__file__).parent / "example_applicants.json").read_text(encoding="utf-8"))
    outputs = [score_extracurricular(c, model_dir=directory) for c in examples]
    results = {}

    class Checks(unittest.TestCase):
        def test_required_output_fields_and_ranges(self):
            self.assertEqual(len(outputs), 5)
            for c, out in zip(examples, outputs):
                self.assertEqual(set(out), {"strength_tier","profile_strength_score","P(Strong)","achievement_archetype","has_research_evidence"})
                self.assertIn(out["strength_tier"], ["Weak","Moderate","Strong"])
                self.assertTrue(0 <= out["profile_strength_score"] <= 100)
                self.assertTrue(0 <= out["P(Strong)"] <= 1)
                self.assertTrue(out["achievement_archetype"].isdigit())
                self.assertEqual(out["has_research_evidence"],int(c["publication_count"]>0 or c["patent_count"]>0))

        def test_determinism(self):
            self.assertEqual(outputs,[score_extracurricular(c,model_dir=directory) for c in examples])

        def test_invalid_input_does_not_silently_fill_or_clip(self):
            for update in [{"leadership_score":11},{"publication_count":-1},{"patent_count":.5},{"research_score":float("nan")},{"field":"Unknown"},{"volunteering_score":True}]:
                with self.subTest(update=update), self.assertRaises(ValueError):
                    score_extracurricular({**examples[0],**update},model_dir=directory)
            with self.assertRaises(ValueError): score_extracurricular({},model_dir=directory)
            with self.assertRaises(ValueError): score_extracurricular({**examples[0],"profile_strength_score":90},model_dir=directory)

        def test_fresh_process_from_unrelated_working_directory(self):
            with tempfile.TemporaryDirectory(prefix="agent7_restart_") as tmp:
                env = dict(os.environ, PYTHONPATH=str(ROOT / 'backend/app/agents'), PYTHONDONTWRITEBYTECODE="1")
                p=subprocess.run([sys.executable,"-B","-m","extracurricular_agent.predict","--input-json",str(Path(__file__).parent/"example_applicants.json"),"--model-dir",str(directory)],cwd=tmp,env=env,text=True,capture_output=True,check=True)
                self.assertEqual(json.loads(p.stdout),outputs)
                results["fresh_restart_foreign_cwd"] = True

        def test_missing_and_corrupt_bundle_errors(self):
            with tempfile.TemporaryDirectory(prefix="agent7_missing_") as tmp:
                with self.assertRaises(ArtifactError): score_extracurricular(examples[0],model_dir=tmp)
            with tempfile.TemporaryDirectory(prefix="agent7_corrupt_") as tmp:
                shutil.copytree(directory,Path(tmp)/"copy")
                (Path(tmp)/"copy"/"agent7_xgb_tier_model.joblib").write_bytes(b"not a model")
                with self.assertRaisesRegex(ArtifactError,"hash mismatch"):
                    score_extracurricular(examples[0],model_dir=Path(tmp)/"copy")

        def test_wrong_artifact_type_is_rejected(self):
            with tempfile.TemporaryDirectory(prefix="agent7_type_") as tmp:
                copied=Path(tmp)/"copy";shutil.copytree(directory,copied)
                target=copied/"agent7_xgb_tier_model.joblib"
                target.write_bytes((copied/"agent7_archetype_scaler.joblib").read_bytes())
                manifest=json.loads((copied/"manifest.json").read_text(encoding="utf-8"))
                manifest["artifact_sha256"][target.name]=hashlib.sha256(target.read_bytes()).hexdigest()
                (copied/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
                with self.assertRaisesRegex(ArtifactError,"expected XGBClassifier"):
                    score_extracurricular(examples[0],model_dir=copied)

        def test_sop_offline_and_blending_keep_model_output(self):
            text="I am inspired by research. I built a project and plan to study Example University MS in Computing to achieve my goal."
            sop=score_sop(text,"Example University","MS in Computing","Computing research and projects")
            self.assertIsNone(sop["semantic_alignment_score"])
            self.assertEqual(sop["llm_rubric"]["status"],"not_requested")
            self.assertTrue(0<=sop["sop_score"]<=100)
            combined=combine_scores(outputs[2],sop)
            self.assertEqual(combined["profile_strength_score"],outputs[2]["profile_strength_score"])
            self.assertEqual(combined["P(Strong)"],outputs[2]["P(Strong)"])
            self.assertIn("blended_profile_strength_score",combined)
            self.assertEqual(score_sop("","Example University","MS in Computing","Computing")["sop_score"],0)
            with self.assertRaises(ValueError): combine_scores(outputs[0],sop,float("nan"))
            with self.assertRaises(ValueError): score_sop("hello","","program","description")
            results["sop_offline_example"]={"input":text,"output":sop,"combined_output":combined}

        def test_optional_sop_providers_and_unavailable_resume(self):
            class Embed:
                def encode(self,text): return [1.,0.]
            class GoodLLM:
                def invoke(self,prompt): return '{"clarity":8,"specificity":7,"program_alignment":9,"authenticity_flags":[]}'
            class BadLLM:
                def invoke(self,prompt): return '{"clarity":99}'
            sop=score_sop("research goals","University","Program","research",embed_model=Embed(),groq_llm=GoodLLM())
            self.assertEqual(sop["semantic_alignment_score"],1)
            self.assertEqual(sop["llm_rubric"]["status"],"provider_evaluated")
            with self.assertRaises(ValueError): score_sop("research","University","Program","research",groq_llm=BadLLM())
            with self.assertRaises(ArtifactError): agent7_full_pipeline("sample","resume")
            out=agent7_output_to_state(examples[0],model_dir=directory)
            self.assertEqual(out["P(Strong)"],outputs[0]["P(Strong)"])
            with self.assertRaises(ValueError): agent7_output_to_state(examples[0],sop_text="draft",model_dir=directory)

    stream=io.StringIO()
    run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    results.update(inputs=examples,outputs=outputs,tests_run=run.testsRun,passed=run.wasSuccessful(),log=stream.getvalue(),process_id=os.getpid(),python=sys.executable)
    return results


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--model-dir",type=Path,required=True)
    parser.add_argument("--output-json",type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.model_dir.resolve())
    with args.output_json.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2)
    print(result["log"],flush=True)
    sys.exit(0 if result["passed"] else 1)
