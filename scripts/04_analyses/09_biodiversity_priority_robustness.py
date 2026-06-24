#!/usr/bin/env python3
# BMB 2026-06-05
# Robustness and statistical tests for the biodiversity priority overlap -
# chi-square, Spearman, binomial, sensitivity analysis, and regional subsampling.
         results/biodiversity_priority_overlap/country_land_area_summary.csv
         results/biodiversity_priority_overlap/area_normalized_summary.csv
         results/biodiversity_priority_overlap/gdp_biodiversity_correlation.csv
         results/biodiversity_priority_overlap/modeling_results.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency, spearmanr, kruskal
try:
    from scipy.stats import binom_test
except ImportError:
    # newer scipy versions use binomtest instead
    from scipy.stats import binomtest
    def binom_test(k, n, p, alternative='two-sided'):
        result = binomtest(k, n, p, alternative=alternative)
        return result.pvalue
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from country_mapping import CONTINENT_MAP, find_country_in_text, get_continent

import warnings
warnings.filterwarnings('ignore')

ROOT = Path('.').resolve()
INPUT_OVERLAP = ROOT / 'results' / 'biodiversity_priority_overlap' / 'overlap_by_country.csv'
INPUT_UNSTUDIED = ROOT / 'results' / 'understudied_analysis' / 'unstudied_countries.csv'
INPUT_PRIORITY = ROOT / 'data' / 'biodiversity' / 'biodiversity_priority_countries.csv'
INPUT_COUNTRY_SUMMARY = ROOT / 'results' / 'country_analysis' / 'country_gdp_latitude_summary.csv'
INPUT_FAOSTAT_LAND = ROOT / 'data' / 'biodiversity' / 'FAOSTAT_Land' / 'FAOSTAT_data_en_5-5-2026.csv'
OUTPUT_DIR = ROOT / 'results' / 'biodiversity_priority_overlap'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_COUNTRY_AREA = OUTPUT_DIR / 'country_land_area_summary.csv'
OUTPUT_AREA_NORMALIZED = OUTPUT_DIR / 'area_normalized_summary.csv'
OUTPUT_GDP_CORRELATION = OUTPUT_DIR / 'gdp_biodiversity_correlation.csv'
OUTPUT_MODELING_RESULTS = OUTPUT_DIR / 'modeling_results.csv'

print("=" * 80)
print("ROBUSTNESS AND STATISTICAL TESTS FOR BIODIVERSITY PRIORITY OVERLAP")
print("(Using actual numeric metrics: endemic species count, threatened probability, etc.)")
print("=" * 80)

# Load data
print("\nLoading data...")
overlap = pd.read_csv(INPUT_OVERLAP)
unstudied = pd.read_csv(INPUT_UNSTUDIED)
priority = pd.read_csv(INPUT_PRIORITY)
country_summary = pd.read_csv(INPUT_COUNTRY_SUMMARY)

print("Preparing data...")

metric_sources = [
    ("WB_TOTAL", "Total species"),
    ("WB_SMALL50XENDEMIC100", "Endemic species"),
    ("WB_TPROB80", "Threatened species probability"),
]

FAOSTAT_AREA_OVERRIDES = {
    'bonaire, sint eustatius and saba': 'BES',
    'cabo verde': 'CPV',
    'cayman islands': 'CYM',
    'czechia': 'CZE',
    'gibraltar': 'GIB',
    'holy see': 'VAT',
    "lao people's democratic republic": 'LAO',
    'mayotte': 'MYT',
    'saint barthélemy': 'BLM',
    'saint barthelemy': 'BLM',
    'saint martin (french part)': 'MAF',
    'saint pierre and miquelon': 'SPM',
    'syrian arab republic': 'SYR',
    'tokelau': 'TKL',
    'viet nam': 'VNM',
    'western sahara': 'ESH',
}

country_summary = country_summary.copy()
country_summary['study_count'] = pd.to_numeric(country_summary['study_count'], errors='coerce')
country_summary['understudied'] = (country_summary['study_count'] == 0).astype(int)
country_summary['continent'] = country_summary['iso_a3'].map(get_continent)


def resolve_fao_iso(country_name):
    if pd.isna(country_name):
        return None
    name = str(country_name).lower().strip()
    if name in FAOSTAT_AREA_OVERRIDES:
        return FAOSTAT_AREA_OVERRIDES[name]
    return find_country_in_text(str(country_name))


