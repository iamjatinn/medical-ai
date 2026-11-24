"""Lab tests used to generate synthetic reports.

Every entry:
  names     how different labs print the test name
  units     (unit text, scale) variants; scale converts the base range/value
  range     adult reference range per sex ("M"/"F"), or "*" for both;
            (low, high) with None for an open end: (None, 200) means "< 200"
  decimals  decimals used when printing a value
  docs      knowledge pages that SHOULD explain the test (for the retrieval check)

All values are invented. Ranges are typical adult ranges and vary by lab; they
are used only to generate test data with a known answer.
"""

CATALOGUE = {
    # ---------------- blood count ----------------
    "hemoglobin": {
        "panel": "cbc", "names": ["Hemoglobin", "Haemoglobin", "Hemoglobin (Hb)", "Hb"],
        "units": [("g/dL", 1)], "range": {"M": (13.5, 17.5), "F": (12.0, 15.5)}, "decimals": 1,
        "docs": ["mplus_hemoglobin_test", "mplus_complete_blood_count_cbc", "anemia"],
    },
    "rbc": {
        "panel": "cbc", "names": ["RBC", "RBC Count", "Red Blood Cell Count"],
        "units": [("M/uL", 1), ("million/uL", 1), ("x10^6/uL", 1)],
        "range": {"M": (4.5, 5.9), "F": (4.1, 5.1)}, "decimals": 2,
        "docs": ["mplus_red_blood_cell_rbc_count", "rbc", "mplus_complete_blood_count_cbc"],
    },
    "hematocrit": {
        "panel": "cbc", "names": ["Hematocrit", "HCT", "PCV"],
        "units": [("%", 1)], "range": {"M": (41, 53), "F": (36, 46)}, "decimals": 1,
        "docs": ["mplus_hematocrit_test", "mplus_complete_blood_count_cbc"],
    },
    "wbc": {
        "panel": "cbc", "names": ["WBC", "WBC Count", "Total Leukocyte Count", "White Blood Cell Count"],
        "units": [("/uL", 1), ("cells/cumm", 1), ("x10^3/uL", 0.001)],
        "range": {"*": (4000, 11000)}, "decimals": 0,
        "docs": ["mplus_white_blood_count_wbc", "wbc", "mplus_complete_blood_count_cbc"],
    },
    "platelets": {
        "panel": "cbc", "names": ["Platelets", "Platelet Count", "PLT"],
        "units": [("/uL", 1), ("x10^3/uL", 0.001)], "range": {"*": (150000, 450000)}, "decimals": 0,
        "docs": ["mplus_platelet_tests", "platelets", "mplus_complete_blood_count_cbc"],
    },
    "mcv": {
        "panel": "cbc", "names": ["MCV"], "units": [("fL", 1)], "range": {"*": (80, 100)}, "decimals": 1,
        "docs": ["mplus_mcv_mean_corpuscular_volume", "mplus_red_blood_cell_rbc_indices"],
    },
    "rdw": {
        "panel": "cbc", "names": ["RDW", "RDW-CV"], "units": [("%", 1)], "range": {"*": (11.5, 14.5)}, "decimals": 1,
        "docs": ["mplus_rdw_red_cell_distribution_width", "mplus_red_blood_cell_rbc_indices"],
    },
    # ---------------- sugar ----------------
    "glucose": {
        "panel": "diabetes", "names": ["Glucose (Fasting)", "Fasting Blood Sugar", "Glucose, Fasting", "FBS"],
        "units": [("mg/dL", 1)], "range": {"*": (70, 99)}, "decimals": 0,
        "docs": ["mplus_blood_glucose_test", "diabetes", "mplus_diabetes_tests"],
    },
    "hba1c": {
        "panel": "diabetes", "names": ["HbA1c", "Hemoglobin A1c", "Glycated Hemoglobin (HbA1c)"],
        "units": [("%", 1)], "range": {"*": (4.0, 5.6)}, "decimals": 1,
        "docs": ["mplus_hemoglobin_a1c_hba1c_test", "mplus_diabetes_tests"],
    },
    # ---------------- lipids ----------------
    "cholesterol": {
        "panel": "lipid", "names": ["Total Cholesterol", "Cholesterol, Total"],
        "units": [("mg/dL", 1)], "range": {"*": (None, 200)}, "decimals": 0,
        "docs": ["mplus_cholesterol_levels", "mplus_heart_disease_risk_assessment"],
    },
    "ldl": {
        "panel": "lipid", "names": ["LDL Cholesterol", "LDL-C", "LDL"],
        "units": [("mg/dL", 1)], "range": {"*": (None, 100)}, "decimals": 0,
        "docs": ["mplus_cholesterol_levels", "mplus_heart_disease_risk_assessment"],
    },
    "hdl": {
        "panel": "lipid", "names": ["HDL Cholesterol", "HDL-C", "HDL"],
        "units": [("mg/dL", 1)], "range": {"M": (40, None), "F": (50, None)}, "decimals": 0,
        "docs": ["mplus_cholesterol_levels", "mplus_heart_disease_risk_assessment"],
    },
    "triglycerides": {
        "panel": "lipid", "names": ["Triglycerides", "TG"],
        "units": [("mg/dL", 1)], "range": {"*": (None, 150)}, "decimals": 0,
        "docs": ["mplus_triglycerides_test", "mplus_cholesterol_levels"],
    },
    # ---------------- thyroid ----------------
    "tsh": {
        "panel": "thyroid", "names": ["TSH", "Thyroid Stimulating Hormone (TSH)"],
        "units": [("mIU/L", 1), ("uIU/mL", 1)], "range": {"*": (0.4, 4.0)}, "decimals": 2,
        "docs": ["mplus_tsh_thyroid_stimulating_hormone_test"],
    },
    "ft4": {
        "panel": "thyroid", "names": ["Free T4", "FT4", "Thyroxine (T4), Free"],
        "units": [("ng/dL", 1)], "range": {"*": (0.8, 1.8)}, "decimals": 2,
        "docs": ["mplus_thyroxine_t4_test"],
    },
    "t3": {
        "panel": "thyroid", "names": ["Total T3", "T3"],
        "units": [("ng/dL", 1)], "range": {"*": (80, 200)}, "decimals": 0,
        "docs": ["mplus_triiodothyronine_t3_tests"],
    },
    # ---------------- liver ----------------
    "alt": {
        "panel": "liver", "names": ["ALT", "SGPT (ALT)", "ALT (SGPT)"],
        "units": [("U/L", 1), ("IU/L", 1)], "range": {"*": (7, 56)}, "decimals": 0,
        "docs": ["mplus_alt_blood_test", "mplus_liver_function_tests"],
    },
    "ast": {
        "panel": "liver", "names": ["AST", "SGOT (AST)"],
        "units": [("U/L", 1), ("IU/L", 1)], "range": {"*": (10, 40)}, "decimals": 0,
        "docs": ["mplus_ast_test", "mplus_liver_function_tests"],
    },
    "alp": {
        "panel": "liver", "names": ["Alkaline Phosphatase", "ALP"],
        "units": [("U/L", 1)], "range": {"*": (44, 147)}, "decimals": 0,
        "docs": ["mplus_alkaline_phosphatase", "mplus_liver_function_tests"],
    },
    "bilirubin": {
        "panel": "liver", "names": ["Total Bilirubin", "Bilirubin, Total"],
        "units": [("mg/dL", 1)], "range": {"*": (0.1, 1.2)}, "decimals": 1,
        "docs": ["mplus_bilirubin_blood_test", "mplus_liver_function_tests"],
    },
    "albumin": {
        "panel": "liver", "names": ["Albumin"],
        "units": [("g/dL", 1)], "range": {"*": (3.5, 5.0)}, "decimals": 1,
        "docs": ["mplus_albumin_blood_test", "mplus_liver_function_tests"],
    },
    # ---------------- kidney ----------------
    "creatinine": {
        "panel": "kidney", "names": ["Creatinine", "Serum Creatinine", "S. Creatinine"],
        "units": [("mg/dL", 1)], "range": {"M": (0.7, 1.3), "F": (0.6, 1.1)}, "decimals": 2,
        "docs": ["mplus_creatinine_test", "mplus_estimated_glomerular_filtration_rate_egfr_and_gfr_tests"],
    },
    "bun": {
        "panel": "kidney", "names": ["BUN", "Blood Urea Nitrogen"],
        "units": [("mg/dL", 1)], "range": {"*": (7, 20)}, "decimals": 0,
        "docs": ["mplus_bun_blood_urea_nitrogen"],
    },
    "egfr": {
        "panel": "kidney", "names": ["eGFR"],
        "units": [("mL/min/1.73m2", 1)], "range": {"*": (60, None)}, "decimals": 0,
        "docs": ["mplus_estimated_glomerular_filtration_rate_egfr_and_gfr_tests"],
    },
    "uric_acid": {
        "panel": "kidney", "names": ["Uric Acid"],
        "units": [("mg/dL", 1)], "range": {"M": (3.5, 7.2), "F": (2.6, 6.0)}, "decimals": 1,
        "docs": ["mplus_uric_acid_test"],
    },
    # ---------------- electrolytes ----------------
    "sodium": {
        "panel": "electrolytes", "names": ["Sodium", "Sodium (Na)"],
        "units": [("mmol/L", 1), ("mEq/L", 1)], "range": {"*": (135, 145)}, "decimals": 0,
        "docs": ["mplus_sodium_blood_test", "mplus_electrolyte_panel"],
    },
    "potassium": {
        "panel": "electrolytes", "names": ["Potassium", "Potassium (K)"],
        "units": [("mmol/L", 1), ("mEq/L", 1)], "range": {"*": (3.5, 5.0)}, "decimals": 1,
        "docs": ["mplus_potassium_blood_test", "mplus_electrolyte_panel"],
    },
    "chloride": {
        "panel": "electrolytes", "names": ["Chloride"],
        "units": [("mmol/L", 1), ("mEq/L", 1)], "range": {"*": (98, 107)}, "decimals": 0,
        "docs": ["mplus_chloride_blood_test", "mplus_electrolyte_panel"],
    },
    "calcium": {
        "panel": "electrolytes", "names": ["Calcium", "Calcium, Total"],
        "units": [("mg/dL", 1)], "range": {"*": (8.6, 10.2)}, "decimals": 1,
        "docs": ["mplus_calcium_blood_test"],
    },
    # ---------------- vitamins and iron ----------------
    "vitamin_d": {
        "panel": "vitamins", "names": ["Vitamin D", "25-OH Vitamin D", "Vitamin D (25-Hydroxy)"],
        "units": [("ng/mL", 1)], "range": {"*": (30, 100)}, "decimals": 0,
        "docs": ["mplus_vitamin_d_test", "vitamin_d"],
    },
    "b12": {
        "panel": "vitamins", "names": ["Vitamin B12", "Cyanocobalamin (B12)"],
        "units": [("pg/mL", 1)], "range": {"*": (200, 900)}, "decimals": 0,
        "docs": ["mplus_vitamin_b_test"],
    },
    "ferritin": {
        "panel": "vitamins", "names": ["Ferritin"],
        "units": [("ng/mL", 1)], "range": {"M": (30, 400), "F": (13, 150)}, "decimals": 0,
        "docs": ["mplus_ferritin_blood_test", "mplus_iron_tests"],
    },
    "iron": {
        "panel": "vitamins", "names": ["Serum Iron", "Iron"],
        "units": [("ug/dL", 1), ("µg/dL", 1)], "range": {"*": (60, 170)}, "decimals": 0,
        "docs": ["mplus_iron_tests"],
    },
    # ---------------- inflammation ----------------
    "crp": {
        "panel": "inflammation", "names": ["CRP", "C-Reactive Protein", "hs-CRP"],
        "units": [("mg/L", 1)], "range": {"*": (None, 3.0)}, "decimals": 1,
        "docs": ["mplus_c_reactive_protein_crp_test"],
    },
    "esr": {
        "panel": "inflammation", "names": ["ESR"],
        "units": [("mm/hr", 1)], "range": {"M": (0, 15), "F": (0, 20)}, "decimals": 0,
        "docs": ["mplus_erythrocyte_sedimentation_rate_esr"],
    },
    # ---------------- hormones ----------------
    "cortisol": {
        "panel": "hormones", "names": ["Cortisol", "Cortisol (Morning)", "Serum Cortisol"],
        "units": [("ug/dL", 1), ("µg/dL", 1)], "range": {"*": (6.0, 23.0)}, "decimals": 1,
        "docs": ["mplus_cortisol_test"],
    },
    "testosterone": {
        "panel": "hormones", "names": ["Testosterone", "Testosterone, Total"],
        "units": [("ng/dL", 1)], "range": {"M": (300, 1000), "F": (15, 70)}, "decimals": 0,
        "docs": ["mplus_testosterone_levels_test"],
    },
    "prolactin": {
        "panel": "hormones", "names": ["Prolactin", "PRL"],
        "units": [("ng/mL", 1)], "range": {"M": (2.0, 18.0), "F": (2.0, 29.0)}, "decimals": 1,
        "docs": ["mplus_prolactin_levels"],
    },
    "pth": {
        "panel": "hormones", "names": ["PTH", "Parathyroid Hormone (Intact)"],
        "units": [("pg/mL", 1)], "range": {"*": (15, 65)}, "decimals": 0,
        "docs": ["mplus_parathyroid_hormone_pth_test"],
    },
    "psa": {
        "panel": "hormones", "names": ["PSA", "PSA, Total", "Prostate Specific Antigen"],
        "units": [("ng/mL", 1)], "range": {"*": (None, 4.0)}, "decimals": 2,
        "docs": ["mplus_prostate_specific_antigen_psa_test"],
    },
    # ---------------- heart, pancreas and other chemistry ----------------
    "troponin": {
        "panel": "chemistry", "names": ["Troponin I", "Troponin"],
        "units": [("ng/mL", 1)], "range": {"*": (None, 0.04)}, "decimals": 3,
        "docs": ["mplus_troponin_test"],
    },
    "ck": {
        "panel": "chemistry", "names": ["CPK", "Creatine Kinase", "CK, Total"],
        "units": [("U/L", 1)], "range": {"*": (30, 200)}, "decimals": 0,
        "docs": ["mplus_creatine_kinase_test"],
    },
    "ldh": {
        "panel": "chemistry", "names": ["LDH", "Lactate Dehydrogenase"],
        "units": [("U/L", 1)], "range": {"*": (140, 280)}, "decimals": 0,
        "docs": ["mplus_lactate_dehydrogenase_ldh_test"],
    },
    "amylase": {
        "panel": "chemistry", "names": ["Amylase", "Serum Amylase"],
        "units": [("U/L", 1)], "range": {"*": (30, 110)}, "decimals": 0,
        "docs": ["mplus_amylase_test"],
    },
    "lipase": {
        "panel": "chemistry", "names": ["Lipase", "Serum Lipase"],
        "units": [("U/L", 1)], "range": {"*": (13, 60)}, "decimals": 0,
        "docs": ["mplus_lipase_tests"],
    },
    "d_dimer": {
        "panel": "chemistry", "names": ["D-Dimer", "D Dimer"],
        "units": [("ng/mL", 1)], "range": {"*": (None, 500)}, "decimals": 0,
        "docs": ["mplus_d_dimer_test"],
    },
    "cea": {
        "panel": "chemistry", "names": ["CEA", "Carcinoembryonic Antigen"],
        "units": [("ng/mL", 1)], "range": {"*": (None, 3.0)}, "decimals": 1,
        "docs": ["mplus_cea_test"],
    },
    "afp": {
        "panel": "chemistry", "names": ["AFP", "Alpha Fetoprotein"],
        "units": [("ng/mL", 1)], "range": {"*": (None, 10.0)}, "decimals": 1,
        "docs": ["mplus_alpha_fetoprotein_afp_tumor_marker_test"],
    },
    "co2": {
        "panel": "chemistry", "names": ["CO2", "Bicarbonate", "Carbon Dioxide, Total"],
        "units": [("mmol/L", 1), ("mEq/L", 1)], "range": {"*": (23, 29)}, "decimals": 0,
        "docs": ["mplus_carbon_dioxide_co2_in_blood"],
    },
}

PANEL_TITLES = {
    "cbc": "COMPLETE BLOOD COUNT", "diabetes": "GLUCOSE / DIABETES", "lipid": "LIPID PROFILE",
    "thyroid": "THYROID FUNCTION", "liver": "LIVER FUNCTION TEST", "kidney": "KIDNEY FUNCTION TEST",
    "electrolytes": "ELECTROLYTES", "vitamins": "VITAMINS AND IRON", "inflammation": "INFLAMMATION MARKERS",
    "hormones": "HORMONES", "chemistry": "SPECIAL CHEMISTRY",
}

PANELS = sorted(PANEL_TITLES)
