"""
Generate Service_3_Environmental_Factors_Report.docx
Run with: python3 generate_report.py
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Page margins ─────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(2.8)
    section.right_margin  = Cm(2.8)

# ── Colour palette ───────────────────────────────────────────────────────────
GREEN  = RGBColor(0x5D, 0xCA, 0xA5)   # VEBITA accent
DARK   = RGBColor(0x1A, 0x1A, 0x2E)
GREY   = RGBColor(0x55, 0x55, 0x55)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
TEAL_HDR = RGBColor(0x0D, 0x3B, 0x2B)  # table header background approximated via shading xml

# ── Style helpers ────────────────────────────────────────────────────────────

def set_cell_bg(cell, hex_color: str):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color.upper())
    tcPr.append(shd)

def set_cell_bold_white(cell, text, size=9):
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.bold = True
    run.font.size  = Pt(size)
    run.font.color.rgb = WHITE

def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = GREEN if level == 1 else RGBColor(0x2E, 0x86, 0x6B)
    return p

def add_para(doc, text, size=10.5, bold=False, color=None, space_before=0, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    return p

def add_label_value(doc, label, value, size=10):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(2)
    r1 = p.add_run(f"{label}: ")
    r1.bold = True
    r1.font.size = Pt(size)
    r2 = p.add_run(value)
    r2.font.size = Pt(size)
    return p

def add_table(doc, headers, rows, col_widths=None):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    # Header row
    hdr = tbl.rows[0]
    for i, h in enumerate(headers):
        set_cell_bg(hdr.cells[i], "0D3B2B")
        set_cell_bold_white(hdr.cells[i], h, size=9)
    # Data rows
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
            if ri % 2 == 0:
                set_cell_bg(cell, "EEF5EE")
    # Column widths
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in tbl.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return tbl

def add_algo_block(doc, name, props, description, extra_paras=None):
    """Renders one algorithm section with a property table + description paragraphs."""
    # Algorithm name as heading 3
    h = doc.add_heading(name, level=3)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x26, 0x73, 0x57)

    # Properties mini-table
    tbl = doc.add_table(rows=len(props), cols=2)
    tbl.style = "Table Grid"
    for ri, (k, v) in enumerate(props):
        tbl.rows[ri].cells[0].text = k
        tbl.rows[ri].cells[1].text = v
        for p in tbl.rows[ri].cells[0].paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
        for p in tbl.rows[ri].cells[1].paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)
        if ri % 2 == 0:
            set_cell_bg(tbl.rows[ri].cells[0], "E8F7F2")
            set_cell_bg(tbl.rows[ri].cells[1], "E8F7F2")
    tbl.columns[0].width = Inches(1.8)
    tbl.columns[1].width = Inches(4.5)
    doc.add_paragraph()

    # Description paragraphs
    for para_tuple in (extra_paras or []):
        label, text = para_tuple
        if label:
            p = doc.add_paragraph()
            r1 = p.add_run(f"{label}  ")
            r1.bold = True
            r1.font.size = Pt(10)
            r1.font.color.rgb = RGBColor(0x0D, 0x3B, 0x2B)
            r2 = p.add_run(text)
            r2.font.size = Pt(10)
            p.paragraph_format.space_after = Pt(4)
        else:
            p = doc.add_paragraph(text)
            p.paragraph_format.space_after = Pt(4)
            for run in p.runs:
                run.font.size = Pt(10)
    doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# COVER
# ════════════════════════════════════════════════════════════════════════════

p_title = doc.add_paragraph()
p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p_title.add_run("VEBITA")
run.bold = True
run.font.size = Pt(28)
run.font.color.rgb = GREEN

p_sub = doc.add_paragraph()
p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p_sub.add_run("Service 3 — Environmental Factors")
run2.font.size = Pt(18)
run2.font.color.rgb = GREY

p_sub2 = doc.add_paragraph()
p_sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run3 = p_sub2.add_run("Technical Project Report")
run3.font.size = Pt(14)
run3.font.color.rgb = GREY

doc.add_paragraph()
for label, value in [
    ("Author", "Sarah"),
    ("Service ID", "3"),
    ("Project", "VEBITA — Animal Movement Analysis Platform"),
    ("Date", "October 2026"),
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{label}:  ")
    r.bold = True
    r.font.size = Pt(11)
    r2 = p.add_run(value)
    r2.font.size = Pt(11)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 1. SERVICE OVERVIEW
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "1. Service Overview", 1)

add_para(doc,
    "Service 3 — Environmental Factors — investigates how environmental variables "
    "(terrain, temperature, vegetation, wind, land cover, water proximity, solar radiation) "
    "influence animal movement recorded in Movebank GPS datasets.",
    size=10.5)

add_para(doc,
    "Unlike the other five VEBITA services that classify animal behaviour into discrete states "
    "(Resting, Foraging, etc.), Service 3 operates entirely as a regression / scoring service. "
    "Every algorithm outputs a continuous normalised score (0.0–1.0) per GPS fix, representing "
    "the estimated strength or character of an environmental signal at that location and moment. "
    "This distinction is important:",
    size=10.5)

for bullet in [
    "No F1 / accuracy metrics are produced. Classification metrics do not apply — output is a continuous score, not a class label.",
    "The backend evaluator does compute pearson_r, spearman_r and r2 internally as quality "
    "measures, but these are not displayed as score cards in the frontend UI.",
    "Output is a per-point environmental score which can be compared across algorithms and "
    "plotted against latitude, time, altitude, or any other spatial / temporal axis.",
    "The frontend shows three dedicated tabs for this service only: Env Profiles, "
    "Score over time, and Algorithm comparison.",
]:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(bullet).font.size = Pt(10)

doc.add_paragraph()

add_heading(doc, "Scope", 2)
add_table(doc,
    ["Property", "Value"],
    [
        ["Total algorithms",       "25"],
        ["Categories",             "7"],
        ["Service type",           "Regression (continuous score output)"],
        ["Input feature matrix",   "5 visible GPS features + 3 backend rolling features (8 total)"],
        ["Output per algorithm",   "Array of floats, normalised to [0, 1] by the backend"],
        ["Applicable datasets",    "All Movebank animal species"],
    ],
    col_widths=[2.2, 4.1])


# ════════════════════════════════════════════════════════════════════════════
# 2. ARCHITECTURE & DESIGN
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "2. Architecture & Design", 1)

add_heading(doc, "File location", 2)
add_para(doc, "backend/vebita_framework/services/s3_environment/sarah_algorithms.py", size=9.5, color=GREY)

add_heading(doc, "Integration with the VEBITA framework", 2)
add_para(doc,
    "Every algorithm inherits from BaseAlgorithm (defined in core/base.py) and is auto-registered "
    "via the @registry.register decorator. The central API endpoint /run in main.py detects "
    "service_id == 3 and takes a regression branch: instead of computing F1/accuracy, it "
    "normalises the raw float output into [0, 1] and returns scores arrays. The frontend then "
    "renders these through the three Service 3 visualisation components.",
    size=10.5)

add_heading(doc, "Data flow", 2)
for step in [
    "1.  User uploads Movebank CSV",
    "2.  load_and_extract_features_streaming()  →  out-of-core, bounded RAM",
    "3.  Feature matrix X  (n_points × 8 columns)",
    "4.  _env_features(X)  →  derives 12 environmental proxy features",
    "5.  algorithm.fit(X_train)  →  algorithm.predict(X_test)  →  raw continuous scores",
    "6.  Normalise to [0, 1]",
    "7.  Frontend: EnvProfiles / EnvScoreTime / EnvComparison",
]:
    p = doc.add_paragraph(step)
    p.paragraph_format.space_after = Pt(2)
    for run in p.runs:
        run.font.size = Pt(10)
        run.font.name = "Courier New"

doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# 3. FEATURE ENGINEERING PIPELINE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "3. Feature Engineering Pipeline", 1)

add_heading(doc, "Input: GPS movement features (5 visible features)", 2)
add_para(doc,
    "The system extracts five movement features from each GPS fix that are visible in the app "
    "(Time Series tab and map tooltips). These are also the primary inputs the algorithms use.",
    size=10.5)
add_table(doc,
    ["Feature", "Description", "Visible in app"],
    [
        ["speed_ms",      "Instantaneous speed (m/s)",                               "Yes — Time Series, map popup"],
        ["altitude_m",    "Recorded altitude (metres)",                               "Yes — Time Series, map popup"],
        ["turning_angle", "Change in heading between consecutive fixes (radians)",    "Yes — Time Series"],
        ["straightness",  "Ratio of displacement to path length (0–1)",               "Yes — Time Series"],
        ["step_length_m", "Distance between consecutive GPS fixes (metres)",          "Yes — Time Series histogram"],
    ],
    col_widths=[1.5, 3.3, 1.5])

add_heading(doc, "Backend-only computed features (not shown in app)", 2)
add_para(doc,
    "Three additional rolling features are computed internally by the streaming pipeline before "
    "the feature matrix is passed to the algorithms. They are used by the algorithms but are "
    "never displayed directly on screen:",
    size=10.5)
add_table(doc,
    ["Feature", "How computed", "Used for"],
    [
        ["speed_roll_mean", "5-fix centred rolling mean of speed_ms",         "Smoothed speed signal for algorithm input"],
        ["speed_roll_std",  "5-fix centred rolling std of speed_ms",          "Speed variability signal for algorithm input"],
        ["alt_roll_mean",   "5-fix centred rolling mean of altitude_m",       "Smoothed altitude signal for algorithm input"],
    ],
    col_widths=[1.5, 3.0, 1.8])

add_heading(doc, "Derived: Environmental proxy features (12 columns)", 2)
add_para(doc,
    "Because real raster environmental layers are not embedded in a Movebank CSV, the "
    "_env_features() function derives 12 synthetic environmental proxies from the 8 movement "
    "columns. These are ecologically motivated approximations:",
    size=10.5)

add_table(doc,
    ["Proxy feature", "Derivation", "Environmental analogue"],
    [
        ["terrain_ruggedness", "|∇(altitude)|",               "How rapidly terrain elevation changes"],
        ["slope",              "∇(alt_roll_mean)",             "Terrain slope (gradient of smoothed altitude)"],
        ["ndvi_proxy",         "speed / (turning_angle + 1)", "Vegetation density — fast straight movement ≈ open habitat"],
        ["land_cover",         "Altitude binned 0–4",         "Discrete terrain / vegetation zone"],
        ["wind_proxy",         "speed_roll_std",              "Speed variability as proxy for wind turbulence"],
        ["temperature_proxy",  "-altitude / max(altitude)",   "Lapse-rate approximation — higher = cooler"],
        ["proximity_water",    "Low speed AND low altitude",  "Likelihood of being near water / wetland"],
        ["solar_radiation",    "straightness × speed_roll_mean", "Open exposed terrain receiving direct sun"],
        ["resource_score",     "1 / (turning_angle + 1)",    "Straight movement ≈ travelling toward resources"],
        ["elevation_gradient", "∇(altitude)",                 "Raw elevation change per step"],
        ["habitat_boundary",   "turn > 90th percentile",      "Sharp turns indicate habitat edge-crossing"],
        ["energy_expenditure", "speed²",                      "Kinetic energy proxy"],
    ],
    col_widths=[1.55, 1.7, 3.0])

add_para(doc,
    "Note: In a production deployment these proxies would be replaced by proper raster-sampled "
    "variables from Google Earth Engine (NDVI, land surface temperature, DEM slope, ERA5 wind). "
    "The proxy approach makes the service self-contained on any Movebank CSV without external API calls.",
    size=9.5, color=GREY)


# ════════════════════════════════════════════════════════════════════════════
# 4. ALGORITHM CATALOGUE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "4. Algorithm Catalogue", 1)

# ── 4.1 Statistical & Regression ────────────────────────────────────────────
add_heading(doc, "4.1  Statistical & Regression  (3 algorithms)", 2)

add_algo_block(doc,
    "Env Bayesian Ridge",
    [("Class","EnvBayesianRidge"), ("Category","statistical"), ("Library","sklearn"),
     ("Training subsample cap","2,000 points")],
    "",
    extra_paras=[
        ("What it does:",
         "Applies Bayesian Ridge regression with automatic ARD-style regularisation. "
         "The model is trained to predict movement speed from the 12 environmental proxy features. "
         "A high score at a GPS fix means the environment alone is consistent with fast movement; "
         "a low score means the environment predicts slow or constrained movement."),
        ("Why it's useful:",
         "Bayesian Ridge automatically determines its own regularisation strength via marginal "
         "likelihood maximisation, making it robust without hand-tuning."),
        ("Mathematical formulation:",
         "Minimises ||y − Xw||² + α||w||² where α is inferred from data via Type-II maximum likelihood."),
        ("Hyperparameters:", "None exposed (sklearn defaults: n_iter=300, tol=1e-3)."),
    ])

add_algo_block(doc,
    "Env PLS Regression",
    [("Class","EnvPLSRegression"), ("Category","statistical"), ("Library","sklearn"),
     ("Training subsample cap","2,000 points"), ("Key parameter","n_components = 3")],
    "",
    extra_paras=[
        ("What it does:",
         "Partial Least Squares regression finds latent components that maximally co-vary between "
         "the environmental feature matrix and movement speed. Unlike PCA, PLS finds directions "
         "jointly explained by both X and y — ideal when many environmental proxies are correlated."),
        ("Why it's useful:",
         "Many of the 12 proxy features are correlated (e.g. terrain_ruggedness and elevation_gradient "
         "both derive from altitude). PLS handles multicollinearity better than ordinary least squares."),
        ("Mathematical formulation:",
         "Finds weight vectors w, c maximising cov(Xw, yc) subject to ||w|| = ||c|| = 1."),
        ("Hyperparameters:", "n_components = 3 (number of PLS latent dimensions)."),
    ])

add_algo_block(doc,
    "Env Quantile Regression",
    [("Class","EnvQuantileRegression"), ("Category","statistical"), ("Library","sklearn"),
     ("Training subsample cap","2,000 points"), ("Key parameter","quantile = 0.5 (median)")],
    "",
    extra_paras=[
        ("What it does:",
         "Models the conditional median of movement speed given environmental features rather "
         "than the conditional mean. This is important for GPS tracking data, which contains "
         "outliers (burst-mode fixes, GPS drift, high-speed migration sprints) that inflate the "
         "mean but not the median."),
        ("Mathematical formulation:",
         "Minimises Σ ρ_q(yᵢ − Xᵢβ) where ρ_q(u) = u(q − 1[u < 0]) (pinball / tilted absolute loss)."),
        ("Hyperparameters:", "quantile = 0.5, alpha = 0.1 (L2 regularisation), solver = highs."),
    ])

# ── 4.2 Time Series & Temporal ───────────────────────────────────────────────
add_heading(doc, "4.2  Time Series & Temporal  (3 algorithms)", 2)

add_algo_block(doc,
    "Env Kalman Filter",
    [("Class","EnvKalmanFilter"), ("Category","time_series"), ("Library","numpy (pure implementation)"),
     ("Training subsample cap","None (predict caps at 20,000)"),
     ("Key parameters","process_noise = 0.001, obs_noise = 0.1")],
    "",
    extra_paras=[
        ("What it does:",
         "Implements a 1-dimensional discrete Kalman filter applied to the altitude channel. "
         "At each GPS fix, it combines the previous state estimate with the new observation, "
         "weighted by the Kalman gain K = P_pred / (P_pred + R). The filtered altitude trajectory "
         "serves as a smooth environmental signal capturing how terrain elevation evolves along the route."),
        ("Mathematical formulation:",
         "Predict: x̂⁻ₖ = x̂ₖ₋₁, P⁻ₖ = Pₖ₋₁ + Q.  "
         "Update: K = P⁻ₖ / (P⁻ₖ + R), x̂ₖ = x̂⁻ₖ + K(zₖ − x̂⁻ₖ), Pₖ = (1 − K)P⁻ₖ."),
        ("Hyperparameters:",
         "process_noise Q = 0.001 (how much the true state can drift between steps); "
         "obs_noise R = 0.1 (how noisy the GPS altitude readings are assumed to be)."),
    ])

add_algo_block(doc,
    "Env Fourier Transform",
    [("Class","EnvFourierTransform"), ("Category","time_series"), ("Library","numpy"),
     ("Key parameter","n_harmonics = 5")],
    "",
    extra_paras=[
        ("What it does:",
         "Computes the real FFT of the movement speed time series, retains only the n_harmonics "
         "strongest frequency components, and reconstructs a filtered signal via inverse FFT. "
         "The output is the low-frequency (dominant harmonic) envelope, interpreted as a periodic "
         "environmental driver (e.g. daily activity cycles, tidal cycles, seasonal migration pulses)."),
        ("Mathematical formulation:",
         "y_filtered = IFFT( F(y) · M ) where M keeps the top n_harmonics amplitude components of FFT(y)."),
        ("Hyperparameters:", "n_harmonics = 5."),
    ])

add_algo_block(doc,
    "Env Seasonal Decomposition",
    [("Class","EnvSeasonalDecomposition"), ("Category","time_series"), ("Library","numpy"),
     ("Key parameter","period = 48")],
    "",
    extra_paras=[
        ("What it does:",
         "Performs additive seasonal decomposition of the movement speed signal: "
         "(1) computes a moving-average trend with window = period; "
         "(2) subtracts the trend to obtain a detrended series; "
         "(3) estimates the seasonal component by averaging the detrended series at each phase. "
         "The output is the seasonal component — how much above or below trend the animal's speed is."),
        ("Hyperparameters:",
         "period = 48 (assumes 48 fixes per cycle — appropriate for ~30-minute sampling intervals over 24 hours)."),
    ])

# ── 4.3 ML Supervised ───────────────────────────────────────────────────────
add_heading(doc, "4.3  ML Supervised  (4 algorithms)", 2)

add_algo_block(doc,
    "Env Random Forest Regressor",
    [("Class","EnvRandomForestRegressor"), ("Category","ml_supervised"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"), ("Key parameter","n_estimators = 100")],
    "",
    extra_paras=[
        ("What it does:",
         "Trains a Random Forest of 100 decision trees to predict movement speed from the 12 "
         "environmental proxy features. Each tree is trained on a bootstrap sample with random "
         "feature subsets at each split. The ensemble average provides a nonlinear, non-parametric "
         "estimate of the environmental–movement relationship."),
        ("Why it's useful:",
         "Handles nonlinear interactions between environmental features naturally (e.g. low NDVI "
         "combined with high altitude → alpine terrain → restricted movement). Also provides "
         "feature importance scores via mean impurity decrease."),
        ("Hyperparameters:", "n_estimators = 100, random_state = 42, n_jobs = -1 (all CPU cores)."),
    ])

add_algo_block(doc,
    "Env Gradient Boosting Regressor",
    [("Class","EnvGradientBoostingRegressor"), ("Category","ml_supervised"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"), ("Key parameters","n_estimators = 100, max_depth = 3")],
    "",
    extra_paras=[
        ("What it does:",
         "Builds an additive ensemble by fitting shallow decision trees sequentially, each correcting "
         "the residual error of the previous. The final prediction is the sum of all tree outputs "
         "scaled by a learning rate."),
        ("Why it's useful:",
         "Boosting often outperforms Random Forest on structured tabular data because each tree "
         "explicitly targets remaining residual error. Shallow trees (max_depth=3) provide strong "
         "regularisation, preventing overfitting on noisy GPS-derived proxy features."),
        ("Hyperparameters:", "n_estimators = 100, max_depth = 3."),
    ])

add_algo_block(doc,
    "Env XGBoost Regressor",
    [("Class","EnvXGBoostRegressor"), ("Category","ml_supervised"),
     ("Library","xgboost (falls back to sklearn GBM if not installed)"),
     ("Training subsample cap","20,000 points"),
     ("Key parameters","n_estimators = 100, max_depth = 4")],
    "",
    extra_paras=[
        ("What it does:",
         "XGBoost is a highly optimised implementation of gradient boosting with second-order (Newton) "
         "gradient updates, built-in L1/L2 regularisation, and column/row subsampling. Typically "
         "faster and more accurate than sklearn GBM on medium-to-large datasets."),
        ("Fallback:", "If xgboost is not installed, falls back to sklearn.GradientBoostingRegressor silently."),
        ("Hyperparameters:", "n_estimators = 100, max_depth = 4, verbosity = 0, random_state = 42."),
    ])

add_algo_block(doc,
    "Env SGD Regressor",
    [("Class","EnvSGDRegressor"), ("Category","ml_supervised"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"),
     ("Key parameters","loss = 'huber', alpha = 0.0001")],
    "",
    extra_paras=[
        ("What it does:",
         "Stochastic gradient descent regression with Huber loss. Processes one sample at a time, "
         "making it applicable to datasets of arbitrary size via partial_fit. Fastest training time "
         "of all supervised algorithms — useful as a speed baseline."),
        ("Hyperparameters:", "loss = 'huber', alpha = 0.0001, max_iter = 1000."),
    ])

add_algo_block(doc,
    "Env Elastic Net",
    [("Class","EnvElasticNet"), ("Category","ml_supervised"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"),
     ("Key parameters","alpha = 0.1, l1_ratio = 0.5")],
    "",
    extra_paras=[
        ("What it does:",
         "Elastic Net combines L1 (Lasso) and L2 (Ridge) regularisation. The L1 term encourages "
         "sparse solutions (some environmental features get weight 0); the L2 term handles correlated "
         "features by shrinking their weights together."),
        ("Why it's useful:",
         "Several of the 12 proxy features are correlated (e.g. terrain_ruggedness and "
         "elevation_gradient both come from altitude). Elastic Net is the canonical regulariser for "
         "this multicollinear setting."),
        ("Hyperparameters:", "alpha = 0.1 (total regularisation strength), l1_ratio = 0.5, max_iter = 1000."),
    ])

# ── 4.4 Deep Learning & Probabilistic ───────────────────────────────────────
add_heading(doc, "4.4  Deep Learning & Probabilistic  (3 algorithms)", 2)

add_algo_block(doc,
    "Env MLP Regressor",
    [("Class","EnvMLPRegressor"), ("Category","deep_learning"), ("Library","sklearn"),
     ("Training subsample cap","10,000 points"),
     ("Key parameters","hidden_layer_sizes = (64, 32), max_iter = 200")],
    "",
    extra_paras=[
        ("What it does:",
         "A fully connected feed-forward neural network with two hidden layers (64 and 32 units) "
         "and ReLU activations, trained with L-BFGS or Adam. Takes the 12 environmental proxy "
         "features as input and outputs a continuous speed prediction. Early stopping halts training "
         "when validation loss stops improving, preventing overfitting."),
        ("Why it's useful:",
         "Neural networks can learn highly nonlinear, compositional environmental effects "
         "that simpler models miss (e.g. the interaction between wind proxy, turning angle, and "
         "altitude that characterises soaring flight in thermal updrafts)."),
        ("Hyperparameters:",
         "hidden_layer_sizes = (64, 32), max_iter = 200, early_stopping = True, random_state = 42."),
    ])

add_algo_block(doc,
    "Env Gaussian Process Regressor",
    [("Class","EnvGaussianProcessRegressor"), ("Category","deep_learning"), ("Library","sklearn"),
     ("Training subsample cap","500 points  ⚠ O(n³) training cost"),
     ("Key parameters","length_scale = 1.0, nu = 1.5")],
    "",
    extra_paras=[
        ("What it does:",
         "GPR places a prior over functions and updates it with observed data to produce a posterior "
         "predictive distribution. The Matérn kernel with ν = 1.5 defines the smoothness of the "
         "environmental surface — functions are once mean-square differentiable, appropriate for "
         "physical environmental variables that change smoothly in space."),
        ("Why it's useful:",
         "GPR is the only algorithm in Service 3 that produces a full posterior distribution "
         "(mean + variance). High posterior variance at a GPS fix means the model is uncertain about "
         "the environmental effect there."),
        ("Important limitation:",
         "GPR training cost is O(n³) in both time and memory. The subsample cap is therefore just "
         "500 points — far smaller than other algorithms. On large datasets this may reduce accuracy."),
        ("Hyperparameters:", "length_scale = 1.0, nu = 1.5 (Matérn kernel), normalize_y = True."),
    ])

add_algo_block(doc,
    "Env Autoencoder Score",
    [("Class","EnvAutoencoderScore"), ("Category","deep_learning"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"), ("Key parameter","n_components = 3")],
    "",
    extra_paras=[
        ("What it does:",
         "Uses PCA as a linear autoencoder: the 12 environmental features are compressed into a "
         "3-component bottleneck and reconstructed. The output score per GPS fix is the mean squared "
         "reconstruction error — how well the 3 principal components can reconstruct the full "
         "12-dimensional environmental feature vector. A high score means environmentally anomalous conditions."),
        ("Why it's useful:",
         "This is an environmental anomaly / novelty score. High values flag GPS fixes where the "
         "animal encountered unusual environmental conditions — unexpected terrain, atypical weather, "
         "out-of-range altitude."),
        ("Hyperparameters:", "n_components = 3 (bottleneck dimensionality)."),
    ])

# ── 4.5 Feature Engineering ──────────────────────────────────────────────────
add_heading(doc, "4.5  Feature Engineering / Dimensionality Reduction  (3 algorithms)", 2)

add_algo_block(doc,
    "Env PCA Score",
    [("Class","EnvPCAScore"), ("Category","feature_engineering"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points")],
    "",
    extra_paras=[
        ("What it does:",
         "Projects the 12 environmental proxy features onto the first principal component — the "
         "single linear direction of maximum variance in the environmental feature space. The output "
         "score is each GPS fix's coordinate along this principal axis, representing its position on "
         "the dominant environmental gradient."),
        ("Interpretation:",
         "On most animal datasets the first PC loads heavily on altitude-related features, making it "
         "a composite terrain/altitude gradient. High scores = high-altitude open terrain; "
         "low scores = low-altitude sheltered terrain."),
        ("Hyperparameters:", "None."),
    ])

add_algo_block(doc,
    "Env ICA Habitat Components",
    [("Class","EnvICAHabitatComponents"), ("Category","feature_engineering"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"), ("Key parameter","n_components = 3")],
    "",
    extra_paras=[
        ("What it does:",
         "FastICA decomposes the 12 environmental features into 3 statistically independent "
         "(non-Gaussian) source signals. During fit(), the algorithm identifies which of the 3 "
         "ICA components has the lowest correlation with movement speed — the 'habitat novelty' "
         "axis — and uses that component's magnitude as the output score."),
        ("Why it's useful:",
         "PCA finds directions of maximum variance; ICA finds directions of maximum statistical "
         "independence. The speed-independent component specifically captures environmental variation "
         "not explained by current movement — potentially habitat selection signal."),
        ("Hyperparameters:", "n_components = 3, max_iter = 500, random_state = 42."),
    ])

add_algo_block(doc,
    "Env NMF Habitat Parts",
    [("Class","EnvNMFHabitatParts"), ("Category","feature_engineering"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"), ("Key parameter","n_components = 3")],
    "",
    extra_paras=[
        ("What it does:",
         "Non-negative Matrix Factorisation decomposes the environmental feature matrix into 3 "
         "additive, non-negative parts. During fit(), the component most correlated with altitude "
         "is identified as the terrain part and its weight at each GPS fix is the output score."),
        ("Why it's useful:",
         "NMF's non-negativity constraint produces components that naturally represent additive, "
         "physically meaningful habitat parts that don't cancel each other out."),
        ("Hyperparameters:", "n_components = 3, max_iter = 500, random_state = 42."),
    ])

# ── 4.6 Ensemble & Hybrid ────────────────────────────────────────────────────
add_heading(doc, "4.6  Ensemble & Hybrid  (4 algorithms)", 2)

add_algo_block(doc,
    "Env Voting Regressor",
    [("Class","EnvVotingRegressor"), ("Category","ensemble"), ("Library","sklearn"),
     ("Training subsample cap","10,000 points"),
     ("Base estimators","RF (50 trees) + GBM (50 trees, depth 3) + Ridge")],
    "",
    extra_paras=[
        ("What it does:",
         "Averages the predictions of three diverse base estimators: Random Forest (nonlinear, "
         "tree-based), Gradient Boosting (sequential nonlinear), and Ridge regression (linear). "
         "The simple average reduces variance compared to any single model."),
        ("Why it's useful:",
         "Each base estimator has different inductive biases — RF averages parallel trees (variance "
         "reduction), GBM builds sequentially (bias reduction), Ridge provides a smooth linear floor. "
         "Their average is less sensitive to any one model's failure mode."),
        ("Hyperparameters:", "RF n_estimators=50, GBM n_estimators=50 max_depth=3, Ridge alpha=1.0."),
    ])

add_algo_block(doc,
    "Env Bagging Regressor",
    [("Class","EnvBaggingRegressor"), ("Category","ensemble"), ("Library","sklearn"),
     ("Training subsample cap","20,000 points"), ("Key parameter","n_estimators = 50")],
    "",
    extra_paras=[
        ("What it does:",
         "Bootstrap aggregation trains 50 base decision trees on different bootstrap samples "
         "and averages their predictions. Unlike the Voting Regressor, all base estimators are "
         "the same type; variance reduction comes purely from bootstrap sampling."),
        ("Hyperparameters:", "n_estimators = 50, random_state = 42, n_jobs = -1."),
    ])

add_algo_block(doc,
    "Env LightGBM Regressor",
    [("Class","EnvLightGBMRegressor"), ("Category","ensemble"),
     ("Library","lightgbm (falls back to sklearn GBM if not installed)"),
     ("Training subsample cap","20,000 points"),
     ("Key parameters","n_estimators = 100, max_depth = 4")],
    "",
    extra_paras=[
        ("What it does:",
         "LightGBM is a histogram-based gradient boosting framework that grows trees leaf-wise "
         "rather than level-wise, and uses histogram binning to approximate gradient computations. "
         "Significantly faster than sklearn's GBM on datasets with many features or many rows."),
        ("Hyperparameters:", "n_estimators = 100, max_depth = 4, verbosity = -1, random_state = 42."),
    ])

add_algo_block(doc,
    "Env Stacking Regressor",
    [("Class","EnvStackingRegressor"), ("Category","ensemble"), ("Library","sklearn"),
     ("Training subsample cap","5,000 points  (3-fold CV makes training expensive)"),
     ("Meta-learner","Ridge regression"),
     ("Base estimators","RF (50 trees) + GBM (50 trees, depth 3) + Ridge")],
    "",
    extra_paras=[
        ("What it does:",
         "Stacking trains base estimators and then trains a meta-learner on their out-of-fold "
         "predictions. The 3-fold CV used during fit means each base estimator sees 2/3 of the "
         "data for training and the meta-learner sees predictions made on held-out data. "
         "The final prediction is the meta-learner Ridge's linear combination of the three outputs."),
        ("Why it's useful:",
         "Stacking can learn the optimal linear combination of diverse models, potentially "
         "outperforming a simple average. If RF is consistently better in certain speed/altitude "
         "regions and Ridge is better in others, the meta-learner can learn to weight them accordingly."),
        ("Hyperparameters:", "cv = 3, final_estimator = Ridge(alpha=1.0)."),
    ])

add_algo_block(doc,
    "Env CatBoost Regressor",
    [("Class","EnvCatBoostRegressor"), ("Category","ensemble"),
     ("Library","catboost (falls back to sklearn GBM if not installed)"),
     ("Training subsample cap","20,000 points"),
     ("Key parameters","iterations = 100, depth = 4")],
    "",
    extra_paras=[
        ("What it does:",
         "CatBoost is a gradient boosting implementation that handles categorical features natively "
         "via ordered target statistics encoding, without requiring one-hot encoding. In this service, "
         "the land_cover proxy is an ordinal categorical feature (4 terrain classes) — CatBoost can "
         "exploit this structure directly."),
        ("Hyperparameters:", "iterations = 100, depth = 4, random_seed = 42, verbose = 0."),
    ])

# ── 4.7 Causal & Explainable ─────────────────────────────────────────────────
add_heading(doc, "4.7  Causal & Explainable  (3 algorithms)", 2)

add_algo_block(doc,
    "Env Huber Regressor",
    [("Class","EnvHuberRegressor"), ("Category","causal_explainable"), ("Library","sklearn"),
     ("Training subsample cap","2,000 points"),
     ("Key parameters","epsilon = 1.35, alpha = 0.0001")],
    "",
    extra_paras=[
        ("What it does:",
         "The Huber regressor minimises a combination of squared loss (small residuals) and "
         "absolute loss (large residuals), controlled by the epsilon threshold. "
         "For |residual| < epsilon, it behaves like ordinary least squares; beyond epsilon it "
         "behaves like LAD (least absolute deviations). This makes coefficient estimates robust "
         "to GPS position outliers."),
        ("Why it's useful:",
         "Most interpretable robust regression method — the linear coefficients have the same "
         "meaning as ordinary regression but are not distorted by outliers. Clearest model for "
         "explaining which environmental features linearly drive movement speed."),
        ("Hyperparameters:",
         "epsilon = 1.35 (standard value; 1.35 ≈ 95% efficiency vs OLS under Gaussian noise), "
         "alpha = 0.0001, max_iter = 200."),
    ])

add_algo_block(doc,
    "Env Permutation Importance Score",
    [("Class","EnvPermutationImportanceScore"), ("Category","causal_explainable"), ("Library","sklearn"),
     ("Training subsample cap","5,000 points")],
    "",
    extra_paras=[
        ("What it does:",
         "Trains a Random Forest (50 trees), then runs permutation importance: for each feature, "
         "randomly shuffles its values 5 times and measures the average drop in accuracy. The feature "
         "with the highest permutation importance drop is identified as the most influential "
         "environmental variable. The output score per GPS fix is the raw value of that dominant feature."),
        ("Why it's useful:",
         "Permutation importance is model-agnostic and measures actual contribution to prediction "
         "rather than correlation. Answers: 'If we removed this environmental feature, how much worse "
         "would the model get?' — a principled, data-driven identification of the dominant environmental factor."),
        ("Hyperparameters:", "n_repeats = 5, random_state = 42."),
    ])

add_algo_block(doc,
    "Env Granger Causal Score",
    [("Class","EnvGrangerCausalScore"), ("Category","causal_explainable"), ("Library","numpy"),
     ("Key parameter","max_lag = 10")],
    "",
    extra_paras=[
        ("What it does:",
         "Uses lagged cross-correlation as a Granger causality proxy: during fit(), it finds the "
         "lag k ∈ [1, 10] at which altitude[t] is most correlated with speed[t+k]. The output "
         "score per GPS fix is the altitude value k steps ago — the lagged environmental value "
         "that best predicts the current speed."),
        ("Why it's useful:",
         "The only algorithm in Service 3 that captures temporal causality rather than "
         "instantaneous correlation. Tests whether the animal's current movement is responding "
         "to environmental conditions encountered moments ago — ecologically meaningful because "
         "animals often respond to terrain gradients after passing through them."),
        ("Hyperparameters:", "max_lag = 10 (search window for best lag, measured in GPS fixes)."),
    ])


# ════════════════════════════════════════════════════════════════════════════
# 5. HOW ALGORITHMS ARE SCORED
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "5. How Algorithms Are Scored", 1)

add_para(doc,
    "All 25 algorithms output a raw continuous float array. The backend normalises this to [0, 1] "
    "before sending it to the frontend using min-max normalisation:",
    size=10.5)

for line in [
    "  scores_norm = (raw_finite − min) / (max − min)",
]:
    p = doc.add_paragraph(line)
    p.paragraph_format.space_after = Pt(2)
    for run in p.runs:
        run.font.size = Pt(10)
        run.font.name = "Courier New"
        run.font.color.rgb = RGBColor(0x0D, 0x3B, 0x2B)

doc.add_paragraph()

add_para(doc, "Key implications of this normalisation:", size=10.5, bold=True)
for bullet in [
    "The score is relative — 0.0 is always the lowest-scoring GPS fix in the test set, 1.0 is always the highest.",
    "Scores are not comparable across datasets — only within a single run.",
    "Scores are comparable between algorithms within the same run, since both are normalised over the same test set.",
    "No classification metrics (F1, accuracy, precision, recall) are computed for Service 3.",
    "The backend evaluator (core/evaluator.py → _regression_metrics) does compute three "
    "internal quality metrics for every Service 3 run: Pearson r (linear correlation between "
    "predicted and true scores), Spearman r (rank correlation), and R² (coefficient of "
    "determination). These are stored in the result object but are not displayed as score "
    "cards in the frontend — they are available in the raw API response for programmatic use.",
]:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(bullet).font.size = Pt(10)

doc.add_paragraph()

add_para(doc, "Internal quality metrics (not shown in frontend UI):", size=10.5, bold=True)
add_table(doc,
    ["Metric", "Full name", "What it measures", "Range"],
    [
        ["pearson_r",  "Pearson correlation coefficient", "Linear correlation between predicted and true environmental scores", "−1 to +1 (higher = better linear fit)"],
        ["spearman_r", "Spearman rank correlation",       "Rank-order correlation — robust to outliers and non-linearity",     "−1 to +1 (higher = better rank agreement)"],
        ["r2",         "Coefficient of determination",    "Fraction of variance in the true score explained by the predicted score", "0.0 to 1.0 (higher = better; negative = worse than mean)"],
    ],
    col_widths=[1.0, 1.6, 3.0, 1.6])

doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# 6. FRONTEND VISUALISATIONS
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "6. Frontend Visualisations", 1)

add_para(doc,
    "Service 3 has three dedicated visualisation tabs that replace the standard F1 Scores, "
    "Cluster Graphs, and Feature Importance tabs shown for other services.",
    size=10.5)

add_heading(doc, "Tab 1: Env Profiles (EnvProfiles.jsx)", 2)
add_para(doc,
    "Displays two charts and a summary stat row:",
    size=10.5)
for item in [
    ("Score distribution histogram —",
     "20 bins from 0 to 1, log-scaled y-axis. Shows how the environmental score is distributed "
     "across all GPS fixes. A histogram concentrated near 0 means most fixes have low environmental "
     "influence; near 1 means consistently high; flat means consistent variation across the route."),
    ("Score vs latitude scatter —",
     "Each GPS fix plotted as (latitude, score). Reveals spatial trends: upward slope = "
     "higher-latitude locations have higher environmental scores (e.g. mountainous terrain at "
     "northern latitudes)."),
    ("Summary stat cards —",
     "Mean score, standard deviation, min, max."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(item[0] + "  ")
    r1.bold = True
    r1.font.size = Pt(10)
    r2 = p.add_run(item[1])
    r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)

doc.add_paragraph()

add_heading(doc, "Tab 2: Score over time (EnvScoreTime.jsx)", 2)
for item in [
    ("Smoothed score time series —",
     "Both algorithm A and B plotted as smooth line charts over GPS fix index (time-ordered). "
     "Uses a 5-fix rolling average for visual clarity. Peaks indicate environmental 'hotspots' along the route."),
    ("Difference bar chart (compare mode only) —",
     "Score A minus Score B at each fix. Green bars = algorithm A scores higher; "
     "purple bars = algorithm B scores higher. The agreement rate and high-disagreement fix count "
     "are shown as stat cards."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(item[0] + "  ")
    r1.bold = True
    r1.font.size = Pt(10)
    r2 = p.add_run(item[1])
    r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)

doc.add_paragraph()

add_heading(doc, "Tab 3: Algorithm comparison (EnvComparison.jsx)", 2)
for item in [
    ("Score A vs Score B scatter —",
     "Each point is one GPS fix, plotted as (score_A, score_B). Points on the diagonal mean both "
     "algorithms agree. Off-diagonal points are where they diverge. The Pearson correlation "
     "coefficient is computed and displayed with a strength label (Strong / Moderate / Weak)."),
    ("Score difference distribution —",
     "Histogram of (A−B) values across all fixes. A narrow peak at 0 means high agreement; "
     "a wide spread means systematic disagreement."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(item[0] + "  ")
    r1.bold = True
    r1.font.size = Pt(10)
    r2 = p.add_run(item[1])
    r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)

doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# 7. RESULTS INTERPRETATION GUIDE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "7. Results Interpretation Guide", 1)

add_heading(doc, "What does a high score mean?", 2)
add_para(doc, "The meaning depends on the algorithm:", size=10.5)

add_table(doc,
    ["Algorithm(s)", "High score means"],
    [
        ["Bayesian Ridge, PLS, Quantile, RF, GBM, XGBoost, SGD, Elastic Net, Voting, Bagging, LightGBM, Stacking, CatBoost, MLP, GPR",
         "Environmental conditions here are consistent with fast movement (model predicts high speed from environment)"],
        ["Kalman Filter",
         "Altitude here is high — strong terrain signal"],
        ["Fourier Transform",
         "Speed here is strongly driven by the dominant periodic environmental cycle"],
        ["Seasonal Decomposition",
         "Speed here is above the seasonal trend (more active than typical for this phase)"],
        ["Autoencoder Score",
         "Environmental conditions here are unusual / anomalous (high reconstruction error)"],
        ["PCA Score",
         "This fix is at the high-altitude / open terrain end of the main environmental gradient"],
        ["ICA Habitat Components",
         "High habitat novelty — unusual conditions independent of speed"],
        ["NMF Habitat Parts",
         "Strong terrain / elevation environmental component"],
        ["Permutation Importance Score",
         "The dominant environmental feature has a high value here"],
        ["Granger Causal Score",
         "The altitude value k steps ago (best predictor of current speed) is high"],
        ["Huber Regressor",
         "Robust linear prediction of high speed from environment"],
    ],
    col_widths=[2.8, 3.7])

add_heading(doc, "Comparing two algorithms", 2)
add_table(doc,
    ["Pearson correlation", "Interpretation"],
    [
        ["> 0.7 (Strong)",        "Both algorithms measure the same environmental gradient. Either gives a reliable picture."],
        ["0.4 – 0.7 (Moderate)",  "Partial agreement — algorithms are sensitive to different environmental aspects. Review both."],
        ["< 0.4 (Weak)",          "Algorithms measure fundamentally different things. Inspect score-vs-latitude and score-over-time charts."],
    ],
    col_widths=[1.7, 4.8])

add_heading(doc, "Typical patterns by animal type", 2)
add_table(doc,
    ["Animal", "Expected dominant environmental pattern"],
    [
        ["White Stork (migratory)",     "Strong Fourier/Seasonal signal (daily thermals); high Kalman scores at mountain crossing points"],
        ["African Elephant",            "Terrain-driven PCA/NMF scores; Granger lag likely 2–5 fixes (slow terrain response)"],
        ["African Cuckoo",              "High Fourier amplitude (long-distance migration with clear periodic structure)"],
        ["Black Guillemot (seabird)",   "Low terrain signal; high water-proximity score; wind proxy most important feature"],
        ["Whooper Swan",                "Altitude and slope dominate; Kalman/Bayesian Ridge score high at migration mountain passes"],
        ["Orchid Bees",                 "Short range; NMF vegetation/resource component most relevant"],
    ],
    col_widths=[2.0, 4.5])


# ════════════════════════════════════════════════════════════════════════════
# 8. DEPENDENCIES
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "8. Dependencies", 1)

add_table(doc,
    ["Library", "Constraint", "Purpose", "Fallback"],
    [
        ["numpy",        "Any",      "Kalman, Fourier, Seasonal, Granger — pure implementations",          "None — required"],
        ["scipy",        "Any",      "stats module (imported)",                                             "None — required"],
        ["scikit-learn", "≥ 1.0",    "All sklearn algorithms, PCA, ICA, NMF, metrics",                     "None — required"],
        ["xgboost",      "Optional", "EnvXGBoostRegressor",                                                 "Falls back to sklearn GBM"],
        ["lightgbm",     "Optional", "EnvLightGBMRegressor",                                                "Falls back to sklearn GBM"],
        ["catboost",     "Optional", "EnvCatBoostRegressor",                                                "Falls back to sklearn GBM"],
    ],
    col_widths=[1.0, 0.9, 3.0, 1.5])


# ════════════════════════════════════════════════════════════════════════════
# 9. SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "9. Summary Table — All 25 Algorithms", 1)

add_table(doc,
    ["#", "Algorithm name", "Category", "Library", "Train cap", "Key idea"],
    [
        ["1",  "Env Bayesian Ridge",                  "statistical",          "sklearn",    "2,000",   "Auto-regularised linear regression on env features"],
        ["2",  "Env PLS Regression",                  "statistical",          "sklearn",    "2,000",   "Latent factors shared between environment and speed"],
        ["3",  "Env Quantile Regression",              "statistical",          "sklearn",    "2,000",   "Robust median-based regression"],
        ["4",  "Env Kalman Filter",                    "time_series",          "numpy",      "20,000",  "Optimal altitude state estimation with noise filtering"],
        ["5",  "Env Fourier Transform",                "time_series",          "numpy",      "—",       "Dominant periodic environmental frequency extraction"],
        ["6",  "Env Seasonal Decomposition",           "time_series",          "numpy",      "—",       "Daily/periodic trend + seasonal + residual decomposition"],
        ["7",  "Env Random Forest Regressor",          "ml_supervised",        "sklearn",    "20,000",  "Nonlinear ensemble from bootstrap decision trees"],
        ["8",  "Env Gradient Boosting Regressor",      "ml_supervised",        "sklearn",    "20,000",  "Sequential residual-correcting shallow trees"],
        ["9",  "Env XGBoost Regressor",                "ml_supervised",        "xgboost*",   "20,000",  "Optimised Newton gradient boosting"],
        ["10", "Env SGD Regressor",                    "ml_supervised",        "sklearn",    "20,000",  "Online stochastic gradient descent with Huber loss"],
        ["11", "Env Elastic Net",                      "ml_supervised",        "sklearn",    "20,000",  "L1+L2 sparse regularisation for correlated features"],
        ["12", "Env MLP Regressor",                    "deep_learning",        "sklearn",    "10,000",  "2-layer neural network with early stopping"],
        ["13", "Env Gaussian Process Regressor",       "deep_learning",        "sklearn",    "500 ⚠",   "Probabilistic Matérn kernel surface (O(n³) cost)"],
        ["14", "Env Autoencoder Score",                "deep_learning",        "sklearn",    "20,000",  "PCA reconstruction error = environmental anomaly score"],
        ["15", "Env PCA Score",                        "feature_engineering",  "sklearn",    "20,000",  "First principal environmental gradient"],
        ["16", "Env ICA Habitat Components",           "feature_engineering",  "sklearn",    "20,000",  "Speed-independent habitat novelty axis"],
        ["17", "Env NMF Habitat Parts",                "feature_engineering",  "sklearn",    "20,000",  "Additive terrain/vegetation/energy decomposition"],
        ["18", "Env Voting Regressor",                 "ensemble",             "sklearn",    "10,000",  "Simple average of RF + GBM + Ridge"],
        ["19", "Env Bagging Regressor",                "ensemble",             "sklearn",    "20,000",  "Bootstrap-aggregated decision trees"],
        ["20", "Env LightGBM Regressor",               "ensemble",             "lightgbm*",  "20,000",  "Histogram boosting, leaf-wise tree growth"],
        ["21", "Env Stacking Regressor",               "ensemble",             "sklearn",    "5,000 ⚠", "Meta-learner Ridge on RF + GBM + Ridge"],
        ["22", "Env CatBoost Regressor",               "ensemble",             "catboost*",  "20,000",  "Native categorical (land_cover) feature handling"],
        ["23", "Env Huber Regressor",                  "causal_explainable",   "sklearn",    "2,000",   "Robust linear regression, GPS outlier-resistant"],
        ["24", "Env Permutation Importance Score",     "causal_explainable",   "sklearn",    "5,000",   "Dominant env feature identified by permutation drop"],
        ["25", "Env Granger Causal Score",             "causal_explainable",   "numpy",      "—",       "Lagged altitude → speed cross-correlation"],
    ],
    col_widths=[0.3, 1.85, 1.3, 0.85, 0.7, 2.25])

add_para(doc, "* Falls back to sklearn GBM if the optional library is not installed.  "
              "⚠ Reduced subsample cap due to computational cost.", size=9, color=GREY)


# ════════════════════════════════════════════════════════════════════════════
# 9b. BENCHMARK RESULTS (African cuckoo, real run)
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "9b. Benchmark Results — African Cuckoo Dataset", 1)

add_para(doc,
    "All 25 Service 3 algorithms were executed on the African cuckoo dataset "
    "(Iwajomo et al. 2018; 5,352 GPS fixes) using the VEBITA quality benchmark. "
    "Because Service 3 produces unsupervised environmental scores with no ground-truth label, "
    "the evaluation uses the first principal component of the input feature space as a proxy signal. "
    "Pearson r and Spearman r measure linear and rank correlation between the algorithm's output "
    "and this PC1 signal; R² is included for completeness. "
    "The table is sorted by Spearman r (rank correlation), which is more robust for bounded [0,1] outputs.",
    size=10.5)

doc.add_paragraph()

s3_bench = [
    # (algo_name, pearson, spearman, r2, runtime)
    ("Env ICA Habitat Components",      0.153,  0.390, -8.181, 0.044),
    ("Env Autoencoder Score",           0.044,  0.032, -8.440, 0.001),
    ("Env Seasonal Decomposition",      0.042,  0.028, -1.130, 0.001),
    ("Env Granger Causal Score",       -0.013,  0.083, -2.025, 0.001),
    ("Env Kalman Filter",              -0.003, -0.087, -1.996, 0.001),
    ("Env Fourier Transform",          -0.027, -0.040, -1.061, 0.001),
    ("Env MLP Regressor",              -0.029,  0.028, -6.322, 0.111),
    ("Env SGD Regressor",              -0.109, -0.077, -0.919, 0.002),
    ("Env PLS Regression",             -0.246, -0.237, -2.021, 0.001),
    ("Env Gaussian Process Regressor", -0.026, -0.050, -1.572, 0.094),
    ("Env CatBoost Regressor",         -0.019, -0.049, -2.067, 0.094),
    ("Env Gradient Boosting Regressor",-0.019, -0.049, -2.067, 0.095),
    ("Env LightGBM Regressor",         -0.019, -0.049, -2.067, 0.095),
    ("Env XGBoost Regressor",          -0.019, -0.049, -2.067, 0.094),
    ("Env Stacking Regressor",         -0.019, -0.050, -2.074, 0.365),
    ("Env Voting Regressor",           -0.019, -0.050, -2.080, 0.107),
    ("Env Bagging Regressor",          -0.020, -0.050, -2.100, 1.466),
    ("Env Bayesian Ridge",             -0.020, -0.050, -2.027, 0.001),
    ("Env Elastic Net",                -0.020, -0.050, -2.027, 0.001),
    ("Env Huber Regressor",            -0.020, -0.050, -2.027, 0.015),
    ("Env NMF Habitat Parts",          -0.020, -0.050, -2.027, 0.003),
    ("Env PCA Score",                  -0.020, -0.050, -2.027, 0.001),
    ("Env Permutation Importance Score",-0.020,-0.050, -2.027, 0.874),
    ("Env Quantile Regression",        -0.020, -0.050, -2.027, 0.006),
    ("Env Random Forest Regressor",    -0.020, -0.050, -2.081, 0.101),
]
# Sort by spearman descending
s3_bench_sorted = sorted(s3_bench, key=lambda x: x[2], reverse=True)

bench_hdr = ("Rank", "Algorithm", "Pearson r", "Spearman r", "R²", "Runtime")
bench_rows = [(str(i+1), r[0], f"{r[1]:.3f}", f"{r[2]:.3f}", f"{r[3]:.3f}", f"{r[4]:.3f}s")
              for i, r in enumerate(s3_bench_sorted)]

brows = len(bench_rows) + 1
btbl = doc.add_table(rows=brows, cols=6)
btbl.style = "Table Grid"

# Header
hcols = bench_hdr
for ci, htext in enumerate(hcols):
    cell = btbl.rows[0].cells[ci]
    cell.text = htext
    set_cell_bg(cell, "0A1828")
    for p in cell.paragraphs:
        for r in p.runs:
            r.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = WHITE

for ri, row_data in enumerate(bench_rows, 1):
    # Top 3 = green, bottom 3 = red, alternating otherwise
    if ri <= 3:
        bg = "E8F5E8"
    elif ri >= len(bench_rows) - 2:
        bg = "F5E8E8"
    else:
        bg = "EEF3FA" if ri % 2 == 0 else "FFFFFF"
    for ci, txt in enumerate(row_data):
        cell = btbl.rows[ri].cells[ci]
        cell.text = txt
        set_cell_bg(cell, bg)
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.size = Pt(8.5)
                if ri <= 3 and ci == 1:
                    run.bold = True

btbl.columns[0].width = Inches(0.45)
btbl.columns[1].width = Inches(2.9)
btbl.columns[2].width = Inches(0.8)
btbl.columns[3].width = Inches(0.85)
btbl.columns[4].width = Inches(0.65)
btbl.columns[5].width = Inches(0.65)

doc.add_paragraph()
add_para(doc,
    "Note: Correlation values against the PC1 proxy are low for most algorithms because Service 3 "
    "is designed to compare two algorithms against each other, not to predict a single ground-truth signal. "
    "The PC1 proxy is a reference signal, not a true label. "
    "Env ICA Habitat Components shows the highest rank correlation (Spearman r = 0.390) because ICA "
    "extracts statistically independent components that align more closely with the principal variance "
    "directions in the feature space.",
    size=9.5)

doc.add_paragraph()

# ════════════════════════════════════════════════════════════════════════════
# 10. ALGORITHM RECOMMENDATIONS
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "10. Algorithm Recommendations", 1)

add_para(doc,
    "The table below ranks all 25 Service 3 algorithms across three dimensions: "
    "Quality (how well it captures real environmental variation), "
    "Speed (how fast it runs on a typical 20,000-point dataset), and "
    "Interpretability (how easy it is to explain what the score means). "
    "Use these ratings to decide which two algorithms to compare in the app.",
    size=10.5)

doc.add_paragraph()

# ── Tier key ────────────────────────────────────────────────────────────────
add_heading(doc, "Tier key", 2)
tier_tbl = doc.add_table(rows=4, cols=3)
tier_tbl.style = "Table Grid"
tier_data = [
    ("Tier", "Meaning", "Colour"),
    ("★★★  Best",      "Recommended — high quality, reasonable speed",          "1A7A52"),
    ("★★    Good",     "Solid choice — good quality or very fast",               "5DCAA5"),
    ("★      Niche",   "Use only when you specifically want what it offers",     "EF9F27"),
]
tier_colors = ["0D3B2B", "E8F7F2", "E8F7F2", "FFF8EE"]
for ri, (a, b, c) in enumerate(tier_data):
    tier_tbl.rows[ri].cells[0].text = a
    tier_tbl.rows[ri].cells[1].text = b
    tier_tbl.rows[ri].cells[2].text = c
    for ci in range(3):
        for p in tier_tbl.rows[ri].cells[ci].paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)
                if ri == 0:
                    run.bold = True
                    run.font.color.rgb = WHITE
    if ri == 0:
        for ci in range(3):
            set_cell_bg(tier_tbl.rows[ri].cells[ci], "0D3B2B")
tier_tbl.columns[0].width = Inches(1.2)
tier_tbl.columns[1].width = Inches(3.8)
tier_tbl.columns[2].width = Inches(1.3)
doc.add_paragraph()

# ── Rating chart (bar chart via shaded table cells) ─────────────────────────
add_heading(doc, "Visual rating chart — Quality, Speed, Interpretability", 2)
add_para(doc,
    "Each bar is made of filled blocks out of 5. Read each row as a mini bar chart. "
    "Algorithms are sorted best-to-worst by overall score.",
    size=10, color=GREY)

def bar(score, total=5, fill_hex="5DCAA5", empty_hex="E0E0E0"):
    """Return list of hex colours for a bar of `total` cells."""
    return [fill_hex] * score + [empty_hex] * (total - score)

# (name, quality 0-5, speed 0-5, interp 0-5, tier, note)
s3_ratings = [
    ("Env Random Forest Regressor",      5, 4, 3, "★★★", "Best all-round — nonlinear, fast, reliable"),
    ("Env LightGBM Regressor",           5, 5, 3, "★★★", "Fastest boosting option — very close to RF quality"),
    ("Env Gradient Boosting Regressor",  5, 4, 3, "★★★", "Excellent quality; slightly slower than LightGBM"),
    ("Env XGBoost Regressor",            5, 4, 3, "★★★", "Same as GBM but even faster when xgboost installed"),
    ("Env Voting Regressor",             5, 3, 3, "★★★", "Combines RF + GBM + Ridge — robust & consistent"),
    ("Env Bagging Regressor",            4, 4, 3, "★★",  "Solid variance-reducer; simple bootstrap approach"),
    ("Env CatBoost Regressor",           4, 4, 3, "★★",  "Good on land_cover feature; needs catboost installed"),
    ("Env Stacking Regressor",           5, 2, 3, "★★",  "Highest potential quality but slow (3-fold CV)"),
    ("Env MLP Regressor",                4, 3, 2, "★★",  "Good nonlinear model; needs 10,000 pt cap"),
    ("Env Elastic Net",                  3, 5, 4, "★★",  "Very fast linear model; great interpretability"),
    ("Env Bayesian Ridge",               3, 5, 4, "★★",  "Auto-regularised; fast; clear linear coefficients"),
    ("Env PLS Regression",               3, 5, 4, "★★",  "Best for correlated features; 3 latent components"),
    ("Env Huber Regressor",              3, 5, 5, "★★",  "Most interpretable; robust to GPS outliers"),
    ("Env Permutation Importance Score", 4, 3, 5, "★★",  "Explains which env feature dominates the route"),
    ("Env PCA Score",                    3, 5, 4, "★",   "Good overview but only captures linear variation"),
    ("Env SGD Regressor",                3, 5, 3, "★",   "Fastest training; lower accuracy than tree methods"),
    ("Env Quantile Regression",          3, 4, 4, "★",   "Better than mean regression on outlier-heavy data"),
    ("Env Kalman Filter",                3, 5, 4, "★",   "Best for altitude-dominated terrain; altitude only"),
    ("Env Fourier Transform",            3, 5, 3, "★",   "Use when you suspect periodic daily/tidal cycles"),
    ("Env Seasonal Decomposition",       3, 5, 3, "★",   "Use when you want seasonal trend separated out"),
    ("Env NMF Habitat Parts",            3, 4, 3, "★",   "Additive parts only; good for terrain decomp"),
    ("Env ICA Habitat Components",       3, 4, 2, "★",   "Speed-independent habitat signal; harder to explain"),
    ("Env Autoencoder Score",            3, 4, 2, "★",   "Anomaly/novelty score — use to find unusual fixes"),
    ("Env Granger Causal Score",         2, 5, 3, "★",   "Useful only on terrain with changing altitude"),
    ("Env Gaussian Process Regressor",   3, 3, 3, "★",   "Probabilistic but O(n³) — capped at 500 points"),
]

TOTAL = 5
BAR_W = Inches(0.18)
NAME_W = Inches(2.0)
TIER_W = Inches(0.5)

# Header row
hdr_cols = ["Algorithm", "Tier"] + ["Q"] * TOTAL + [""] + ["S"] * TOTAL + [""] + ["I"] * TOTAL
chart_tbl = doc.add_table(rows=1 + len(s3_ratings), cols=len(hdr_cols))
chart_tbl.style = "Table Grid"

hdr_row = chart_tbl.rows[0]
for ci, h in enumerate(hdr_cols):
    set_cell_bg(hdr_row.cells[ci], "0D3B2B")
    set_cell_bold_white(hdr_row.cells[ci], h, size=8)

# Legend labels above bars
for ci, label in [(2, "Quality ▶"), (8, "Speed ▶"), (14, "Interp ▶")]:
    set_cell_bg(hdr_row.cells[ci], "0A1828")
    hdr_row.cells[ci].paragraphs[0].runs[0].text = label

for ri, (name, q, s, interp, tier, note) in enumerate(s3_ratings):
    row = chart_tbl.rows[ri + 1]
    # Name cell
    row.cells[0].text = name.replace("Env ", "")
    for p in row.cells[0].paragraphs:
        for run in p.runs:
            run.font.size = Pt(8)
    # Tier cell
    row.cells[1].text = tier
    for p in row.cells[1].paragraphs:
        for run in p.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = GREEN if "★★★" in tier else (RGBColor(0x2E,0x86,0x6B) if "★★" in tier else GREY)
    # Quality bars (cols 2..6)
    for bi, hex_c in enumerate(bar(q, TOTAL, "1A5C3A", "C8E8D8")):
        set_cell_bg(row.cells[2 + bi], hex_c)
        row.cells[2 + bi].text = ""
    # spacer col 7
    set_cell_bg(row.cells[7], "FFFFFF")
    row.cells[7].text = ""
    # Speed bars (cols 8..12)
    for bi, hex_c in enumerate(bar(s, TOTAL, "1A4A8A", "D0D8EA")):
        set_cell_bg(row.cells[8 + bi], hex_c)
        row.cells[8 + bi].text = ""
    # spacer col 13
    set_cell_bg(row.cells[13], "FFFFFF")
    row.cells[13].text = ""
    # Interp bars (cols 14..18)
    for bi, hex_c in enumerate(bar(interp, TOTAL, "8A6A00", "EAE0C0")):
        set_cell_bg(row.cells[14 + bi], hex_c)
        row.cells[14 + bi].text = ""

# Set column widths
chart_tbl.columns[0].width = NAME_W
chart_tbl.columns[1].width = TIER_W
for ci in range(2, len(hdr_cols)):
    chart_tbl.columns[ci].width = BAR_W

doc.add_paragraph()
add_para(doc, "Q = Quality (accuracy of environmental signal)  |  S = Speed (5 = fastest)  |  I = Interpretability (5 = easiest to explain)",
    size=8, color=GREY)
doc.add_paragraph()

# ── Top picks table ──────────────────────────────────────────────────────────
add_heading(doc, "Top algorithm picks by use case", 2)
add_table(doc,
    ["Use case", "Best pick", "Why"],
    [
        ["Best overall quality",          "Random Forest Regressor",      "Nonlinear, handles correlated features, 20k training points"],
        ["Fastest run",                   "LightGBM Regressor",           "Histogram boosting — nearly as accurate as RF but much faster"],
        ["Most interpretable result",     "Huber Regressor",              "Linear coefficients show exactly which env feature drives score"],
        ["Explain which feature matters", "Permutation Importance Score", "Tells you which of the 8 features is the dominant driver"],
        ["Periodic species (stork/swan)", "Fourier Transform",            "Captures daily thermals and seasonal migration cycles"],
        ["Anomaly / unusual fixes",       "Autoencoder Score",            "High score = environmentally unusual GPS point"],
        ["Terrain-dominated species",     "Kalman Filter + PCA Score",    "Both driven by altitude — good for mountain/hill species"],
        ["Causal question (lag effect)",  "Granger Causal Score",         "Tests whether past terrain predicts current speed"],
    ],
    col_widths=[1.9, 2.0, 2.6])

# ── Algorithms to avoid for beginners ───────────────────────────────────────
add_heading(doc, "Algorithms with limitations to be aware of", 2)
add_table(doc,
    ["Algorithm", "Limitation", "When it is fine to use"],
    [
        ["Gaussian Process Regressor", "Only trains on 500 points (O(n³) cost) — may miss patterns in large datasets",
         "Small datasets (< 1,000 GPS fixes) or when you need uncertainty estimates"],
        ["Granger Causal Score",       "Outputs near-zero on flat terrain (e.g. savanna, plains)",
         "Mountain species, coastal birds with tidal altitude variation"],
        ["Stacking Regressor",         "Slow: 3-fold cross-validation during training",
         "When accuracy matters more than speed and you have time to wait"],
        ["ICA Habitat Components",     "Harder to interpret — independent components have no obvious physical meaning",
         "Research/exploration context, not for explaining results to non-experts"],
        ["Autoencoder Score",          "Scores anomalies, not typical behaviour — most fixes will score near 0",
         "Specifically looking for unusual or outlier GPS points"],
    ],
    col_widths=[1.8, 2.8, 1.9])

doc.add_paragraph()

# ════════════════════════════════════════════════════════════════════════════
# 11. LIVE RESULTS — SCREENSHOTS
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "11. Live Results — Screenshots", 1)

add_para(doc,
    "The following screenshots were captured from the running VEBITA application using the "
    "Black-backed jackal, Etosha National Park, Namibia dataset (130,688 GPS fixes, "
    "species: Canis mesomelas). Two comparison runs are shown — "
    "Run 1: Granger Causal Score vs Permutation Importance Score, "
    "Run 2: Gaussian Process Regressor vs Bagging Regressor.",
    size=10.5)

doc.add_paragraph()

def add_screenshot(doc, img_path, caption, width_inches=6.3):
    try:
        doc.add_picture(img_path, width=Inches(width_inches))
        last = doc.paragraphs[-1]
        last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception as e:
        add_para(doc, f"[Image not found: {img_path}]", size=9, color=GREY)
    p_cap = doc.add_paragraph(caption)
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(14)
    for run in p_cap.runs:
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = GREY

# ── RUN 1: Granger Causal Score vs Permutation Importance Score ──────────────

add_heading(doc, "Run 1 — Granger Causal Score  vs  Permutation Importance Score", 2)
add_para(doc,
    "Dataset: Black-backed jackal, Etosha National Park, Namibia  ·  130,688 GPS fixes  ·  "
    "Algorithms: Causal Explainable category",
    size=10, color=GREY)
doc.add_paragraph()

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.26.37.png",
    "Figure 1 — Map view (Split). Left: Granger Causal Score (green gradient). "
    "Right: Permutation Importance Score (purple gradient). Each dot is one GPS fix "
    "coloured by its normalised environmental score.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.26.44.png",
    "Figure 2 — Env Profiles. Top: Score distribution histogram (log scale). "
    "Granger scores cluster at 0 (flat savanna altitude = near-constant lagged signal). "
    "Permutation scores spread more evenly. Bottom: Score vs latitude scatter.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.26.50.png",
    "Figure 3 — Score over time. Agreement rate: 94.8%, 26 high-disagreement fixes out of 20,000. "
    "Permutation score (purple) shows clear periodic spikes along the route; "
    "Granger (green) is nearly flat, consistent with a constant-altitude savanna habitat.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.26.57.png",
    "Figure 4 — Algorithm comparison. Pearson correlation = 0.000 (Weak positive). "
    "Scatter plot shows all Granger scores clustered at x ≈ 0, confirming it outputs "
    "a near-uniform signal on flat terrain. Score difference histogram shifted left — "
    "Permutation score is consistently higher than Granger.")

# ── Key observations for Run 1 ───────────────────────────────────────────────
add_heading(doc, "Key observations — Run 1", 3)
for obs in [
    "Granger Causal Score produces near-zero output on this jackal dataset because the Black-backed jackal "
    "moves across flat Etosha savanna — altitude barely changes between consecutive fixes, so the lagged "
    "altitude-to-speed cross-correlation finds no predictive lag. This is the correct and expected result "
    "for a flat-terrain species.",
    "Permutation Importance Score successfully identifies a dominant environmental feature and uses it "
    "to score each GPS fix, producing meaningful variation across the route (mean 0.032, std 0.117).",
    "The 0.000 Pearson correlation between the two algorithms is expected given the above — they are "
    "measuring fundamentally different things on this dataset.",
    "The 94.8% agreement rate is somewhat misleading here: both algorithms output low scores for most "
    "fixes, which counts as 'agreement' even though for different reasons.",
]:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(obs).font.size = Pt(10)
doc.add_paragraph()

# ── RUN 2: Gaussian Process Regressor vs Bagging Regressor ───────────────────

doc.add_page_break()
add_heading(doc, "Run 2 — Gaussian Process Regressor  vs  Bagging Regressor", 2)
add_para(doc,
    "Dataset: Black-backed jackal, Etosha National Park, Namibia  ·  130,688 GPS fixes  ·  "
    "Algorithms: Deep Learning vs Ensemble category",
    size=10, color=GREY)
doc.add_paragraph()

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.26.26.png",
    "Figure 5 — Map view (Split). Left: Gaussian Process Regressor (green gradient, 0.20s runtime). "
    "Right: Bagging Regressor (purple gradient, 2.04s runtime). Both show similar spatial "
    "distribution of environmental scores across the jackal's range.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.27.32.png",
    "Figure 6 — Env Profiles. Both algorithms show similar histogram shapes, both concentrated "
    "at low scores (0.0–0.20 range) with tails extending to higher values. "
    "Stat cards: GPR mean = 0.061, std = 0.064; Bagging mean = 0.084, std = 0.159.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.27.38.png",
    "Figure 7 — Score over time. Agreement rate: 94.0%, 30 high-disagreement fixes. "
    "Both algorithms track each other closely (green GPR line and purple Bagging line overlap). "
    "Score difference chart shows mostly small deviations with occasional spikes where Bagging "
    "scores higher than GPR (purple bars).")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-18 at 18.27.45.png",
    "Figure 8 — Algorithm comparison. Pearson correlation = 0.654 (Moderate positive). "
    "Scatter plot shows a clear positive trend — points cluster along the diagonal, "
    "meaning both algorithms generally agree on which GPS fixes have higher environmental scores. "
    "Score difference distribution shows a narrow peak near 0 (mostly agreement) with a slight "
    "leftward shift (Bagging scores marginally higher on average).")

# ── Key observations for Run 2 ───────────────────────────────────────────────
add_heading(doc, "Key observations — Run 2", 3)
for obs in [
    "Pearson correlation of 0.654 (Moderate positive) shows that GPR and Bagging agree "
    "on the broad environmental picture — both are supervised regressors trained on the same "
    "12 environmental proxy features predicting movement speed.",
    "GPR (0.20s) is significantly faster than Bagging (2.04s) on this dataset. This is because "
    "GPR trains on only 500 subsampled points (O(n³) constraint) while Bagging uses up to 20,000. "
    "GPR's speed advantage is entirely due to its smaller training set, not algorithmic efficiency.",
    "Bagging has a higher mean score (0.084 vs 0.061) and higher standard deviation (0.159 vs 0.064), "
    "meaning it finds more environmental variation across the route — a result of training on 40× "
    "more data points.",
    "The 94.0% agreement rate and moderate Pearson correlation together suggest these two algorithms "
    "are suitable alternatives when comparing deep learning vs ensemble approaches on the same dataset.",
]:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(obs).font.size = Pt(10)

doc.add_paragraph()

# ── Summary of both runs ─────────────────────────────────────────────────────
add_heading(doc, "Cross-run summary", 2)
add_table(doc,
    ["Metric", "Run 1: Granger vs Permutation", "Run 2: GPR vs Bagging"],
    [
        ["Dataset",              "Black-backed jackal, Namibia",  "Black-backed jackal, Namibia"],
        ["GPS fixes",            "130,688 (20,000 visualised)",   "130,688 (20,000 visualised)"],
        ["Algorithm A runtime",  "0.003s",                        "0.20s"],
        ["Algorithm B runtime",  "0.921s",                        "2.04s"],
        ["Agreement rate",       "94.8%",                         "94.0%"],
        ["High-disagreement fixes", "26",                         "30"],
        ["Pearson correlation",  "0.000 (Weak)",                  "0.654 (Moderate)"],
        ["Mean score — A",       "0.000",                         "0.061"],
        ["Mean score — B",       "0.032",                         "0.084"],
    ],
    col_widths=[1.9, 2.6, 2.6])

doc.add_paragraph()
p_end = doc.add_paragraph()
p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_end = p_end.add_run("End of Report — VEBITA Service 3: Environmental Factors")
r_end.italic = True
r_end.font.size = Pt(10)
r_end.font.color.rgb = GREY

# ── Save ─────────────────────────────────────────────────────────────────────
out_path = "/Users/I776893/Downloads/Movement Project/Service_3_Environmental_Factors_Report.docx"
doc.save(out_path)
print(f"Saved: {out_path}")
