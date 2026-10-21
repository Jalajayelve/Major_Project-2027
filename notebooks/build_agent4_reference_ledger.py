"""Manually transcribed official-source facts, reviewed 2026-10-21.

This creates evaluation references only. No values are used as estimator inputs.
Amounts are USD; blanks mean unresolved, never zero. Each scenario is explicit.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
crosswalk = pd.read_csv(ROOT / 'data/raw/agent4/agent2_ipeds_crosswalk.csv')
rows = []

def add(i, url, year='', months=None, tuition=None, fees=None, living=None, total=None,
        scenario='', notes='', extra_url='', total_basis='published_total', other=None):
    institution = crosswalk.iloc[i-1]
    rows.append({'unitid': int(institution.unitid), 'university_name': institution.university_name,
        'reference_program_level': "Graduate / Master's", 'reference_scenario': scenario,
        'academic_year_reference': year, 'reference_months': months, 'currency_reference': 'USD',
        'published_tuition_usd': tuition, 'published_fees_usd': fees,
        'published_housing_food_usd': living, 'published_other_usd': other,
        'published_total_usd': total, 'total_basis': total_basis if total is not None else 'unresolved',
        'source_url': url, 'additional_source_url': extra_url, 'checked_on': '2026-10-21',
        'reviewer': 'Codex source transcription; not two-human adjudication',
        'comparison_status': 'scope_year_unconfirmed' if total is not None else 'reference_incomplete',
        'notes': notes})

add(1,'https://sfs.mit.edu/graduate-students/cost-of-attendance/grad-cost-of-attendance/',
    '2026-27',9,66720,420,24930,109017,'Standard graduate; insurance included',other=16947)
add(2,'https://financialaid.stanford.edu/grad/budget/index.html','2025-26',9,
    tuition=67686,fees=813,living=26760,total=114801,other=19542,
    scenario='Engineering graduate; 11-18 units per quarter; three quarters',
    notes='22562 per quarter times three + published academic-year non-tuition expenses 47115, including insurance.',
    total_basis='sum_of_published_components',
    extra_url='https://studentservices.stanford.edu/my-finances/tuition-fees/tuition-rates/past-tuition-rates/2025-2026-rates/2025-2026-graduate-and')
add(3,'https://www.cmu.edu/sfs/tuition/graduate/scs.html','2026-27',None,62200,1040,23416,99574,
    'SCS masters; fall and spring; published loan allowance included',
    'Total = 62200 tuition + published 37374 non-tuition total.',total_basis='sum_of_published_components',other=12918)
add(4,'https://financialaid.berkeley.edu/how-aid-works/student-budgets-cost-of-attendance/',
    '2026-27',None,32652,None,26720,74106,'Academic graduate off campus; nonresident',
    'Published resident academic total 59004 plus explicit graduate nonresident supplement 15102. Tuition includes fees. Professional MEng differs.',
    total_basis='sum_of_published_components',other=14734)
add(5,'https://finaid.gatech.edu/costs/graduate-costs','2025-26',None,
    tuition=31210,fees=1496,living=20106,total=57502,other=4690,
    scenario='Regular graduate off-campus nonresident; 12+ credits; fall/spring',
    notes='Two terms at 15605 tuition + 748 fees each; indirect budget 24796. No assistantship reduction; international tuition differs.',
    total_basis='sum_of_published_components',
    extra_url='https://bursar.gatech.edu/student/tuition/fa25/fa25_totals.pdf')
add(6,'https://www.registrar.illinois.edu/tuition-fees/tuition-fee-rates/tf-rates-academic-year/g-tuition-rates-2526/',
    '2025-26',None,39344,5538,15730,65502,'Grainger engineering nonresident graduate; 12 credits; fall/spring',
    other=4890,extra_url='https://cost.illinois.edu/Home/Cost/N/G/Compare/12/120258/120258')
add(7,'https://finaid.umich.edu/getting-started/estimating-costs','2026-27',None,
    63604,None,22276,94852,'Rackham general graduate nonresident; fall/winter',
    'Tuition column includes fees. Engineering program-specific rates may differ.',other=8972)
add(8,'https://onestop.utexas.edu/managing-costs/cost-tuition-rates/cost-of-attendance/','2026-27',None,
    scenario='Nonresident graduate; 9 hours; fall/spring',
    notes='Published total is a range 41880-44279; tuition 17312-19340; housing/food 17052-17423. Do not choose a point estimate without program/enrollment detail.')
add(9,'https://www.washington.edu/financialaid/cost-of-attendance/','2026-27',None,
    33555,None,23199,61668,'Seattle Tier I nonresident graduate on/off campus',
    'Tuition column includes fees; fee-based professional programs differ.',other=4914)
add(10,'https://fas.ucsd.edu/cost-of-attendance/graduate-students/index.html','',None,
    scenario='Standard graduate; three quarters full-time',notes='Current numeric cost table remains Loading in accessible page; no amounts inferred.')
add(11,'https://sfs.columbia.edu/content/graduate-engineering-cost-attendance','2026-27',None,
    67728,4223,25340,109479,'Engineering MS; 12 points/semester; fall/spring; international fee included',
    'Fees include health services and first-term document fee; other includes insurance/books/personal/transit.',other=12188)
add(12,'https://finaid.cornell.edu/graduate-students','2026-27',None,
    tuition=29500,fees=701,living=25730,total=66345,other=10414,
    scenario='Ithaca endowed research MS; annual graduate budget',
    notes='Endowed research MS tuition, not professional MEng. Published mandatory fee total 701 retained; its footnote components sum to 690. Insurance not separately included in source budget.',
    total_basis='sum_of_published_components',extra_url='https://bursar.cornell.edu/students-parents/tuition-rates-and-fees')
add(13,'https://gradadm.usc.edu/overview-of-student-visas/financial-documentation-requirements/',
    '2026',None,56049,None,28044,84093,'Viterbi all masters; annual I-20 estimate',
    'Fall/summer 2026 admissions table. Tuition column includes fees; living is the entire published living aggregate. Actual enrollment charges vary.')
add(14,'https://bulletins.nyu.edu/nyu/cost-attendance/','2026-27',None,
    living=31324,scenario='Tandon masters traditional program; 9 credits/semester',
    notes='Graduate indirect total 42274. Need same-year Tandon tuition; undergraduate total excluded. 2025-26 Tandon rate 2525/credit is not combined with 2026-27 living.',
    extra_url='https://www.nyu.edu/content/dam/nyu/bursar/documents/2025-2026%20Tuition%20and%20Fees.pdf')
add(15,'https://srfs.upenn.edu/costs-budgeting/seas','2026-27',None,
    52950,5848,18966,87282,'On-campus engineering masters; 3 CU/term; fall/spring',
    'Calculated two terms at published 29399 tuition/fees + published living total 28484.',
    total_basis='sum_of_published_components',other=9518)
add(16,'https://www.purdue.edu/treasurer/finance/bursar-office/tuition/fee-rates-2026-2027/graduate-tuition-and-fees-2026-2027/',
    '2026-27',None,29918,None,16734,50522,'West Lafayette CS/engineering nonresident graduate; 8+ credits; fall/spring',
    'Tuition includes fees and 1124 differential; on-campus transport allowance. International fee is extra.',other=3870)
add(17,'https://marylandglobal.umd.edu/sites/default/files/2025-05/Tuition%20Rates.pdf',
    '2025-26',12,living=21000,total=59500,scenario='Most UMD graduate programs without assistantship',
    notes='Source publishes total and other-expense components; tuition/fee decomposition not explicit. Do not apply assistantship discount.')
add(18,'https://lafollette.wisc.edu/graduate/admissions/funding-financial/',
    '2025-26',None,25732,None,16414,None,'Public affairs masters; NOT a CS reference',
    'Published 49618 total belongs to public-affairs program; retain source but do not score CS against it.')
add(19,'https://international.northeastern.edu/ogs/new-students/i-20-ds-2019-application/estimate-of-expenses-for-i-20-requests-2026-2027/',
    '2026-27',None,31721,None,27728,59449,'Khoury MS Computer Science; Boston',
    'Tuition includes fees; living field is the source living aggregate rather than housing/food only.')
add(20,'https://global.tamu.edu/_files/_documents/isss-documents/ecoa-2026/2026-ecoa-12m-no-su.pdf','2026',12,
    14641,8356,19995,46015,'College Station engineering graduate nonresident; fall/spring tuition; no summer enrollment',
    'Living is source aggregate; insurance 3023 for 12 months. No dependents or tuition waiver.',other=3023,
    extra_url='https://global.tamu.edu/isss/student-scholar-resources/costs.html')
add(21,'https://international.vt.edu/new_students/pre-departure_steps.html','2026',None,
    36212,None,16990,67284,'Graduate Blacksburg engineering',
    'Source base 65284 plus explicit engineering supplement 2000. Tuition includes fees before supplement.',
    total_basis='sum_of_published_components',other=14082)
add(22,'https://admission.asu.edu/cost-aid/graduate','2026-27',None,
    29196,1657,21087,62315,'Metro Phoenix nonresident; 9 credits/semester; base graduate',
    'Program-specific tuition not included; international tuition differs.',other=10375)
add(23,'https://onestop.umn.edu/finances/costs/cost-attendance','2026-27',None,
    36372,None,20510,65670,'Twin Cities general graduate nonresident; 6-14 credits/term; fall/spring',
    'Tuition column includes fees.',other=8788)
add(24,'https://sfa.osu.edu/graduate-students/about-aid/financial-aid-eligibility','2026-27',None,
    45924,None,15902,67098,'Columbus general graduate nonresident off campus',
    'Calculated from 14732 tuition/fees + 31192 nonresident fees + 21174 indirect costs.',
    total_basis='sum_of_published_components',other=5272)
add(25,'https://global.psu.edu/page/financial-guarantee-requirements','2026-27',None,
    38600,None,21900,65300,'University Park graduate business/science/IST/engineering; minimum full-time load',
    'Tuition includes fees; living is published aggregate; insurance 4800. Financial-guarantee estimate.',other=4800)
add(26,'https://www.colorado.edu/bursar/costs/graduate-costs/graduate-costs-engineering',
    '2026-27',None,28272,890,18684,61026,'Boulder traditional engineering graduate nonresident; 6 credits/term; fall/spring',
    'Uses financial-aid full-time example enrollment (6 credits); replaces Arts/Sciences tuition with engineering rate. Excludes one-time new-student fee and optional international fee; books 1200, personal 1782, transport 2062, medical 8136.',
    extra_url='https://www.colorado.edu/financialaid/cost/example-aid',total_basis='sum_of_published_components',other=13180)
add(27,'https://studentservices.ncsu.edu/finances/estimated-cost-of-attendance/graduate-student-estimated-cost-of-attendance/',
    '2026-27',None,35002,None,17354,57498,'General graduate nonresident off campus; fall/spring',
    'General total does not include all program incremental tuition/COE fees; not verified CS total.',other=5142)
add(28,'https://www.sfa.ufl.edu/cost/graduate-costs/','2026-27',None,
    34780,None,18090,58470,'Graduate nonresident off campus',
    'Tuition includes fees; new-student projected budget.',other=5600)
add(29,'https://www.ofas.uci.edu/cost/graduate-costs/continuing-students.php','2025-26',None,
    36687,None,29479,None,'Continuing general graduate nonresident off campus',
    'Published component sums and resident total disagree (21585+38640 != 60755); unscored pending clarification. Nonresident supplement 15102.')
add(30,'https://financialaid.ucdavis.edu/graduate/gradstudies/cost','2026-27',None,
    31360,None,21846,69405,'General graduate nonresident',
    'Tuition includes fees and 15102 NR supplement; other includes 8820 health insurance.',other=16199)
add(31,'https://www.bu.edu/cas/admissions/ma-ms/cost-of-attendance/','2026-27',9,
    73024,1048,16250,95998,'Arts and Sciences MA/MS full-time 12-18 credits/semester',
    'Published total excludes optional SHIP 4054.',other=5676)
add(32,'https://gradschool.duke.edu/financial-support/cost-attend/','2026-27',9,
    69880,1644,18648,101780,'International masters standard Graduate School',
    'Fees exclude insurance 4290 recorded in other; some masters exceptions.',other=11608)
add(33,'https://www.northwestern.edu/evanston-graduate-financial-aid/getting-started/tuition-cost-of-attendance/tgs/masters.html',
    '2025-26',9,68919,861,22059,106011,'TGS full-time masters 3-4 units; three quarters',
    'Calculated tuition 22973*3 + health fee 287*3 + annual insurance 5919 + indirect 30312.',
    total_basis='sum_of_published_components',other=14172)
add(34,'https://engineering.jhu.edu/education/graduate-studies/affording-masters-phd/cost-of-attendance/',
    '2026-27',None,68670,500,20703,96767,'WSE full-time residential masters; no federal loan fees',
    'Calculated sum includes insurance 3292. Non-resident fee is an alternative registration status, not an out-of-state surcharge.',
    total_basis='sum_of_published_components',other=6894)
add(35,'https://oiss.rice.edu/oissportal','2026-27',None,
    tuition=67562,living=22365,total=89927,scenario='Graduate PhD/MA/MS; OISS annual estimate',
    notes='Manually read official image updated 2026-05-20. Tuition includes fees; living is aggregate. Professional engineering masters rate differs from research MS.',
    extra_url='https://oiss.rice.edu/sites/g/files/bxs3146/files/inline-images/Cost-of-Attendance2627_0.jpg')
add(36,'https://masters.cs.uchicago.edu/mpcs-admissions/tuition-fees/','2026-27',None,
    66762,scenario='9-course MS Computer Science; three courses per quarter',
    notes='Published whole-program tuition; no annual total until enrollment period and living are confirmed.')
add(37,'https://www.umass.edu/financialaid/financial-aid-services/guide-understanding-financial-aid',
    '2025-26',12,36728,None,28339,72531,'International graduate off campus; 9 credits full-time',
    'Tuition includes fees; other includes insurance 4314.',other=7464)
add(38,'https://gradstudy.rutgers.edu/apply/forms/certification-of-funds','2026 (October update)',12,
    41117,None,25920,67037,'General Graduate School New Brunswick; 24 credits/year',
    'Source general graduate rate covers New Brunswick as well as other campuses; separately listed programs excluded. Tuition includes fees, living is source aggregate.')
add(39,'https://www.buffalo.edu/financialaid/costs/costs.html','2026-27',None,
    26510,3320,18606,55472,'Standard graduate nonresident',
    'Published total includes loan allowance.',other=7036)
add(40,'https://www.stonybrook.edu/commcms/finaid/students/graduate/grad_coa.php','2025-26',None,
    26990,2912,16676,50726,'Graduate nonresident on campus',
    'Source indirect total 4148 differs from listed individual components sum 3960; published total retained, discrepancy flagged.',other=4148)
add(41,'https://financialaid.utah.edu/tuition-and-fees/cost-of-attendance-2025-2026/cost-of-attendance-graduate-general.php',
    '2025-26',None,34956,None,24000,72356,'Engineering graduate nonresident off campus; two semesters',
    'Average engineering-group tuition including fees; specific courses may add fees.',other=13400)
add(42,'https://financialaid.arizona.edu/cost/graduate-professional','2026-27',None,
    36000,None,17300,61650,'Main-campus graduate nonresident; fall/spring',
    'Tuition includes fees; base full-time projections.',other=8350)
add(43,'https://www.ois.pitt.edu/sites/default/files/historical_docs/Graduate-Financial-Document-Handout.pdf',
    '2026-27',12,51448,None,26150,80835,'Pittsburgh School of Computing and Information; except MLIS',
    'Despite historical_docs URL, document is 2026-27; explicitly based on 2025-26 actual costs. Tuition includes fees; living is aggregate, not just housing/food.',other=3237)
add(44,'https://www.rochester.edu/college/gradstudies/costs-financial-support/cost.html','2026-27',None,
    tuition=40212,fees=1200,living=16146,total=67304,other=9746,
    scenario='SAS/Hajim graduate; minimum full-time 9 credits per term for two terms; international fee included',
    notes='Scenario calculation: 2234 per credit times 18 credits. Insurance 3720 and books/miscellaneous 6026. Source notes insurance/health fees use 2025-26 rates. Not a guaranteed MSCS annual credit load.',
    extra_url='https://www.rochester.edu/college/gradstudies/academics/registration.html',total_basis='sum_of_published_components')
add(45,'https://gradadmissions.rpi.edu/accepted-students','2026-27',None,
    66300,None,18870,92357,'Graduate accepted-student annual budget',
    'Living is source aggregate; remaining fees/insurance/books require decomposition.')
add(46,'https://www.stevens.edu/page-right-nav/graduate-costs-funding','2026-27',None,
    47826,None,20744,71176,'Full-time graduate off campus',
    'Tuition includes fees; source total includes 206 loan fees.',other=2606)
add(47,'https://www.wpi.edu/admissions/tuition-aid/cost-attendance','2026-27',None,
    31950,None,19732,61882,'General graduate; 18 credits; off campus',
    'Published total excludes possible student organization/program fees and health plan 2945.',other=10200)
add(48,'https://case.edu/studentaccounts/tuition-fees/graduateprofessional-tuition-fees/school-graduate-studies',
    '2026-27',None,scenario='On-campus graduate programs not listed separately',
    notes='Full-time tuition/fee total 61990.50; living housing/meals 14838; personal/transport 10802; books depend on credit load (86/credit). No credit load inferred.')
add(49,'https://www.udel.edu/academics/colleges/grad/prospective-students/cost-of-attendance/',
    '2026-27',12,20682,1462,25644,55125.54,'Graduate base 9 credits/semester; fall/spring tuition with 12-month living; international no assistantship',
    'Calculated 22144 tuition/mandatory fees + 25644 living + 3450 other + 3887.54 insurance.',
    total_basis='sum_of_published_components',other=7337.54)
add(50,'https://financialaid.uconn.edu/cost/','2026-27',None,
    41424,3886,18818,70328,'Graduate nonresident full-time 9 credits; fall/spring',
    'Published total includes 216 loan fees.',other=6200)

assert len(rows) == 50
frame = pd.DataFrame(rows)
assert frame.unitid.is_unique
frame.to_csv(ROOT / 'data/raw/agent4/published_costs_50.csv', index=False)
print('Official-source inventory:', len(frame), '; numeric totals:', frame.published_total_usd.notna().sum())