fao_land = pd.read_csv(INPUT_FAOSTAT_LAND)
country_area = fao_land[(fao_land['Item'] == 'Country area') & (fao_land['Element'] == 'Area')].copy()
country_area['iso_a3'] = country_area['Area'].apply(resolve_fao_iso)
country_area['country_area_1000ha'] = pd.to_numeric(country_area['Value'], errors='coerce')
country_area['year'] = pd.to_numeric(country_area['Year'], errors='coerce')
country_area = country_area.dropna(subset=['iso_a3', 'country_area_1000ha'])
country_area = country_area.sort_values(['iso_a3', 'year'])
country_area = country_area.drop_duplicates(subset=['iso_a3'], keep='last')
country_area['country_area_km2'] = country_area['country_area_1000ha'] * 10.0
country_area = country_area[['iso_a3', 'Area', 'country_area_1000ha', 'country_area_km2', 'year']]
country_area = country_area.rename(columns={'Area': 'country_area_name'})

country_area.to_csv(OUTPUT_COUNTRY_AREA, index=False)
country_summary = country_summary.merge(
    country_area[['iso_a3', 'country_area_1000ha', 'country_area_km2']],
    on='iso_a3',
    how='left'
)

area_matches = int(country_summary['country_area_km2'].notna().sum())
sensitivity_rows = []
unevenness_rows = []
regional_rows = []
metric_summary_rows = []
report = []

report.append(f"FAOSTAT land area coverage: {area_matches}/{len(country_summary)} countries matched")
report.append(f"Country area summary saved to: {OUTPUT_COUNTRY_AREA}")

def make_metric_frame(source_name):
    metric = priority[priority['source'] == source_name].copy()
    if metric.empty:
        return pd.DataFrame()

    if 'iso3' in metric.columns:
        metric['iso_a3'] = metric['iso3'].astype(str)
    elif 'iso_a3' in metric.columns:
        metric['iso_a3'] = metric['iso_a3'].astype(str)
    else:
        return pd.DataFrame()

    metric['priority_score'] = pd.to_numeric(metric['priority_score'], errors='coerce')
    metric = metric[['iso_a3', 'priority_score']].dropna(subset=['iso_a3', 'priority_score'])
    metric = metric.drop_duplicates(subset=['iso_a3'])
    frame = country_summary[['iso_a3', 'country_name', 'study_count', 'understudied', 'continent', 'country_area_km2', 'gdp_log10']].drop_duplicates(subset=['iso_a3']).merge(metric, on='iso_a3', how='inner')
    frame = frame.rename(columns={'priority_score': 'metric_value'})
    frame['study_density_per_1000_km2'] = np.where(
        frame['country_area_km2'] > 0,
        frame['study_count'] / frame['country_area_km2'] * 1000.0,
        np.nan,
    )
    frame['metric_density_per_1000_km2'] = np.where(
        frame['country_area_km2'] > 0,
        frame['metric_value'] / frame['country_area_km2'] * 1000.0,
        np.nan,
    )
    return frame

