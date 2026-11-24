"""Download MedlinePlus lab-test pages and turn them into knowledge-base text files.

Source: MedlinePlus, a service of the U.S. National Library of Medicine (NLM).
Terms:  medical-test information on MedlinePlus is a U.S. government work and is
        not copyrighted; MedlinePlus asks for credit. (A.D.A.M. encyclopedia
        articles and many images are licensed and are NOT used here.)
        https://medlineplus.gov/about/using/usingcontent/

What it does
  - fetches each page politely (identifiable User-Agent, a pause between requests)
  - keeps only the article text (title, sections, paragraphs, lists, tables)
  - drops the "References" and "Related ..." sections
  - writes data/medical_docs/mplus_<slug>.txt
  - records title, URL and download date in data/sources.json (for citations)

Run from the repository root:
    backend\\venv\\Scripts\\python tools\\fetch_medlineplus.py
Files that already exist are skipped, so it is safe to run again.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "medical_docs"
MANIFEST = ROOT / "data" / "sources.json"

BASE_URL = "https://medlineplus.gov/lab-tests/"
USER_AGENT = "AuraHealth-student-project/1.0 (educational use; polite, rate-limited)"
PAUSE_SECONDS = 1.5

CREDIT = "MedlinePlus, National Library of Medicine (NLM), https://medlineplus.gov"

# Tests that appear on typical blood / urine lab reports.
SLUGS = [
    # complete blood count and its parts
    "complete-blood-count-cbc", "hemoglobin-test", "hematocrit-test", "red-blood-cell-rbc-count",
    "red-blood-cell-rbc-indices", "mcv-mean-corpuscular-volume", "rdw-red-cell-distribution-width",
    "white-blood-count-wbc", "blood-differential", "platelet-tests", "mpv-blood-test", "reticulocyte-count",
    # sugar
    "blood-glucose-test", "hemoglobin-a1c-hba1c-test", "diabetes-tests", "insulin-in-blood-test",
    # fats
    "cholesterol-levels", "triglycerides-test", "heart-disease-risk-assessment",
    # chemistry panels, electrolytes, kidney
    "basic-metabolic-panel-bmp", "comprehensive-metabolic-panel-cmp", "electrolyte-panel",
    "sodium-blood-test", "potassium-blood-test", "chloride-blood-test", "calcium-blood-test",
    "magnesium-blood-test", "phosphate-in-blood", "creatinine-test", "bun-blood-urea-nitrogen",
    "estimated-glomerular-filtration-rate-egfr-and-gfr-tests", "uric-acid-test",
    # liver
    "liver-function-tests", "alt-blood-test", "ast-test", "alkaline-phosphatase", "bilirubin-blood-test",
    "albumin-blood-test", "total-protein-and-albumin-globulin-a-g-ratio", "gamma-glutamyl-transferase-ggt-test",
    # thyroid
    "tsh-thyroid-stimulating-hormone-test", "thyroxine-t4-test", "triiodothyronine-t3-tests",
    # vitamins and iron
    "vitamin-d-test", "vitamin-b-test", "iron-tests", "ferritin-blood-test", "homocysteine-test",
    # inflammation
    "c-reactive-protein-crp-test", "erythrocyte-sedimentation-rate-esr",
    # understanding results
    "how-to-understand-your-lab-results", "fasting-for-a-blood-test", "what-you-need-to-know-about-blood-testing",
    # urine, stool and fluids
    "urinalysis", "urine-culture", "microalbumin-creatinine-ratio", "bilirubin-in-urine", "protein-in-urine",
    "glucose-in-urine-test", "ketones-in-urine", "nitrites-in-urine", "blood-in-urine", "urobilinogen-in-urine",
    "calcium-in-urine-test", "crystals-in-urine", "epithelial-cells-in-urine", "fecal-occult-blood-test-fobt",
    "bacteria-culture-test",
    # hormones
    "cortisol-test", "testosterone-levels-test", "estrogen-levels-test", "progesterone-test", "prolactin-levels",
    "follicle-stimulating-hormone-fsh-levels-test", "luteinizing-hormone-lh-levels-test",
    "parathyroid-hormone-pth-test", "thyroid-antibody-tests", "dhea-sulfate-test", "pregnancy-test",
    # heart and clotting
    "troponin-test", "d-dimer-test", "prothrombin-time-test-and-inr-ptinr", "partial-thromboplastin-time-ptt-test",
    "natriuretic-peptide-tests-bnp-nt-probnp", "lipoprotein-a-blood-test", "creatine-kinase-test",
    "arterial-blood-gas-abg-test", "lactate-test",
    # liver, pancreas, other chemistry
    "amylase-test", "lipase-tests", "lactate-dehydrogenase-ldh-test", "ammonia-levels", "globulin-test",
    "osmolality-tests", "anion-gap-blood-test", "carbon-dioxide-co2-in-blood", "alpha-1-antitrypsin-test",
    "immunoglobulins-blood-test",
    # tumour markers, infection and immunity
    "prostate-specific-antigen-psa-test", "cea-test", "ca-125-blood-test-ovarian-cancer",
    "alpha-fetoprotein-afp-tumor-marker-test", "ana-antinuclear-antibody-test", "rheumatoid-factor-rf-test",
    "procalcitonin-test", "hiv-screening-test", "hepatitis-testing", "celiac-disease-screening",
    "helicobacter-pylori-h-pylori-tests", "malaria-tests", "dengue-fever-test",
    # blood disorders
    "hemoglobin-electrophoresis", "g6pd-test", "blood-smear",
]

SKIP_SECTIONS = {"references", "related health topics", "related medical tests", "related topics"}
BLOCK_END_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "tr", "caption"}
SKIP_TAGS = {"script", "style", "nav", "noscript", "button", "form", "svg", "figure", "iframe"}


class ArticleParser(HTMLParser):
    """Collects the text of the <article> element as a list of (kind, text) blocks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_article = False
        self.skip_depth = 0
        self.tag_stack = []
        self.buffer = []
        self.cells = []
        self.in_row = False
        self.blocks = []          # (kind, text): kind is h1 / h2 / h3 / p / li / tr
        self.current_kind = None

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.in_article = True
        if not self.in_article:
            return
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        self.tag_stack.append(tag)
        if tag in ("h1", "h2", "h3", "h4", "p", "li", "caption"):
            self.flush()
            self.current_kind = "h3" if tag == "h4" else tag
        elif tag == "tr":
            self.flush()
            self.in_row, self.cells = True, []
        elif tag in ("td", "th") and self.in_row:
            self.buffer = []
        elif tag == "br":
            self.buffer.append(" ")

    def handle_endtag(self, tag):
        if tag == "article":
            self.flush()
            self.in_article = False
            return
        if not self.in_article:
            return
        if tag in ("td", "th") and self.in_row:
            self.cells.append(self.clean("".join(self.buffer)))
            self.buffer = []
        elif tag == "tr" and self.in_row:
            row = [c for c in self.cells if c]
            if row:
                self.blocks.append(("tr", " | ".join(row)))
            self.in_row, self.cells, self.buffer = False, [], []
        elif tag in BLOCK_END_TAGS:
            self.flush()
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

    def handle_data(self, data):
        if self.in_article and not self.skip_depth:
            self.buffer.append(data)

    @staticmethod
    def clean(text):
        return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()

    def flush(self):
        if self.in_row:                 # table cells are collected on </td>
            return
        text = self.clean("".join(self.buffer))
        self.buffer = []
        if text and self.current_kind:
            self.blocks.append((self.current_kind, text))
        self.current_kind = None


