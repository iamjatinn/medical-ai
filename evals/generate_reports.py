"""Generate randomized synthetic lab-report PDFs, each with an answer key.

Every report is different: which panels it has, how each test is spelled,
the units, the reference ranges, the values (about 62 % normal, 19 % low,
19 % high) and, above all, the LAYOUT. Nine layouts are produced, some of them
deliberately hard (two columns, a flag glued to the value, a scanned image).

The answer key (a .json next to each .pdf) records the true values, ranges and
Low/Normal/High status, so evals/pipeline_eval.py can measure the app against
the truth instead of guessing.

Everything is invented; no real patient data is involved.

    backend\\venv\\Scripts\\python evals\\generate_reports.py --count 120 --seed 7
"""

import argparse
import json
import random
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lab_catalogue import CATALOGUE, PANEL_TITLES, PANELS  # noqa: E402

# layout name -> weight (how often it is drawn)
LAYOUTS = {
    "cells_status": 18,        # one cell per line: name / "value unit" / range / status word
    "cells_unit_flag": 16,     # one cell per line, separate unit line, H/L flag
    "rows_status": 14,         # one test per line, status word at the end
    "rows_flag_letter": 12,    # one test per line, H / L flag
    "grouped_cells": 12,       # like cells_status, with panel headings
    "value_flag_inline": 8,    # "11.2 L": the flag is glued to the value
    "no_status": 8,            # no status column at all
    "two_columns": 6,          # two tests per text row, side by side
    "scanned": 6,              # an image: no text to read (the app falls back to the AI to read it)
    "flag_before_cells": 8,    # name / FLAG / value / unit / range, one cell per line (real CBC report)
    "rows_flag_before": 6,     # "Lymphocyte  L 18 %  20 - 40": the flag comes before the value
}

# how the reference range is printed
RANGE_STYLES = {"plain": 50, "upto": 12, "parens": 8, "to_word": 8, "unit_in_range": 8, "sex_both": 14}

LAB_NAMES = ["ABC Diagnostics", "CityCare Pathology Lab", "Sunrise Clinical Laboratory", "Apex Health Labs",
             "Metro Path Labs", "GreenLeaf Diagnostics"]
PATIENTS = ["John Doe", "Asha Verma", "Rahul Mehta", "Priya Nair", "Sam Wilson", "Neha Kapoor", "Omar Khan"]

X_NAME, X_VALUE, X_UNIT, X_RANGE, X_STATUS = 40, 215, 300, 370, 485


# ---------------------------------------------------------------- numbers ---

def number(x, decimals=None, thousands=False):
    """Format a number the way a lab report would."""

    if decimals is None:
        text = f"{x:g}"
    else:
        text = f"{x:.{decimals}f}"

    if thousands and abs(x) >= 1000:
        whole, _, fraction = text.partition(".")
        text = f"{int(whole):,}" + (f".{fraction}" if fraction else "")

    return text


