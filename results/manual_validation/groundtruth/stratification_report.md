# Ground-truth sample - stratification report

- extraction frame: `Ollama_cleaned_synresolved_standardized_year.csv`  |  seed: `20260828`
- core n = 200 (full-text fraction 0.35) + rare-function oversample n = 30
- kappa block n = 50 papers, rated by ALL annotators; it is the balanced prefix of a stratified pool, so raising --n-kappa later stays valid
- within the kappa block, the first **15** papers are a calibration round: everyone does them, then a reconciliation call refines the rubric before continuing. Reported Fleiss' kappa uses the remaining 35 measurement papers (calibration agreement reported separately as a pilot)
- **230 unique papers total**; the 71 full-text papers each get a paired abstract-only row + full-text row (~301 annotation rows)

## Selected sample by stratum

### doc_type
| level | sampled | frame % |
|---|---|---|
| abstract-only | 159 | 85.1% |
| full-text | 71 | 14.9% |

### function
| level | sampled | frame % |
|---|---|---|
| biocontrol_antagonist | 31 | 5.5% |
| endophyte_asymptomatic | 89 | 63.3% |
| mutualist_pgpr | 24 | 4.5% |
| mycorrhizal | 17 | 4.3% |
| pathogen | 33 | 15.4% |
| saprotroph | 15 | 1.0% |
| unknown | 21 | 6.0% |

### continent
| level | sampled | frame % |
|---|---|---|
| Africa | 4 | 2.7% |
| Asia | 39 | 16.3% |
| Europe | 16 | 5.8% |
| Europe/Asia | 1 | 0.2% |
| North America | 28 | 6.3% |
| Oceania | 5 | 1.9% |
| South America | 15 | 4.4% |
| unassigned | 122 | 61.0% |

### era
| level | sampled | frame % |
|---|---|---|
| 2000-2012 | 54 | 17.5% |
| 2013-2024 | 131 | 71.1% |
| pre-2000 | 28 | 7.9% |
| unknown | 17 | 3.4% |

### assignment
| level | sampled |
|---|---|
| kappa_block | 50 |
| solo | 180 |

### annotator
| level | sampled |
|---|---|
| ALL | 50 |
| bea | 80 |
| ian | 50 |
| jack | 50 |

### bucket
| level | sampled |
|---|---|
| core | 200 |
| rare_function_oversample | 30 |

## Workload per annotator (kappa block + own solo block)

| annotator | kappa papers | own solo papers | total papers | rows | est. hours |
|---|---|---|---|---|---|
| Bea | 50 | 80 | 130 | 173 | ~30 |
| Nancy | 50 | 0 | 50 | 70 | ~12 |
| Kitty | 50 | 0 | 50 | 70 | ~12 |
| Ian | 50 | 50 | 100 | 134 | ~23 |
| Jack | 50 | 50 | 100 | 134 | ~23 |

The kappa block is 50 papers (30 abstract-only + 20 full-text = 70 rows, ~12 h) - EVERY annotator rates it.
Nancy & Kitty rate only the kappa block.
Each full-text paper = an abstract-only row (done first, ~5 min) + a full-text
row (~20 min); an abstract-only paper = one row (~8 min).
The paired rows give a human-annotated measure of what abstracts omit vs their
own full text - it strengthens the Task 1 abstract/full-text validation.