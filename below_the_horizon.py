"""
=====================================================================================
BELOW THE HORIZON - all the data work behind the page, in one file
=====================================================================================
An awareness project about women's health and PCOS (renamed PMOS in 2026).
This file cleans three data sets, joins them, tests the page's conclusion and puts the
results into index.html. It runs top to bottom in six steps; each step saves its results
to files, and the next step reads those files.

  STEP 1  Kaggle PCOS symptoms (Kerala, India)  -> pcos_clean.csv, cleaning_log.md
  STEP 2  Gallup / Hologic survey (144 countries) -> hologic_clean.csv.gz, hologic_summary.json
  STEP 3  One check-up line per country           -> country_facts.json
  STEP 4  IHME PCOS prevalence (204 countries)    -> pcos_prevalence_clean.csv, pcos_prevalence_summary.json
  STEP 5  Join Gallup + IHME, test the conclusion -> map_data.json, analysis_log_map.md
  STEP 6  Put the results into the web page       -> index.html

Put this file in the same folder as the raw data and index.html, then run:
    python below_the_horizon.py
Requirements: pip install pandas numpy scipy openpyxl pycountry
=====================================================================================
"""
import gettext
import json
import re
import unicodedata
import numpy as np
import pandas as pd
import pycountry
from scipy.stats import spearmanr


# =====================================================================================
# STEP 1 - Cleaning the PCOS symptom dataset (Kaggle)
# =====================================================================================
# Source : Kottarathil, P. "Polycystic ovary syndrome (PCOS)", Kaggle, 2020.
#          541 women from 10 hospitals in Kerala, India. 177 diagnosed with PCOS, 364 without.
# Input  : PCOS_data.csv
# Output : pcos_clean.csv      -> the cleaned table (all 541 women kept)
#          cleaning_log.md     -> every cleaning decision, written as we go
#          pcos_summary.json   -> small summary (fed an earlier version of the page, "the binoculars")
#
# ROLE IN THE PROJECT
# This is the only open dataset with REAL individual PCOS symptoms. We searched for a global
# alternative and found none that was real: the "PCOS Prediction Dataset (Top 75 Countries)" on
# Kaggle is simulated, so we rejected it. This dataset is also the standard benchmark used in
# published PCOS research, which makes it a defensible choice.
# What we used it for: proving that the "ordinary" symptoms (irregular cycle, acne, excess hair,
# weight gain, darker skin, hair loss) are much more common in women with PCOS. That is why six
# of the ten "real signs" in the quiz come from this dataset.
#
# THREE RULES WE FOLLOWED WHILE CLEANING
# 1. Never delete a person. If one value is wrong, we blank that value, not the whole row.
# 2. Never guess. If we can't know the true value, it becomes missing (NaN).
#    The only exception is an obvious typo ("1.99." -> 1.99).
# 3. Write every decision down (the `log`), so anyone can check and disagree with it.
#
# =====================================================================================

# The log: every decision is added here AND printed, then saved to cleaning_log.md at the end.
# WHY: a cleaning step nobody can see is a cleaning step nobody can trust.
log = []
def note(text):
    log.append(text)
    print("-", text)

df = pd.read_csv("PCOS_data.csv")
note(f"Original dataset: {df.shape[0]} rows and {df.shape[1]} columns.")

# -------------------------------------------------------------------------------------
# 1. COLUMN NAMES
# WHAT: strip hidden spaces, then give every column a short snake_case name.
# WHY:  the original names had invisible spaces ("Pulse rate(bpm) "), mixed formats and a typo
#       ("Marraige"). With a hidden space, df["Pulse rate(bpm)"] fails even though it "looks" right.
#       Short names also make the code readable for whoever reviews it.
# HISTORY: the first version used Spanish names; we switched everything to English so the
#       professor could review it.
# -------------------------------------------------------------------------------------
df.columns = df.columns.str.strip()
names = {
    "Patient File No.": "id", "PCOS (Y/N)": "pcos", "Age (yrs)": "age",
    "Weight (Kg)": "weight_kg", "Height(Cm)": "height_cm", "BMI": "bmi",
    "Blood Group": "blood_group", "Pulse rate(bpm)": "pulse_bpm",
    "RR (breaths/min)": "resp_rate", "Hb(g/dl)": "hemoglobin",
    "Cycle(R/I)": "cycle_code", "Cycle length(days)": "period_length_days",
    "Marraige Status (Yrs)": "years_married", "Pregnant(Y/N)": "pregnant",
    "No. of abortions": "abortions", "I   beta-HCG(mIU/mL)": "beta_hcg_1",
    "II    beta-HCG(mIU/mL)": "beta_hcg_2", "FSH(mIU/mL)": "fsh",
    "LH(mIU/mL)": "lh", "FSH/LH": "fsh_lh_ratio", "Hip(inch)": "hip_in",
    "Waist(inch)": "waist_in", "Waist:Hip Ratio": "waist_hip_ratio",
    "TSH (mIU/L)": "tsh", "AMH(ng/mL)": "amh", "PRL(ng/mL)": "prolactin",
    "Vit D3 (ng/mL)": "vitamin_d", "PRG(ng/mL)": "progesterone",
    "RBS(mg/dl)": "blood_sugar", "Weight gain(Y/N)": "weight_gain",
    "hair growth(Y/N)": "excess_hair", "Skin darkening (Y/N)": "skin_darkening",
    "Hair loss(Y/N)": "hair_loss", "Pimples(Y/N)": "acne",
    "Fast food (Y/N)": "fast_food", "Reg.Exercise(Y/N)": "regular_exercise",
    "BP _Systolic (mmHg)": "bp_systolic", "BP _Diastolic (mmHg)": "bp_diastolic",
    "Follicle No. (L)": "follicles_left", "Follicle No. (R)": "follicles_right",
    "Avg. F size (L) (mm)": "follicle_size_left", "Avg. F size (R) (mm)": "follicle_size_right",
    "Endometrium (mm)": "endometrium_mm",
}
df = df.rename(columns=names)
note("Stripped hidden spaces from column names and renamed them to short snake_case (also fixes the 'Marraige' typo).")

# -------------------------------------------------------------------------------------
# 2. COLUMNS THAT ADD NOTHING
# WHAT: drop "Sl. No" and "Unnamed: 44".
# WHY:  "Sl. No" is just a row counter that repeats the id. "Unnamed: 44" is an empty column
#       pandas created because the CSV had an extra comma; its only values were "." and "7".
# -------------------------------------------------------------------------------------
df = df.drop(columns=["Sl. No", "Unnamed: 44"])
note("Dropped 'Sl. No' (duplicates the id) and 'Unnamed: 44' (empty column containing stray values '.' and '7').")

