"""
Converts the three analysis scripts into proper Jupyter notebooks (.ipynb).
Each section comment (# ── SECTION ──) becomes a Markdown heading cell.
"""

import nbformat
import re
from pathlib import Path


def make_notebook(script_path, out_path, title, description):
    src = Path(script_path).read_text()

    nb = nbformat.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.0"},
    }

    cells = []

    # ── Title & description markdown
    cells.append(nbformat.v4.new_markdown_cell(
        f"# {title}\n\n{description}"
    ))

    # ── Setup / imports cell (everything before first section divider)
    # Split the entire script on "# ─────" or "# ═════" dividers
    divider_pattern = re.compile(r'\n# [─═]{10,}.*\n# .*\n# [─═]{10,}', re.MULTILINE)

    # Find all divider spans
    dividers = list(divider_pattern.finditer(src))

    if not dividers:
        # No dividers — just one big code cell
        cells.append(nbformat.v4.new_code_cell(src.strip()))
    else:
        # Preamble before first divider
        preamble = src[:dividers[0].start()].strip()
        if preamble:
            cells.append(nbformat.v4.new_code_cell(preamble))

        for i, div in enumerate(dividers):
            # Extract section title from divider block
            div_text = div.group()
            title_line = [ln for ln in div_text.split('\n') if ln.startswith('# ')
                          and not set(ln.replace('# ','').strip()) <= set('─═')]
            section_title = title_line[0].lstrip('# ').strip() if title_line else "Section"

            cells.append(nbformat.v4.new_markdown_cell(f"## {section_title}"))

            # Code between this divider end and next divider start (or end of file)
            code_start = div.end()
            code_end   = dividers[i + 1].start() if i + 1 < len(dividers) else len(src)
            code_block  = src[code_start:code_end].strip()

            if code_block:
                cells.append(nbformat.v4.new_code_cell(code_block))

    nb["cells"] = cells
    nbformat.write(nb, out_path)
    print(f"  Wrote {out_path}  ({len(nb['cells'])} cells)")


make_notebook(
    "scripts/03_eda.py",
    "notebooks/03_eda.ipynb",
    "Notebook 3 — Exploratory Data Analysis",
    "**Problem:** Analyze scheduling factors in FIFA World Cup history (1930–2014).\n\n"
    "Covers: tournament growth, match results, goals patterns, host advantage, "
    "rest days, discipline, attendance, match timing, team performance, player workload, "
    "and a correlation heatmap."
)

make_notebook(
    "scripts/04_statistical_analysis.py",
    "notebooks/04_statistical_analysis.ipynb",
    "Notebook 4 — Statistical Analysis",
    "**Problem:** Test 10 scheduling-relevant hypotheses using t-tests, chi-square, "
    "ANOVA, correlation, and logistic regression.\n\n"
    "Key questions: Is home advantage real? Does host status help? Do rest days matter? "
    "Can we predict match outcome from scheduling factors?"
)

make_notebook(
    "scripts/05_kpi_tableau_prep.py",
    "notebooks/05_final_load_prep.ipynb",
    "Notebook 5 — KPI Computation & Tableau Export",
    "**Problem:** Compute all scheduling KPIs and export Tableau-ready CSVs.\n\n"
    "Outputs: 11 KPI tables + 3 main Tableau datasets exported to `tableau/`."
)

print()
print("All notebooks created.")