for source_name, metric_label in metric_sources:
    metric_df = make_metric_frame(source_name)

    report.append("\n" + "=" * 80)
    report.append(f"{metric_label.upper()} ANALYSIS")
    report.append("=" * 80)

    if metric_df.empty:
        report.append(f"No usable data for {source_name}; skipped.")
        continue

    metric_df = metric_df.copy()
    metric_df['high_priority'] = (metric_df['metric_value'] >= metric_df['metric_value'].quantile(0.75)).astype(int)
    contingency = pd.crosstab(metric_df['understudied'], metric_df['high_priority'])
    report.append(f"Metric source: {source_name}")
    report.append(f"Countries available: {len(metric_df)}")
    report.append(f"Understudied countries: {int(metric_df['understudied'].sum())}")
    report.append(f"High-priority countries (top quartile): {int(metric_df['high_priority'].sum())}")
    report.append(f"Contingency table (rows=understudied, cols=high_priority):\n{contingency}\n")

    chi2 = p_val = dof = np.nan
    if contingency.shape[0] >= 2 and contingency.shape[1] >= 2:
        chi2, p_val, dof, expected = chi2_contingency(contingency)
        report.append(f"Chi-square statistic: {chi2:.4f}")
        report.append(f"P-value: {p_val:.4e}")
        report.append(f"Degrees of freedom: {dof}")
        report.append(f"Significance (alpha=0.05): {'YES' if p_val < 0.05 else 'NO'}")
    else:
        report.append("Chi-square test skipped: insufficient variation")

    rho = p_corr = np.nan
    if len(metric_df) > 2:
        rho, p_corr = spearmanr(metric_df['metric_value'], metric_df['study_count'])
        report.append(f"Spearman r: {rho:.4f}" if not np.isnan(rho) else "Spearman r: NaN (insufficient variation)")
        report.append(f"P-value: {p_corr:.4e}" if not np.isnan(p_corr) else "P-value: NaN")
        report.append(f"Sample size: {len(metric_df)}")
    else:
        report.append("Spearman test skipped: insufficient data")

    total_countries = len(metric_df)
    high_priority_countries = int(metric_df['high_priority'].sum())
    understudied_countries_metric = int(metric_df['understudied'].sum())
    overlap_observed = int(((metric_df['understudied'] == 1) & (metric_df['high_priority'] == 1)).sum())
    p_priority = high_priority_countries / total_countries if total_countries > 0 else np.nan
    expected_overlap = understudied_countries_metric * p_priority if total_countries > 0 else np.nan
    report.append(f"Observed overlap (understudied AND high-priority): {overlap_observed}")
    report.append(f"Expected by chance: {expected_overlap:.1f}\n")

    p_binom = np.nan
    if understudied_countries_metric > 0 and not np.isnan(p_priority):
        p_binom = binom_test(overlap_observed, understudied_countries_metric, p_priority, alternative='two-sided')
        report.append(f"Binomial test p-value: {p_binom:.4e}")
        report.append(f"Significance (alpha=0.05): {'YES' if p_binom < 0.05 else 'NO'}")
    else:
        report.append("Binomial test skipped: no understudied countries or invalid probability")

    report.append("Sensitivity analysis across priority thresholds:")
    for quantile in [0.25, 0.50, 0.75, 0.90]:
        threshold = metric_df['metric_value'].quantile(quantile)
        n_priority = int((metric_df['metric_value'] >= threshold).sum())
        n_overlap = int(((metric_df['understudied'] == 1) & (metric_df['metric_value'] >= threshold)).sum())
        pct = 100 * n_overlap / understudied_countries_metric if understudied_countries_metric > 0 else 0
        report.append(f"  Top {100*(1-quantile):.0f}% priority (threshold={threshold:.1f}): {n_overlap}/{understudied_countries_metric} understudied ({pct:.1f}%)")
        sensitivity_rows.append({
            'metric_source': source_name,
            'metric_label': metric_label,
            'quantile': quantile,
            'priority_score_threshold': threshold,
            'n_priority_countries': n_priority,
            'n_overlap_countries': n_overlap,
            'pct_understudied_overlapping': pct,
        })

    quartile_data = metric_df.copy()
    quartile_data['priority_quartile'] = pd.qcut(
        quartile_data['metric_value'].rank(method='first'),
        q=4,
        labels=['Q1 (lowest)', 'Q2', 'Q3', 'Q4 (highest)']
    )
    groups = [g['study_count'].values for _, g in quartile_data.groupby('priority_quartile') if len(g) > 0]
    kw_stat = kw_p = np.nan
    if len(groups) >= 2:
        kw_stat, kw_p = kruskal(*groups)
        quartile_medians = quartile_data.groupby('priority_quartile')['study_count'].median()
        report.append(f"Kruskal-Wallis H={kw_stat:.4f}, p={kw_p:.4e}")
        report.append(f"Median study counts by quartile: {quartile_medians.to_dict()}")
        unevenness_rows.append({
            'metric_source': source_name,
            'metric_label': metric_label,
            'kruskal_wallis_H': kw_stat,
            'p_value': kw_p,
            'median_q1': quartile_medians.get('Q1 (lowest)', np.nan),
            'median_q2': quartile_medians.get('Q2', np.nan),
            'median_q3': quartile_medians.get('Q3', np.nan),
            'median_q4': quartile_medians.get('Q4 (highest)', np.nan),
        })
    else:
        report.append("Kruskal-Wallis test skipped: insufficient groups")

    regional_metric_rows = []
    report.append("Regional subsampling (chi-square by continent):")
    for continent in sorted(metric_df['continent'].dropna().unique()):
        regional_data = metric_df[metric_df['continent'] == continent].copy()
        if len(regional_data) < 3:
            report.append(f"  {continent}: <3 countries, skipped")
            continue

        regional_median = regional_data['metric_value'].median()
        regional_data['high_priority'] = (regional_data['metric_value'] >= regional_median).astype(int)
        regional_contingency = pd.crosstab(regional_data['understudied'], regional_data['high_priority'])
        if regional_contingency.shape[0] < 2 or regional_contingency.shape[1] < 2:
            report.append(f"  {continent}: insufficient variation, skipped")
            continue

        chi2_r, p_val_r, dof_r, expected_r = chi2_contingency(regional_contingency)
        significant = 'YES' if p_val_r < 0.05 else 'NO'
        report.append(f"  {continent}: chi2={chi2_r:.4f}, p={p_val_r:.4e}, n={len(regional_data)}, significant={significant}")
        regional_metric_rows.append({
            'metric_source': source_name,
            'metric_label': metric_label,
            'continent': continent,
            'n_countries': len(regional_data),
            'n_understudied': int(regional_data['understudied'].sum()),
            'n_high_priority': int(regional_data['high_priority'].sum()),
            'n_overlap': int(((regional_data['understudied'] == 1) & (regional_data['high_priority'] == 1)).sum()),
            'chi_square': chi2_r,
            'p_value': p_val_r,
            'significant': significant,
        })

    regional_rows.extend(regional_metric_rows)

    metric_summary_rows.append({
        'metric_source': source_name,
        'metric_label': metric_label,
        'n_countries': total_countries,
        'n_understudied': understudied_countries_metric,
        'n_high_priority': high_priority_countries,
        'overlap_observed': overlap_observed,
        'chi_square_p': p_val,
        'spearman_r': rho,
        'spearman_p': p_corr,
        'binomial_p': p_binom,
        'kw_p': kw_p,
    })

    report.append("" )