def article_text(html: str):
    """Return (title, text) for a MedlinePlus lab-test page."""

    parser = ArticleParser()
    parser.feed(html)

    title = next((t for k, t in parser.blocks if k == "h1"), "")
    lines, skipping = [], False

    for kind, text in parser.blocks:

        if kind in ("h2", "h3"):
            skipping = text.strip("?: ").lower() in SKIP_SECTIONS
            if not skipping:
                lines.append(text)
            continue

        if kind == "h1" or skipping:
            continue

        lines.append(f"- {text}" if kind == "li" else text)

    # blank line between blocks, like the existing knowledge files
    return title, "\n\n".join(lines).strip() + "\n"


def fetch(slug: str) -> str:

    request = urllib.request.Request(BASE_URL + slug + "/", headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def main():

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    saved = skipped = failed = 0

    print(f"Fetching {len(SLUGS)} MedlinePlus lab-test pages (about {len(SLUGS) * PAUSE_SECONDS:.0f} s) ...\n")

    for slug in SLUGS:

        file_name = "mplus_" + slug.replace("-", "_") + ".txt"
        target = OUT_DIR / file_name

        if target.exists() and file_name in manifest:
            skipped += 1
            continue

        try:
            title, text = article_text(fetch(slug))
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"  FAILED  {slug}: {error}")
            failed += 1
            time.sleep(PAUSE_SECONDS)
            continue

        if len(text) < 400 or not title:
            print(f"  EMPTY   {slug}: nothing usable extracted, not saved")
            failed += 1
            time.sleep(PAUSE_SECONDS)
            continue

        target.write_text(text, encoding="utf-8")

        manifest[file_name] = {
            "title": title,
            "url": BASE_URL + slug + "/",
            "source": CREDIT,
            "downloaded": date.today().isoformat(),
            "license": "U.S. government work (not copyrighted); credit MedlinePlus/NLM",
            "characters": len(text),
        }

        saved += 1
        print(f"  saved   {file_name:<62}{len(text):>6} chars  {title}")
        time.sleep(PAUSE_SECONDS)

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone: {saved} saved, {skipped} already present, {failed} failed.")
    print(f"Sources recorded in {MANIFEST.relative_to(ROOT)}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
