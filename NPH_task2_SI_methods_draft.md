# Task 2 ground-truth validation — draft SI methods text

*Draft, 2026-09-18. Written from the actual generated sample (`sample_selected.csv`)
and `score_groundtruth.py`/`build_groundtruth_sample.py` as currently committed on
`nph-task2-ground-truth`. Bracketed notes mark places that need a number filled in
once annotation is complete, or a citation double-checked before submission — nothing
below is invented to fill a gap.*

## Ground-truth sample

We drew a ground-truth validation sample of 230 papers from the deduplicated
literature-search corpus (19,586 records with a usable DOI, combined from Web of
Science, Scopus, and PubMed exports and deduplicated by DOI, then by normalized
abstract, then by normalized title). Sampling was stratified by publication era
(pre-2000, 2000–2012, 2013–2024) with proportional allocation and a fixed random
seed; we did not stratify by predicted ecological function or geography at this
stage, since those labels are produced by the extraction pipeline under evaluation
and are not available prior to extraction. Full-text availability was determined by
cross-referencing each paper's DOI against our PDF-retrieval manifest.

Of the 230 sampled papers, 80 had a successfully retrieved full-text PDF; the
remaining 150 were scored from the abstract only. A full-text-eligible paper was
read and scored twice by the same annotator — once from the abstract alone, then
again from the full text — producing a paired abstract-versus-full-text comparison
[feeds the Task 1 analysis; cross-reference that section].

The sample was divided among [N] annotators as follows: [name] scored 170 papers
solo (122 abstract-only, 48 full-text-paired); two additional annotators ([names])
each scored a further 20 papers solo (14 abstract-only, 6 full-text-paired); and a
20-paper subset, drawn only from the full-text-eligible portion of the sample, was
scored independently by all five annotators to estimate inter-annotator agreement
(the "κ block," described below).

## Inter-annotator agreement

The κ block (20 full-text papers, scored as an abstract row and a full-text row by
each of five annotators, 40 rated items per annotator) was scored as a single blind,
independent pass — no calibration sub-round was scored toward the reported
agreement statistic. Rubric training instead took place beforehand on two papers (one
abstract-only, one full-text) drawn from outside the 230-paper sample entirely, so
that no paper used for training was later rescored for the reported measurement.

Agreement was computed separately for each paper-level field (whether the paper
reports a fungus recovered from a plant; primary aim; sampling approach; presence of
sequence-only/uncultured taxa; strain-level variation; sampling-location
completeness; whether surface sterilisation was checked) and each interaction-level
field (tissue, fungal lifestyle, effect on host, evidence basis), using items with
≥2 (paper-level) or ≥3 (interaction-level) raters overlapping.

Our primary agreement statistic is Gwet's AC1 (Gwet, 2008), with Fleiss' κ (Fleiss,
1971) reported alongside for comparability with the wider inter-rater-reliability
literature. We chose AC1 as primary because kappa's chance-agreement correction is
known to understate agreement, sometimes severely, whenever one category dominates a
field's base rate (the "kappa paradox"; Wongpakaran et al., 2013) — a real risk for
several of our fields (e.g., most papers being positive for Q1; `effect_on_host`
frequently coded "not reported"). Both statistics were computed from the same
per-item rating-distribution table and both were given percentile bootstrap 95%
confidence intervals (2,000 resamples).

A pre-registered simulation (Monte Carlo, 5 raters, category base rates matched to
this corpus, run before scores were seen) gave an expected 95% CI half-width of
approximately 0.14–0.16 kappa units at n = 20 items for a true κ of 0.7–0.8 — narrower
than an equivalently sized two-rater study, since five raters per item partly buys
back precision, but wide enough that we report the interval rather than a bare point
estimate throughout.

Thresholds were set before scores were seen, using the conventional Landis & Koch
(1977) benchmark bands applied to AC1 (the two statistics share a −1…1 scale): <0.4
poor, 0.4–0.6 moderate, ≥0.6 substantial, with a target of AC1 ≥ 0.6 for a field to be
treated as validated. Where a field fell below that threshold, we used the per-item
breakdown to identify the source of disagreement, conducted and documented a group
reconciliation on the disagreeing items only (following the practice recommended by
Belur et al., 2021, who found that documenting the reasoning behind a resolved
disagreement improved later-round agreement more than informal discussion alone),
tightened that field's coding rubric as needed, and re-tested the revision on a
fresh, disjoint set of papers rather than rescoring the original 20 (which would
trivially inflate agreement). [Insert observed AC1/κ values, CIs, and any
reconciliation outcomes here once the κ block is complete — Table SX.]

## Sample size rationale

Sample size followed the convention for LLM/text-mining extraction validation in
ecology and evidence synthesis, where validation sets of roughly 100–500 records,
scored for precision/recall/F1 with 95% Wilson confidence intervals, are typical. At
a realistic precision of ≈0.85, n ≈ 200 gives a ±5-percentage-point 95% CI; our core
sample of 200 [170 + the 20-paper κ block scored by the same primary annotator, N.B.
adjust if the final split differs] meets that target.

---

### References (verify against journal style before submission)

- Belur, J., Tompson, L., Thornton, A., & Simon, M. (2021). Interrater reliability in
  systematic review methodology: Exploring variation in coder decision-making.
  *Sociological Methods & Research*, 50(2), 837–865.
  https://doi.org/10.1177/0049124118799372
- Fleiss, J. L. (1971). Measuring nominal scale agreement among many raters.
  *Psychological Bulletin*, 76(5), 378–382. https://doi.org/10.1037/h0031619
- Gwet, K. L. (2008). Computing inter-rater reliability and its variance in the
  presence of high agreement. *British Journal of Mathematical and Statistical
  Psychology*, 61(1), 29–48. https://doi.org/10.1348/000711006X126600
- Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for
  categorical data. *Biometrics*, 33(1), 159–174. https://doi.org/10.2307/2529310
- Wongpakaran, N., Wongpakaran, T., Wedding, D., & Gwet, K. L. (2013). A comparison
  of Cohen's Kappa and Gwet's AC1 when calculating inter-rater reliability
  coefficients: A study conducted with personality disorder samples. *BMC Medical
  Research Methodology*, 13, 61. https://doi.org/10.1186/1471-2288-13-61

### Still needed before this is submission-ready

- Fill in annotator names/initials (kept generic above pending your author-list
  preference).
- Insert the actual AC1/κ table once the κ block is scored (`agreement.csv` from
  `score_groundtruth.py`).
- The deep-recall subset (still an open design question per the plan doc, §7) isn't
  described here — add a paragraph once its size/sampling method is finalized.
- Double-check the Wongpakaran et al. citation's page/article number against the
  journal's own listing before submission — BMC's article-number format varies by
  citation style guide.