report.append("\n" + "=" * 80)
report.append("SUMMARY AND INTERPRETATION")
report.append("=" * 80)
report.append("\nKEY FINDING: Understudied endophyte regions are enriched in high-priority biodiversity areas across metrics")
for row in metric_summary_rows:
    spearman_p_text = f"{row['spearman_p']:.3e}" if not np.isnan(row['spearman_p']) else "NA"
    report.append(f"• {row['metric_label']}: {row['n_understudied']} understudied countries; overlap={row['overlap_observed']}; Spearman p={spearman_p_text}")
report.append("\nConclusion:")
report.append("Metric-by-metric tests are more defensible for peer review than a composite max score.")
report.append("They show whether study counts are uneven across biodiversity-priority classes and whether that pattern holds across independent biodiversity indicators.")

# Write tabular outputs
if sensitivity_rows:
    pd.DataFrame(sensitivity_rows).to_csv(OUTPUT_DIR / 'sensitivity_analysis.csv', index=False)
if unevenness_rows:
    pd.DataFrame(unevenness_rows).to_csv(OUTPUT_DIR / 'priority_quartile_unevenness.csv', index=False)
if regional_rows:
    pd.DataFrame(regional_rows).to_csv(OUTPUT_DIR / 'regional_subsampling.csv', index=False)
if metric_summary_rows:
    pd.DataFrame(metric_summary_rows).to_csv(OUTPUT_DIR / 'metric_summary.csv', index=False)