def make_test(rng, key, sex, thousands, dash, spaced_less_than, range_style="plain", censor=False):
    """Pick the spelling, unit, range and a random value for one test."""

    spec = CATALOGUE[key]

    name = rng.choice(spec["names"])
    unit, scale = rng.choice(spec["units"])
    low, high = spec["range"].get(sex) or spec["range"]["*"]

    decimals = spec["decimals"] if scale == 1 else 1

    # a random value in the base unit
    roll = rng.random()
    kind = "normal" if roll < 0.62 else ("low" if roll < 0.81 else "high")

    if low is not None and high is not None:
        width = high - low
        if kind == "normal":
            base = rng.uniform(low + 0.08 * width, high - 0.08 * width)
        elif kind == "low":
            base = max(low - rng.uniform(0.06, 0.35) * width, low * 0.3)
        else:
            base = high + rng.uniform(0.06, 0.5) * width
    elif high is not None:                                   # "< high"
        base = (rng.uniform(0.4, 0.92) * high if kind != "high" else rng.uniform(1.08, 1.8) * high)
        kind = "normal" if kind == "low" else kind           # nothing can be "low" here
    else:                                                    # "> low"
        base = (rng.uniform(1.08, 1.7) * low if kind != "low" else rng.uniform(0.45, 0.92) * low)
        kind = "normal" if kind == "high" else kind

    value = round(base * scale, decimals)
    if decimals == 0:
        value = float(int(value))

    low_s = None if low is None else low * scale
    high_s = None if high is None else high * scale

    status = "Normal"
    if low_s is not None and value < low_s:
        status = "Low"
    elif high_s is not None and value > high_s:
        status = "High"

    # how the range is printed
    if low_s is not None and high_s is not None:
        range_text = f"{number(low_s, None, thousands)}{dash}{number(high_s, None, thousands)}"
    elif high_s is not None:
        range_text = ("< " if spaced_less_than else "<") + number(high_s, None, thousands)
    else:
        range_text = ("> " if spaced_less_than else ">") + number(low_s, None, thousands)

    value_text = number(value, decimals if decimals else 0, thousands)

    # ---- range printing variants seen in real reports ----
    both_sexes = (spec["range"].get("M") and spec["range"].get("F")
                  and None not in spec["range"]["M"] and None not in spec["range"]["F"])
    if range_style == "upto" and high_s is not None and low_s is None:
        range_text = rng.choice(["Up to ", "Upto "]) + number(high_s, None, thousands)
    elif range_style == "parens" and low_s is not None and high_s is not None:
        range_text = f"({range_text})"
    elif range_style == "to_word" and low_s is not None and high_s is not None:
        range_text = f"{number(low_s, None, thousands)} to {number(high_s, None, thousands)}"
    elif range_style == "unit_in_range" and low_s is not None and high_s is not None:
        range_text = f"{range_text} {unit}"
    elif range_style == "sex_both" and both_sexes:
        (m_low, m_high), (f_low, f_high) = spec["range"]["M"], spec["range"]["F"]
        label_m, label_f = rng.choice([("M", "F"), ("Male", "Female")])
        range_text = (f"{label_m}: {number(m_low * scale)}{dash}{number(m_high * scale)} "
                      f"{label_f}: {number(f_low * scale)}{dash}{number(f_high * scale)}")

    # ---- a result below the detection limit, printed "<0.5" ----
    if censor and high_s is not None and low_s is None and status == "Normal":
        shown = round(high_s * rng.uniform(0.04, 0.25), decimals + 1)
        if shown > 0:
            value = shown
            value_text = "<" + number(shown, None, False)

    return {
        "key": key, "printed_name": name, "value": value, "unit": unit,
        "min": low_s, "max": high_s, "expected_status": status,
        "value_text": value_text,
        "range_text": range_text, "panel": spec["panel"],
    }


# ---------------------------------------------------------------- drawing ---

class Writer:
    """Draws text onto A4 pages, adding pages as needed."""

    def __init__(self):
        self.doc = pymupdf.open()
        self.y = 0
        self.page = None
        self.header_cells = None
        self.new_page()

    def new_page(self):
        self.page = self.doc.new_page(width=595, height=842)
        self.y = 50
        if self.header_cells and len(self.doc) > 1:
            self.cells(self.header_cells, bold=True)

    def ensure_room(self, needed=16):
        if self.y > 790 - needed:
            self.new_page()

    def line(self, text, x=40, bold=False, size=9.5, gap=15):
        self.ensure_room(gap)
        self.page.insert_text((x, self.y), text, fontsize=size, fontname="hebo" if bold else "helv")
        self.y += gap

    def cells(self, cells, bold=False, size=9.5, gap=15):
        """Each cell is a separate text object, like a table in a real PDF."""
        self.ensure_room(gap)
        for x, text in cells:
            if text:
                self.page.insert_text((x, self.y), text, fontsize=size, fontname="hebo" if bold else "helv")
        self.y += gap

    def gap(self, amount=8):
        self.y += amount

    def finish(self):
        total = len(self.doc)
        for number_, page in enumerate(self.doc, start=1):
            page.insert_text((250, 825), f"Page {number_} of {total}", fontsize=8, fontname="helv")
        return self.doc


def flag_word(status):
    return {"Low": "Low", "High": "High", "Normal": "Normal"}[status]


def flag_letter(status):
    return {"Low": "L", "High": "H", "Normal": ""}[status]


