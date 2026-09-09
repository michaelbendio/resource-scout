"""Record the coordinator's bounded, source-checked assessment; no model calls."""
import json
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_workbench import LearningWorkbench

P = Path(__file__).resolve().parent
load = lambda name: json.loads((P / name).read_text())
save = lambda name, value: (P / name).write_text(json.dumps(value, indent=2) + '\n')

# One note for every original question entry. Semicolon-separated subjects are
# assessed separately where answerability differs; entries are not issue counts.
notes = {
 'workoptions': {
  'baseline': [
   'Eligibility subjects remain unestablished on cited current pages. The older application was found only by the candidate; that is retrieval variation.',
   'Hours and seats remain unresolved. Meal assistance is partly answered: the cited programs page reports meals included with culinary training for food-insecure students, but does not establish current individual entitlement. Uniforms and tools remain unresolved. Count one partially answerable issue, not the whole compound question.',
   'Research-access note, not a provider question; the usable in-person route is already given.',
   'Placement rates, wages and completion rates are optional outcome research. Current apprenticeship openings can matter and remain unresolved; candidate keeps places available as a question.'
  ],
  'candidate': [
   'Current validity and accommodations remain consequential gaps in a January 2024 application; retaining them is appropriate.',
   'Documents, language and residency remain gaps. Published help obtaining ID does not establish permission to begin without it.',
   'Current start and paid places remain gaps. Published existence of paid apprenticeships does not establish availability. Stipends remain unspecified.'
  ]
 },
 'micasa': {
  'baseline': [
   'Seats and waivers remain unanswered; a published price is not a waiver policy.',
   'The respondent reports conflicting schedules. Online title and venue coexist in event listings; total workload and credit conditions are not settled by class meeting hours. Do not count the entire question as answered.',
   'Spanish availability and equipment/internet assistance remain gaps; ability to request a language is not proof a course is taught in it.',
   'Optional outcome/guarantee note, not a confirmed answerable provider question.'
  ],
  'candidate': [
   'Seats remain open. General career-trainings page publishes education and authorization requirements, but this arm did not cite it. Record a retrieval gap, not an already-reviewed-source failure.',
   'Waivers and additional credit charges remain unanswered.',
   'Online title and physical venue both appear on cited HR event page. Technology requirements appear on a different general page not cited by this arm. Spanish teaching remains unestablished.'
  ]
 },
 'activate': {
  'baseline': [
   'A background-check step is published, but disqualifying findings and individual review are not supplied on cited pages.',
   'The cited local course page does not specify laptop, internet, transportation, childcare or accommodation provision. Additional support pages found elsewhere are retrieval differences.',
   'The cited page establishes an interest-free living-expense loan, not full eligibility and repayment terms.',
   'Optional outcome research and no-job-guarantee note, not an already-answered question.'
  ],
  'candidate': [
   'The respondent identifies a consequential conflict between local eligibility wording and the partner application/FAQ. Keep it visible.',
   'Background-check consequences remain unresolved.',
   'Equipment assessed individually and general support descriptions do not establish upcoming local availability. Loan terms are not fully established. Keep these narrower uncertainties.'
  ]
 },
 'indian': {
  'baseline': [
   'The cited Native Workforce page says Native adults, but does not provide exact age, documentation, geography, income or work-status rules.',
   'Grant funding does not establish individual costs or coverage; all subjects remain gaps.',
   'Appointment-only and first-come service do not establish wait, available training, internships or pay.',
   'Optional outcome research; not an already-answered question.'
  ],
  'candidate': [
   'Exact eligibility and documentation remain gaps on the cited page.',
   'Funding coverage and internship pay remain gaps.',
   'Next appointment, documents and particular supports remain gaps.'
  ]
 },
 'secondchance': {
  'baseline': [
   'Published contact route does not establish self-referral versus prior care-management intake.',
   'Formerly incarcerated is a broad audience, not exact intake or supervision rules.',
   'Published construction training does not settle next cohort, venue or compensation. Paid urban forestry experience on the same services page is a different program.',
   'Current accepting sponsors remain unresolved; placement outcomes are optional outcome research.'
  ],
  'candidate': [
   'Self-referral, appointment and documentation/release rules remain gaps.',
   'Denver office hours do not establish the venue or registration rules for every calendar activity.',
   'Current enrollment, schedule and pay remain gaps. Credentials and connections appear on services-all, cited only by baseline. Candidate failed to carry these useful details, but retained the program and explicit questions. This is a retrieval/completeness difference, not demonstrated suppression by the lesson.'
  ]
 },
 'employmentfirst': {
  'baseline': [
   'Reported broken intake form leaves replacement and turnaround unresolved.',
   'Published support types do not establish current funding, individual limits or preapproval.',
   'Uncovered costs remain unestablished; no inference that grant funding means universally free.',
   'Local pending-applicant wording and state recipient wording are already stated. Individual access and benefit requirements remain unresolved; do not count a stated discrepancy as a redundant question.'
  ],
  'candidate': [
   'Respondent could not retrieve production pages and could not date/establish ownership of the directory. Checking current contact and intake is appropriate.',
   'State general provisions and a local case example do not establish current Denver benefits, costs or procedures.',
   'Preapproval service/payment eligibility and individual work requirements remain uncertain. Relevant lead is needs-check, not excluded or described as closed.'
  ]
 }
}
comparisons = {
 'workoptions': 'At most one partially answered meal-support issue improves numerically, but the candidate drops that subject rather than carrying the published partial answer into the resource. Older application retrieval adds useful cautions. No two-case primary benefit.',
 'micasa': 'Arms chose different upcoming courses and different pages. Candidate removes a generic outcome note but leaves admission/technology questions answered on an uncited general page. No demonstrated same-source improvement.',
 'activate': 'Candidate retrieves partner FAQ/application, retains a GED conflict and explains loan versus grant. Those are useful observations, but new retrieval cannot prove that baseline ignored an already reviewed answer.',
 'indian': 'Both preserve appointment access and unspecified eligibility/costs. Candidate removes an optional outcomes note. No primary-measure improvement.',
 'secondchance': 'Candidate removes some outcome research but leaves construction credentials/connections less complete after citing fewer program details. No demonstrated same-source improvement; no claim of a comprehensive fact audit.',
 'employmentfirst': 'Source access differs materially. Candidate conservatively retains an actionable lead for checking. Neither a failed URL nor a development page establishes closure or current eligibility. Local unresolved facts cannot be fully graded from accessible evidence.'
}
responses = {a: load(a + '-response.json') for a in ('baseline', 'candidate')}
cases = []
judgments = []
for i, before in enumerate(responses['baseline']['cases']):
 cid = before['caseId']
 row = {'caseId': cid, 'comparison': comparisons[cid]}
 evidence_urls = set()
 import re
 for arm in ('baseline', 'candidate'):
  case = next(c for c in responses[arm]['cases'] if c['caseId'] == cid)
  assert len(case['openQuestions']) == len(notes[cid][arm])
  urls = sorted(set(re.findall(r'https?://[^)\s]+', '\n'.join(case['criticalDetails']))))
  evidence_urls.update(urls)
  row[arm] = {'citedUrls': urls, 'questions': [
   {'entry': n + 1, 'text': q, 'judgment': note}
   for n, (q, note) in enumerate(zip(case['openQuestions'], notes[cid][arm]))]}
 cases.append(row)
 judgment = {'caseId': cid, 'evidence': comparisons[cid] + ' Sources and entry-level judgments: question-review.json; ' + ' ; '.join(sorted(evidence_urls))}
 for arm in ('baseline', 'candidate'):
  judgment[arm] = {k: False for k in ('criticalError', 'missedUsefulResource', 'lostCriticalDetail', 'unsupportedPromise')}
  judgment[arm]['reason'] = 'No demonstrated material error in this bounded question-quality comparison; false means not detected, not comprehensive verification. ' + comparisons[cid]
 judgments.append(judgment)