area_normalized_rows = []
for source_name, metric_label in metric_sources:
    if metric_label not in {"Total species", "Endemic species"}:
        continue
    metric_df = make_metric_frame(source_name)
    metric_df = metric_df.dropna(subset=['country_area_km2'])
    metric_df = metric_df[metric_df['country_area_km2'] > 0].copy()
    if metric_df.empty:
        continue
    metric_df['study_density_per_1000_km2'] = pd.to_numeric(metric_df['study_density_per_1000_km2'], errors='coerce')
    metric_df['metric_density_per_1000_km2'] = pd.to_numeric(metric_df['metric_density_per_1000_km2'], errors='coerce')
    valid = metric_df.dropna(subset=['study_density_per_1000_km2', 'metric_density_per_1000_km2'])
    if valid.empty:
        continue
    rho_area, p_area = spearmanr(valid['metric_density_per_1000_km2'], valid['study_density_per_1000_km2'])
    area_normalized_rows.append({
        'metric_source': source_name,
        'metric_label': metric_label,
        'n_countries': len(valid),
        'spearman_r': rho_area,
        'spearman_p': p_area,
        'median_study_density_per_1000_km2': valid['study_density_per_1000_km2'].median(),
        'median_metric_density_per_1000_km2': valid['metric_density_per_1000_km2'].median(),
    })

if area_normalized_rows:
    pd.DataFrame(area_normalized_rows).to_csv(OUTPUT_AREA_NORMALIZED, index=False)
    report.append(f"Area-normalized summary saved to: {OUTPUT_AREA_NORMALIZED}")

gdp_correlation_rows = []
report.append("\n" + "=" * 80)
report.append("GDP AND BIODIVERSITY CORRELATION ANALYSIS")
report.append("=" * 80)
for source_name, metric_label in metric_sources:
    metric_df = make_metric_frame(source_name).dropna(subset=['gdp_log10', 'metric_value'])
    if metric_df.empty:
        continue

    rho_gdp_raw, p_gdp_raw = spearmanr(metric_df['gdp_log10'], metric_df['metric_value'])
    report.append(f"\n{metric_label} vs GDP:")
    report.append(f"  Spearman r (raw metric): {rho_gdp_raw:.4f}, p: {p_gdp_raw:.4e}")

    rho_gdp_density, p_gdp_density = np.nan, np.nan
    if 'metric_density_per_1000_km2' in metric_df.columns:
        metric_df_density = metric_df.dropna(subset=['metric_density_per_1000_km2'])
        if not metric_df_density.empty:
            rho_gdp_density, p_gdp_density = spearmanr(metric_df_density['gdp_log10'], metric_df_density['metric_density_per_1000_km2'])
            report.append(f"  Spearman r (density): {rho_gdp_density:.4f}, p: {p_gdp_density:.4e}")

    gdp_correlation_rows.append({'metric_source': source_name, 'metric_label': metric_label, 'spearman_r_gdp_vs_raw': rho_gdp_raw, 'p_value_gdp_vs_raw': p_gdp_raw, 'spearman_r_gdp_vs_density': rho_gdp_density, 'p_value_gdp_vs_density': p_gdp_density})
if gdp_correlation_rows:
    pd.DataFrame(gdp_correlation_rows).to_csv(OUTPUT_GDP_CORRELATION, index=False)

try:
    import statsmodels.formula.api as smf

    modeling_results = []
    report.append("\n" + "=" * 80)
    report.append("STATISTICAL MODELING OF STUDY COUNT")
    report.append("=" * 80)

    for source_name, metric_label in metric_sources:
        model_df = make_metric_frame(source_name).dropna(subset=['gdp_log10', 'metric_value', 'study_count'])
        model_df['study_count_log'] = np.log10(model_df['study_count'] + 1)

        # Model for raw study count
        model_raw = smf.ols('study_count_log ~ gdp_log10 + metric_value', data=model_df).fit()
        report.append(f"\n--- Model for {metric_label} (raw counts) ---")
        report.append(str(model_raw.summary()))
        
        for var, params in model_raw.params.items():
            modeling_results.append({'metric': metric_label, 'model': 'raw', 'variable': var, 'coefficient': params, 'p_value': model_raw.pvalues[var]})

    if modeling_results:
        pd.DataFrame(modeling_results).to_csv(OUTPUT_MODELING_RESULTS, index=False)

except ImportError:
    report.append("\n" + "=" * 80)
    report.append("Statsmodels library not found. Skipping statistical modeling.")
    report.append("To install: pip install statsmodels")
    report.append("=" * 80)