def draw_header(writer, rng, sex, age):
    writer.line(rng.choice(LAB_NAMES), bold=True, size=14, gap=20)
    writer.line("Complete Laboratory Report", size=11, gap=18)
    writer.line(f"Patient Name: {rng.choice(PATIENTS)}")
    style = rng.choice(["separate", "sex_word", "age_sex"])
    if style == "separate":
        writer.line(f"Age: {age}")
        writer.line(f"Gender: {'Male' if sex == 'M' else 'Female'}")
    elif style == "sex_word":
        writer.line(f"Age: {age} Years    Sex: {'M' if sex == 'M' else 'F'}")
    else:
        writer.line(f"Age / Sex : {age} YRS / {sex}")
    writer.line(f"Sample ID: LAB-{rng.randint(10000, 99999)}")
    writer.gap(10)


def render(rng, layout, tests, sex, age, upper, wide_range=False):
    """Draw one report and return the PDF document."""

    writer = Writer()
    draw_header(writer, rng, sex, age)

    # a two-sex range ("Male: 13.5-17.5 Female: 12-15.5") is wide: move the last column right
    x_status = 540 if wide_range else X_STATUS

    shown = [dict(t, printed_name=t["printed_name"].upper() if upper and len(t["printed_name"]) <= 20 else t["printed_name"])
             for t in tests]

    for t, s in zip(tests, shown):
        t["printed_name"] = s["printed_name"]

    # ---- table headers and rows per layout ----
    if layout in ("cells_status", "grouped_cells"):
        writer.header_cells = [(X_NAME, "Test"), (X_VALUE, "Result"), (X_RANGE, "Reference Range"), (x_status, "Status")]
        writer.cells(writer.header_cells, bold=True)

        last_panel = None
        for t in shown:
            if layout == "grouped_cells" and t["panel"] != last_panel:
                writer.gap(6)
                writer.line(PANEL_TITLES[t["panel"]], bold=True, size=10)
                last_panel = t["panel"]
            writer.cells([(X_NAME, t["printed_name"]), (X_VALUE, f"{t['value_text']} {t['unit']}"),
                          (X_RANGE, t["range_text"]), (x_status, flag_word(t["expected_status"]))])

    elif layout == "cells_unit_flag":
        writer.header_cells = [(X_NAME, "Test"), (X_VALUE - 40, "Result"), (X_UNIT, "Unit"),
                               (X_RANGE, "Reference Range"), (x_status, "Flag")]
        writer.cells(writer.header_cells, bold=True)
        for t in shown:
            writer.cells([(X_NAME, t["printed_name"]), (X_VALUE - 40, t["value_text"]), (X_UNIT, t["unit"]),
                          (X_RANGE, t["range_text"]), (x_status, flag_letter(t["expected_status"]))])
        writer.gap(6)
        writer.line("H = High, L = Low", size=8)

    elif layout == "value_flag_inline":
        writer.header_cells = [(X_NAME, "Test"), (X_VALUE - 40, "Result"), (X_UNIT, "Unit"), (X_RANGE, "Reference Range")]
        writer.cells(writer.header_cells, bold=True)
        for t in shown:
            flagged = f"{t['value_text']} {flag_letter(t['expected_status'])}".strip()
            writer.cells([(X_NAME, t["printed_name"]), (X_VALUE - 40, flagged), (X_UNIT, t["unit"]),
                          (X_RANGE, t["range_text"])])

    elif layout == "flag_before_cells":
        X_FLAG, XV, XU, XR = 215, 245, 320, 385
        writer.header_cells = [(X_NAME, "TEST"), (XV, "VALUE"), (XU, "UNIT"), (XR, "REFERENCE")]
        writer.cells(writer.header_cells, bold=True)
        for t in shown:
            writer.cells([(X_NAME, t["printed_name"]), (X_FLAG, flag_letter(t["expected_status"])),
                          (XV, t["value_text"]), (XU, t["unit"]), (XR, t["range_text"])])

    elif layout == "rows_flag_before":
        writer.line("Test   Flag   Result   Reference Range", bold=True)
        for t in shown:
            flag = flag_letter(t["expected_status"])
            result = f"{flag} {t['value_text']} {t['unit']}".strip()
            writer.line(f"{t['printed_name']}   {result}   {t['range_text']}")

    elif layout == "no_status":
        writer.header_cells = [(X_NAME, "Test"), (X_VALUE, "Result"), (X_RANGE, "Reference Range")]
        writer.cells(writer.header_cells, bold=True)
        for t in shown:
            writer.cells([(X_NAME, t["printed_name"]), (X_VALUE, f"{t['value_text']} {t['unit']}"),
                          (X_RANGE, t["range_text"])])

    elif layout in ("rows_status", "scanned"):
        writer.line("Test   Result   Reference Range   Status", bold=True)
        for t in shown:
            writer.line(f"{t['printed_name']}   {t['value_text']} {t['unit']}   {t['range_text']}   "
                        f"{flag_word(t['expected_status'])}")

    elif layout == "rows_flag_letter":
        writer.line("Test   Result   Unit   Reference Range   Flag", bold=True)
        for t in shown:
            writer.line(f"{t['printed_name']}   {t['value_text']}   {t['unit']}   {t['range_text']}   "
                        f"{flag_letter(t['expected_status'])}".rstrip())
        writer.gap(6)
        writer.line("H = High, L = Low", size=8)

    elif layout == "two_columns":
        half = (len(shown) + 1) // 2
        left, right = shown[:half], shown[half:]
        top = writer.y
        writer.line("Test   Result   Reference Range", bold=True, gap=16)
        for t in left:
            writer.line(f"{t['printed_name']}   {t['value_text']} {t['unit']}   {t['range_text']}")
        if writer.page is not None and len(writer.doc) == 1:
            writer.y = top
            writer.line("Test   Result   Reference Range", x=315, bold=True, gap=16)
            for t in right:
                writer.line(f"{t['printed_name']}   {t['value_text']} {t['unit']}   {t['range_text']}", x=315)

    # ---- footer notes ----
    writer.gap(10)
    if rng.random() < 0.5:
        writer.line("Note: Reference ranges may vary between laboratories.", size=8)
    if rng.random() < 0.4:
        writer.line("Doctor's Note: This is a computer generated test report.", size=8)

    doc = writer.finish()

    if layout == "scanned":                       # replace the text with a picture of it
        image_doc = pymupdf.open()
        for page in doc:
            pixmap = page.get_pixmap(dpi=100)
            new_page = image_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=pixmap)
        return image_doc

    return doc


