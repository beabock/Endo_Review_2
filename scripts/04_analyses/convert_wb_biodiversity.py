#!/usr/bin/env python3
import csv
import os

paths = [
    ("data/biodiversity/World_Bank/WB_GBIOD_N_SPP_SMALL50XENDEMIC100.csv","WB_SMALL50XENDEMIC100"),
    ("data/biodiversity/World_Bank/WB_GBIOD_N_SPP_TPROB80.csv","WB_TPROB80"),
    ("data/biodiversity/World_Bank/WB_GBIOD_N_SPP_TOTAL.csv","WB_TOTAL"),
]
out_path = "data/biodiversity/biodiversity_priority_countries.csv"
fieldnames = ["iso3","country_name","priority_score","source"]
count=0
with open(out_path, "w", newline='', encoding='utf-8') as outf:
    writer = csv.DictWriter(outf, fieldnames=fieldnames)
    writer.writeheader()
    for p, src in paths:
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                continue
            # normalize header to plain strings
            header_l = [h.strip() for h in header]
            # find column indices
            def idx(names):
                for n in names:
                    if n in header_l:
                        return header_l.index(n)
                return None
            idx_iso = idx(["REF_AREA","iso3","REF_AREA_CODE","REF_AREA_CODE_LABEL"]) 
            idx_label = idx(["REF_AREA_LABEL","REF_AREA_NAME","REF_AREA_LABEL_EN","REF_AREA_LABEL_ENGLISH","REF_AREA_LABEL\n"])
            if idx_label is None:
                idx_label = idx(["REF_AREA"])  # fallback
            idx_obs = idx(["OBS_VALUE","VALUE","OBSERVATION","OBS_VAL"]) 
            if idx_iso is None or idx_obs is None:
                # try case-insensitive match
                header_lower = [h.lower() for h in header_l]
                try:
                    idx_iso = header_lower.index('ref_area')
                except ValueError:
                    idx_iso = None
                try:
                    idx_obs = header_lower.index('obs_value')
                except ValueError:
                    idx_obs = None
            if idx_iso is None or idx_obs is None:
                continue
            for row in reader:
                if len(row) <= max(idx_iso, idx_obs):
                    continue
                iso = row[idx_iso].strip()
                name = row[idx_label].strip() if idx_label is not None and len(row)>idx_label else ""
                val_raw = row[idx_obs].strip() if len(row)>idx_obs else ""
                try:
                    val = float(val_raw)
                except:
                    val = ""
                writer.writerow({"iso3": iso, "country_name": name, "priority_score": val, "source": src})
                count += 1
print(f"Wrote {count} rows to {out_path}")
