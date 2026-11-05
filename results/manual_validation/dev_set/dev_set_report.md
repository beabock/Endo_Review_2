# DEV set - draw report

- seed `20261105`, script sha1 `965d8d4d6e`, corpus `All_abstracts_deduped.csv`, PDF manifest `pdf_manifest.csv`
- n = 40 (24 abstract-only, 16 full-text). One annotation row per paper.
- excluded from the draw: 232 paper_ids (sample_selected.csv: 230, groundtruth_MOCK.xlsx: 2, groundtruth_bea_main.xlsx: 170, groundtruth_ian_main.xlsx: 20, groundtruth_jack_main.xlsx: 20, groundtruth_kappa_MASTER.xlsx: 20, groundtruth_kappa_bea.xlsx: 20, groundtruth_kappa_ian.xlsx: 20)
- eligible frame after exclusions: 19,100 papers
- quota sampling (marginals), NOT proportional - see header of draw_dev_set.py; design/table classes are heuristics on title+abstract / PDF text, not model output.
- the first 25 rows (`poc_prefix_25`) are the proof-of-concept set and are balanced on their own.

## Achieved vs frame

### doc_type
| level | n |
|---|---|
| abstract-only | 24 |
| full-text | 16 |

### era (frame % in brackets)

| level | n | frame_pct |
|---|---|---|
| 2013+ | 26 | 75.5 |
| 2000-2012 | 9 | 16.7 |
| pre-2000 | 5 | 7.8 |

### design hint (frame % in brackets)

| level | n | frame_pct |
|---|---|---|
| isolate_culture | 17 | 21.1 |
| other | 12 | 68.8 |
| metabarcoding | 11 | 10.1 |

### table-heaviness (full-text only)
| level | n |
|---|---|
| prose | 8 |
| table-heavy | 8 |

### natural-products hint (not stratified; just so you know what you are getting)
| level | n |
|---|---|
| False | 30 |
| True | 10 |

### language_hint
| level | n |
|---|---|
| English | 38 |
| Chinese | 1 |

### doc_type x era x design

| doc_type | era | design | n |
|---|---|---|---|
| abstract-only | 2000-2012 | isolate_culture | 2 |
| abstract-only | 2000-2012 | metabarcoding | 3 |
| abstract-only | 2000-2012 | other | 1 |
| abstract-only | 2013+ | isolate_culture | 8 |
| abstract-only | 2013+ | metabarcoding | 1 |
| abstract-only | 2013+ | other | 4 |
| abstract-only | pre-2000 | metabarcoding | 3 |
| abstract-only | pre-2000 | other | 2 |
| full-text | 2000-2012 | isolate_culture | 1 |
| full-text | 2000-2012 | metabarcoding | 1 |
| full-text | 2000-2012 | other | 1 |
| full-text | 2013+ | isolate_culture | 6 |
| full-text | 2013+ | metabarcoding | 3 |
| full-text | 2013+ | other | 4 |

## Rough annotation load for Bea

abstract rows x ~8 min + full-text rows x ~20 min = about 8.5 h. Annotate in `order` (first 25 first) so a partial pass is still usable.