# ------------------------------------------------------------------- main ---

def generate_one(rng, index):

    layout = rng.choices(list(LAYOUTS), weights=list(LAYOUTS.values()))[0]
    sex = rng.choice(["M", "F"])
    age = rng.randint(19, 78)
    thousands = rng.random() < 0.35
    dash = rng.choice([" - ", " - ", "-", " – "])
    spaced_less_than = rng.random() < 0.6
    upper = rng.random() < 0.12

    panels = rng.sample(PANELS, rng.randint(1, 3))
    keys = [k for p in panels for k, v in CATALOGUE.items() if v["panel"] == p]
    keys = rng.sample(keys, min(len(keys), rng.randint(5, 16))) if len(keys) > 5 else keys
    keys.sort(key=lambda k: (CATALOGUE[k]["panel"], k))

    range_style = rng.choices(list(RANGE_STYLES), weights=list(RANGE_STYLES.values()))[0]
    censor_report = rng.random() < 0.3
    if range_style == "sex_both" and layout == "two_columns":
        range_style = "plain"        # the two side-by-side columns have no room for two ranges
    tests = [make_test(rng, k, sex, thousands, dash, spaced_less_than, range_style,
                       censor_report and rng.random() < 0.5) for k in keys]

    doc = render(rng, layout, tests, sex, age, upper, wide_range=(range_style == "sex_both"))

    return layout, sex, tests, doc


def main():

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default=str(HERE / "synthetic"))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for old in list(out.glob("report_*.pdf")) + list(out.glob("report_*.json")):
        old.unlink()

    rng = random.Random(args.seed)

    counts = {}

    for index in range(1, args.count + 1):

        layout, sex, tests, doc = generate_one(rng, index)

        name = f"report_{index:03d}_{layout}"
        doc.save(out / f"{name}.pdf")
        doc.close()

        key = {
            "file": f"{name}.pdf", "layout": layout, "sex": sex,
            "expect_readable": layout != "scanned",
            "tests": [{k: t[k] for k in ("key", "printed_name", "value", "unit", "min", "max", "expected_status")}
                      for t in tests],
        }
        (out / f"{name}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")

        counts[layout] = counts.get(layout, 0) + 1

    print(f"Generated {args.count} reports in {out}  (seed {args.seed})")
    for layout, count in sorted(counts.items(), key=lambda item: -item[1]):
        print(f"  {layout:<20}{count}")


if __name__ == "__main__":
    main()
