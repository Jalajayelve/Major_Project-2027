"""Regression tests for the retained optional experimental base-rate model source.

No retraining, network calls or notebook demo execution are needed for these tests.
"""
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[2]


class Agent2BaseRateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT/'notebooks/agent2_base_rate_extension.py').read_text(encoding='utf-8')
        code = source.split('# %% Monotone admission model with a fixed logit offset\n',1)[1].split('# %% Applicant-grouped CV',1)[0]
        namespace = {'np':np,'pd':pd,'minimize':minimize,'expit':expit,'logit':logit}
        exec(compile(code,'agent2-embedded-model','exec'),namespace)
        cls.model = namespace['OffsetAdmissionModel'].from_dict(
            json.loads((ROOT/'data/processed/agent2/offset_admission_model.json').read_text()))
        cls.base = {**cls.model.medians,'tier_score':70.,'program_admit_rate':.25}

    def test_same_applicant_tier88_has_lower_probability_than_tier60(self):
        rows=pd.DataFrame([{**self.base,'tier_score':60.},{**self.base,'tier_score':88.}])
        tier60,tier88=self.model.predict_proba(rows)[:,1]
        self.assertLess(tier88,tier60)

    def test_monotonicity_across_varied_applicants_and_priors(self):
        rng=np.random.default_rng(2026)
        rows=pd.DataFrame({
            'gpa':rng.uniform(1,3.9,200),'gre_quant':rng.uniform(130,169,200),
            'gre_verbal':rng.uniform(130,169,200),'profile_strength_score':rng.uniform(0,99,200),
            'tier_score':rng.uniform(20,89,200),'program_admit_rate':rng.uniform(.01,.95,200)})
        before=self.model.predict_proba(rows)[:,1]
        for feature,increment in [('gpa',.1),('gre_quant',1),('gre_verbal',1),('profile_strength_score',1)]:
            with self.subTest(feature=feature):
                stronger=rows.copy();stronger[feature]+=increment
                self.assertTrue(np.all(self.model.predict_proba(stronger)[:,1]>=before-1e-12))
        selective=rows.copy();selective.tier_score+=10
        self.assertTrue(np.all(self.model.predict_proba(selective)[:,1]<before))

    def test_group_cv_has_no_applicant_overlap(self):
        oof=pd.read_csv(ROOT/'data/processed/agent2/oof_predictions.csv')
        self.assertEqual(oof.fold.nunique(),5)
        self.assertTrue((oof.groupby('applicant_id').fold.nunique()==1).all())
        self.assertTrue(oof.with_profile_strength.between(0,1).all())


if __name__=='__main__':
    unittest.main()
