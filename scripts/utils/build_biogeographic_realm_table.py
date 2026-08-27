#!/usr/bin/env python3
# BMB 2026-08-27
# Builds data/Reference_datasets/country_biogeographic_realm.csv: a curated
# country -> biogeographic realm crosswalk (Olson et al. 2001 / WWF terrestrial
# realms), replacing the political EU / Global North-South groupings for the
# NPH-MS-2026-57711 resubmission (Referee 3).
#
# Eight realms: Palearctic, Nearctic, Neotropic, Afrotropic, Indomalaya,
# Australasia, Oceania, Antarctic.
#
# Method: each country is assigned to the realm covering the majority of its
# land area. Countries that straddle a realm boundary carry a `realm_secondary`
# and a note; a sensitivity analysis re-assigns those to the secondary realm to
# confirm the pattern is robust (see 03c_biogeographic_bias_mapping.R).
#
# Re-run: python scripts/utils/build_biogeographic_realm_table.py
# This is authored, not computed; edit the dicts below and re-run. A future
# refinement is a polygon-intersection build against the WWF ecoregion shapefile
# (see NPH_task4_biogeographic_plan.md).

import csv
from pathlib import Path

# Checked in (data/Reference_datasets is gitignored). Co-located with the loaders
# in country_mapping.py (get_realm) and biogeographic_mapping.R.
OUT = Path(__file__).resolve().parent / "country_biogeographic_realm.csv"

PALEARCTIC = """
ALB AND ARM AUT AZE BLR BEL BIH BGR HRV CYP CZE DNK EST FRO FIN FRA GEO DEU GIB
GRC GGY HUN ISL IRL IMN ITA JEY LVA LIE LTU LUX MLT MDA MCO MNE NLD MKD NOR POL
PRT ROU RUS SMR SRB SVK SVN ESP SJM SWE CHE UKR GBR VAT ALA XKX
DZA EGY LBY MAR TUN ESH
TUR SYR LBN ISR PSE JOR IRQ IRN KWT BHR QAT ARE OMN SAU
KAZ KGZ TJK TKM UZB MNG AFG
JPN PRK KOR CHN
""".split()

NEARCTIC = "CAN USA GRL BMU SPM".split()

NEOTROPIC = """
MEX GTM BLZ SLV HND NIC CRI PAN
CUB JAM HTI DOM BHS TTO BRB LCA VCT GRD DMA ATG KNA PRI VIR VGB AIA MSR GLP MTQ
ABW CUW SXM BES BLM MAF CYM TCA
COL VEN GUY SUR GUF ECU PER BRA BOL PRY URY ARG CHL FLK
""".split()

AFROTROPIC = """
AGO BEN BWA BFA BDI CMR CPV CAF TCD COM COG COD CIV DJI GNQ ERI SWZ ETH GAB GMB
GHA GIN GNB KEN LSO LBR MDG MWI MLI MRT MUS MYT MOZ NAM NER NGA REU RWA STP SEN
SYC SLE SOM ZAF SSD SDN TZA TGO UGA ZMB ZWE SHN
YEM
IOT
""".split()

INDOMALAYA = """
PAK IND NPL BTN BGD LKA MDV MMR THA LAO KHM VNM MYS SGP BRN IDN PHL TWN HKG MAC
CXR CCK
""".split()

AUSTRALASIA = "AUS PNG NZL NCL SLB TLS".split()

OCEANIA = """
FJI TON WSM ASM KIR TUV NRU MHL FSM PLW GUM MNP COK NIU PYF WLF TKL PCN NFK UMI
VUT
""".split()

ANTARCTIC = "ATA ATF SGS BVT HMD".split()

REALMS = {
    "Palearctic": PALEARCTIC,
    "Nearctic": NEARCTIC,
    "Neotropic": NEOTROPIC,
    "Afrotropic": AFROTROPIC,
    "Indomalaya": INDOMALAYA,
    "Australasia": AUSTRALASIA,
    "Oceania": OCEANIA,
    "Antarctic": ANTARCTIC,
}

# Trans-realm countries: primary is set above; record the secondary realm and why.
SECONDARY = {
    "MEX": ("Nearctic", "N Mexico is Nearctic; most land area and endemism Neotropic"),
    "USA": ("Neotropic", "S Florida Neotropic; Hawaii Oceanian - both small"),
    "CHN": ("Indomalaya", "S China (Yunnan, Guangxi, Hainan) is Indomalayan"),
    "IDN": ("Australasia", "Papua and islands E of Wallace's Line are Australasian"),
    "IND": ("Palearctic", "the Himalaya and NW arid zone are Palearctic"),
    "PAK": ("Palearctic", "Balochistan and N mountains are Palearctic"),
    "AFG": ("Indomalaya", "mostly Palearctic; only the SE lowlands are Indomalayan"),
    "EGY": ("Afrotropic", "far S (Gebel Elba) is Afrotropic"),
    "SAU": ("Afrotropic", "SW highlands (Asir) are Afrotropic"),
    "OMN": ("Afrotropic", "Dhofar in the far S is Afrotropic"),
    "YEM": ("Palearctic", "the interior desert is Palearctic; SW highlands + Socotra Afrotropic"),
    "SDN": ("Palearctic", "the far N Nubian desert is Palearctic"),
    "ARG": ("Antarctic", "southern Patagonia grades into the Antarctic realm"),
    "CHL": ("Antarctic", "far S Magellanic zone grades into the Antarctic realm"),
    "NZL": ("Antarctic", "the subantarctic islands are Antarctic realm"),
    "TLS": ("Indomalaya", "Timor is Wallacea - transitional Indomalaya/Australasia"),
    "VUT": ("Australasia", "Vanuatu is on the Australasia/Oceania boundary"),
    "TWN": ("Palearctic", "N Taiwan has Palearctic affinities"),
}

def main():
    seen = {}
    for realm, codes in REALMS.items():
        for c in codes:
            if c in seen:
                raise SystemExit(f"{c} assigned to both {seen[c]} and {realm}")
            seen[c] = realm

    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for iso, realm in sorted(seen.items()):
        sec, note = SECONDARY.get(iso, ("", ""))
        rows.append({
            "iso_a3": iso,
            "realm": realm,
            "realm_secondary": sec,
            "notes": note,
        })

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["iso_a3", "realm", "realm_secondary", "notes"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    dist = Counter(r["realm"] for r in rows)
    print(f"Wrote {len(rows)} countries to {OUT}")
    for realm, n in dist.most_common():
        print(f"  {realm:12s} {n}")
    print(f"  trans-realm (with secondary): {sum(1 for r in rows if r['realm_secondary'])}")


if __name__ == "__main__":
    main()
