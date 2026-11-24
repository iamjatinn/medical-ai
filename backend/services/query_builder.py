import logging
import re

logger = logging.getLogger(__name__)

# Labs often print only an abbreviation. The knowledge pages use full names, so
# the abbreviation is spelled out in the search query (the original is kept).
ABBREVIATIONS = {
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "hct": "hematocrit",
    "pcv": "packed cell volume hematocrit",
    "plt": "platelet count",
    "wbc": "white blood cell count",
    "rbc": "red blood cell count",
    "mcv": "mean corpuscular volume",
    "mch": "mean corpuscular hemoglobin",
    "mchc": "mean corpuscular hemoglobin concentration",
    "esr": "erythrocyte sedimentation rate",
    "fbs": "fasting blood glucose",
    "rbs": "random blood glucose",
    "ppbs": "postprandial blood glucose",
    "hba1c": "hemoglobin A1c glycated",
    "tg": "triglycerides",
    "hdl": "HDL cholesterol",
    "hdl-c": "HDL cholesterol",
    "ldl": "LDL cholesterol",
    "ldl-c": "LDL cholesterol",
    "vldl": "VLDL cholesterol",
    "alt": "alanine aminotransferase liver",
    "sgpt": "alanine aminotransferase liver",
    "ast": "aspartate aminotransferase liver",
    "sgot": "aspartate aminotransferase liver",
    "alp": "alkaline phosphatase",
    "ggt": "gamma-glutamyl transferase",
    "bun": "blood urea nitrogen",
    "egfr": "estimated glomerular filtration rate kidney",
    "tsh": "thyroid stimulating hormone",
    "t3": "triiodothyronine thyroid",
    "t4": "thyroxine thyroid",
    "crp": "C-reactive protein",
    "b12": "vitamin B12 cobalamin",
    "25-oh": "vitamin D 25-hydroxy",
    "pt": "prothrombin time", "inr": "INR prothrombin time", "aptt": "partial thromboplastin time",
    "ptt": "partial thromboplastin time", "psa": "prostate specific antigen",
    "cea": "carcinoembryonic antigen", "afp": "alpha-fetoprotein", "ana": "antinuclear antibody",
    "rf": "rheumatoid factor", "bnp": "natriuretic peptide", "ldh": "lactate dehydrogenase",
    "cpk": "creatine kinase", "ck": "creatine kinase", "hscrp": "C-reactive protein", "hs-crp": "C-reactive protein",
    "pth": "parathyroid hormone", "prl": "prolactin", "fsh": "follicle stimulating hormone",
    "lh": "luteinizing hormone", "hcg": "pregnancy test hCG", "dhea-s": "DHEA sulfate",
    "trop": "troponin", "tni": "troponin", "tibc": "iron tests total iron binding capacity",
    "urea": "blood urea nitrogen", "creat": "creatinine", "na": "sodium", "k": "potassium", "cl": "chloride",
    "ca": "calcium", "mg": "magnesium", "po4": "phosphate", "co2": "carbon dioxide bicarbonate",
    "sgpt-alt": "alanine aminotransferase liver", "ddimer": "D-dimer",
}


def expand_abbreviations(name):
    """'TG' -> 'triglycerides'; names without a known abbreviation give ''."""

    words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", str(name).lower())
    extra = []

    for word in words:
        full = ABBREVIATIONS.get(word)
        if full and full not in extra:
            extra.append(full)

    return " ".join(extra)


def build_query(finding):

    expanded = expand_abbreviations(finding["parameter"])

    query = (
        f"{finding['parameter']} {expanded} "
        f"{finding['calculated_status']} "
        f"meaning causes symptoms treatment diet"
    ).replace("  ", " ")

    logger.debug("Generated query: %s", query)

    return query
