# Ground-truth sample - stratification report

- corpus: `All_abstracts_deduped.csv`  |  seed: `20260828`
- n = 230 (full-text fraction 0.35). Stratified by era + doc_type only (2026-09-17: no function/continent stratification until the Task 1 re-extraction runs on this corpus - see the script header note)
- kappa block n = 20 papers, all full-text, rated by ALL annotators; it is the balanced prefix of a stratified pool, so raising --n-kappa later stays valid
- single blind measurement pass, no calibration sub-round (2026-09-17 decision - rubric training instead happens on the 2 MOCK papers, drawn from outside the sample, before the real block starts)
- **230 unique papers total**; the 80 full-text papers each get a paired abstract-only row + full-text row (~310 annotation rows)

## Selected sample by stratum

### doc_type
| level | sampled | frame % |
|---|---|---|
| abstract-only | 150 | 69.6% |
| full-text | 80 | 30.4% |

### era
| level | sampled | frame % |
|---|---|---|
| 2000-2012 | 40 | 16.7% |
| 2013-2024 | 167 | 75.5% |
| pre-2000 | 20 | 7.8% |
| unknown | 3 | 0.0% |

### assignment
| level | sampled |
|---|---|
| kappa_block | 20 |
| solo | 210 |

### annotator
| level | sampled |
|---|---|
| ALL | 20 |
| bea | 170 |
| ian | 20 |
| jack | 20 |

## Workload per annotator (kappa block + own solo block)

| annotator | kappa papers | own solo papers | total papers | rows | est. hours |
|---|---|---|---|---|---|
| Bea | 20 | 170 | 190 | 258 | ~45 |
| Nancy | 20 | 0 | 20 | 40 | ~8 |
| Kitty | 20 | 0 | 20 | 40 | ~8 |
| Ian | 20 | 20 | 40 | 66 | ~13 |
| Jack | 20 | 20 | 40 | 66 | ~13 |

The kappa block is 20 papers (0 abstract-only + 20 full-text = 40 rows, ~8 h) - EVERY annotator rates it.
Nancy & Kitty rate only the kappa block.
Each full-text paper = an abstract-only row (done first, ~5 min) + a full-text
row (~20 min); an abstract-only paper = one row (~8 min).
The paired rows give a human-annotated measure of what abstracts omit vs their
own full text - it strengthens the Task 1 abstract/full-text validation.