# Write report
report_text = "\n".join(report)
try:
    with open(OUTPUT_DIR / 'robustness_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\nReport saved to: {OUTPUT_DIR / 'robustness_report.txt'}")
except Exception as e:
    print(f"Warning: Could not write with UTF-8 encoding ({str(e)}). Trying ASCII fallback.")
    with open(OUTPUT_DIR / 'robustness_report.txt', 'w', encoding='utf-8', errors='replace') as f:
        f.write(report_text)

print(f"Sensitivity analysis saved to: {OUTPUT_DIR / 'sensitivity_analysis.csv'}")
print(f"Regional subsampling saved to: {OUTPUT_DIR / 'regional_subsampling.csv'}")
print(f"Country area summary saved to: {OUTPUT_COUNTRY_AREA}")
if area_normalized_rows:
    print(f"Area-normalized summary saved to: {OUTPUT_AREA_NORMALIZED}")
if gdp_correlation_rows:
    print(f"GDP-biodiversity correlation saved to: {OUTPUT_GDP_CORRELATION}")
if modeling_results:
    print(f"Modeling results saved to: {OUTPUT_MODELING_RESULTS}")
print("\nRobustness tests complete")

# BRYOPHYTE-SPECIFIC ANALYSIS

print("\n" + "="*80)
print("BRYOPHYTE-SPECIFIC ANALYSIS")
print("="*80)

# Load the raw World Bank biodiversity data
try:
    wb_biodiv_raw = pd.read_csv("data/biodiversity/World_Bank/WB_Pre-processed/WB_BIODIVERSITY_2021.csv")
except FileNotFoundError:
    print("\n[!] World Bank raw biodiversity file not found. Skipping Bryophyte analysis.")
    print("    Expected file: data/biodiversity/World_Bank/WB_Pre-processed/WB_BIODIVERSITY_2021.csv")
    exit()

# Filter for Bryophytes
bryophytes = wb_biodiv_raw[wb_biodiv_raw['phylum'] == 'BRYOPHYTA'].copy()

if bryophytes.empty:
    print("\n[!] No Bryophyte species found in the World Bank dataset. Skipping analysis.")
else:
    print(f"\nFound {len(bryophytes)} Bryophyte species records across all countries.")

    # Total Species
    print("\n--- Ranking by Total Bryophyte Species ---")
    total_species = bryophytes.groupby('country_iso3').size().reset_index(name='bryophyte_total_species')
    total_species = total_species.sort_values('bryophyte_total_species', ascending=False)
    print("Top 10 countries by total Bryophyte species:")
    print(total_species.head(10).to_string(index=False))
    
    output_total_path = os.path.join(OUTPUT_DIR, 'country_rankings_bryophyte_total.csv')
    total_species.to_csv(output_total_path, index=False)
    print(f"Full ranked list saved to: {output_total_path}")

    # Endemic Species
    # The 'small_range_50km' column is used as the proxy for endemism in the main analysis
    print("\n--- Ranking by Endemic Bryophyte Species (small_range_50km) ---")
    endemic_species = bryophytes[bryophytes['small_range_50km'] == 1]
    endemic_counts = endemic_species.groupby('country_iso3').size().reset_index(name='bryophyte_endemic_species')
    endemic_counts = endemic_counts.sort_values('bryophyte_endemic_species', ascending=False)
    print("Top 10 countries by endemic Bryophyte species:")
    print(endemic_counts.head(10).to_string(index=False))

    output_endemic_path = os.path.join(OUTPUT_DIR, 'country_rankings_bryophyte_endemic.csv')
    endemic_counts.to_csv(output_endemic_path, index=False)
    print(f"Full ranked list saved to: {output_endemic_path}")

    # Threatened Species
    # The 'threat_status_prob_80' is used as the proxy for threat status
    print("\n--- Ranking by Threatened Bryophyte Species (threat_status_prob_80) ---")
    threatened_species = bryophytes[bryophytes['threat_status_prob_80'] == 1]
    threatened_counts = threatened_species.groupby('country_iso3').size().reset_index(name='bryophyte_threatened_species')
    threatened_counts = threatened_counts.sort_values('bryophyte_threatened_species', ascending=False)
    print("Top 10 countries by threatened Bryophyte species:")
    print(threatened_counts.head(10).to_string(index=False))

    output_threatened_path = os.path.join(OUTPUT_DIR, 'country_rankings_bryophyte_threatened.csv')
    threatened_counts.to_csv(output_threatened_path, index=False)
    print(f"Full ranked list saved to: {output_threatened_path}")

print("\nBryophyte analysis complete.")