review = {
 'reviewedOn': '2026-09-09', 'reviewer': 'Codex coordinator, unblinded',
 'unit': 'Distinct answerable issue within an original question entry. Optional outcomes notes, retrieval failures and partially answered compounds are not interchangeable with answered issues.',
 'primaryFinding': {'baselineConfirmedFullyAnswerableIssues': 0, 'baselinePartiallyAnswerableIssues': 1, 'candidateConfirmedFullyAnswerableIssues': 0, 'candidatePartiallyAnswerableIssues': 0,
  'casesWithPossibleDecrease': ['workoptions'], 'requiredDecrease': 2, 'requiredCases': 2,
  'thresholdMet': False, 'interpretation': 'Even crediting the single partial meal-support issue as one reduction, the predeclared two-case threshold is not met. Removal without preserving its supported answer is not a demonstrated successful application of the lesson. Unknown pages are not scored as clean.'},
 'sourceChecks': 'Coordinator inspected Work Options training/program pages, Mi Casa course event/general training material, ActivateWork local course and Per Scholas FAQ, Denver Indian Center Native Workforce, and SCC services. Original responses and CLI traces retain respondent source provenance. Some production state/Denver and Mi Casa pages could not be re-fetched; associated uncertainty is explicit. This is a comparison of question handling, not a phone-vetted resource audit.',
 'additionalCoordinatorSource': 'https://micasaresourcecenter.org/career-trainings/',
 'cases': cases,
 'conclusion': 'no-clear-benefit', 'confirmationRun': 'Not triggered by predeclared rule; do not repeat until positive.',
 'activation': 'None. Candidate remains evaluated and inactive.'}
save('question-review.json', review)
assessment = {'reviewer': review['reviewer'], 'method': 'Entry-by-entry question review against respondent-cited sources; distinguish partial answers, new retrieval and optional outcome notes. See question-review.json. Predeclared threshold not met even with favorable credit for the sole partial-answer issue.',
 'caseJudgments': judgments, 'conclusion': 'no-clear-benefit',
 'limitations': 'Six purposively selected leads; same model; one pair; unblinded coordinator; differing sources and source access; no human verification. No-error flags mean no demonstrated material error in this bounded comparison, not comprehensive correctness. Page counts and dollar cost unavailable. Fewer question entries do not establish fewer unresolved issues or reduced curator time.'}
save('assessment.json', assessment)
w = LearningWorkbench(ResearchStore(P.parents[1] / 'output/learning-questions-20260909/trial.sqlite3'))
save('report.json', w.assess(load('trial.json')['trialId'], assessment))
assert not w.manifest()['entries']
print('Saved no-clear-benefit assessment; no confirmation triggered and no guidance activated.')