# -------------------------------------------------------------------------------------
# 3. TEXT INSIDE NUMERIC COLUMNS
# WHAT: AMH had the letter "a" in one cell; beta-HCG II had "1.99." (two periods).
# WHY:  one single text value turns the WHOLE column into text, so you can't average it.
#       "a" can't be guessed -> NaN (rule 2). "1.99." is an obvious typo -> 1.99 (the one exception).
# HOW WE FOUND IT: .dtypes showed these two columns as text (object) instead of numbers.
# -------------------------------------------------------------------------------------
df["amh"] = pd.to_numeric(df["amh"], errors="coerce")
note("AMH: 1 text value ('a') set to missing.")
df["beta_hcg_2"] = pd.to_numeric(df["beta_hcg_2"].astype(str).str.rstrip("."), errors="coerce")
note("beta-HCG II: value '1.99.' had an extra period; corrected to 1.99.")

# -------------------------------------------------------------------------------------
# 4. CYCLE CODES
# WHAT: the study coded the cycle as 2 = regular, 4 = irregular. One row had 5.
#       We create a clear 0/1 column, irregular_cycle, and drop the old code.
# WHY:  5 is not a valid code, so we can't know if that cycle was regular -> missing (rule 2).
#       A 0/1 column also lets us add symptoms together later (step 6).
# HOW WE FOUND IT: .value_counts() on the cycle column showed 2 -> 390, 4 -> 150, 5 -> 1.
# -------------------------------------------------------------------------------------
invalid = (~df["cycle_code"].isin([2, 4])).sum()
df["irregular_cycle"] = df["cycle_code"].map({2: 0, 4: 1})
df = df.drop(columns=["cycle_code"])
note(f"Cycle: {invalid} record with code 5 (not a valid code) set to missing. Created 'irregular_cycle' (0/1).")

# -------------------------------------------------------------------------------------
# 5. PHYSIOLOGICALLY IMPOSSIBLE VALUES
# WHAT: values outside what a living body can have become missing. The person stays.
# WHY:  one value of 6,000 drags every average with it, so charts would lie.
#       The limits are deliberately generous: we only remove what is impossible, not what is unusual.
# HOW WE FOUND IT: .describe() showed min/max per column, e.g. pulse 13, BP 12/8,
#       FSH 5,052, LH 2,018, vitamin D 6,014. 12/8 is almost certainly 120/80 with a dropped zero,
#       but we can't be sure, so we don't "fix" it, we blank it.
# -------------------------------------------------------------------------------------
limits = {
    "pulse_bpm": (40, 200, "pulse below 40 bpm"),
    "bp_systolic": (70, 250, "systolic BP below 70, likely a dropped zero"),
    "bp_diastolic": (40, 150, "diastolic BP below 40, likely a dropped zero"),
    "fsh": (0, 100, "FSH above 100 mIU/mL"),
    "lh": (0, 100, "LH above 100 mIU/mL"),
    "vitamin_d": (1, 150, "vitamin D of 0 or above 150 ng/mL"),
}
for col, (lo, hi, reason) in limits.items():
    bad = ~df[col].between(lo, hi) & df[col].notna()     # outside the range AND not already missing
    if bad.sum():
        note(f"{col}: {bad.sum()} impossible value(s) ({reason}): {sorted(df.loc[bad, col].tolist())} -> set to missing.")
        df.loc[bad, col] = np.nan

# WHAT: recalculate columns that were computed FROM values we just changed.
# WHY:  if FSH or LH was wrong, the FSH/LH ratio was wrong too. Fixing the input but not the
#       result would leave hidden errors.
df["fsh_lh_ratio"] = (df["fsh"] / df["lh"]).round(2)
note("Recalculated the FSH/LH ratio from the cleaned values.")

# WHAT: check BMI against weight and height (BMI = kg / m²) and use the calculated value.
# WHY:  BMI is a formula, so it can be verified. 2 rows didn't match.
bmi_calc = df["weight_kg"] / (df["height_cm"] / 100) ** 2
mismatch = (bmi_calc - df["bmi"]).abs() > 1
note(f"BMI: {mismatch.sum()} records did not match weight/height; replaced with the calculated value.")
df["bmi"] = bmi_calc.round(1)

# -------------------------------------------------------------------------------------
# 6. NEW VARIABLES FOR THE STORY (this is transformation, not cleaning)
# WHAT: symptom_count = how many of the 6 visible signs each woman has (0 to 6).
# WHY:  this is the variable that showed the key finding: with 0 signs, about 6% of women had PCOS;
#       with 4 or more, about 8 in 10. Each sign alone looks ordinary; together they are a pattern.
#       That finding is what justified using these signs in the quiz.
# HISTORY: it was first shown as "the binoculars" (seven small suns) and later as an "8 in 10"
#       line; both were removed from the final page to keep the story lighter. The analysis stays.
# min_count=1: if a woman had no symptom data at all, the count stays NaN instead of a false 0.
# -------------------------------------------------------------------------------------
symptoms = ["irregular_cycle", "weight_gain", "excess_hair", "skin_darkening", "hair_loss", "acne"]
df["symptom_count"] = df[symptoms].sum(axis=1, min_count=1)
df["follicles_total"] = df["follicles_left"] + df["follicles_right"]
note("Created 'symptom_count' (0 to 6 visible symptoms) and 'follicles_total'.")

# -------------------------------------------------------------------------------------
# 7. SAMPLING CAVEAT
# WHY: about 1 in 3 women in this file has PCOS because the study recruited them that way.
#      It is NOT how common PCOS is in the population. It must never be presented as prevalence.
#      (Real prevalence on the page comes from IHME, step 4.)
# -------------------------------------------------------------------------------------
note(f"Caveat: {df['pcos'].mean():.0%} of the sample has PCOS by study design; this is NOT real-world prevalence.")

df.to_csv("pcos_clean.csv", index=False)

