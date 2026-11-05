# Endophyte literature check — instructions for annotators

Thank you for helping. The shared block is **40 papers / 52 rows**, roughly **~9 hours**,
over however long you like within the deadline.

## The job

An **independent expert read** of a sample of papers from our endophyte literature
database, so we can measure how accurately our automated pipeline pulled the biology out.
You will **not** see any software output — you just read each paper and record what it
says. Your reading is the reference we score the pipeline against.

## Calibration round first

Everyone does the **first ~18 papers of the agreement block** and then **stops**. We
compare answers on a short call, settle disagreements, tweak the rubric if needed, and
only then does everyone continue. Your file's **Instructions** tab names the exact
stop row.

## Your file

`groundtruth_kappa_<yourname>.xlsx`, **Review** tab. Keep **`guild_rubric.md`** open beside
it — it defines every dropdown.

### Rows
Most rows are one abstract-only paper. Some papers have **two adjacent rows** —
`reading_stage = abstract` then `reading_stage = full text` for the same paper (row_id
ends `a`, then `b`):
- `abstract` row: read **only** the abstract text shown in that row's `abstract` column.
  **Do not open the link.** Fill the row from the abstract alone — it's fine (expected,
  even) to answer "not stated" a lot on these.
- `full text` row: open `doi_link`, read the whole paper; you may copy your abstract
  answers across and then **correct / add** what the full text tells you.

Both are kept — the difference tells us what abstracts leave out.

### For each row, left to right
1. **`paper_reviewed`** — set this when done; it decides how much else you fill:
   - `complete` → fill the whole row
   - `could not access the paper` → a full-text row you couldn't get; stop there
   - `review or secondary compilation` → Q1 = no, Q3 = review, Q4 (language); leave
     Q2, Q5–Q11, method ticks and interaction blocks blank
   - `not a fungus-in-plant study` → Q1 = no, leave everything else blank
   A blank `paper_reviewed` = not done yet. (See the table in `guild_rubric.md`.)
2. **Read** to the depth `reading_stage` says.
3. **Q1–Q11** — the header of each is the question. Dropdowns + one number (Q10). If the
   right answer isn't offered, **type it in** (Excel warns but keeps it). The rubric
   covers Q1, Q3, Q8, Q9, Q11.
4. **Method columns** (the purple block — plain-English headers like `culture from
   sterilised tissue`, `microscopy in tissue`) — put `yes` in **every** method the paper
   used to show the fungus was inside the plant. As many as apply. The rubric defines each.
5. **Interaction blocks 1–5** — one per distinct fungus × host-plant pair the paper
   **names**. Six cells each:
   - `fungus`, `host_plant` — **exactly as the authors name them.** If you know the fungus
     has since been renamed, still write the authors' name — the renaming is handled
     programmatically later, and hand-editing names breaks it.
   - `tissue` — **several tissues for one pair go in the one cell**: `leaf, root`. "Shoots" /
     "aerial parts" with no split → `leaf, stem`.
   - `fungal_lifestyle` — *how the fungus lives* (endophyte / plant pathogen / saprotroph /
     mycorrhizal / …)
   - `effect_on_host` — *what happened to this plant* (harmful / beneficial / neutral /
     no-symptoms-not-tested / not-reported)
   - `evidence_basis` — tested here / observed here / inferred from the taxon
   `fungal_lifestyle` and `effect_on_host` are **different questions** — a plant pathogen
   can be present with no symptoms.
6. **Metabarcoding / NGS paper?** Don't list every OTU — fill blocks only for taxa the
   paper names, and summarise the community in `extra_pairs_or_NGS_community_summary`
   (host, tissue, richness e.g. "142 OTUs / 38 genera", dominant taxa, framing).
7. **`date_reviewed`** (3rd column, on the left — no scrolling needed) and flag anything
   you were unsure about in `anything_you_were_unsure_about` (far right). No initials — the
   file name is your name.

**Record what the paper says, not what you know to be true in general.** If a paper
isolates *Colletotrichum* as a symptomless endophyte and never tests its effect, that's
`fungal_lifestyle = endophyte`, `effect_on_host = no visible symptoms; benefit or harm
not tested` — even though you know the genus contains pathogens.

This is the shared agreement block: **work independently**, don't discuss the papers with
the other reviewers until all files are back.

Worked examples are in **`guild_rubric.md`** (bottom).
