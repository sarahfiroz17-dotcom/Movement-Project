"""
Generate Service_4_Anomaly_Detection_Report.docx
Run with: /usr/bin/python3 generate_s4_report.py
Matches structure and detail level of the Service 4 PDF (Dua Muhammad).
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

for section in doc.sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(2.8)
    section.right_margin  = Cm(2.8)

# Colours — blue/purple palette for Service 4
BLUE   = RGBColor(0x37, 0x8A, 0xDD)
PURPLE = RGBColor(0x7F, 0x77, 0xDD)
AMBER  = RGBColor(0xEF, 0x9F, 0x27)
GREEN  = RGBColor(0x5D, 0xCA, 0xA5)
RED    = RGBColor(0xCC, 0x44, 0x44)
GREY   = RGBColor(0x55, 0x55, 0x55)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
DARK   = RGBColor(0x1A, 0x1A, 0x2E)

HDR_HEX   = "1A2A4A"   # dark navy header
BEST_HEX  = "1A4A2A"   # dark green — top tier
GOOD_HEX  = "2A3A5A"   # medium blue — good tier
WARN_HEX  = "4A2A00"   # amber — caution
FAIL_HEX  = "4A1A1A"   # dark red — poor

# ── Helpers ───────────────────────────────────────────────────────────────────

def set_cell_bg(cell, hex_color):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.upper()); tcPr.append(shd)

def set_cell_bold_white(cell, text, size=9):
    cell.text = ""
    p = cell.paragraphs[0]; run = p.add_run(text)
    run.bold = True; run.font.size = Pt(size); run.font.color.rgb = WHITE

def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    col = BLUE if level == 1 else (PURPLE if level == 2 else RGBColor(0x4A, 0x6A, 0xAA))
    for run in p.runs:
        run.font.color.rgb = col
    return p

def add_para(doc, text, size=10.5, bold=False, color=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text); run.font.size = Pt(size); run.bold = bold
    if color: run.font.color.rgb = color
    return p

def add_bullet(doc, text, size=10):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(text).font.size = Pt(size)
    return p

def add_table(doc, headers, rows, col_widths=None, hdr_hex=None):
    hdr_hex = hdr_hex or HDR_HEX
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    hdr = tbl.rows[0]
    for i, h in enumerate(headers):
        set_cell_bg(hdr.cells[i], hdr_hex)
        set_cell_bold_white(hdr.cells[i], h, size=9)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.rows[ri+1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
            if ri % 2 == 0:
                set_cell_bg(cell, "EEF3FA")
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in tbl.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return tbl

def add_algo_block(doc, name, props, extra_paras=None):
    h = doc.add_heading(name, level=3)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x26, 0x50, 0x8A)
    tbl = doc.add_table(rows=len(props), cols=2)
    tbl.style = "Table Grid"
    for ri, (k, v) in enumerate(props):
        tbl.rows[ri].cells[0].text = k
        tbl.rows[ri].cells[1].text = v
        for p in tbl.rows[ri].cells[0].paragraphs:
            for run in p.runs:
                run.bold = True; run.font.size = Pt(9)
        for p in tbl.rows[ri].cells[1].paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)
        if ri % 2 == 0:
            set_cell_bg(tbl.rows[ri].cells[0], "E8EEF7")
            set_cell_bg(tbl.rows[ri].cells[1], "E8EEF7")
    tbl.columns[0].width = Inches(1.8)
    tbl.columns[1].width = Inches(4.5)
    doc.add_paragraph()
    for label, text in (extra_paras or []):
        p = doc.add_paragraph()
        if label:
            r1 = p.add_run(f"{label}  "); r1.bold = True
            r1.font.size = Pt(10); r1.font.color.rgb = RGBColor(0x1A, 0x2A, 0x4A)
        r2 = p.add_run(text); r2.font.size = Pt(10)
        p.paragraph_format.space_after = Pt(4)
    doc.add_paragraph()

def bar(score, total=5, fill_hex="1A4A8A", empty_hex="D0D8EA"):
    return [fill_hex] * score + [empty_hex] * (total - score)


# ════════════════════════════════════════════════════════════════════════════
# COVER
# ════════════════════════════════════════════════════════════════════════════

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("VEBITA"); r.bold = True; r.font.size = Pt(28); r.font.color.rgb = BLUE

p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = p2.add_run("Service 4 — Anomaly Detection")
r2.font.size = Pt(18); r2.font.color.rgb = GREY

p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = p3.add_run("Technical Project Report")
r3.font.size = Pt(14); r3.font.color.rgb = GREY

doc.add_paragraph()
for lbl, val in [("Author", "Dua Muhammad"), ("Service ID", "4"),
                  ("Project", "VEBITA — Animal Movement Analysis Platform"),
                  ("Date", "October 2026")]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{lbl}:  "); r.bold = True; r.font.size = Pt(11)
    r2 = p.add_run(val); r2.font.size = Pt(11)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 1. SERVICE OVERVIEW
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "1. Service Overview", 1)
add_para(doc,
    "Service 4 — Anomaly Detection — finds GPS fixes in animal tracking data that are "
    "either measurement errors (position jumps, impossible speeds, altitude spikes) or "
    "genuinely rare behaviour events (escape runs, migration starts, predator encounters). "
    "Both must be identified before any downstream analysis because a single bad fix can "
    "corrupt step length, speed, turning angle and straightness for all adjacent fixes.")

add_para(doc,
    "Unlike Services 3 and 6 which produce continuous scores or behaviour labels, "
    "Service 4 produces a binary output: 1 = anomalous fix, 0 = normal fix. "
    "All 23 detectors are unsupervised — they require no labelled training data, "
    "which is essential because no Movebank dataset records which fixes are wrong.")

add_heading(doc, "Scope", 2)
add_table(doc,
    ["Property", "Value"],
    [
        ["Total algorithms",       "23"],
        ["Algorithm families",     "6  (Statistical, Tree/Ensemble, Kernel/Distance, Probabilistic, Neural, Movement-specific)"],
        ["Service type",           "Binary anomaly detection (0 = normal, 1 = anomaly)"],
        ["Output per algorithm",   "Binary array (0/1 per GPS fix)"],
        ["Threshold strategy",     "95th percentile of training scores (most detectors); 5% contamination (Elliptic Envelope, Isolation Forest, One-Class SVM)"],
        ["Applicable datasets",    "All Movebank animal species"],
        ["File location",          "backend/vebita_framework/services/s4_anomaly/dua_algorithms.py"],
    ],
    col_widths=[2.0, 4.3])

add_heading(doc, "What is an anomaly?", 2)
add_para(doc, "There are three kinds of anomalies the service can detect:")
for name, desc in [
    ("Point anomaly",       "A single fix that is extreme on its own — e.g. a swan recorded at ground speed 90 m/s."),
    ("Contextual anomaly",  "A fix that is only unusual given its neighbours in time — e.g. altitude 200 m between two fixes at 20–25 m."),
    ("Collective anomaly",  "A run of consecutive fixes that are unusual together — e.g. slow positional drift while the animal is resting."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{name}:  "); r1.bold = True; r1.font.size = Pt(10)
    r1.font.color.rgb = BLUE
    r2 = p.add_run(desc); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)

doc.add_paragraph()
add_para(doc,
    "Most of the 23 detectors find point anomalies in the 8-dimensional feature space. "
    "The movement-specific detectors (F91, F93, F97, F100) and CUSUM (A11) also use the "
    "order of fixes, so they can find contextual and collective anomalies.",
    size=10, color=GREY)


# ════════════════════════════════════════════════════════════════════════════
# 2. ARCHITECTURE & DATA FLOW
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "2. Architecture & Data Flow", 1)

add_heading(doc, "Integration into the VEBITA framework", 2)
add_para(doc,
    "Every detector inherits from BaseAlgorithm (core/base.py), implements fit(X) and "
    "predict(X), and self-registers with @registry.register under service_id = 4. "
    "Adding a new detector means adding one class — no changes to the backend are needed.")

add_heading(doc, "Run pipeline", 2)
for step in [
    "1.  User uploads a Movebank CSV",
    "2.  Shared streaming pipeline extracts 8 features per GPS fix",
    "3.  Temporal split: first 80% of fixes → training, last 20% → test",
    "4.  User picks two detectors in the UI",
    "5.  detector.fit(X_train)  →  detector.predict(X_test)  →  binary vector",
    "6.  Frontend shows flagged fixes on map + comparison charts + runtime",
]:
    p = doc.add_paragraph(step)
    p.paragraph_format.space_after = Pt(2)
    for run in p.runs:
        run.font.size = Pt(10); run.font.name = "Courier New"
doc.add_paragraph()

add_heading(doc, "Input feature matrix (5 visible + 3 internal)", 2)
add_para(doc,
    "All 23 detectors work on the same 8-column feature matrix. Five features are visible "
    "in the app (map popups, Time Series tab). Three rolling features are computed internally "
    "by the streaming pipeline and never shown as raw values on screen.")

add_table(doc,
    ["Col", "Feature", "Description", "Visible in app"],
    [
        ["0", "speed_ms",        "Ground speed (m/s), or step length ÷ time when tag doesn't record it",  "Yes — Time Series, popup"],
        ["1", "altitude_m",      "Height above MSL (0 if tag doesn't record altitude)",                    "Yes — Time Series, popup"],
        ["2", "turning_angle",   "Change in heading between consecutive fixes (0–180°)",                   "Yes — Time Series"],
        ["3", "straightness",    "Net displacement ÷ path length over 5 fixes (0–1)",                     "Yes — Time Series"],
        ["4", "speed_roll_mean", "5-fix centred rolling mean of speed_ms",                                 "No — backend only"],
        ["5", "speed_roll_std",  "5-fix centred rolling std of speed_ms",                                  "No — backend only"],
        ["6", "step_length_m",   "Haversine distance to previous GPS fix (metres)",                        "Yes — Time Series histogram"],
        ["7", "alt_roll_mean",   "5-fix centred rolling mean of altitude_m",                               "No — backend only"],
    ],
    col_widths=[0.4, 1.4, 3.3, 1.2])

add_heading(doc, "Threshold strategy", 2)
add_para(doc,
    "Most detectors flag fixes whose score exceeds the 95th percentile of scores seen on "
    "training data — so roughly 5% of normal fixes are flagged (false alarms). "
    "Three detectors instead set an expected contamination of 5%: Elliptic Envelope, "
    "Isolation Forest and One-Class SVM. This makes all 23 detectors directly comparable "
    "in the app's side-by-side view.")


# ════════════════════════════════════════════════════════════════════════════
# 3. ALGORITHM CATALOGUE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "3. Algorithm Catalogue", 1)

add_heading(doc, "Family overview", 2)
add_table(doc,
    ["Family", "Definition of 'normal'", "Detectors in this family"],
    [
        ["A — Statistical",          "Close to the centre of a fitted distribution",          "A01 Z-Score Max, A04 Mahalanobis, A05 Robust Mahalanobis, A06 IQR Outlier, A07 Modified Z-Score (MAD), A11 CUSUM, A13 Elliptic Envelope"],
        ["B — Tree & ensemble",      "Hard to separate from the rest with random splits",     "B31 Isolation Forest, B41 DBSCAN Noise Points, B45 One-Class SVM"],
        ["C — Kernel & distance",    "Close to other fixes in feature space",                 "C56 LOF k=20, C60 LOF Cosine, C61 KNN Mean Distance, C64 Gaussian KDE"],
        ["D — Probabilistic",        "High probability under a fitted statistical model",     "D71 Gaussian Log-Likelihood, D73 Gamma Distribution Tail, D80 GMM Log-Likelihood"],
        ["E — Neural proxy",         "Easy to compress and reconstruct",                      "E81 PCA Reconstruction, E85 Autoencoder Tanh"],
        ["F — Movement-specific",    "Physically plausible change between consecutive fixes", "F91 Velocity Jerk, F93 Altitude Drop, F97 Multi-Feature Temporal Change, F100 Composite Movement Score"],
    ],
    col_widths=[1.4, 2.0, 3.0])

doc.add_page_break()

# ── Family A: Statistical ─────────────────────────────────────────────────────
add_heading(doc, "3.1  Family A — Statistical  (7 detectors)", 2)

add_algo_block(doc, "A01 Z-Score Max",
    [("Family","A — Statistical"), ("Anomaly score","Largest absolute z-score over all 8 features"),
     ("Features used","All 8"), ("Threshold","95th percentile of training scores"), ("Runtime (stork)","0.04 s")],
    extra_paras=[
        ("What it does:",
         "For each GPS fix, computes the standard z-score for each of the 8 features "
         "((value − mean) / std) and takes the maximum absolute value. A fix is anomalous "
         "if ANY single feature is unusually far from its mean. Fast and effective as a baseline."),
        ("Benchmark result:", "F1 = 0.41 (rank 2). Found 94% of position errors, 100% of speed errors. Simple and strong."),
    ])

add_algo_block(doc, "A04 Mahalanobis Distance",
    [("Family","A — Statistical"), ("Anomaly score","Squared Mahalanobis distance from the mean"),
     ("Features used","All 8"), ("Covariance","Pseudo-inverse (handles near-singular matrices)"), ("Runtime (stork)","0.05 s")],
    extra_paras=[
        ("What it does:",
         "Extends the z-score to multiple correlated features. Uses the full covariance matrix Σ, "
         "so a fix that is unusual only in its combination of speed AND step length (even if each "
         "is individually normal) is still detected. Formula: D²(x) = (x − μ)ᵀ Σ⁻¹ (x − μ)."),
        ("Benchmark result:", "F1 = 0.41 (rank 3). Found 96% of position and 100% of speed errors. Accounts for feature correlations at almost no cost."),
    ])

add_algo_block(doc, "A05 Robust Mahalanobis",
    [("Family","A — Statistical"), ("Anomaly score","Mahalanobis distance with robust mean and covariance"),
     ("Robust estimation","Mean and covariance computed only from fixes inside the IQR of every feature"),
     ("Fallback","Uses all fixes if too few survive the IQR filter"), ("Runtime (stork)","0.09 s")],
    extra_paras=[
        ("What it does:",
         "Same as A04 but protects against the case where many anomalies inflate the mean and "
         "covariance, making outliers look normal. By computing the centre and spread only from "
         "well-behaved fixes (inside the IQR), the reference point itself stays clean."),
        ("Benchmark result:", "F1 = 0.40 (rank 7). Found every position error, 91% of speed errors. Best on cuckoo data (F1 = 0.48)."),
    ])

add_algo_block(doc, "A06 IQR Outlier",
    [("Family","A — Statistical"), ("Anomaly score","1 if any feature is outside Q1 − 1.5·IQR or Q3 + 1.5·IQR"),
     ("Threshold","Fixed Tukey fences — no percentile"), ("Runtime (stork)","0.05 s")],
    extra_paras=[
        ("What it does:",
         "Applies standard Tukey box-plot fences to each of the 8 features. A fix is flagged "
         "if any single feature falls outside those fixed fences. Very simple to understand."),
        ("Key limitation:",
         "Movement features are heavily skewed (most steps are short but a few are very long). "
         "This caused A06 to flag 19% of perfectly clean fixes on average — far too many false alarms."),
        ("Benchmark result:", "F1 = 0.22 (rank 18). Found every error but 19% false alarms make it unreliable."),
    ])

add_algo_block(doc, "A07 Modified Z-Score (MAD)",
    [("Family","A — Statistical"), ("Anomaly score","Largest modified z-score using median and MAD"),
     ("Formula","Mᵢ = 0.6745 · (xᵢ − median) / MAD"), ("Features used","All 8"), ("Runtime (stork)","0.07 s")],
    extra_paras=[
        ("What it does:",
         "Replaces mean and standard deviation with median and Median Absolute Deviation (MAD). "
         "Because the median and MAD are not affected by the outliers themselves, this avoids "
         "the 'masking effect' where many outliers inflate the scale and hide each other."),
        ("Benchmark result:", "F1 = 0.37 (rank 12). Found every position error but only 52% of speed errors — speed is dominated by step length in unscaled features."),
    ])

add_algo_block(doc, "A11 CUSUM",
    [("Family","A — Statistical"), ("Anomaly score","Running maximum of the absolute cumulative sum of speed minus its mean"),
     ("Features used","Speed only"), ("Uses fix order","Yes"), ("Runtime (stork)","0.00 s")],
    extra_paras=[
        ("What it does:",
         "Cumulative Sum control chart: accumulates the deviation of speed from its mean. "
         "A sustained increase or decrease in speed shows up as a drift in the cumulative sum. "
         "Designed to catch slow trends and step changes, not single-point spikes."),
        ("Key limitation:",
         "On the long training series the running maximum grows large. The shorter test series "
         "rarely reaches that level, so CUSUM flags almost nothing. A windowed reset would fix this."),
        ("Benchmark result:", "F1 = 0.01 (rank 22). Found only 13% of position errors. Not recommended in current form."),
    ])

add_algo_block(doc, "A13 Elliptic Envelope",
    [("Family","A — Statistical"), ("Anomaly score","Robust Mahalanobis distance via Minimum Covariance Determinant"),
     ("Contamination","5% (sklearn contamination=0.05)"), ("Support fraction","0.9"),
     ("Runtime (stork)","6.78 s — 127.5 s on 13.4 million fixes")],
    extra_paras=[
        ("What it does:",
         "Fits a multivariate Gaussian to the 'core' 90% of training fixes (the minimum covariance "
         "determinant estimate). This is the most robust statistical detector — not just the IQR "
         "per feature but a proper multivariate robust fit. Fixes outside the ellipsoid boundary "
         "are flagged."),
        ("Key limitation:", "Training cost scales with all training fixes, not a sample — takes 127 seconds on 13.4 million fixes."),
        ("Benchmark result:", "F1 = 0.41 (rank 5). Found 100% of all error types. Most reliable statistical detector."),
    ])

# ── Family B: Tree & ensemble ─────────────────────────────────────────────────
add_heading(doc, "3.2  Family B — Tree & Ensemble  (3 detectors)", 2)

add_algo_block(doc, "B31 Isolation Forest",
    [("Family","B — Tree & ensemble"), ("Anomaly score","Average path length in 100 random trees"),
     ("Contamination","5% (contamination=0.05)"), ("Library","sklearn"), ("Runtime (stork)","1.02 s")],
    extra_paras=[
        ("What it does:",
         "Builds 100 random decision trees that split the data on randomly chosen features and "
         "values. Anomalies are few and extreme, so they get isolated (separated from all others) "
         "with fewer splits. The score is the average path length — shorter path = more anomalous."),
        ("Benchmark result:", "F1 = 0.39 (rank 10). Found 100% of position and speed errors but only 53% of altitude errors."),
    ])

add_algo_block(doc, "B41 DBSCAN Noise Points",
    [("Family","B — Tree & ensemble"), ("Anomaly score","Distance to the nearest core point of DBSCAN clusters"),
     ("Settings","eps = 0.8, min_samples = 5"), ("Training sample","2,000 standardised fixes"),
     ("Library","sklearn"), ("Runtime (stork)","0.58 s")],
    extra_paras=[
        ("What it does:",
         "Runs DBSCAN density-based clustering on the standardised features. Fixes that don't "
         "belong to any cluster (noise points) are flagged as anomalies. The score is the distance "
         "to the nearest core point — farther from all clusters = more anomalous."),
        ("Important caveat:",
         "DBSCAN ranked #1 on the current pipeline (F1 = 0.62) because it raised only 3% false "
         "alarms. However, this was because speed was always 0 on 3 of 5 datasets (a pipeline "
         "bug), making the feature space artificially simple. With a corrected pipeline its F1 "
         "drops to 0.29 (rank 17) because its fixed eps radius no longer fits the true variation."),
        ("Benchmark result:", "F1 = 0.62 (rank 1, current pipeline) / 0.29 (rank 17, corrected pipeline). Not a safe default."),
    ])

add_algo_block(doc, "B45 One-Class SVM",
    [("Family","B — Tree & ensemble"), ("Anomaly score","Signed distance to an RBF kernel boundary"),
     ("Settings","nu = 0.05"), ("Training sample","2,000 standardised fixes"),
     ("Library","sklearn"), ("Runtime (stork)","0.18 s")],
    extra_paras=[
        ("What it does:",
         "Learns a tight non-linear boundary around the normal fixes in the high-dimensional "
         "RBF kernel space. Fixes outside the boundary are anomalies. nu controls the fraction "
         "of training fixes that may fall outside the boundary (like a soft contamination rate)."),
        ("Benchmark result:", "F1 = 0.38 (rank 11). Found 100% of position and speed errors, 99% of altitude errors. Consistent across datasets."),
    ])

# ── Family C: Kernel & distance ───────────────────────────────────────────────
add_heading(doc, "3.3  Family C — Kernel & Distance  (4 detectors)", 2)

add_algo_block(doc, "C56 LOF k=20",
    [("Family","C — Kernel & distance"), ("Anomaly score","Local Outlier Factor against a reference set"),
     ("Reference set","500 training fixes, novelty mode"), ("k","20 nearest neighbours"), ("Runtime (stork)","0.14 s")],
    extra_paras=[
        ("What it does:",
         "Compares the density around each test fix with the density around its 20 nearest "
         "reference fixes. A ratio well above 1.0 means the test fix sits in a sparser region "
         "than its neighbours — it is locally unusual even if it is not globally extreme. "
         "Uses scikit-learn novelty mode so new fixes are scored against the fixed reference set."),
        ("Benchmark result:", "F1 = 0.34 (rank 15). Found every position error and every altitude error but only 57% of speed errors (unscaled features)."),
    ])

add_algo_block(doc, "C60 LOF Cosine",
    [("Family","C — Kernel & distance"), ("Anomaly score","LOF with cosine distance metric"),
     ("Reference set","500 training fixes, novelty mode"), ("Runtime (stork)","1.87 s")],
    extra_paras=[
        ("What it does:",
         "Identical to C56 but uses cosine distance (angle between feature vectors) instead of "
         "Euclidean distance. Cosine distance cares about direction, not magnitude."),
        ("Key limitation:",
         "A position error makes step length and speed larger — it changes the magnitude of the "
         "feature vector, not its direction. Cosine distance misses this, finding only 30% of "
         "position errors. Use C56 LOF k=20 instead."),
        ("Benchmark result:", "F1 = 0.12 (rank 19). Poor on position errors. Not recommended."),
    ])

add_algo_block(doc, "C61 KNN Mean Distance",
    [("Family","C — Kernel & distance"), ("Anomaly score","Mean Euclidean distance to the 5 nearest reference fixes"),
     ("Reference set","500 training fixes"), ("Runtime (stork)","0.09 s")],
    extra_paras=[
        ("What it does:",
         "Computes the average distance to the 5 nearest training fixes. A fix far from all its "
         "neighbours is anomalous. Simpler than LOF — it doesn't account for how dense the "
         "neighbourhood itself is, but is faster and easier to understand."),
        ("Key limitation:", "Works on unscaled features, so step length (thousands of metres) dominates over speed errors (a few m/s)."),
        ("Benchmark result:", "F1 = 0.31 (rank 16). Found every position error but only 25% of speed errors."),
    ])

add_algo_block(doc, "C64 Gaussian KDE",
    [("Family","C — Kernel & distance"), ("Anomaly score","Negative log density under a Gaussian kernel"),
     ("Bandwidth","1.0"), ("Reference set","200 standardised training fixes"), ("Runtime (stork)","0.47 s")],
    extra_paras=[
        ("What it does:",
         "Fits a smooth probability density function over the 200 reference fixes using a "
         "Gaussian kernel. Each test fix is scored by how unlikely it is under this density — "
         "low density = anomalous. Standardises features before fitting."),
        ("Benchmark result:", "F1 = 0.31 (rank 17). Found 97–100% of all error types but flagged 10.5% of clean fixes."),
    ])

# ── Family D: Probabilistic ───────────────────────────────────────────────────
add_heading(doc, "3.4  Family D — Probabilistic  (3 detectors)", 2)

add_algo_block(doc, "D71 Gaussian Log-Likelihood",
    [("Family","D — Probabilistic"), ("Anomaly score","Negative multivariate Gaussian log-likelihood"),
     ("Note","Mathematically identical to A04 Mahalanobis on every dataset"), ("Runtime (stork)","0.05 s")],
    extra_paras=[
        ("What it does:",
         "Fits a multivariate Gaussian and scores each fix by its negative log-likelihood under "
         "that distribution. Mathematically, this produces the same ranking as squared Mahalanobis "
         "distance — D71 only differs by adding 10⁻⁶ to the diagonal of the covariance matrix "
         "for numerical stability."),
        ("Benchmark result:", "F1 = 0.41 (rank 4). Identical results to A04 on every dataset — adds no new information in a comparison."),
    ])

add_algo_block(doc, "D73 Gamma Distribution Tail",
    [("Family","D — Probabilistic"), ("Anomaly score","Negative log density under a gamma distribution fitted to speed"),
     ("Features used","Speed only"), ("Limitation","Crashes when speed column is all zeros"), ("Runtime (stork)","0.01 s")],
    extra_paras=[
        ("What it does:",
         "Fits a gamma distribution to the training speed values (speed is always positive and "
         "right-skewed — gamma is a natural fit). Flags fixes where the speed is in the far tail "
         "of the fitted distribution — speeds that are impossibly high for this species."),
        ("Key limitation:",
         "When the Movebank dataset has no ground-speed column, the pipeline fills speed with 0. "
         "A constant-zero series has no variance, so the gamma fit fails. This caused D73 to "
         "crash on cuckoo, guillemot and jackal datasets in the current pipeline."),
        ("Benchmark result:", "F1 = 0.11 (rank 20, current pipeline) / 0.34 (rank 10, corrected pipeline). Only useful when speed data is real."),
    ])

add_algo_block(doc, "D80 GMM Log-Likelihood",
    [("Family","D — Probabilistic"), ("Anomaly score","Negative log-likelihood under a 3-component Gaussian mixture"),
     ("Training sample","20,000 fixes"), ("Library","sklearn GaussianMixture"), ("Runtime (stork)","0.66 s")],
    extra_paras=[
        ("What it does:",
         "Fits a mixture of 3 Gaussian distributions to the 8-dimensional feature space. "
         "Normal fixes belong clearly to one of the 3 clusters; anomalous fixes have low "
         "probability under all three. Unlike a single Gaussian (D71), the mixture can model "
         "multi-modal behaviour — e.g. resting, foraging and migrating have different speed profiles."),
        ("Benchmark result:", "F1 = 0.40 (rank 8). Found 100% of position and speed errors, 97% of altitude errors. One of the three most stable detectors."),
    ])

# ── Family E: Neural proxy ────────────────────────────────────────────────────
add_heading(doc, "3.5  Family E — Neural Proxy  (2 detectors)", 2)

add_algo_block(doc, "E81 PCA Reconstruction",
    [("Family","E — Neural proxy"), ("Anomaly score","Mean squared reconstruction error using 2 principal components"),
     ("Features used","All 8"), ("Library","sklearn PCA"), ("Runtime (stork)","0.03 s")],
    extra_paras=[
        ("What it does:",
         "Compresses each fix into 2 principal components (the two directions of maximum variance) "
         "and reconstructs it. Normal fixes are well-explained by these two components; anomalous "
         "fixes have high reconstruction error because they don't fit the dominant patterns."),
        ("Key limitation:",
         "The two principal components are dominated by step length and altitude (the features with "
         "the largest ranges). A position error changes step length, so PCA catches it. But it "
         "reconstructs a quarter of position errors well and misses them entirely — see rank 14."),
        ("Benchmark result:", "F1 = 0.34 (rank 14). Found 74% of position errors and 100% of speed errors."),
    ])

add_algo_block(doc, "E85 Autoencoder Tanh",
    [("Family","E — Neural proxy"), ("Anomaly score","Reconstruction error of an 8-4-8 tanh autoencoder"),
     ("Architecture","Input(8) → Hidden(4) → Output(8)"), ("Training","50 epochs, lr = 0.01"),
     ("Training sample","20,000 standardised fixes"), ("Runtime (stork)","0.15 s")],
    extra_paras=[
        ("What it does:",
         "Trains a small neural autoencoder to compress 8 features into 4 and reconstruct them. "
         "The bottleneck forces the network to learn only what is common to normal fixes. "
         "Anomalous fixes don't fit the learned compression — their reconstruction error is high. "
         "Note: this network is implemented in pure numpy (no PyTorch/TensorFlow)."),
        ("Benchmark result:", "F1 = 0.40 (rank 9). Found 94% of position, 100% of speed, 96% of altitude errors. Behaves similarly to Mahalanobis (Jaccard overlap 0.80)."),
    ])

# ── Family F: Movement-specific ───────────────────────────────────────────────
add_heading(doc, "3.6  Family F — Movement-Specific  (4 detectors)", 2)

add_algo_block(doc, "F91 Velocity Jerk",
    [("Family","F — Movement-specific"), ("Anomaly score","Absolute third difference of speed"),
     ("Features used","Speed only"), ("Uses fix order","Yes"), ("Runtime (stork)","0.00 s")],
    extra_paras=[
        ("What it does:",
         "Jerk is the rate of change of acceleration — the third derivative of position. "
         "For GPS data it is approximated as the third difference of speed: "
         "|speed[t] − 3·speed[t-1] + 3·speed[t-2] − speed[t-3]|. "
         "A sudden spike in speed (like a GPS jump) produces a large jerk value."),
        ("Key limitation:", "Only looks at speed. A position error does not change recorded ground speed (when the tag records it), so F91 misses 88% of position errors."),
        ("Benchmark result:", "F1 = 0.10 (rank 21, current) / 0.27 (rank 18, corrected). Only useful for speed errors when real speed is available."),
    ])

add_algo_block(doc, "F93 Altitude Drop",
    [("Family","F — Movement-specific"), ("Anomaly score","Size of altitude decrease since the previous fix"),
     ("Features used","Altitude only"), ("Uses fix order","Yes"), ("Runtime (stork)","0.00 s")],
    extra_paras=[
        ("What it does:",
         "Flags fixes where altitude drops sharply relative to the previous fix. Designed for "
         "birds where a sudden altitude drop may indicate a GPS error (altitude spike then "
         "return) or a genuine dive event."),
        ("Key limitation:",
         "Altitude is read from the height-above-msl column in Movebank CSVs, which is empty "
         "in all 13 uploaded datasets. Altitude is therefore 0 everywhere in the current pipeline, "
         "and F93 cannot fire at all. With corrected altitude it found 97% of altitude errors."),
        ("Benchmark result:", "F1 = 0.00 (rank 23, current) / 0.15 (rank 21, corrected). Unusable until pipeline reads height-above-ellipsoid instead."),
    ])

add_algo_block(doc, "F97 Multi-Feature Temporal Change",
    [("Family","F — Movement-specific"), ("Anomaly score","Sum of absolute changes across all 8 features since the previous fix"),
     ("Features used","All 8"), ("Uses fix order","Yes"), ("Runtime (stork)","0.01 s")],
    extra_paras=[
        ("What it does:",
         "Computes how much each feature changed between consecutive fixes, then sums the "
         "absolute changes across all 8 features. A GPS position error creates a sudden jump "
         "in step length, turning angle and straightness simultaneously — the sum of changes "
         "is very large."),
        ("Key limitation:", "Works on unscaled features. A speed error of a few m/s contributes very little to the sum compared to a step length jump of thousands of metres."),
        ("Benchmark result:", "F1 = 0.36 (rank 13). Found 100% of position errors but only 23% of speed errors."),
    ])

add_algo_block(doc, "F100 Composite Movement Score",
    [("Family","F — Movement-specific"), ("Anomaly score","Sum of absolute z-scores of speed, altitude, turning angle, step length"),
     ("Features used","4 key movement features"), ("Runtime (stork)","0.01 s")],
    extra_paras=[
        ("What it does:",
         "Computes the z-score for each of the 4 most ecologically meaningful movement features "
         "(speed, altitude, turning angle, step length) and sums the absolute values. "
         "A fix that is extreme on ANY of these four dimensions contributes to the score. "
         "By using z-scores it normalises for the different scales of each feature — "
         "a speed of 5 m/s vs a step of 5,000 m both contribute equally if both are 3 standard deviations from their means."),
        ("Why it's the best overall:",
         "It is the ONLY detector that ranks in the top 10 in both the current and corrected "
         "pipeline (rank 6 and rank 1). It is also the fastest detector at 0.01 s, and it is "
         "easy to explain — a high score simply means the animal's movement was unusual on at "
         "least one dimension."),
        ("Benchmark result:", "F1 = 0.40 (rank 6, current) / 0.41 (rank 1, corrected). Best overall. Found 98% of position, 100% of speed, 97% of altitude errors."),
    ])


# ════════════════════════════════════════════════════════════════════════════
# 4. BENCHMARK RESULTS
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "4. Benchmark Results", 1)

add_para(doc,
    "Because no Movebank dataset labels which fixes are wrong, a purpose-built benchmark "
    "was used: artificial GPS errors were injected into 5 real datasets and all 23 detectors "
    "were tested on whether they found them. Results are shown for both the current "
    "VEBITA pipeline (speed = 0 on 3 datasets, altitude = 0 everywhere) and a corrected pipeline.")

add_heading(doc, "Datasets used in the benchmark", 2)
add_table(doc,
    ["Dataset", "GPS fixes", "Animals", "Test fixes", "Ground speed recorded"],
    [
        ["African cuckoo, Nigeria",       "5,352",   "5",  "1,071",  "No"],
        ["Black guillemot, Bangor",        "3,109",  "10",   "622",  "No"],
        ["Whooper swan, Latvia",          "76,706",   "9", "15,341", "Yes"],
        ["Black-backed jackal, Etosha",  "130,688",  "22", "26,138", "No"],
        ["White stork, Tunisia",         "204,727",   "9", "40,946", "Yes"],
    ],
    col_widths=[2.4, 0.9, 0.8, 1.0, 1.6])

add_heading(doc, "How errors were injected", 2)
for item in [
    ("2% of test fixes corrupted", "at least 3 fixes apart, never at track start/end"),
    ("Position error",             "fix moved in a random direction by 2–10× the dataset's 99th-percentile step length"),
    ("Speed error",                "recorded ground speed set to 1.5–4× its 99th percentile (only on datasets that record speed)"),
    ("Tolerance window",           "a detector counts as finding an error if it flags the corrupted fix OR either of the 2 fixes before/after it"),
    ("Seeds",                      "each experiment repeated with 3 random seeds and averaged"),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{item[0]}:  "); r1.bold = True; r1.font.size = Pt(10)
    r2 = p.add_run(item[1]); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)
doc.add_paragraph()

add_heading(doc, "Full ranked results — current VEBITA pipeline", 2)
add_para(doc, "Sorted by F1 score (best first). All 23 detectors on 5 datasets.", size=10, color=GREY)
results_tbl = add_table(doc,
    ["Rank", "Algorithm", "Fam", "Precision", "Recall", "F1", "False alarms", "Runtime (s)"],
    [
        ["1",  "B41 DBSCAN Noise Points",          "B", "0.47", "0.97", "0.62", "3.1%",  "0.58"],
        ["2",  "A01 Z-Score Max",                  "A", "0.27", "0.97", "0.41", "6.8%",  "0.04"],
        ["3",  "A04 Mahalanobis",                  "A", "0.26", "0.98", "0.41", "6.8%",  "0.05"],
        ["4",  "D71 Gaussian Log-Likelihood",       "D", "0.26", "0.98", "0.41", "6.8%",  "0.05"],
        ["5",  "A13 Elliptic Envelope",             "A", "0.26", "1.00", "0.41", "7.1%",  "6.78"],
        ["6",  "F100 Composite Movement Score",     "F", "0.26", "0.99", "0.40", "7.1%",  "0.01"],
        ["7",  "A05 Robust Mahalanobis",            "A", "0.25", "0.98", "0.40", "7.2%",  "0.09"],
        ["8",  "D80 GMM Log-Likelihood",            "D", "0.25", "1.00", "0.40", "6.9%",  "0.66"],
        ["9",  "E85 Autoencoder Tanh",              "E", "0.25", "0.97", "0.40", "6.9%",  "0.15"],
        ["10", "B31 Isolation Forest",              "B", "0.24", "1.00", "0.39", "7.4%",  "1.02"],
        ["11", "B45 One-Class SVM",                 "B", "0.24", "1.00", "0.38", "6.9%",  "0.18"],
        ["12", "A07 Modified Z-Score (MAD)",        "A", "0.24", "0.90", "0.37", "7.1%",  "0.07"],
        ["13", "F97 Multi-Feature Temporal Change", "F", "0.23", "0.85", "0.36", "7.3%",  "0.01"],
        ["14", "E81 PCA Reconstruction",            "E", "0.22", "0.86", "0.34", "6.4%",  "0.03"],
        ["15", "C56 LOF k=20",                      "C", "0.21", "0.91", "0.34", "7.8%",  "0.14"],
        ["16", "C61 KNN Mean Distance",             "C", "0.19", "0.85", "0.31", "8.9%",  "0.09"],
        ["17", "C64 Gaussian KDE",                  "C", "0.19", "0.99", "0.31", "10.5%", "0.47"],
        ["18", "A06 IQR Outlier",                   "A", "0.12", "1.00", "0.22", "19.4%", "0.05"],
        ["19", "C60 LOF Cosine",                    "C", "0.08", "0.40", "0.12", "11.4%", "1.87"],
        ["20", "D73 Gamma Distribution Tail",       "D", "0.18", "0.63", "0.11", "8.1%",  "0.01"],
        ["21", "F91 Velocity Jerk",                 "F", "0.07", "0.26", "0.10", "2.9%",  "0.00"],
        ["22", "A11 CUSUM",                         "A", "0.01", "0.12", "0.01", "3.6%",  "0.00"],
        ["23", "F93 Altitude Drop",                 "F", "0.00", "0.00", "0.00", "0.0%",  "0.00"],
    ],
    col_widths=[0.38, 2.2, 0.38, 0.7, 0.6, 0.5, 0.95, 0.82])

# Colour top 3 rows
for ri in [1, 2, 3]:
    for cell in results_tbl.rows[ri].cells:
        set_cell_bg(cell, "E8F5E8")
for ri in [20, 21, 22, 23]:
    for cell in results_tbl.rows[ri].cells:
        set_cell_bg(cell, "F5E8E8")

add_heading(doc, "F1 per dataset — current pipeline", 2)
add_para(doc, "Rows = algorithms (top performers only), columns = dataset. DBSCAN was best on every dataset.", size=10, color=GREY)
add_table(doc,
    ["Algorithm", "Cuckoo", "Guillemot", "Swan", "Jackal", "Stork"],
    [
        ["B41 DBSCAN Noise Points",      "0.75", "0.62", "0.59", "0.80", "0.33"],
        ["A01 Z-Score Max",              "0.36", "0.59", "0.49", "0.39", "0.21"],
        ["A04 Mahalanobis",              "0.36", "0.55", "0.53", "0.38", "0.22"],
        ["D71 Gaussian Log-Likelihood",  "0.36", "0.55", "0.53", "0.38", "0.22"],
        ["A13 Elliptic Envelope",        "0.48", "0.50", "0.42", "0.40", "0.24"],
        ["F100 Composite Movement Score","0.42", "0.51", "0.44", "0.38", "0.25"],
        ["A05 Robust Mahalanobis",       "0.48", "0.50", "0.38", "0.40", "0.25"],
        ["D80 GMM Log-Likelihood",       "0.47", "0.43", "0.46", "0.37", "0.26"],
        ["E85 Autoencoder Tanh",         "0.37", "0.52", "0.50", "0.39", "0.21"],
        ["A06 IQR Outlier",              "0.26", "0.28", "0.20", "0.24", "0.09"],
        ["F91 Velocity Jerk",            "0.00", "0.00", "0.32", "0.00", "0.20"],
        ["A11 CUSUM",                    "0.00", "0.00", "0.03", "0.00", "0.04"],
        ["F93 Altitude Drop",            "0.00", "0.00", "0.00", "0.00", "0.00"],
    ],
    col_widths=[2.3, 0.78, 0.85, 0.72, 0.75, 0.72])

add_heading(doc, "Ranked results — corrected pipeline (real speed + altitude)", 2)
add_para(doc,
    "With a corrected pipeline (speed computed from step/time when missing, altitude from "
    "height-above-ellipsoid), the ranking changes significantly. F100 moves from rank 6 to rank 1. "
    "DBSCAN falls from rank 1 to rank 17.",
    size=10)
add_table(doc,
    ["Rank", "Algorithm", "Precision", "Recall", "F1", "Altitude recall", "False alarms", "Rank (current)"],
    [
        ["1",  "F100 Composite Movement Score",  "0.27", "0.96", "0.41", "97%",  "6.9%",  "6"],
        ["2",  "A13 Elliptic Envelope",          "0.24", "0.99", "0.38", "96%",  "7.0%",  "5"],
        ["3",  "D80 GMM Log-Likelihood",         "0.23", "0.98", "0.37", "97%",  "7.1%",  "8"],
        ["4",  "A01 Z-Score Max",                "0.23", "0.93", "0.36", "96%",  "7.0%",  "2"],
        ["5",  "A05 Robust Mahalanobis",         "0.22", "0.96", "0.35", "89%",  "7.3%",  "7"],
        ["6",  "E85 Autoencoder Tanh",           "0.22", "0.91", "0.35", "96%",  "6.9%",  "9"],
        ["7",  "A04 Mahalanobis",                "0.22", "0.93", "0.35", "97%",  "7.2%",  "3"],
        ["8",  "D71 Gaussian Log-Likelihood",    "0.22", "0.93", "0.35", "97%",  "7.2%",  "4"],
        ["17", "B41 DBSCAN Noise Points",        "0.18", "1.00", "0.29", "98%", "14.5%",  "1"],
        ["22", "A06 IQR Outlier",                "0.07", "1.00", "0.12", "100%","31.3%", "18"],
        ["23", "A11 CUSUM",                      "0.02", "0.62", "0.04", "44%", "10.1%", "22"],
    ],
    col_widths=[0.4, 2.2, 0.75, 0.65, 0.5, 1.0, 0.9, 1.0])


# ════════════════════════════════════════════════════════════════════════════
# 5. ALGORITHM RECOMMENDATIONS (visual chart)
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "5. Algorithm Recommendations", 1)

add_para(doc,
    "The chart below rates all 23 detectors across three dimensions: "
    "Quality (F1 score on the corrected pipeline — the fairest measure), "
    "Speed (how fast on the White Stork 13.4M fix dataset), and "
    "Interpretability (how easy it is to explain what the detector flagged).")

doc.add_paragraph()

# Tier key
add_heading(doc, "Tier key", 2)
tier_tbl = doc.add_table(rows=4, cols=2)
tier_tbl.style = "Table Grid"
for ri, (a, b) in enumerate([("Tier", "Meaning"),
    ("★★★  Best",    "Recommended for production use — stable F1 in both pipelines"),
    ("★★    Good",   "Solid detector — good quality or very fast with acceptable F1"),
    ("★      Niche", "Use only for a specific error type or research question")]):
    tier_tbl.rows[ri].cells[0].text = a
    tier_tbl.rows[ri].cells[1].text = b
    for ci in range(2):
        for p in tier_tbl.rows[ri].cells[ci].paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)
                if ri == 0:
                    run.bold = True; run.font.color.rgb = WHITE
    if ri == 0:
        set_cell_bg(tier_tbl.rows[0].cells[0], HDR_HEX)
        set_cell_bg(tier_tbl.rows[0].cells[1], HDR_HEX)
tier_tbl.columns[0].width = Inches(1.2)
tier_tbl.columns[1].width = Inches(5.1)
doc.add_paragraph()

# Visual bar chart
add_heading(doc, "Visual rating chart — Quality, Speed, Interpretability", 2)
add_para(doc, "Filled blocks out of 5. Q = Quality (F1, corrected pipeline)  |  S = Speed (5 = fastest)  |  I = Interpretability (5 = easiest to explain).",
    size=10, color=GREY)

# (name, quality 0-5, speed 0-5, interp 0-5, tier, note)
s4_ratings = [
    ("F100 Composite Movement Score",  5, 5, 5, "★★★", "Best overall: top F1, fastest, most explainable"),
    ("A13 Elliptic Envelope",          5, 2, 3, "★★★", "Most reliable statistical — slow on huge datasets"),
    ("D80 GMM Log-Likelihood",         5, 4, 3, "★★★", "3-component mixture — stable in both pipelines"),
    ("A01 Z-Score Max",                4, 5, 5, "★★★", "Simplest strong baseline — fast and interpretable"),
    ("A05 Robust Mahalanobis",         4, 5, 4, "★★",  "Best on small/noisy datasets (cuckoo F1 = 0.48)"),
    ("E85 Autoencoder Tanh",           4, 5, 2, "★★",  "Neural proxy — behaves like Mahalanobis"),
    ("A04 Mahalanobis",                4, 5, 4, "★★",  "Accounts for feature correlations at near-zero cost"),
    ("B45 One-Class SVM",              4, 4, 3, "★★",  "Good non-linear boundary; consistent across datasets"),
    ("B31 Isolation Forest",           4, 4, 3, "★★",  "Good on position and speed; misses altitude errors"),
    ("A07 Modified Z-Score (MAD)",     3, 5, 4, "★★",  "Robust to masking; misses speed errors on unscaled"),
    ("F97 Multi-Feature Temporal",     3, 5, 4, "★★",  "Catches position jumps via temporal change sum"),
    ("C56 LOF k=20",                   3, 4, 3, "★",   "Good at local density — misses speed on unscaled"),
    ("C64 Gaussian KDE",               3, 4, 2, "★",   "Finds most errors but 10.5% false alarms"),
    ("E81 PCA Reconstruction",         3, 5, 3, "★",   "Misses 26% of position errors; fast"),
    ("D73 Gamma Distribution Tail",    3, 5, 4, "★",   "Speed-only; crashes without real speed data"),
    ("C61 KNN Mean Distance",          3, 5, 3, "★",   "Misses speed errors; use with scaled features"),
    ("B41 DBSCAN Noise Points",        2, 4, 2, "★",   "Rank 1 current / rank 17 corrected — not a safe default"),
    ("A06 IQR Outlier",                1, 5, 5, "★",   "Too many false alarms (19%); avoid for real use"),
    ("F91 Velocity Jerk",              2, 5, 4, "★",   "Speed errors only; useless without real speed"),
    ("F93 Altitude Drop",              1, 5, 3, "★",   "Unusable until pipeline reads height-above-ellipsoid"),
    ("C60 LOF Cosine",                 1, 3, 2, "★",   "Misses 70% of position errors — not recommended"),
    ("D71 Gaussian Log-Likelihood",    4, 5, 3, "★",   "Identical to A04 — adds no new information"),
    ("A11 CUSUM",                      1, 5, 3, "★",   "Threshold doesn't transfer between series lengths"),
]

TOTAL = 5
BAR_W  = Inches(0.18)
NAME_W = Inches(2.2)
TIER_W = Inches(0.5)

hdr_cols = ["Algorithm", "Tier"] + ["Q"]*TOTAL + [""]*1 + ["S"]*TOTAL + [""]*1 + ["I"]*TOTAL
chart_tbl = doc.add_table(rows=1 + len(s4_ratings), cols=len(hdr_cols))
chart_tbl.style = "Table Grid"

hdr_row = chart_tbl.rows[0]
for ci, h in enumerate(hdr_cols):
    set_cell_bg(hdr_row.cells[ci], HDR_HEX)
    set_cell_bold_white(hdr_row.cells[ci], h, size=8)

for ci, label in [(2, "Quality ▶"), (8, "Speed ▶"), (14, "Interp ▶")]:
    set_cell_bg(hdr_row.cells[ci], "0A1828")
    hdr_row.cells[ci].paragraphs[0].runs[0].text = label

for ri, (name, q, s, interp, tier, note) in enumerate(s4_ratings):
    row = chart_tbl.rows[ri + 1]
    row.cells[0].text = name
    for p in row.cells[0].paragraphs:
        for run in p.runs:
            run.font.size = Pt(8)
    row.cells[1].text = tier
    for p in row.cells[1].paragraphs:
        for run in p.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = BLUE if "★★★" in tier else (PURPLE if "★★" in tier else GREY)
    for bi, hex_c in enumerate(bar(q, TOTAL, "1A4A8A", "D0D8EA")):
        set_cell_bg(row.cells[2 + bi], hex_c)
        row.cells[2 + bi].text = ""
    set_cell_bg(row.cells[7], "FFFFFF")
    row.cells[7].text = ""
    for bi, hex_c in enumerate(bar(s, TOTAL, "2A6A4A", "D0E8DA")):
        set_cell_bg(row.cells[8 + bi], hex_c)
        row.cells[8 + bi].text = ""
    set_cell_bg(row.cells[13], "FFFFFF")
    row.cells[13].text = ""
    for bi, hex_c in enumerate(bar(interp, TOTAL, "8A6A00", "EAE0C0")):
        set_cell_bg(row.cells[14 + bi], hex_c)
        row.cells[14 + bi].text = ""

chart_tbl.columns[0].width = NAME_W
chart_tbl.columns[1].width = TIER_W
for ci in range(2, len(hdr_cols)):
    chart_tbl.columns[ci].width = BAR_W

doc.add_paragraph()

# ── Top picks table ────────────────────────────────────────────────────────────
add_heading(doc, "Top algorithm picks by use case", 2)
add_table(doc,
    ["Use case", "Best pick", "Why"],
    [
        ["Best overall (works in both pipelines)",     "F100 Composite Movement Score",  "Rank 1 corrected, rank 6 current, 0.01s, most explainable"],
        ["Most reliable statistical detector",         "A13 Elliptic Envelope",           "100% recall on all error types; robust covariance fit"],
        ["Fast + good on large datasets",              "A01 Z-Score Max",                 "0.04s runtime, F1 = 0.36–0.41, simple to explain"],
        ["Best multivariate catch (correlations)",     "A04 Mahalanobis",                 "Accounts for correlated features, 0.05s, F1 = 0.41"],
        ["Fewest false alarms (current pipeline)",     "B41 DBSCAN",                      "3% false alarms — but re-tune eps if pipeline changes"],
        ["Speed-error specialist",                     "D73 Gamma / F91 Velocity Jerk",   "100% speed recall; only use when real speed is recorded"],
        ["Altitude-error specialist",                  "F93 Altitude Drop",               "97% altitude recall once height-above-ellipsoid is read"],
        ["Exploring unusual behaviour",                "A13 Elliptic Envelope + B41 DBSCAN", "Low agreement (Jaccard 0.30) — together show more candidates"],
    ],
    col_widths=[2.0, 2.2, 2.3])

# ── Detectors to avoid ─────────────────────────────────────────────────────────
add_heading(doc, "Detectors with known limitations", 2)
add_table(doc,
    ["Detector", "Problem", "When it is acceptable"],
    [
        ["A11 CUSUM",            "Running maximum threshold doesn't transfer — flags almost nothing in test period",
         "Only if you reset the threshold per-window; not recommended in current form"],
        ["C60 LOF Cosine",       "Cosine distance ignores feature magnitude — misses 70% of position errors",
         "Only if you specifically want to detect direction-based anomalies, not magnitude"],
        ["A06 IQR Outlier",      "Fixed Tukey fences flag 19% of clean fixes — most flags are false alarms",
         "Quick visual exploration only; not for production anomaly flagging"],
        ["B41 DBSCAN",          "F1 drops from 0.62 → 0.29 when pipeline is corrected; eps was never tuned",
         "Current pipeline only, and only after re-tuning eps on the specific dataset"],
        ["D71 Gaussian Log-Likelihood", "Mathematically identical to A04 Mahalanobis — adds no new information",
         "Never compare D71 vs A04; pair either with a different-family detector instead"],
        ["F93 Altitude Drop",    "Altitude is 0 everywhere in current pipeline — cannot fire at all",
         "Only after pipeline is fixed to read height-above-ellipsoid from Movebank CSVs"],
    ],
    col_widths=[1.6, 2.8, 2.1])

doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# 6. KEY FINDINGS FROM THE BENCHMARK
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "6. Key Findings from the Benchmark", 1)

add_heading(doc, "What the benchmark revealed", 2)
for obs in [
    "Most multivariate detectors found over 90% of position errors. The ranking was decided mainly by false alarms, not by recall.",
    "DBSCAN ranked #1 on the current pipeline (F1 = 0.62) only because a pipeline bug made speed = 0 on 3 datasets, creating an artificially simple feature space with only 3% false alarms. With real speed and altitude, it falls to rank 17 (F1 = 0.29).",
    "F100 Composite Movement Score is the only detector that ranked in the top 10 on both pipelines (rank 6 and rank 1). It is also the fastest (0.01 s) and the most interpretable.",
    "Speed errors separate detectors from each other. Position errors are caught by nearly everyone. Detectors that work on unscaled features (KNN, LOF, PCA) miss speed errors because step length dominates the scale.",
    "The White Stork Tunisia dataset was hardest for all algorithms (best F1 = 0.33), because its test period contains movement not seen in training.",
    "Detectors mostly disagree about which normal fixes are unusual: average Jaccard index = 0.37 over all detector pairs. One in three pairs shares less than 30% of flags.",
]:
    add_bullet(doc, obs)
doc.add_paragraph()

add_heading(doc, "Three pipeline bugs that affect ALL services", 2)
add_para(doc,
    "The benchmark revealed three problems in the shared VEBITA feature pipeline that are not "
    "caused by the detectors themselves — they affect every service, not just anomaly detection.",
    size=10)
add_table(doc,
    ["Problem", "Where in code", "Effect"],
    [
        ["Animals of a study are mixed together in one time-sorted series",
         "load_movebank_csv and the streaming pipeline",
         "Consecutive rows often belong to different animals. Step length then measures the distance between two animals. On White Stork Tunisia, 49.3% of steps exceeded 50 km (vs 0.06% when animals are processed separately)."],
        ["Speed is always 0 when the file has no ground-speed column",
         "extract_features: feat.get('ground-speed', zeros).fillna(...)",
         "The fallback to step_length ÷ time never runs because the default is a series of zeros, not missing values. Affected cuckoo, guillemot and jackal: Gamma crashed on all three, Jerk and CUSUM flagged nothing."],
        ["Altitude is read only from height-above-msl",
         "extract_features",
         "None of the 13 uploaded datasets has values there, although swan, stork and guillemot data contain height-above-ellipsoid. Altitude is 0 everywhere, so Altitude Drop (F93) never fires."],
    ],
    col_widths=[1.9, 1.6, 2.8])


# ════════════════════════════════════════════════════════════════════════════
# 7. REDUNDANT DETECTOR PAIRS
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "7. Redundant Detector Pairs", 1)
add_para(doc,
    "Some detectors flag nearly identical fixes and add no new information when compared "
    "together. The Jaccard index measures overlap: 1.00 = always flag the same fixes.")
add_table(doc,
    ["Pair", "Jaccard", "Why redundant"],
    [
        ["A04 Mahalanobis  vs  D71 Gaussian Log-Likelihood",  "1.00", "Identical score; D71 only adds 10⁻⁶ to the diagonal — same ranking always"],
        ["A05 Robust Mahal.  vs  A07 Modified Z-Score (MAD)", "0.95", "Both use robust median-based estimates of centre and spread"],
        ["A05 Robust Mahal.  vs  A13 Elliptic Envelope",      "0.90", "Both are robust covariance estimators"],
        ["A04 Mahalanobis  vs  E85 Autoencoder Tanh",         "0.80", "Small autoencoder learns a mostly linear compression of the same covariance"],
    ],
    col_widths=[3.0, 0.65, 2.8])

add_para(doc,
    "Avoid comparing any of these pairs — they will show nearly identical maps and "
    "add no value. Instead compare detectors from different families, e.g. "
    "A13 Elliptic Envelope (statistical) vs B41 DBSCAN (density/distance).",
    size=10, color=GREY)


# ════════════════════════════════════════════════════════════════════════════
# 8. DEPENDENCIES
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "8. Dependencies", 1)
add_table(doc,
    ["Library", "Required?", "Used by"],
    [
        ["numpy",        "Required",  "All detectors — array operations, z-scores, CUSUM, movement-specific"],
        ["scikit-learn", "Required",  "Isolation Forest, One-Class SVM, LOF, KDE, GMM, PCA, Elliptic Envelope, DBSCAN"],
        ["scipy",        "Optional",  "D73 Gamma Distribution Tail (scipy.stats.gamma)"],
    ],
    col_widths=[1.2, 0.9, 4.2])


# ════════════════════════════════════════════════════════════════════════════
# 9. SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "9. Summary Table — All 23 Detectors", 1)
add_table(doc,
    ["ID", "Detector", "Family", "F1 (current)", "F1 (corrected)", "False alarms", "Runtime (s)", "Tier"],
    [
        ["B41",  "DBSCAN Noise Points",          "B — Tree",           "0.62",  "0.29",  "3.1%",  "0.58",  "★ (pipeline-dependent)"],
        ["F100", "Composite Movement Score",      "F — Movement",       "0.40",  "0.41",  "7.1%",  "0.01",  "★★★"],
        ["A01",  "Z-Score Max",                   "A — Statistical",    "0.41",  "0.36",  "6.8%",  "0.04",  "★★★"],
        ["A13",  "Elliptic Envelope",             "A — Statistical",    "0.41",  "0.38",  "7.1%",  "6.78",  "★★★"],
        ["D80",  "GMM Log-Likelihood",            "D — Probabilistic",  "0.40",  "0.37",  "6.9%",  "0.66",  "★★★"],
        ["A04",  "Mahalanobis",                   "A — Statistical",    "0.41",  "0.35",  "6.8%",  "0.05",  "★★"],
        ["A05",  "Robust Mahalanobis",            "A — Statistical",    "0.40",  "0.35",  "7.2%",  "0.09",  "★★"],
        ["E85",  "Autoencoder Tanh",              "E — Neural",         "0.40",  "0.35",  "6.9%",  "0.15",  "★★"],
        ["B31",  "Isolation Forest",              "B — Tree",           "0.39",  "0.32",  "7.4%",  "1.02",  "★★"],
        ["B45",  "One-Class SVM",                 "B — Tree",           "0.38",  "0.33",  "6.9%",  "0.18",  "★★"],
        ["A07",  "Modified Z-Score (MAD)",        "A — Statistical",    "0.37",  "0.33",  "7.1%",  "0.07",  "★★"],
        ["F97",  "Multi-Feature Temporal Change", "F — Movement",       "0.36",  "0.35",  "7.3%",  "0.01",  "★★"],
        ["E81",  "PCA Reconstruction",            "E — Neural",         "0.34",  "0.32",  "6.4%",  "0.03",  "★"],
        ["C56",  "LOF k=20",                      "C — Distance",       "0.34",  "0.25",  "7.8%",  "0.14",  "★"],
        ["C61",  "KNN Mean Distance",             "C — Distance",       "0.31",  "0.31",  "8.9%",  "0.09",  "★"],
        ["C64",  "Gaussian KDE",                  "C — Distance",       "0.31",  "0.30",  "10.5%", "0.47",  "★"],
        ["D71",  "Gaussian Log-Likelihood",       "D — Probabilistic",  "0.41",  "0.35",  "6.8%",  "0.05",  "★ (same as A04)"],
        ["D73",  "Gamma Distribution Tail",       "D — Probabilistic",  "0.11",  "0.34",  "8.1%",  "0.01",  "★"],
        ["A06",  "IQR Outlier",                   "A — Statistical",    "0.22",  "0.12",  "19.4%", "0.05",  "★"],
        ["F91",  "Velocity Jerk",                 "F — Movement",       "0.10",  "0.27",  "2.9%",  "0.00",  "★"],
        ["C60",  "LOF Cosine",                    "C — Distance",       "0.12",  "0.18",  "11.4%", "1.87",  "★"],
        ["A11",  "CUSUM",                         "A — Statistical",    "0.01",  "0.04",  "3.6%",  "0.00",  "★"],
        ["F93",  "Altitude Drop",                 "F — Movement",       "0.00",  "0.15",  "0.0%",  "0.00",  "★"],
    ],
    col_widths=[0.45, 2.0, 1.3, 0.85, 0.9, 0.85, 0.8, 1.25])

doc.add_paragraph()
p_end = doc.add_paragraph(); p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_end = p_end.add_run("End of Report — VEBITA Service 4: Anomaly Detection")
r_end.italic = True; r_end.font.size = Pt(10); r_end.font.color.rgb = GREY

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = "/Users/I776893/Downloads/Movement Project/Service_4_Anomaly_Detection_Report.docx"
doc.save(out_path)
print(f"Saved: {out_path}")