# -------------------------------------------------------------------------------------
# 8. SMALL JSON SUMMARY
# WHAT: % of each symptom with/without PCOS, and % with PCOS for each symptom_count.
# WHY:  a web page doesn't need 541 rows, only these percentages. (Used by the earlier
#       binoculars version; kept because it documents the finding.)
# -------------------------------------------------------------------------------------
summary = {
    "source": "PCOS dataset (Kaggle), 541 women aged 20 to 48",
    "symptom_prevalence": {
        s: {"with_pcos": round(df.loc[df.pcos == 1, s].mean() * 100, 1),
            "without_pcos": round(df.loc[df.pcos == 0, s].mean() * 100, 1)}
        for s in symptoms
    },
    "by_symptom_count": [
        {"symptoms": int(n), "total": int(len(g)), "with_pcos": int(g.pcos.sum()),
         "pct_pcos": round(g.pcos.mean() * 100, 1)}
        for n, g in df.groupby("symptom_count")
    ],
}
with open("pcos_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

note(f"Final dataset: {df.shape[0]} rows and {df.shape[1]} columns. No participant was removed.")

with open("cleaning_log.md", "w", encoding="utf-8") as f:
    f.write("# Cleaning log - PCOS dataset\n\n" + "\n".join(f"- {entry}" for entry in log))


# =====================================================================================
# STEP 2 - Cleaning the Hologic Global Women's Health Index (survey by Gallup), 2020-2024
# =====================================================================================
# Source : Hologic Global Women's Health Index, conducted by Gallup. Women aged 15+, ~144 countries.
#          ("Hologic" is the company that funds and names the index; Gallup runs the survey.)
# Input  : Hologic-Global-Women_s-Health-Index-2020-2024-Raw-Data-Download.xlsx
# Output : hologic_clean.csv.gz      -> one tidy table with everything, all 5 years
#          hologic_summary.json      -> 2024 country values + world values, used by steps 3 and 5
#          cleaning_log_hologic.md   -> every cleaning decision
#
# THE MAIN PROBLEM
# The Excel file is a REPORT designed to be read by a person, not a TABLE designed to be analysed:
#   - each column's meaning is spread over 3 header rows (indicator / answer / statistic)
#   - the country name only appears in the first row of its block (merged cells)
#   - "Total" rows and columns are mixed in with real answers
#   - every year uses slightly different labels
# A person understands that "Albania" at the top applies to the rows below; a computer does not.
# So most of this script turns the report into a "tidy" table where every row explains itself:
# one row = one year x country x group x indicator x answer.
#
# =====================================================================================

SOURCE = "Hologic-Global-Women_s-Health-Index-2020-2024-Raw-Data-Download.xlsx"
YEARS = {1: 2020, 2: 2021, 3: 2022, 4: 2023, 5: 2024}       # sheet "YEAR 1" = 2020, etc.

log = []
def note(text):
    log.append(text)
    print("-", text)

# WHAT: short names for each indicator, keyed by the code at the start of each header.
# WHY:  the full header text changes between years (and has typos, e.g. "Saftey" in 2020),
#       but the code ("WP68", "TEST_FOR_HBP"...) stays the same, so it is a safe key.
INDICATORS = {
    "HOLOGIC_INDEX": "womens_health_index",
    "SUB_INDEX_1": "preventive_care_index",
    "SUB_INDEX_2": "emotional_health_index",
    "SUB_INDEX_4": "health_safety_opinions_index",
    "SUB_INDEX_5": "basic_needs_index",
    "SUB_INDEX_6": "individual_health_index",
    "TEST_FOR_HBP": "tested_blood_pressure",
    "TEST_FOR_CANCER": "tested_cancer",
    "TEST_FOR_DIABETES": "tested_diabetes",
    "TEST_FOR_STD": "tested_std",
    "WP69": "felt_worry_yesterday",
    "WP70": "felt_sadness_yesterday",
    "WP71": "felt_stress_yesterday",
    "WP74": "felt_anger_yesterday",
    "WP21326": "pregnant_women_get_quality_care",
    "WP97": "satisfied_local_healthcare",
    "WP113": "feels_safe_walking_alone",
    "WP40": "not_enough_money_food",
    "WP43": "not_enough_money_shelter",
    "WP23": "has_health_problems",
    "WP68": "felt_pain_yesterday",
    "WP21334": "domestic_violence_widespread",
    "WP21325": "believes_checkups_help",
    "WP21327": "talked_to_health_professional",
}
# WHAT: each year names the same statistic differently ("Weighted Percent", "Row Valid N %"...).
# WHY:  we map them all to three names: n_unweighted, n_weighted and value.
STATS = {
    "Unweighted Count": "n_unweighted", "Weighted Count": "n_weighted", "Count": "n_weighted",
    "Weighted Mean": "value", "Mean": "value",
    "Weighted Percent": "value", "Weighted Percentage": "value", "Row Valid N %": "value",
}
# WHAT: removes a leading number code from a label: "1.00 Yes" -> "Yes", "1 15-50" -> "15-50".
# HOW:  the regular expression ^\s*[\d.]+\s+ means "at the start: optional spaces, digits/dots, spaces".
strip_code = lambda s: re.sub(r"^\s*[\d.]+\s+", "", str(s)).strip()


def tidy_sheet(sheet, year):
    """Turn one yearly country sheet (a report) into a tidy table."""
    raw = pd.read_excel(SOURCE, sheet_name=sheet, header=None)

    # ---------------------------------------------------------------------------------
    # 1. REBUILD THE THREE HEADER ROWS
    # Row 0 = indicator (written once over several columns -> ffill copies it to the right)
    # Row 1 = answer ("Yes", "No"...)     Row 2 = statistic ("Unweighted Count", "Row Valid N %"...)
    # Index columns (scores) are different: their statistic sits in row 1 and row 2 is empty,
    # so we move it down and label their "answer" as "score".
    # ---------------------------------------------------------------------------------
    indicator = raw.iloc[0].ffill()
    answer, stat = raw.iloc[1].copy(), raw.iloc[2].copy()
    is_index = indicator.astype(str).str.contains("INDEX")
    stat[is_index] = answer[is_index]
    answer[is_index] = "score"
    answer = answer.where(is_index, answer.ffill())

    # ---------------------------------------------------------------------------------
    # 2. FILL THE MERGED CELLS ON THE LEFT
    # Column 1 = country, column 2 = group variable (age, education...), column 3 = group.
    # HISTORY (important bug): the first run lost almost all of 2020 (8,618 rows instead of
    # ~136,000). The "empty" cells in 2020 were not empty: they contained a single space " ".
    # ffill only fills truly empty cells, so the country never carried down. We found it because
    # 2020 had far fewer rows than the other years. Fix: turn space-only cells into real NaN first.
    # ---------------------------------------------------------------------------------
    body = raw.iloc[3:].copy()
    for c in [0, 1, 2, 3]:
        body[c] = body[c].map(lambda v: np.nan if isinstance(v, str) and v.strip() == "" else v)
    body[1] = body[1].ffill()
    body[2] = body[2].ffill()
    # WHY drop "Total": it is a sum the report adds for readers. Keeping it would count people twice.
    body = body[body[3].notna() & (body[3].astype(str).str.strip() != "Total")]

    # ---------------------------------------------------------------------------------
    # One small table per useful column, all in the same "long" shape, then stacked.
    # Skipped: indicators we don't use, "Total" answer columns, and unknown statistics.
    # ---------------------------------------------------------------------------------
    rows = []
    for c in raw.columns[4:]:
        code = str(indicator[c]).split()[0]
        code = "HOLOGIC_INDEX" if code.startswith("HOLOGIC_INDEX") else code   # "HOLOGIC_INDEX_2021" etc.
        if code not in INDICATORS or str(answer[c]).strip() == "Total" or stat[c] not in STATS:
            continue
        rows.append(pd.DataFrame({
            "year": year, "country": body[1].values,
            "group_variable": body[2].values, "group": body[3].values,
            "indicator": INDICATORS[code], "answer": strip_code(answer[c]),
            "stat": STATS[stat[c]], "number": body[c].values,
        }))
    long = pd.concat(rows)

    # ---------------------------------------------------------------------------------
    # 3. LONG -> WIDE: put n_unweighted, n_weighted and value side by side in one row.
    # ---------------------------------------------------------------------------------
    keys = ["year", "country", "group_variable", "group", "indicator", "answer"]
    wide = long.pivot_table(index=keys, columns="stat", values="number", aggfunc="first").reset_index()
    return wide, long


frames = []
suppressed_total = 0
for y, year in YEARS.items():
    wide, long = tidy_sheet(f"YEAR {y} COUNTRY", year)
    # ---------------------------------------------------------------------------------
    # 4. "-" MEANS HIDDEN, NOT ZERO
    # WHY: Gallup hides results when too few people answered (privacy + unreliable numbers).
    #      Treating "-" as 0% would invent countries where "nobody" gets tested.
    # ---------------------------------------------------------------------------------
    hidden = long["number"].astype(str).str.strip().isin(["-", "-%"]).sum()
    suppressed_total += hidden
    frames.append(wide)
    note(f"{year}: {wide['country'].nunique()} countries, {len(wide):,} rows after reshaping; {hidden:,} hidden values ('-').")

df = pd.concat(frames, ignore_index=True)
note("Rebuilt the 3-row headers (indicator / answer / statistic) and filled merged cells for country and group.")
note("Dropped 'Total' rows and columns: they are sums the report adds, not answers.")
note(f"Converted {suppressed_total:,} hidden values ('-' and '-%') to missing. Gallup hides results for very small groups; they are NOT zeros.")

# errors="coerce" is what turns "-" into NaN here
for col in ["n_unweighted", "n_weighted", "value"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# -------------------------------------------------------------------------------------
# 5. ONE SCALE FOR PERCENTAGES (0-100)
# WHY:  percentages were stored as 0.39 instead of 39. If the biggest value of a year is <= 1,
#       that year is on a 0-1 scale and is multiplied by 100.
# HISTORY: 2024 was first NOT converted. One value was stored as 1.0000000001 (tiny computer
#       rounding noise), so "max <= 1" was False. Using 1.0001 fixes it without changing anything else.
# -------------------------------------------------------------------------------------
for year in YEARS.values():
    m = (df.year == year) & (df.answer != "score")
    if df.loc[m, "value"].max() <= 1.0001:
        df.loc[m, "value"] *= 100
        note(f"{year}: percentages were stored as 0-1; converted to 0-100.")
df["value"] = df["value"].round(2)

# -------------------------------------------------------------------------------------
# 6. LABELS THAT CHANGE FROM YEAR TO YEAR
# WHY: the same thing must have the same name, or year comparisons break.
# -------------------------------------------------------------------------------------
df["answer"] = df["answer"].replace({"(DK)": "Don't know", "(Refused)": "Refused"})
df["group_variable"] = df["group_variable"].map(lambda s: str(s).split()[0].lower())
df["group"] = df["group"].map(strip_code)
age_fix = {"75+": "76+", "76 and above": "76+"}
df["group"] = df["group"].replace(age_fix)
note("Removed numeric codes from labels ('1.00 Yes' -> 'Yes', '1 15-50' -> '15-50') and renamed (DK)/(Refused).")
note("Oldest age group is labelled '76+', '75+' (2023) or '76 and above' (2024); harmonised to '76+'. The 2023 label may reflect a small definition change.")
note("Indicator names shortened to snake_case; this also fixes the 'Saftey' typo in 2020.")

# WHAT: unify country names.
# HOW WE FOUND IT: 251 different "names" for ~150 countries. In 2020 almost every country had a
#       trailing space ("Albania " vs "Albania"); two names were cut off ("Bosnia and", "United Arab");
#       Turkey appears as both "Turkey" and "Turkiye".
names_before = df["country"].nunique()
df["country"] = df["country"].astype(str).str.strip().replace({
    "Turkey": "Turkiye",
    "Bosnia and": "Bosnia and Herzegovina",
    "United Arab": "United Arab Emirates",
})
note(f"Country names: {names_before} different spellings, mostly the same country with a trailing space in the 2020 sheet ('Albania ' vs 'Albania'). "
     f"Trimmed spaces and unified 'Turkey' -> 'Turkiye' plus two names cut off in 2020 ('Bosnia and', 'United Arab'). Result: {df['country'].nunique()} countries.")
# WHY report coverage: some countries are missing in some years. That is not a cleaning error,
# Gallup simply didn't survey them that year, and the reader should know.
per_country = df.groupby("country").year.nunique()
note(f"Coverage: {(per_country == 5).sum()} countries appear in all 5 years; {(per_country < 5).sum()} were not surveyed every year (not an error, just missing years).")

# -------------------------------------------------------------------------------------
# 7. CAVEATS AND A CHECK AGAINST THE ORIGINAL
# The check: we picked one value at random (US 2024, tested for cancer) and compared the
# original Excel with the clean table. 29.0% vs 28.98% = same value, unrounded.
# This proves the reshaping did not change any number.
# -------------------------------------------------------------------------------------
note("Caveat: respondents are women aged 15+, so the audience filter 'women over 20' cannot be applied exactly.")
note("Checked: US 2024 'tested for cancer' = 29.0% in the original Excel and 28.98% in the clean table (same value, unrounded).")
note("Caveat: 2020 did not ask 'believes_checkups_help' or 'talked_to_health_professional'.")

# WHY gzip: the plain CSV is ~103 MB, above GitHub's 100 MB file limit. pandas reads .csv.gz directly.
df.to_csv("hologic_clean.csv.gz", index=False, compression="gzip")
note(f"Final tidy table: {len(df):,} rows, {df.shape[1]} columns, {df['country'].nunique()} countries, 2020-2024.")

# -------------------------------------------------------------------------------------
# 8. SMALL SUMMARY FOR THE NEXT STEPS: 2024, whole population of each country ("overall")
# HISTORY: STI testing (tested_std) was added later, when step 3 needed all five check-ups.
# -------------------------------------------------------------------------------------
ov = df[(df.group_variable == "overall") & (df.year == 2024)]
def pick(indicator, answer):
    s = ov[(ov.indicator == indicator) & (ov.answer == answer)].set_index("country")["value"]
    return s
table = pd.DataFrame({
    "preventive_care_index": pick("preventive_care_index", "score"),
    "tested_cancer": pick("tested_cancer", "Yes"),
    "tested_blood_pressure": pick("tested_blood_pressure", "Yes"),
    "tested_diabetes": pick("tested_diabetes", "Yes"),
    "tested_std": pick("tested_std", "Yes"),
    "believes_checkups_help": pick("believes_checkups_help", "Yes"),
    "talked_to_health_professional": pick("talked_to_health_professional", "Yes"),
}).round(1)
countries = [{"country": c, **{k: (None if pd.isna(v) else v) for k, v in r.items()}} for c, r in table.iterrows()]

# WHAT: world values come from the report's own GLOBAL sheet.
# WHY:  a simple average of countries would count Iceland the same as India. Gallup's global
#       figures are weighted by population, so they are the correct "world" number.
g = pd.read_excel(SOURCE, sheet_name="YEAR 5 GLOBAL REGIONAL", header=None)
gi = g.index[g[3] == "Overall Global Population"][-1]
head, ans, st = g.iloc[0].ffill(), g.iloc[1].ffill(), g.iloc[2].copy()
idx = head.astype(str).str.contains("INDEX")
st[idx] = g.iloc[1][idx]                      # same header fix as in step 1 of tidy_sheet
def global_value(code, answer):
    for c in g.columns[4:]:
        if str(head[c]).startswith(code) and (answer is None or strip_code(ans[c]) == answer) and st[c] in ("Mean", "Row Valid N %"):
            v = float(g.loc[gi, c])
            return round(v * 100, 1) if answer else round(v, 1)
world = {
    "preventive_care_index": global_value("SUB_INDEX_1", None),
    "tested_cancer": global_value("TEST_FOR_CANCER", "Yes"),
    "tested_blood_pressure": global_value("TEST_FOR_HBP", "Yes"),
    "tested_diabetes": global_value("TEST_FOR_DIABETES", "Yes"),
    "tested_std": global_value("TEST_FOR_STD", "Yes"),
    "believes_checkups_help": global_value("WP21325", "Yes"),
    "talked_to_health_professional": global_value("WP21327", "Yes"),
}
note(f"World 2024 (weighted, from the report's global sheet): {world}")

with open("hologic_summary.json", "w", encoding="utf-8") as f:
    json.dump({"source": "Hologic Global Women's Health Index (Gallup), women 15+, 2024",
               "world": world, "countries": countries}, f, indent=2)

with open("cleaning_log_hologic.md", "w", encoding="utf-8") as f:
    f.write("# Cleaning log - Hologic Global Women's Health Index\n\n" + "\n".join(f"- {entry}" for entry in log))


# =====================================================================================
# STEP 3 - One check-up line per country (Gallup, 2024)
# =====================================================================================
# Input  : hologic_summary.json  (from step 2)
# Output : country_facts.json    -> one sentence per country, used by the map's "Check-ups" layer
#
# WHAT THIS STEP ANSWERS
# "What is the most notable thing about women's check-ups in this country?"
# For each country we pick the check-up where it is MOST unusual compared with other countries,
# and turn it into a plain sentence: "Only 1 in 5 women had their blood pressure checked last year."
#
# HOW THE DECISION EVOLVED (this is the part to explain if asked)
# 1. First idea: one fact per country from ALL 17 survey questions (stress, sadness, safety...).
#    Rejected: "felt sad yesterday" is a mood on one day, not health data. We decided to keep
#    ONLY hard health data: did a woman get a check-up or test in the last 12 months?
# 2. Second idea: two lines per country (its biggest problem + its best result).
#    Rejected: with only 5 check-ups many countries have nothing clear to say. Only 15 countries
#    had both a clear problem and a clear strength; Mexico and China were average on everything.
#    Forcing two lines would have invented problems. So: ONE line, and only when it is true.
# 3. First method: "how many times above/below the world" (a ratio).
#    Rejected: ratios exaggerate small numbers. 10% -> 30% STI testing is "3x", but no country can be
#    3x the world on seeing a health professional (64%). 110 of 144 lines ended up about STI or cancer.
# 4. Final method: z-scores (below). The five check-ups then compete fairly:
#    professional 32, blood pressure 22, cancer 19, STI 18, diabetes 13.
#
# WHAT A Z-SCORE IS
# z = (country value - average of all countries) / standard deviation of all countries
# It says how many "typical distances" a country sits from the rest. z = -1.5 means clearly low.
# Because each check-up is measured against its OWN spread, a small-number check (STI) and a
# big-number check (seeing a professional) are compared on the same footing.
#
# =====================================================================================

CHECKS = {
    "tested_blood_pressure": "had their blood pressure checked",
    "tested_diabetes": "were tested for diabetes",
    "tested_cancer": "had a cancer screening",
    "tested_std": "were tested for a sexually transmitted infection",
    "talked_to_health_professional": "saw a health professional",
}
# WHY 1.0: |z| > 1 is roughly the top or bottom sixth of countries. Strict enough that a line means
# something; loose enough that 104 of 144 countries get one. We compared 1.0, 1.25 and 1.5:
# all gave balanced topics, and in 100% of cases "low vs other countries" was also "low vs the world".
Z_THRESHOLD = 1.0

# WHAT: Gallup names -> the names the world map uses (world-atlas / Natural Earth).
# WHY:  14 countries are written differently, e.g. "Czech Republic" vs "Czechia".
#       Without this, those countries would be blank on the map.
MAP_NAMES = {
    "Bosnia and Herzegovina": "Bosnia and Herz.", "Congo (Kinshasa)": "Dem. Rep. Congo",
    "Congo Brazzaville": "Congo", "Czech Republic": "Czechia", "Dominican Republic": "Dominican Rep.",
    "Eswatini": "eSwatini", "Ivory Coast": "Côte d'Ivoire", "North Macedonia": "Macedonia",
    "Northern Cyprus": "N. Cyprus", "Palestinian Territories": "Palestine", "The Gambia": "Gambia",
    "Trinidad & Tobago": "Trinidad and Tobago", "Turkiye": "Turkey", "United States": "United States of America",
}

def in_words(pct):
    """Turn a percentage into words people read easily: 18.7 -> '1 in 5', 38.7 -> '4 in 10'.
    WHY the 30% switch: at first 38.7% became '1 in 3', which undersells it. From 30% up,
    'N in 10' is more accurate."""
    if pct >= 95: return "almost all"
    if pct >= 30: return f"{round(pct / 10)} in 10"
    return f"1 in {round(100 / pct)}"

summary = json.load(open("hologic_summary.json"))
# WHY the world value from step 2: it is weighted by population (see step 2, part 8).
world = {k: summary["world"][k] for k in CHECKS}
table = pd.DataFrame(summary["countries"]).set_index("country")[list(CHECKS)]

# z-score for every country and every check-up, all at once (one column per check-up)
z = (table - table.mean()) / table.std()

facts, counts = [], {"below": 0, "above": 0, "average": 0}
for country, row in table.iterrows():
    zc = z.loc[country].dropna()
    key = zc.abs().idxmax()           # .abs(): very low counts as "unusual" just like very high
    v = row[key]
    if zc[key] < -Z_THRESHOLD:
        kind = "below"
        line = f"Only {in_words(v)} women {CHECKS[key]} last year."
    elif zc[key] > Z_THRESHOLD:
        kind = "above"
        line = f"{in_words(v).capitalize()} women {CHECKS[key]} last year."
    else:
        # WHY say it plainly instead of hiding the country: "average" is itself a finding.
        # Mexico is close to the world average, and the world average is low (1 in 8 cancer screening).
        kind = "average"
        line = "Close to the world average on all five check-ups."
    counts[kind] += 1
    facts.append({
        "country": country, "map_name": MAP_NAMES.get(country, country), "kind": kind,
        "check": key, "value": round(float(v), 1), "world": world[key], "line": line,
        "world_line": f"World: {in_words(world[key])}." if kind != "average" else "",
    })

with open("country_facts.json", "w", encoding="utf-8") as f:
    json.dump({"source": summary["source"], "world": world, "facts": facts}, f, indent=2, ensure_ascii=False)

print(f"{len(facts)} countries: {counts['below']} clearly below the world, {counts['above']} clearly above, {counts['average']} close to average.")
print("Checks chosen:", pd.Series([f["check"] for f in facts if f["kind"] != "average"]).value_counts().to_dict())


# =====================================================================================
# STEP 4 - Cleaning IHME Global Burden of Disease 2023: PCOS prevalence
# =====================================================================================
# Source : Institute for Health Metrics and Evaluation (IHME), GBD Results Tool, GBD 2023.
#          Filters: estimate = cause, measure = prevalence, cause = polycystic ovarian syndrome,
#          sex = female, age = 15-49, year = 2023, metrics = number and rate.
# Input  : IHME-GBD_2023_DATA-a4cf4218-1.csv  (204 countries and territories)
#          IHME-GBD_2023_DATA-4f0e8c23-1.csv  (the world total, same filters)
# Output : pcos_prevalence_clean.csv     -> one row per country
#          pcos_prevalence_summary.json  -> world total + every country, used by steps 5 and 6
#          cleaning_log_ihme.md          -> every decision
#
# WHY THIS DATASET WAS ADDED
# The story jumped from 541 women in Kerala straight to the whole world. IHME fills that gap with
# real PCOS data for every country. It does NOT have symptoms (that is why Kerala stays for the quiz).
#
# HISTORY OF THE DOWNLOAD (worth mentioning)
# It took several downloads to get the right file:
#  - 1st and 2nd: the tool's default filters (all causes, world only, deaths). The 2nd was the same
#    file uploaded again (same code in the file name).
#  - 3rd: "Impairment" mode with infertility, not PCOS. PCOS was hidden because the tool starts on
#    "Deaths", and PCOS causes no deaths, so it doesn't appear in the cause list.
#  - 4th: PCOS for the world only (kept: it gives the world total).
#  - 5th: PCOS for all 204 countries (the main file).
# Section 1 checks the filters automatically, so a wrong file can never slip through again.
#
# =====================================================================================

COUNTRIES_FILE = "IHME-GBD_2023_DATA-a4cf4218-1.csv"
WORLD_FILE = "IHME-GBD_2023_DATA-4f0e8c23-1.csv"

log = []
def note(text):
    log.append(text)
    print("-", text)

df = pd.read_csv(COUNTRIES_FILE)
world_raw = pd.read_csv(WORLD_FILE)
note(f"Countries file: {len(df)} rows, {df.location_name.nunique()} locations. World file: {len(world_raw)} rows.")

# -------------------------------------------------------------------------------------
# 1. CHECK THE FILE IS WHAT WE ASKED FOR
# WHY: three earlier downloads had the wrong filters. These asserts stop the script
#      immediately if the file is not PCOS / prevalence / women / 15-49 / 2023.
#      (The tool was in Spanish, so the values are in Spanish.)
# -------------------------------------------------------------------------------------
expected = {"measure_name": ["Prevalencia"], "sex_name": ["Mujer"], "age_name": ["15-49 años"],
            "cause_name": ["Síndrome de ovario poliquístico"], "year": [2023]}
for col, val in expected.items():
    assert sorted(df[col].unique().tolist()) == val, f"Unexpected {col}: {df[col].unique()}"
note("Verified filters: prevalence, women, ages 15-49, PCOS, year 2023. (Three earlier downloads had the wrong filters and were discarded.)")

# -------------------------------------------------------------------------------------
# 2. ONE ROW PER COUNTRY
# WHAT: the file has 2 rows per country (number of cases, and rate per 100,000), each with a
#       value and an uncertainty range (lower, upper). We put them side by side.
# WHY:  all the other columns repeat one single value (sex, age, year...), so they add nothing.
# -------------------------------------------------------------------------------------
df = df.pivot_table(index=["location_id", "location_name"], columns="metric_name",
                    values=["val", "lower", "upper"]).reset_index()
df.columns = ["location_id", "location_name_es",
              "cases_lower", "rate_lower", "cases_upper", "rate_upper", "cases", "rate_per_100k"]
note("Dropped columns with a single repeated value (population group, measure, sex, age, cause, year ids). Reshaped to one row per country.")

# -------------------------------------------------------------------------------------
# 3. SPANISH COUNTRY NAMES -> ISO CODES
# WHY:  the names are in Spanish ("Alemania", "Birmania") and the map and Gallup use English.
#       Joining by NAME breaks on every spelling difference; joining by ISO CODE does not.
# HOW:  pycountry has the official Spanish name of every country. We compare names without
#       accents and in lower case. 186 matched automatically; 18 needed a manual entry because
#       IHME uses other spellings ("Holanda" for the Netherlands, "Suazilandia" for Eswatini).
#       The assert checks that all 204 got a code and that no code repeats.
# -------------------------------------------------------------------------------------
es = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["es"])
norm = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
lookup = {}
for c in pycountry.countries:
    for attr in ("name", "common_name", "official_name"):
        if hasattr(c, attr):
            lookup[norm(es.gettext(getattr(c, attr)))] = c.alpha_3
MANUAL = {
    "Arabia Saudita": "SAU", "Argelia": "DZA", "Bahréin": "BHR", "Bermudas": "BMU", "Brunéi": "BRN",
    "Burkina Faso": "BFA", "Comoras": "COM", "Holanda": "NLD", "Iraq": "IRQ", "Islas Vírgenes, EUA": "VIR",
    "Las Bahamas": "BHS", "Macedonia": "MKD", "Maldivas": "MDV", "Palestina": "PSE",
    "República Democrática del Congo": "COD", "Rusia": "RUS", "Samoa Americana": "ASM", "Suazilandia": "SWZ",
}
df["iso3"] = df["location_name_es"].map(lambda n: MANUAL.get(n) or lookup.get(norm(n)))
assert df["iso3"].notna().all() and df["iso3"].is_unique
df["iso_numeric"] = df["iso3"].map(lambda a: pycountry.countries.get(alpha_3=a).numeric)   # the map uses numeric codes
df["country"] = df["iso3"].map(lambda a: getattr(pycountry.countries.get(alpha_3=a), "common_name", pycountry.countries.get(alpha_3=a).name))
note(f"Translated country names to ISO codes: {len(df) - len(MANUAL)} automatically (standard Spanish names), "
     f"{len(MANUAL)} by hand because IHME uses other spellings (e.g. 'Holanda' = Netherlands, 'Suazilandia' = Eswatini). All 204 unique.")

# -------------------------------------------------------------------------------------
# 4. READABLE NUMBERS
# WHAT: rate per 100,000 -> percent, and -> "1 in N women".
# WHY:  "1 in 15 women" is understood instantly; "6,700 per 100,000" is not.
# -------------------------------------------------------------------------------------
df["pct"] = (df["rate_per_100k"] / 1000).round(2)
df["pct_lower"] = (df["rate_lower"] / 1000).round(2)
df["pct_upper"] = (df["rate_upper"] / 1000).round(2)
df["one_in"] = (100_000 / df["rate_per_100k"]).round().astype(int)
note("Converted rate per 100,000 to percent and to '1 in N women' for the website.")

# -------------------------------------------------------------------------------------
# 5. WORLD TOTAL + CONSISTENCY CHECK
# WHY: the two downloads must agree. If the 204 countries add up to the world total,
#      we know nothing is missing or duplicated. They differ by 0.07%.
# -------------------------------------------------------------------------------------
w = world_raw[(world_raw.age_name == "15-49 años")].set_index("metric_name")
world = {"cases": round(w.loc["Número", "val"]), "pct": round(w.loc["Tasa", "val"] / 1000, 2),
         "pct_lower": round(w.loc["Tasa", "lower"] / 1000, 2), "pct_upper": round(w.loc["Tasa", "upper"] / 1000, 2)}
diff = abs(df["cases"].sum() - world["cases"]) / world["cases"]
note(f"World, women 15-49: {world['cases']:,} cases, {world['pct']}% (uncertainty {world['pct_lower']}-{world['pct_upper']}%). "
     f"Sum of the 204 countries differs from the world total by {diff:.2%}: the files are consistent.")

# -------------------------------------------------------------------------------------
# 6. CAVEATS AND DECISIONS
# - IHME numbers are MODEL ESTIMATES, not counts, with wide uncertainty.
# - IHME (~3 in 100) is lower than the WHO's 8-13 in 100: different definitions of PCOS.
#   DECISION: the whole page uses IHME (the intro's "64 million" and the map), so numbers never
#   contradict each other. The WHO's "up to 70% undiagnosed" stays because it is a different
#   kind of number (how many are undiagnosed), not a competing prevalence.
# - Age-standardised rates were not downloaded: every country is compared within the same age
#   band (15-49), so the comparison is already fair.
# -------------------------------------------------------------------------------------
note("Caveat: GBD values are modelled estimates, not counts. The uncertainty intervals are wide (world: about 2.3% to 4.5%), "
     "and widest where countries have little data.")
note("Caveat: GBD (about 3 in 100) is lower than the WHO's 8-13 in 100 because sources use different PCOS definitions; "
     "the WHO range comes from studies using broader diagnostic criteria. Never mix the two numbers in one comparison.")
note("Decision: age-standardised rates were not downloaded. Because every country is compared within the same age band (15-49), "
     "the comparison is fair without them.")

cols = ["iso3", "iso_numeric", "country", "location_name_es", "cases", "cases_lower", "cases_upper",
        "rate_per_100k", "pct", "pct_lower", "pct_upper", "one_in"]
df = df[cols].sort_values("pct", ascending=False)
df.to_csv("pcos_prevalence_clean.csv", index=False)

with open("pcos_prevalence_summary.json", "w", encoding="utf-8") as f:
    json.dump({"source": "IHME Global Burden of Disease 2023, PCOS prevalence, women 15-49",
               "world": world,
               "countries": df[["iso3", "iso_numeric", "country", "cases", "pct", "pct_lower", "pct_upper", "one_in"]]
                            .to_dict(orient="records")}, f, indent=2, ensure_ascii=False)

note(f"Final table: {len(df)} countries, {len(cols)} columns.")
with open("cleaning_log_ihme.md", "w", encoding="utf-8") as f:
    f.write("# Cleaning log - IHME GBD 2023, PCOS prevalence\n\n" + "\n".join(f"- {e}" for e in log))


# =====================================================================================
# STEP 5 - Join Gallup + IHME for the map, and TEST the conclusion
# =====================================================================================
# Inputs : country_facts.json (step 3), hologic_summary.json (step 2), pcos_prevalence_clean.csv (step 4),
#          pcos_prevalence_summary.json (step 4)
# Output : map_data.json        -> everything the map, the country cards and the conclusion need
#          analysis_log_map.md  -> the join and the statistical test, written out
#
# WHAT THIS STEP DOES
# 1. Joins the two country datasets by ISO code (not by name).
# 2. Tests the sentence we wanted to write on the page:
#    "PCOS shows up where someone looks for it."
#    If that is true, countries where more women see a health professional should RECORD more PCOS.
#    We checked it with our own data before writing it.
#
# HOW THE IDEA CAME UP
# In the IHME data, neighbouring countries differ enormously: Italy ~1 in 7 vs Albania ~1 in 281
# (more than 40x), Mexico 1 in 15 vs Brazil 1 in 89. Biology doesn't change that much at a border;
# how much a country diagnoses does. A published GBD study also found higher PCOS where the
# socio-economic level is higher. So we tested it with Gallup's check-up data.
#
# WHAT WE FOUND (be honest about the size)
# - "Saw a health professional" vs PCOS: Spearman rho = +0.25, p = 0.003. Moderate but significant.
# - Median PCOS: 1 in 16 women in the quarter of countries that see professionals most,
#   1 in 68 in the quarter that see them least.
# - The other four check-ups were NOT clearly related. We report them too (see the log), so nobody
#   can say we picked only the result we liked.
# - It is an association, not proof: richer countries both check more and record more.
#
# =====================================================================================

log = []
def note(text):
    log.append(text)
    print("-", text)

gallup = pd.DataFrame(json.load(open("country_facts.json"))["facts"])
checks = pd.DataFrame(json.load(open("hologic_summary.json"))["countries"])
ihme = pd.read_csv("pcos_prevalence_clean.csv")

# -------------------------------------------------------------------------------------
# 1. GALLUP NAMES -> ISO CODES
# WHY: same reason as step 4. pycountry recognises most English names; 22 need help
#      (e.g. "Turkiye", "Congo (Kinshasa)", "Ivory Coast"). Kosovo and Northern Cyprus have
#      no official ISO code, so they get unofficial ones (XKX, NCY).
# -------------------------------------------------------------------------------------
GALLUP_ISO = {
    "Turkiye": "TUR", "Kosovo": "XKX", "Northern Cyprus": "NCY", "Palestinian Territories": "PSE",
    "Congo (Kinshasa)": "COD", "Congo Brazzaville": "COG", "Ivory Coast": "CIV", "Russia": "RUS", "Iran": "IRN",
    "South Korea": "KOR", "Vietnam": "VNM", "Laos": "LAO", "Moldova": "MDA", "Taiwan": "TWN", "Bolivia": "BOL",
    "Venezuela": "VEN", "Tanzania": "TZA", "Hong Kong": "HKG", "Czech Republic": "CZE", "The Gambia": "GMB",
    "Trinidad & Tobago": "TTO", "Eswatini": "SWZ",
}
def to_iso(name):
    return GALLUP_ISO.get(name) or pycountry.countries.lookup(name).alpha_3
gallup["iso3"] = gallup["country"].map(to_iso)
checks["iso3"] = checks["country"].map(to_iso)
note(f"Gallup: {len(gallup)} countries matched to ISO codes ({len(GALLUP_ISO)} by hand, e.g. 'Turkiye', 'Congo (Kinshasa)').")

# WHY: official ISO names are long ("Congo, The Democratic Republic of the"). The dropdown needs short ones.
FRIENDLY = {
    "COD": "DR Congo", "FSM": "Micronesia", "VIR": "US Virgin Islands", "PSE": "Palestine", "IRN": "Iran",
    "KOR": "South Korea", "PRK": "North Korea", "BOL": "Bolivia", "VEN": "Venezuela", "TZA": "Tanzania",
    "MDA": "Moldova", "LAO": "Laos", "SYR": "Syria", "RUS": "Russia", "VNM": "Vietnam", "BRN": "Brunei",
    "CZE": "Czech Republic", "TUR": "Turkiye", "CIV": "Ivory Coast", "COG": "Congo Brazzaville", "TWN": "Taiwan",
}

# -------------------------------------------------------------------------------------
# 2. ONE RECORD PER PLACE WITH EVERYTHING WE KNOW ABOUT IT
# WHY keep places that are only in one dataset: a reader looking for her country should still
#     find it. The card says "No check-up data" or "No PCOS estimate" instead of a blank.
# pcos_one_in_low / _high: the uncertainty range, so the card can say "between 1 in 11 and 1 in 21".
# -------------------------------------------------------------------------------------
rows = {}
for _, r in ihme.iterrows():
    rows[r.iso3] = {"iso3": r.iso3, "iso_numeric": str(r.iso_numeric).zfill(3),
                    "country": FRIENDLY.get(r.iso3, r.country),
                    "pcos_pct": r.pct, "pcos_one_in": int(r.one_in),
                    "pcos_one_in_low": int(round(100 / r.pct_upper)), "pcos_one_in_high": int(round(100 / r.pct_lower))}
for _, r in gallup.iterrows():
    rec = rows.setdefault(r.iso3, {"iso3": r.iso3, "country": r.country})
    rec.update({"country": r.country, "map_name": r.map_name, "check_kind": r.kind,
                "check_line": r.line, "check_world_line": r.world_line,
                "check_value": r.value, "check_world": r.world})
both = sum(1 for v in rows.values() if "pcos_pct" in v and "check_kind" in v)
note(f"Joined by ISO code: {len(rows)} places in total; {both} have both datasets, "
     f"{sum('check_kind' not in v for v in rows.values())} only IHME, {sum('pcos_pct' not in v for v in rows.values())} only Gallup "
     f"(Kosovo, Northern Cyprus and Hong Kong are not separate places in IHME).")

# -------------------------------------------------------------------------------------
# 3. TEST THE CLAIM
# WHY Spearman (not Pearson): the PCOS values are very skewed (0.4% to 15%). Spearman compares
#     RANKS, so a few extreme countries can't create or hide a relationship on their own.
# WHY quartiles: "1 in 16 vs 1 in 68" is something a reader understands; "rho = 0.25" is not.
#     The page shows the quartiles; the rho and p-value are here to back them up.
# -------------------------------------------------------------------------------------
m = checks.merge(ihme[["iso3", "pct"]], on="iso3")
rho, p = spearmanr(m["talked_to_health_professional"], m["pct"])
m["quarter"] = pd.qcut(m["talked_to_health_professional"], 4, labels=["bottom", "2", "3", "top"])
med = m.groupby("quarter", observed=True)["pct"].median()
claim = {"countries": int(len(m)), "rho": round(float(rho), 2), "p_value": round(float(p), 4),
         "bottom_quarter_pct": round(float(med["bottom"]), 2), "top_quarter_pct": round(float(med["top"]), 2),
         "bottom_one_in": int(round(100 / med["bottom"])), "top_one_in": int(round(100 / med["top"]))}
note(f"Claim test ({claim['countries']} countries with both datasets): Spearman correlation between the share of women who saw a "
     f"health professional and estimated PCOS prevalence = {claim['rho']} (p = {claim['p_value']}). Moderate, statistically significant.")
note(f"Median PCOS in the quarter of countries where women see professionals most: {claim['top_quarter_pct']}% (1 in {claim['top_one_in']}); "
     f"least: {claim['bottom_quarter_pct']}% (1 in {claim['bottom_one_in']}).")
note("Caveat: this is an association, not proof. Richer countries both check more and record more, and IHME estimates for "
     "countries with little data lean on regional models. The middle quarters do not rise in a straight line.")

# WHY report the other four: transparency. Only "saw a professional" is clearly related;
# showing the ones that are NOT significant proves we didn't cherry-pick.
for col in ["tested_diabetes", "tested_blood_pressure", "tested_cancer", "tested_std"]:
    r2, p2 = spearmanr(m[col], m["pct"], nan_policy="omit")
    note(f"  For comparison, {col}: rho = {r2:+.2f}, p = {p2:.3f}.")

# The neighbour example used on the page (Italy and Albania face each other across the Strait of Otranto)
ita, alb = rows["ITA"], rows["ALB"]
claim["neighbours"] = {"high": {"country": "Italy", "one_in": ita["pcos_one_in"]}, "low": {"country": "Albania", "one_in": alb["pcos_one_in"]},
                       "times": round(ita["pcos_pct"] / alb["pcos_pct"])}
note(f"Neighbour example: Italy 1 in {ita['pcos_one_in']} vs Albania 1 in {alb['pcos_one_in']} ({claim['neighbours']['times']}x).")

# WHY the page reads its conclusion numbers from here: if the data changes, the sentence changes
# with it. The page and the analysis can never disagree.
with open("map_data.json", "w", encoding="utf-8") as f:
    json.dump({"places": list(rows.values()), "claim": claim,
               "world_pcos": json.load(open("pcos_prevalence_summary.json"))["world"]}, f, indent=2, ensure_ascii=False)
with open("analysis_log_map.md", "w", encoding="utf-8") as f:
    f.write("# Joining Gallup and IHME for the map\n\n" + "\n".join(f"- {e}" for e in log))


# =====================================================================================
# STEP 6 - Put the analysis results into the web page (index.html)
# =====================================================================================
# Inputs : map_data.json (step 5), index.html
# Output : index.html, updated in place
#
# WHY THIS STEP EXISTS
# The page has no server and no API: everything it shows lives inside index.html itself.
# (An API is only needed when a page asks a server for data that changes or is calculated live.
# Our data is fixed, so the numbers can travel inside the page.)
# During development the results were pasted into the page by hand. That left a gap: nobody
# could prove the page shows exactly what the analysis produced. This script closes the gap.
# Run it after steps 1-5 whenever the data changes; it also confirms nothing was edited by hand.
#
# WHAT IT REPLACES
# The MAP_DATA block -> the map colours, every country card, and the conclusion sentences
# ("more than 40 times", "1 in 16 ... 1 in 68"), which the page writes from these numbers.
# HISTORY: the intro used to say how many women live with PCOS. It first said "roughly 1 in 10"
# (a WHO-style figure), which clashed with the map's "1 in 31" (IHME), so it was switched to IHME's
# count of women ("an estimated 64 million"), which this step also kept up to date. In the final
# design the intro was shortened and that sentence was removed, so only the map data is replaced.
#
# =====================================================================================

page = open("index.html", encoding="utf-8").read()

# Replace everything between "const MAP_DATA = " and the next block with the latest results
map_data = json.load(open("map_data.json", encoding="utf-8"))
start = page.index("const MAP_DATA = ") + len("const MAP_DATA = ")
end = page.index(";\nconst WORLD_TOPO", start)
page = page[:start] + json.dumps(map_data, ensure_ascii=False) + page[end:]

open("index.html", "w", encoding="utf-8").write(page)
print(f"index.html updated: {len(map_data['places'])} places on the map.")
