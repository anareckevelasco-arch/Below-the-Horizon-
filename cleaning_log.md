# Cleaning log - PCOS dataset

- Original dataset: 541 rows and 45 columns.
- Stripped hidden spaces from column names and renamed them to short snake_case (also fixes the 'Marraige' typo).
- Dropped 'Sl. No' (duplicates the id) and 'Unnamed: 44' (empty column containing stray values '.' and '7').
- AMH: 1 text value ('a') set to missing.
- beta-HCG II: value '1.99.' had an extra period; corrected to 1.99.
- Cycle: 1 record with code 5 (not a valid code) set to missing. Created 'irregular_cycle' (0/1).
- pulse_bpm: 2 impossible value(s) (pulse below 40 bpm): [13, 18] -> set to missing.
- bp_systolic: 1 impossible value(s) (systolic BP below 70, likely a dropped zero): [12] -> set to missing.
- bp_diastolic: 1 impossible value(s) (diastolic BP below 40, likely a dropped zero): [8] -> set to missing.
- fsh: 1 impossible value(s) (FSH above 100 mIU/mL): [5052.0] -> set to missing.
- lh: 1 impossible value(s) (LH above 100 mIU/mL): [2018.0] -> set to missing.
- vitamin_d: 3 impossible value(s) (vitamin D of 0 or above 150 ng/mL): [0.0, 5418.6, 6014.66] -> set to missing.
- Recalculated the FSH/LH ratio from the cleaned values.
- BMI: 2 records did not match weight/height; replaced with the calculated value.
- Created 'symptom_count' (0 to 6 visible symptoms) and 'follicles_total'.
- Caveat: 33% of the sample has PCOS by study design; this is NOT real-world prevalence.
- Final dataset: 541 rows and 45 columns. No participant was removed.