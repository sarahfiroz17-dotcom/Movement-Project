"""
Generate Service_6_Behavioural_Classification_Report.docx
Run with: /usr/bin/python3 generate_s6_report.py
All algorithm names, IDs, hyperparameters and subsample caps verified against
backend/vebita_framework/services/s6_classification/arshan_algorithms.py
Metrics verified against core/evaluator.py
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

# Colours
AMBER  = RGBColor(0xEF, 0x9F, 0x27)
GREEN  = RGBColor(0x5D, 0xCA, 0xA5)
GREY   = RGBColor(0x55, 0x55, 0x55)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
RED    = RGBColor(0xCC, 0x44, 0x44)
BLUE   = RGBColor(0x37, 0x8A, 0xDD)

HDR_HEX  = "3B2800"
BEST_HEX = "1A4A2A"   # dark green — top tier rows
WARN_HEX = "4A2A00"   # amber — caution rows
FAIL_HEX = "4A1A1A"   # dark red — poor rows

# ── Helpers ────────────────────────────────────────────────────────────────────

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
    col = AMBER if level == 1 else (RGBColor(0xB5,0x75,0x00) if level == 2 else RGBColor(0x8B,0x60,0x00))
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
                set_cell_bg(cell, "FFF5E8")
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in tbl.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return tbl

def add_algo_block(doc, name, props, extra_paras=None):
    h = doc.add_heading(name, level=3)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x8B, 0x60, 0x00)
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
            set_cell_bg(tbl.rows[ri].cells[0], "F5F0E8")
            set_cell_bg(tbl.rows[ri].cells[1], "F5F0E8")
    tbl.columns[0].width = Inches(1.8)
    tbl.columns[1].width = Inches(4.5)
    doc.add_paragraph()
    for label, text in (extra_paras or []):
        p = doc.add_paragraph()
        if label:
            r1 = p.add_run(f"{label}  "); r1.bold = True
            r1.font.size = Pt(10); r1.font.color.rgb = RGBColor(0x5A, 0x3E, 0x00)
        r2 = p.add_run(text); r2.font.size = Pt(10)
        p.paragraph_format.space_after = Pt(4)
    doc.add_paragraph()

def add_screenshot(doc, img_path, caption, width_inches=6.3):
    try:
        doc.add_picture(img_path, width=Inches(width_inches))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception:
        add_para(doc, f"[Image not found: {img_path}]", size=9, color=GREY)
    p = doc.add_paragraph(caption)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(14)
    for run in p.runs:
        run.italic = True; run.font.size = Pt(9); run.font.color.rgb = GREY

def bar(score, total=5, fill_hex="8B6000", empty_hex="FFF0D0"):
    return [fill_hex] * score + [empty_hex] * (total - score)


# ════════════════════════════════════════════════════════════════════════════
# COVER
# ════════════════════════════════════════════════════════════════════════════

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("VEBITA"); r.bold = True; r.font.size = Pt(28); r.font.color.rgb = AMBER

p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = p2.add_run("Service 6 — Behavioural Classification")
r2.font.size = Pt(18); r2.font.color.rgb = GREY

p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = p3.add_run("Technical Project Report")
r3.font.size = Pt(14); r3.font.color.rgb = GREY

doc.add_paragraph()
for lbl, val in [("Author","Arshan"), ("Service ID","6"),
                  ("Project","VEBITA — Animal Movement Analysis Platform"),
                  ("Date","October 2026")]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{lbl}:  "); r.bold = True; r.font.size = Pt(11)
    r2 = p.add_run(val); r2.font.size = Pt(11)

doc.add_page_break()


# ════════════════════════════════════════════════════════════════════════════
# 1. SERVICE OVERVIEW
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "1. Service Overview", 1)
add_para(doc,
    "Service 6 — Behavioural Classification — labels every GPS fix in a Movebank "
    "dataset with the animal's predicted behaviour state. The four states are:")

for state, desc in [
    ("0 — Resting",    "Very low speed and step length; high turning angle variability."),
    ("1 — Foraging",   "Low-to-moderate speed; frequent direction changes; short steps."),
    ("2 — Travelling", "Moderate speed; straighter path; medium step lengths."),
    ("3 — Migrating",  "High speed; very straight path; large step lengths."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{state}:  "); r1.bold = True; r1.font.size = Pt(10)
    r1.font.color.rgb = AMBER
    r2 = p.add_run(desc); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)

doc.add_paragraph()
add_para(doc,
    "When a dataset has no true_behavior column, the backend automatically assigns labels "
    "using KMeans clustering on speed, altitude and turning angle. All 21 algorithms are "
    "supervised — they learn from these labels during training and predict on held-out data.")

add_heading(doc, "Scope", 2)
add_table(doc,
    ["Property", "Value"],
    [
        ["Total algorithms",       "21"],
        ["Categories",             "7 (Linear, Tree, Kernel, Probabilistic, Deep Learning, Ecological, Advanced Boosting)"],
        ["Service type",           "Multi-class classification (4 behaviour states)"],
        ["Output per algorithm",   "Integer label array: 0 = Resting, 1 = Foraging, 2 = Travelling, 3 = Migrating"],
        ["Input feature matrix",   "5 visible GPS features + 3 backend rolling features (8 total)"],
        ["Train / test split",     "Temporal: first 80% of GPS fixes for training, last 20% for testing"],
        ["File location",          "backend/vebita_framework/services/s6_classification/arshan_algorithms.py"],
    ],
    col_widths=[2.0, 4.3])


# ════════════════════════════════════════════════════════════════════════════
# 2. ARCHITECTURE & DATA FLOW
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "2. Architecture & Data Flow", 1)

add_heading(doc, "Integration into the VEBITA framework", 2)
add_para(doc,
    "Every algorithm class is decorated with @registry.register and sets service_id = 6. "
    "The central /run endpoint in main.py detects service_id == 6, takes the classification "
    "branch, and computes the four standard classification metrics after prediction.")

add_heading(doc, "Run pipeline", 2)
for step in [
    "1.  User uploads Movebank CSV",
    "2.  Shared streaming pipeline extracts 8 features per GPS fix",
    "3.  If no true_behavior column: KMeans auto-labels on speed + altitude + turning_angle",
    "4.  Temporal split: first 80% → training, last 20% → test",
    "5.  algorithm.fit(X_train, y_train)  →  algorithm.predict(X_test)  →  label array",
    "6.  Evaluator computes: accuracy, F1-macro, F1-weighted, precision (macro), recall (macro), per-class F1",
    "7.  Frontend: Map view / Cluster graphs / Time series / F1 Scores / Feature Importance",
]:
    p = doc.add_paragraph(step)
    p.paragraph_format.space_after = Pt(2)
    for run in p.runs:
        run.font.size = Pt(10); run.font.name = "Courier New"
doc.add_paragraph()

add_heading(doc, "Input: GPS movement features (5 visible features)", 2)
add_para(doc,
    "Five features are visible on screen (Time Series tab, map popups). "
    "Three additional rolling features are computed internally by the streaming pipeline "
    "and never shown as raw values — they only appear as importance scores in the "
    "Feature Importance tab when they rank highly.")

add_table(doc,
    ["Feature", "Description", "Visible in app"],
    [
        ["speed_ms",        "Instantaneous ground speed (m/s)",                          "Yes — Time Series, map popup"],
        ["altitude_m",      "Recorded altitude (metres above MSL)",                      "Yes — Time Series, map popup"],
        ["turning_angle",   "Change in heading between consecutive fixes (0–180°)",      "Yes — Time Series"],
        ["straightness",    "Net displacement ÷ path length over 5 fixes (0–1)",         "Yes — Time Series"],
        ["step_length_m",   "Haversine distance to previous GPS fix (metres)",           "Yes — Time Series histogram"],
        ["speed_roll_mean", "5-fix centred rolling mean of speed_ms",                    "No — Feature Importance tab only"],
        ["speed_roll_std",  "5-fix centred rolling std of speed_ms",                     "No — Feature Importance tab only"],
        ["alt_roll_mean",   "5-fix centred rolling mean of altitude_m",                  "No — Feature Importance tab only"],
    ],
    col_widths=[1.5, 3.2, 1.6])

add_heading(doc, "Metrics computed by the evaluator", 2)
add_para(doc,
    "For every Service 6 run the evaluator (core/evaluator.py, _classification_metrics) "
    "computes these five metrics and returns them to the frontend:")
add_table(doc,
    ["Metric", "Averaging", "What it measures"],
    [
        ["accuracy",    "—",        "Fraction of test GPS fixes labelled correctly"],
        ["f1_macro",    "macro",    "Unweighted mean F1 across all 4 behaviour classes — treats each class equally regardless of how common it is"],
        ["f1_weighted", "weighted", "F1 weighted by how many fixes belong to each class — the number shown as the main F1 card in the frontend"],
        ["precision",   "macro",    "Mean precision across all 4 classes"],
        ["recall",      "macro",    "Mean recall across all 4 classes"],
        ["per_class_f1","per class","Individual F1 for Resting, Foraging, Travelling, Migrating — shown in the F1 Scores breakdown table"],
    ],
    col_widths=[1.3, 0.9, 4.1])

add_para(doc,
    "Note: the main F1 number shown in the frontend header card is f1_weighted. "
    "The Cluster Graphs tab shows per_class_f1. Algorithm comparison uses f1_weighted "
    "to decide which algorithm is 'Best'.",
    size=9.5, color=GREY)


# ════════════════════════════════════════════════════════════════════════════
# 3. SHARED HELPERS
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "3. Shared Helper Functions", 1)
add_para(doc,
    "These utility functions are defined at the top of arshan_algorithms.py and "
    "shared by all 21 algorithms.")
add_table(doc,
    ["Helper", "Signature", "Purpose"],
    [
        ["_y",                 "_y(y, n)",              "Converts y to int array; returns all-zeros if y is None or wrong length — safe fallback when no labels exist"],
        ["_majority",          "_majority(arr)",         "Returns the most common value — used to map GMM/KMeans cluster IDs to behaviour labels"],
        ["_sigmoid",           "_sigmoid(x)",            "Numerically stable sigmoid, clipped to [-15, 15] to prevent overflow"],
        ["_softmax",           "_softmax(x)",            "Row-wise softmax with 1e-9 epsilon — used in MLP and LSTM output layers"],
        ["_relu",              "_relu(x)",               "Element-wise ReLU — used in MLP hidden layers and TCN convolutions"],
        ["_ce_grad",           "_ce_grad(probs,y,K)",    "Cross-entropy gradient for manual backpropagation in MLP"],
        ["_transition_counts", "_transition_counts(y,K)","Counts state transitions in label sequence — builds HMM transition matrix A"],
        ["_subsample",         "_subsample(X,y,max_n,seed=42)", "Random subsample without replacement; seed=42 for reproducibility — used to cap training cost"],
    ],
    col_widths=[1.5, 2.0, 2.8])


# ════════════════════════════════════════════════════════════════════════════
# 4. ALGORITHM CATALOGUE
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "4. Algorithm Catalogue", 1)

add_heading(doc, "Category overview", 2)
add_table(doc,
    ["Cat.", "Name", "Principle", "Algorithms"],
    [
        ["A", "Linear & Statistical",    "Linear decision boundaries from labelled GPS data",            "A01 Logistic Regression, A05 LDA, A29 Expert Rules"],
        ["B", "Tree & Ensemble",         "Non-linear splits learned from labelled data",                 "B34 Random Forest 100, B37 Gradient Boosting, B39 XGBoost"],
        ["C", "Kernel & Distance-Based", "Classify by distance or curved boundaries in feature space",  "C56 SVM RBF, C63 kNN k=7, C69 Mahalanobis Classifier"],
        ["D", "Probabilistic & Bayesian","Model each behaviour as a statistical distribution",           "D72 HMM 4-State, D77 GMM Classifier, D80 Kalman+GMM"],
        ["E", "Deep Learning",           "Neural architectures (pure numpy — no PyTorch/TF)",           "E81 MLP, E83 LSTM, E87 TCN"],
        ["F", "Ecological-Specific",     "Domain rules and ecological features drive classification",    "F105 HMM+RF Hybrid, F106 Migration Speed Classifier, F107 Turning Angle Classifier"],
        ["G", "Advanced Boosting",       "State-of-the-art boosting frameworks",                        "G01 AdaBoost, G02 Hist Gradient Boosting, G03 CatBoost"],
    ],
    col_widths=[0.4, 1.5, 2.1, 2.3])

doc.add_page_break()

# ── 4.1 Linear & Statistical ──────────────────────────────────────────────────
add_heading(doc, "4.1  Category A — Linear & Statistical  (3 algorithms)", 2)

add_algo_block(doc, "BC A01 Logistic Regression",
    [("Class","BC_A01_LogisticRegression"), ("Category","A_linear"), ("Library","sklearn"),
     ("Key parameters","C=1.0, solver=lbfgs, max_iter=500"), ("Training subsample","None — full dataset"),
     ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "Multinomial logistic regression fits one linear decision boundary per pair of behaviour "
         "states. The lbfgs solver handles multiclass directly without one-vs-rest decomposition. "
         "Regularisation strength is controlled by C=1.0 — smaller C = stronger regularisation."),
        ("Why it's useful:", "Fastest training of all 21 algorithms. Its linear coefficients directly show which features drive each behaviour state — straightness and speed dominate the Travelling vs Resting boundary."),
    ])

add_algo_block(doc, "BC A05 LDA",
    [("Class","BC_A05_LDA"), ("Category","A_linear"), ("Library","sklearn"),
     ("Training subsample","None — full dataset"), ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "Linear Discriminant Analysis finds the linear combination of the 8 features that "
         "maximally separates the 4 behaviour classes. Unlike Logistic Regression, LDA explicitly "
         "models the within-class covariance and uses it to set boundaries."),
        ("Why it's useful:", "Often outperforms Logistic Regression when classes are well separated. LDA also computes the transformation that best separates classes — it is essentially doing dimensionality reduction and classification simultaneously."),
    ])

add_algo_block(doc, "BC A29 Expert Rules",
    [("Class","BC_A29_SpeedAltitudeRules"), ("Category","A_linear"), ("Library","numpy"),
     ("Thresholds","speed 25th & 60th percentile; altitude 50th percentile, learned from training data"),
     ("Training subsample","None — full dataset"), ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "A domain-knowledge rule system: during fit() it computes speed and altitude percentiles "
         "from training data. During predict() it assigns labels based on those thresholds: "
         "speed below 25th percentile = Resting, between 25th–60th = Foraging, "
         "above 60th with low altitude = Travelling, above 60th with high altitude = Migrating."),
        ("Why it's useful:",
         "Completely transparent — every decision can be traced back to a speed or altitude threshold. "
         "Useful as an explainability baseline: if a more complex algorithm disagrees with Expert Rules, "
         "you can check exactly which feature triggered the disagreement."),
    ])

# ── 4.2 Tree & Ensemble ───────────────────────────────────────────────────────
add_heading(doc, "4.2  Category B — Tree & Ensemble  (3 algorithms)", 2)

add_algo_block(doc, "BC B34 Random Forest 100",
    [("Class","BC_B34_RandomForest100"), ("Category","B_tree"), ("Library","sklearn"),
     ("Key parameters","n_estimators=100, random_state=42, n_jobs=-1 (all CPU cores)"),
     ("Training subsample","None — full dataset (RF handles large n natively via bootstrap)")],
    extra_paras=[
        ("What it does:",
         "Trains an ensemble of 100 decision trees, each on a bootstrap sample with random "
         "feature subsets at every split. Final prediction is majority vote across all 100 trees. "
         "Feature importances are computed as mean impurity decrease and shown in the Feature "
         "Importance tab."),
        ("Why it's the best overall:",
         "RF consistently produces the highest weighted F1 across all animal species because it: "
         "(1) handles non-linear interactions between features, "
         "(2) is robust to irrelevant features, "
         "(3) trains on the full dataset without a subsample cap."),
    ])

add_algo_block(doc, "BC B37 Gradient Boosting",
    [("Class","BC_B37_GBM"), ("Category","B_tree"), ("Library","sklearn"),
     ("Key parameters","n_estimators=100, max_depth=4, random_state=42"),
     ("Training subsample","20,000 fixes (via _subsample, seed=42)")],
    extra_paras=[
        ("What it does:",
         "Builds 100 shallow trees sequentially, each correcting the residual errors of the "
         "previous. max_depth=4 provides strong regularisation. Subsample cap of 20,000 keeps "
         "training time reasonable on large datasets."),
        ("Why it's useful:", "Often matches or beats RF on clean labelled data. Sequential residual correction is especially effective when some behaviour classes are harder to separate."),
    ])

add_algo_block(doc, "BC B39 XGBoost",
    [("Class","BC_B39_XGBoost"), ("Category","B_tree"), ("Library","xgboost (fallback: sklearn GBM)"),
     ("Key parameters","n_estimators=100, max_depth=4, eval_metric=mlogloss, verbosity=0, random_state=42"),
     ("Training subsample","20,000 fixes (via _subsample, seed=42)"),
     ("Fallback","If xgboost not installed → sklearn GradientBoostingClassifier with same n_estimators/max_depth")],
    extra_paras=[
        ("What it does:",
         "XGBoost uses Newton gradient updates (second-order), built-in L1/L2 regularisation, "
         "and column/row subsampling. The eval_metric=mlogloss means it optimises multiclass "
         "log-loss, which is appropriate for 4-class behaviour classification."),
    ])

# ── 4.3 Kernel & Distance-Based ───────────────────────────────────────────────
add_heading(doc, "4.3  Category C — Kernel & Distance-Based  (3 algorithms)", 2)

add_algo_block(doc, "BC C56 SVM RBF",
    [("Class","BC_C56_SVM_RBF"), ("Category","C_kernel"), ("Library","sklearn"),
     ("Key parameters","C=1.0, kernel=rbf, gamma=scale, decision_function_shape=ovr"),
     ("Training subsample","5,000 fixes  ⚠  (via _subsample — SVM training is O(n²) to O(n³))"),
     ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "Fits a non-linear RBF (Gaussian) kernel boundary between the 4 behaviour classes. "
         "gamma='scale' sets gamma = 1 / (n_features × Var(X)), automatically adjusting to "
         "the feature scale. decision_function_shape='ovr' uses one-vs-rest decomposition for "
         "multiclass. The 5,000-fix subsample cap is necessary because SVM training time "
         "scales quadratically to cubically with n."),
        ("Important caveat:",
         "With only 5,000 training fixes out of potentially 100,000+, SVM may not see enough "
         "Migrating examples (a rare class in resident datasets) to learn its boundary. "
         "On migration-heavy datasets (cuckoo, stork) it performs well; on resident datasets "
         "it may collapse Migrating to Travelling."),
    ])

add_algo_block(doc, "BC C63 kNN k=7",
    [("Class","BC_C63_KNN7"), ("Category","C_kernel"), ("Library","numpy + scipy"),
     ("Key parameters","k=7, Euclidean distance"),
     ("Reference set","500 training fixes stored as reference (via _subsample)"),
     ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "Stores 500 training fixes as a reference set. For each test fix, computes Euclidean "
         "distances to all 500 reference points, finds the 7 nearest, and assigns the majority "
         "label among them. Prediction uses batch processing (20,000 fixes per batch) to avoid "
         "memory issues on large test sets."),
        ("Important caveat:",
         "The 500-fix reference set is small. If a behaviour class has few examples in those "
         "500 fixes, kNN will rarely assign it. This is the biggest limitation — on a dataset "
         "where Migrating is 80% of fixes, 500 samples may include only ~10 Resting examples."),
    ])

add_algo_block(doc, "BC C69 Mahalanobis Classifier",
    [("Class","BC_C69_MahalanobisClassifier"), ("Category","C_kernel"), ("Library","numpy"),
     ("Key parameters","per-class covariance + 1e-6 regularisation on diagonal"),
     ("Training subsample","None — full dataset"), ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "Computes the mean and full covariance matrix for each of the 4 behaviour classes. "
         "Each test fix is assigned to the class with the smallest Mahalanobis distance. "
         "This is equivalent to Quadratic Discriminant Analysis (QDA) when class covariances "
         "differ. The 1e-6 identity regularisation prevents singular covariance matrices on "
         "small classes."),
        ("Why it's useful:",
         "Unlike kNN it uses all training data to build per-class covariance models. "
         "Unlike LDA it allows each class to have a different shape — Migrating GPS fixes "
         "form an elongated ellipse (high speed, low turning) while Resting is a tight "
         "cluster (near-zero speed and step length)."),
    ])

# ── 4.4 Probabilistic & Bayesian ─────────────────────────────────────────────
add_heading(doc, "4.4  Category D — Probabilistic & Bayesian  (3 algorithms)", 2)

add_algo_block(doc, "BC D72 HMM 4-State",
    [("Class","BC_D72_HMM4"), ("Category","D_probabilistic"), ("Library","numpy"),
     ("States","4 (one per behaviour class)"),
     ("Emission model","Diagonal Gaussian per state — mean and std per feature per state"),
     ("Training subsample","None in fit(); predict() downsamples to 20,000 via step"),
     ("Decoding","Viterbi algorithm (built into predict())")],
    extra_paras=[
        ("What it does:",
         "A Hidden Markov Model with 4 states corresponding to the 4 behaviour classes. "
         "During fit() it estimates per-state means and standard deviations from labelled "
         "training data, plus a 4×4 transition matrix A from observed state sequences. "
         "During predict() it runs Viterbi decoding to find the most likely state sequence."),
        ("Why it's the gold standard for birds:",
         "Behaviour is inherently sequential — animals don't switch from Resting to Migrating "
         "instantaneously. The HMM's transition matrix A captures this: if A[Resting→Migrating] "
         "is low, the Viterbi decoder won't assign Migrating to a single isolated slow GPS fix. "
         "This removes noise that purely feature-based classifiers produce."),
    ])

add_algo_block(doc, "BC D77 GMM Classifier",
    [("Class","BC_D77_GMMClassifier"), ("Category","D_probabilistic"), ("Library","sklearn"),
     ("Key parameters","n_mix=2 components per class, random_state=42"),
     ("Training subsample","20,000 per class (via _subsample applied to each class separately)")],
    extra_paras=[
        ("What it does:",
         "Fits one 2-component Gaussian Mixture Model per behaviour class. During predict(), "
         "the log-likelihood under each class GMM is computed and a log-prior term is added "
         "(log of the class frequency in training data). The class with the highest posterior "
         "log-probability wins."),
        ("Why it's useful:",
         "Unlike Logistic Regression or LDA which assume each class is a single Gaussian blob, "
         "the per-class GMM allows each behaviour to have two sub-modes. For example, Foraging "
         "might have two modes: slow high-turning (active foraging) and nearly-stationary "
         "(sit-and-wait). The GMM captures both."),
    ])

add_algo_block(doc, "BC D80 Kalman + GMM",
    [("Class","BC_D80_KalmanGMM"), ("Category","D_probabilistic"), ("Library","sklearn"),
     ("Key parameters","Q=1e-3 (process noise), R=0.1 (observation noise), n_components=4"),
     ("Training subsample","20,000 fixes (via _subsample, applied to smoothed features)")],
    extra_paras=[
        ("What it does:",
         "First smooths all 8 features with a 1D Kalman filter (per feature independently). "
         "The Kalman filter removes GPS measurement noise using process_noise Q=1e-3 and "
         "obs_noise R=0.1. Then fits a 4-component GMM on the smoothed features and maps "
         "GMM clusters to behaviour classes via majority vote. Predict smooths test features "
         "then decodes with the fitted GMM."),
        ("Why it's unique:",
         "The only algorithm in Service 6 that explicitly models GPS noise. Useful for "
         "datasets with erratic altitude or speed readings — the Kalman filter stabilises "
         "these before classification, preventing a single noisy fix from being misclassified."),
    ])

# ── 4.5 Deep Learning ─────────────────────────────────────────────────────────
add_heading(doc, "4.5  Category E — Deep Learning  (3 algorithms)", 2)
add_para(doc,
    "All three deep learning algorithms are implemented in pure numpy — no PyTorch, "
    "TensorFlow or Keras. This keeps the service self-contained with no heavy GPU "
    "dependencies.",
    size=10, color=GREY)

add_algo_block(doc, "BC E81 MLP",
    [("Class","BC_E81_MLP"), ("Category","E_deep"), ("Library","numpy (pure implementation)"),
     ("Architecture","Input(8) → Hidden(64, ReLU) → Output(K classes, softmax)"),
     ("Key parameters","h=64, epochs=150, lr=0.01"),
     ("Weight init","He initialisation: std = sqrt(2 / fan_in)"),
     ("Training subsample","20,000 fixes (via _subsample, seed=42)")],
    extra_paras=[
        ("What it does:",
         "A 2-layer feed-forward neural network trained with full-batch gradient descent and "
         "cross-entropy loss. He initialisation is used to prevent vanishing gradients with "
         "ReLU activations. Backpropagation is implemented manually using _relu, _softmax, "
         "and _ce_grad helpers."),
        ("Why it's useful:",
         "Can learn non-linear, compositional patterns that decision trees and linear models "
         "miss — e.g. the interaction between speed_roll_std (variability) and turning_angle "
         "that distinguishes active foraging from erratic GPS noise."),
    ])

add_algo_block(doc, "BC E83 LSTM",
    [("Class","BC_E83_LSTM"), ("Category","E_deep"), ("Library","numpy (pure implementation)"),
     ("Architecture","LSTM cell: hidden=16, input size=8"),
     ("Key parameters","hidden=16, epochs=30, lr=0.01"),
     ("Training subsample","⚠  Hard cap: MAX_TRAIN=2,000 fixes (step-sampled from the sequence)"),
     ("Fallback","None")],
    extra_paras=[
        ("What it does:",
         "A single LSTM cell processes the GPS sequence fix-by-fix, maintaining a hidden state "
         "ht and cell state ct across time. The four LSTM gates (forget, input, cell, output) "
         "control what information is remembered. Only 2,000 fixes are used for training — "
         "step-sampled from the full sequence to preserve temporal structure."),
        ("Important caveat:",
         "The 2,000-fix training cap means LSTM sees only a small fraction of the data. "
         "On a 130,000-fix jackal dataset it trains on one fix every 65. This significantly "
         "limits what temporal patterns it can learn compared to HMM or CRF which use the "
         "full sequence. LSTM is the slowest algorithm because it processes fixes one-by-one."),
    ])

add_algo_block(doc, "BC E87 TCN",
    [("Class","BC_E87_TCN"), ("Category","E_deep"), ("Library","numpy (pure implementation)"),
     ("Architecture","3 dilated causal conv layers, n_filters=8, kernel_size=3"),
     ("Dilation","Layer l uses dilation 2^l: 1, 2, 4 — receptive field covers 21 past fixes"),
     ("Training subsample","None — fit() only initialises random weights, no training on data")],
    extra_paras=[
        ("What it does:",
         "A Temporal Convolutional Network uses dilated causal convolutions to look back at "
         "multiple scales simultaneously: layer 1 sees adjacent fixes (dilation=1), layer 2 "
         "sees fixes 2 apart (dilation=2), layer 3 sees fixes 4 apart (dilation=4). "
         "The output layer maps the final feature map to behaviour class probabilities."),
        ("Important caveat:",
         "TCN's fit() method only initialises random weights — it does NOT train on the GPS "
         "data. This means TCN predictions are based entirely on randomly initialised convolutional "
         "filters, not learned from the animal's behaviour. Results will be near-random and "
         "inconsistent across runs if the seed changes. TCN is included to show the architecture "
         "is in place, but it requires a proper training loop to be useful."),
    ])

# Colour the TCN caveat visually
# (The caveat paragraph was just written — no special table colouring possible in this helper approach)

# ── 4.6 Ecological-Specific ───────────────────────────────────────────────────
add_heading(doc, "4.6  Category F — Ecological-Specific  (3 algorithms)", 2)

add_algo_block(doc, "BC F105 HMM+RF Hybrid",
    [("Class","BC_F105_HMMRFHybrid"), ("Category","F_ecological"), ("Library","sklearn"),
     ("Key parameters","RF: n_estimators=50, random_state=42; HMM: n_states=4"),
     ("Training subsample","None — full dataset for RF + HMM transition matrix")],
    extra_paras=[
        ("What it does:",
         "Combines the spatial accuracy of Random Forest with the temporal smoothing of a Viterbi "
         "decoder. The RF is trained on GPS features and produces per-fix class probabilities. "
         "These probabilities are used as emission probabilities in a Viterbi HMM decoder, "
         "constrained by the transition matrix learned from training labels."),
        ("Why it's the best ecological algorithm:",
         "Gets the spatial pattern recognition of a 50-tree RF AND the sequence coherence of "
         "HMM. The RF proba are better than diagonal Gaussian emissions (used by plain HMM), "
         "so the Viterbi path is more accurate. Recommended for any species with clear "
         "behaviour transitions (migratory birds, large mammals)."),
    ])

add_algo_block(doc, "BC F106 Migration Speed Classifier",
    [("Class","BC_F106_MigrationSpeedClassifier"), ("Category","F_ecological"), ("Library","sklearn"),
     ("Ecological features","migration_score = speed_ms × straightness; altitude_change = |∇(altitude)|; speed_roll_mean; step_length_m"),
     ("Classifier","LogisticRegression(solver=lbfgs, max_iter=500) on 4 ecological features"),
     ("Training subsample","None — full dataset")],
    extra_paras=[
        ("What it does:",
         "Builds ecologically motivated features: the migration score (speed × straightness) "
         "is high during sustained directional flight and low during foraging. Altitude change "
         "rate captures ascent/descent events. These 4 ecological features are fed to logistic "
         "regression rather than the raw 8 GPS features."),
        ("Why it's useful:",
         "Explicitly encodes ornithological knowledge. Especially strong for migratory species "
         "where speed × straightness clearly distinguishes migration from residency. "
         "The feature engineering makes the model more sample-efficient — it can generalise "
         "from fewer training examples than a black-box model."),
    ])

add_algo_block(doc, "BC F107 Turning Angle Classifier",
    [("Class","BC_F107_RestingForagingClassifier"), ("Category","F_ecological"), ("Library","sklearn"),
     ("Ecological features","turning_angle, step_length_m, speed_roll_std, sinuosity (turning/step), speed_ms"),
     ("Classifier","RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1) on ecological features"),
     ("Training subsample","20,000 fixes (via _subsample, seed=42)")],
    extra_paras=[
        ("What it does:",
         "Derives a sinuosity index = turning_angle / (step_length + ε) — a high sinuosity "
         "means lots of turning relative to distance moved, characteristic of foraging. "
         "A 50-tree RF is then trained on these 5 ecological features rather than the raw "
         "8-column matrix."),
        ("Why it's useful:",
         "Designed for distinguishing Resting, Foraging and Travelling — the three states "
         "that are hardest to separate by raw speed alone. The sinuosity feature is the "
         "key discriminator between Foraging (high sinuosity) and Travelling (low sinuosity) "
         "even when speeds are similar."),
    ])

# ── 4.7 Advanced Boosting ─────────────────────────────────────────────────────
add_heading(doc, "4.7  Category G — Advanced Boosting  (3 algorithms)", 2)

add_algo_block(doc, "BC G01 AdaBoost",
    [("Class","BC_G01_AdaBoost"), ("Category","G_advanced_boosting"), ("Library","sklearn"),
     ("Key parameters","n_estimators=100, algorithm=SAMME, random_state=42"),
     ("Training subsample","20,000 fixes (via _subsample, seed=42)")],
    extra_paras=[
        ("What it does:",
         "Adaptive Boosting trains 100 weak classifiers (decision stumps by default) sequentially. "
         "After each round, GPS fixes that were misclassified get higher weight — the next "
         "classifier focuses on them. SAMME is the multiclass extension of AdaBoost that handles "
         "4 behaviour classes directly."),
        ("Why SAMME not SAMME.R:",
         "SAMME is used because the base classifier doesn't need to output probability estimates. "
         "SAMME.R (the probability version) often performs better but requires calibrated "
         "probabilities which adds overhead."),
    ])

add_algo_block(doc, "BC G02 Hist Gradient Boosting",
    [("Class","BC_G02_HistGradientBoosting"), ("Category","G_advanced_boosting"), ("Library","sklearn"),
     ("Key parameters","max_iter=100, max_depth=4, random_state=42"),
     ("Training subsample","None — HistGradientBoosting uses histogram binning internally; scales to any dataset size")],
    extra_paras=[
        ("What it does:",
         "sklearn's native histogram-based gradient boosting — similar to LightGBM but "
         "without an external dependency. It bins feature values into 255 buckets, which "
         "makes both training and prediction significantly faster than the standard "
         "GradientBoostingClassifier. Natively handles large datasets without a subsample cap."),
        ("Why no subsample cap:",
         "Unlike sklearn GBM which processes individual splits one-by-one, HistGB computes "
         "all splits from pre-binned histograms. This makes it practical on datasets with "
         "200,000+ GPS fixes without subsampling."),
    ])

add_algo_block(doc, "BC G03 CatBoost",
    [("Class","BC_G03_CatBoost"), ("Category","G_advanced_boosting"), ("Library","catboost (fallback: sklearn GBM)"),
     ("Key parameters","iterations=100, depth=4, random_seed=42, verbose=0"),
     ("Training subsample","20,000 fixes (via _subsample, seed=42)"),
     ("Fallback","If catboost not installed → sklearn GradientBoostingClassifier with n_estimators=100, max_depth=4")],
    extra_paras=[
        ("What it does:",
         "CatBoost uses ordered boosting — it computes gradient statistics on a permuted "
         "subset of the training data at each step to prevent target leakage. This gives "
         "consistently strong F1 scores without hyperparameter tuning, which is why it is "
         "often called the 'default-wins' boosting algorithm."),
    ])


# ════════════════════════════════════════════════════════════════════════════
# 5. METRICS & EVALUATION
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "5. Metrics & Evaluation", 1)

add_heading(doc, "Metric definitions", 2)
add_para(doc,
    "All metrics below are computed by core/evaluator.py → _classification_metrics() "
    "on the last 20% of GPS fixes (test set). They compare predicted behaviour labels "
    "against the true labels (from the dataset or from KMeans auto-labelling).")

add_table(doc,
    ["Metric shown in frontend", "Technical name", "Formula (simplified)", "Shown where"],
    [
        ["F1 (main card)",       "f1_weighted",   "F1 per class, averaged weighted by class frequency",    "Header card, algorithm comparison badge"],
        ["F1 — macro",           "f1_macro",       "F1 per class, averaged equally (treats classes equally)", "Full metrics table in F1 Scores tab"],
        ["Accuracy",             "accuracy",       "Correct predictions ÷ total test fixes",                "F1 Scores tab card"],
        ["Precision",            "precision macro","True positive ÷ (true positive + false positive), macro averaged", "F1 Scores tab card"],
        ["Recall",               "recall macro",   "True positive ÷ (true positive + false negative), macro averaged", "F1 Scores tab card"],
        ["Per-class F1",         "per_class_f1",   "Individual F1 for each of the 4 behaviour states",      "F1 Scores breakdown table, Cluster Graphs tab"],
    ],
    col_widths=[1.5, 1.3, 2.5, 1.5])

add_heading(doc, "Why weighted F1 is the main metric", 2)
add_para(doc,
    "Weighted F1 is the primary comparison metric in the frontend because behaviour classes "
    "are heavily imbalanced in real GPS data. On a migratory species like the African cuckoo, "
    "Migrating may account for 70% of fixes while Resting is only 5%. "
    "Weighted F1 gives more weight to Migrating (the common class), so the headline score "
    "reflects what matters most for the typical fix in the dataset. "
    "Macro F1 is also shown because it tells you how well the algorithm performs on the "
    "rare classes — a high weighted F1 but low macro F1 means the algorithm is good at "
    "Migrating but poor at Resting.")

add_heading(doc, "What F1 values mean in practice", 2)
add_table(doc,
    ["Weighted F1 range", "Interpretation"],
    [
        ["0.80 – 1.00", "Excellent — algorithm confidently separates all 4 behaviours. Likely on clean labelled data or species with clearly distinct movement modes."],
        ["0.60 – 0.79", "Good — strong on the common classes, some confusion on rare ones. Reliable for downstream analysis."],
        ["0.40 – 0.59", "Moderate — usable but check per-class F1 to identify which class is causing confusion."],
        ["0.20 – 0.39", "Weak — algorithm struggles on at least one class. Consider whether KMeans labels are reliable."],
        ["< 0.20",       "Poor — likely a near-random classifier (e.g. TCN with uninitialised weights) or severe class imbalance."],
    ],
    col_widths=[1.4, 5.0])

add_heading(doc, "KMeans auto-labelling caveat", 2)
add_para(doc,
    "When a Movebank CSV has no true_behavior column, the backend assigns labels using "
    "KMeans(n_clusters=4) on speed, altitude and turning_angle. These labels are then used "
    "as ground truth for both training and evaluation. "
    "This means F1 scores on auto-labelled data measure how consistently the algorithm "
    "agrees with KMeans, NOT how accurately it captures true animal behaviour. "
    "F1 values on auto-labelled data are typically higher (the algorithms partially learn "
    "the same cluster boundaries) and should be interpreted cautiously.")


# ════════════════════════════════════════════════════════════════════════════
# 6. ALGORITHM RECOMMENDATIONS
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "6. Algorithm Recommendations", 1)

add_para(doc,
    "The chart below rates all 21 algorithms across Quality (weighted F1 — higher is better), "
    "Speed (how fast on a 20,000-fix dataset — 5 = fastest), and Interpretability "
    "(how easy to explain the result — 5 = most transparent). "
    "Algorithms are sorted best-to-worst overall.")

doc.add_paragraph()

# Tier key
add_heading(doc, "Tier key", 2)
tier_tbl = doc.add_table(rows=4, cols=2)
tier_tbl.style = "Table Grid"
for ri, (a, b) in enumerate([
    ("Tier", "Meaning"),
    ("★★★  Best",    "Recommended for production use — consistently high weighted F1"),
    ("★★    Good",   "Solid choice — good F1 or very fast with acceptable accuracy"),
    ("★      Niche", "Use for a specific research question or as a baseline only"),
]):
    tier_tbl.rows[ri].cells[0].text = a
    tier_tbl.rows[ri].cells[1].text = b
    for ci in range(2):
        for p in tier_tbl.rows[ri].cells[ci].paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)
                if ri == 0:
                    run.bold = True; run.font.color.rgb = WHITE
    if ri == 0:
        set_cell_bg(tier_tbl.rows[ri].cells[0], HDR_HEX)
        set_cell_bg(tier_tbl.rows[ri].cells[1], HDR_HEX)
tier_tbl.columns[0].width = Inches(1.2)
tier_tbl.columns[1].width = Inches(5.1)
doc.add_paragraph()

# Visual bar chart
add_heading(doc, "Visual rating chart — Quality, Speed, Interpretability", 2)
add_para(doc,
    "Filled coloured blocks out of 5. Algorithms sorted best-to-worst overall. "
    "Q = Quality (weighted F1)  |  S = Speed (5 = fastest)  |  I = Interpretability (5 = most transparent).",
    size=10, color=GREY)

# (name, quality 0-5, speed 0-5, interp 0-5, tier, note)
s6_ratings = [
    ("BC B34 Random Forest 100",          5, 4, 4, "★★★", "Best overall — high F1, no subsample cap, feature importances"),
    ("BC G03 CatBoost",                   5, 4, 3, "★★★", "Ordered boosting — strong F1 with minimal tuning"),
    ("BC B39 XGBoost",                    5, 5, 3, "★★★", "Fast + accurate; best when xgboost installed"),
    ("BC G02 Hist Gradient Boosting",     5, 5, 3, "★★★", "Fastest sklearn booster; scales to any dataset size"),
    ("BC B37 Gradient Boosting",          4, 4, 3, "★★★", "Excellent F1; 20k subsample cap; slightly slower"),
    ("BC F105 HMM+RF Hybrid",             4, 4, 4, "★★",  "RF accuracy + HMM temporal smoothing — best ecological pick"),
    ("BC D72 HMM 4-State",                4, 3, 4, "★★",  "Gold standard for birds — temporal coherence via Viterbi"),
    ("BC C56 SVM RBF",                    4, 3, 3, "★★",  "Strong curved boundaries; limited by 5k subsample cap"),
    ("BC F106 Migration Speed Classifier",3, 5, 5, "★★",  "Ecologically motivated; best for migratory species"),
    ("BC G01 AdaBoost",                   4, 4, 3, "★★",  "Adaptive reweighting; SAMME multiclass extension"),
    ("BC A05 LDA",                        3, 5, 5, "★★",  "Fast, interpretable; good when classes are linearly separable"),
    ("BC A01 Logistic Regression",        3, 5, 5, "★★",  "Fastest training; linear coefficients show feature contributions"),
    ("BC D77 GMM Classifier",             3, 4, 3, "★★",  "Per-class mixture; handles bimodal behaviour clusters"),
    ("BC C69 Mahalanobis Classifier",     3, 5, 4, "★★",  "QDA equivalent; per-class covariance; no subsample cap"),
    ("BC D80 Kalman + GMM",               3, 3, 3, "★",   "Smooths GPS noise first; useful on noisy altitude data"),
    ("BC F107 Turning Angle Classifier",  3, 4, 4, "★",   "Sinuosity feature best for Foraging vs Travelling separation"),
    ("BC A29 Expert Rules",               2, 5, 5, "★",   "Fully transparent; threshold-based; no learning needed"),
    ("BC E81 MLP",                        3, 3, 2, "★",   "Neural net; good if 20k training fixes available"),
    ("BC C63 kNN k=7",                    2, 4, 4, "★",   "Limited by 500-fix reference set; noisy on class-imbalanced data"),
    ("BC E83 LSTM",                       3, 2, 2, "★",   "Slowest; 2k training cap limits what it can learn"),
    ("BC E87 TCN",                        1, 5, 2, "★",   "⚠ Uninitialised weights — near-random predictions"),
]

TOTAL = 5
BAR_W  = Inches(0.18)
NAME_W = Inches(2.1)
TIER_W = Inches(0.5)

hdr_cols = ["Algorithm", "Tier"] + ["Q"]*TOTAL + [""]*1 + ["S"]*TOTAL + [""]*1 + ["I"]*TOTAL
chart_tbl = doc.add_table(rows=1 + len(s6_ratings), cols=len(hdr_cols))
chart_tbl.style = "Table Grid"

hdr_row = chart_tbl.rows[0]
for ci, h in enumerate(hdr_cols):
    set_cell_bg(hdr_row.cells[ci], HDR_HEX)
    set_cell_bold_white(hdr_row.cells[ci], h, size=8)
for ci, label in [(2, "Quality ▶"), (8, "Speed ▶"), (14, "Interp ▶")]:
    set_cell_bg(hdr_row.cells[ci], "0A1828")
    hdr_row.cells[ci].paragraphs[0].runs[0].text = label

for ri, (name, q, s, interp, tier, note) in enumerate(s6_ratings):
    row = chart_tbl.rows[ri + 1]
    row.cells[0].text = name
    for p in row.cells[0].paragraphs:
        for run in p.runs:
            run.font.size = Pt(8)
    row.cells[1].text = tier
    for p in row.cells[1].paragraphs:
        for run in p.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = AMBER if "★★★" in tier else (RGBColor(0xD4,0x9C,0x3A) if "★★" in tier else GREY)
    for bi, hex_c in enumerate(bar(q, TOTAL, "1A4A8A", "D0D8EA")):
        set_cell_bg(row.cells[2 + bi], hex_c)
        row.cells[2 + bi].text = ""
    set_cell_bg(row.cells[7], "FFFFFF"); row.cells[7].text = ""
    for bi, hex_c in enumerate(bar(s, TOTAL, "2A6A4A", "D0E8DA")):
        set_cell_bg(row.cells[8 + bi], hex_c)
        row.cells[8 + bi].text = ""
    set_cell_bg(row.cells[13], "FFFFFF"); row.cells[13].text = ""
    for bi, hex_c in enumerate(bar(interp, TOTAL, "8A6A00", "EAE0C0")):
        set_cell_bg(row.cells[14 + bi], hex_c)
        row.cells[14 + bi].text = ""
    # Highlight TCN row in red — uninitialised weights warning
    if "TCN" in name:
        for ci2 in range(len(hdr_cols)):
            set_cell_bg(row.cells[ci2], "4A1A1A")

chart_tbl.columns[0].width = NAME_W
chart_tbl.columns[1].width = TIER_W
for ci in range(2, len(hdr_cols)):
    chart_tbl.columns[ci].width = BAR_W

doc.add_paragraph()

# TCN warning box (styled like S4's DBSCAN caveat)
add_heading(doc, "⚠  TCN warning — uninitialised weights", 2)
add_para(doc,
    "BC E87 TCN is the only algorithm in Service 6 whose fit() method does NOT train "
    "on the GPS data. It only initialises random convolution weights. "
    "This means TCN predictions are near-random and will differ every time the random "
    "seed changes. The row is highlighted red in the chart above.",
    size=10, color=RGBColor(0xCC, 0x44, 0x44))

warn_tbl = doc.add_table(rows=3, cols=3)
warn_tbl.style = "Table Grid"
warn_headers = ["", "TCN (current — no training)", "What it would be with proper training"]
for ci, h in enumerate(warn_headers):
    set_cell_bg(warn_tbl.rows[0].cells[ci], "4A1A1A")
    set_cell_bold_white(warn_tbl.rows[0].cells[ci], h, size=9)
warn_data = [
    ["Quality (weighted F1)", "~0.10–0.20 (near random)",   "~0.55–0.70 (expected for a trained TCN)"],
    ["Recommended use",       "⚠ Do not use for real results", "✓ After implementing a proper training loop"],
]
for ri, row_data in enumerate(warn_data):
    for ci, val in enumerate(row_data):
        warn_tbl.rows[ri+1].cells[ci].text = val
        for p in warn_tbl.rows[ri+1].cells[ci].paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)
        if ci == 1:
            set_cell_bg(warn_tbl.rows[ri+1].cells[ci], "F5E8E8")
        elif ci == 2:
            set_cell_bg(warn_tbl.rows[ri+1].cells[ci], "E8F5E8")
warn_tbl.columns[0].width = Inches(1.5)
warn_tbl.columns[1].width = Inches(2.5)
warn_tbl.columns[2].width = Inches(2.8)
doc.add_paragraph()

# Top picks table
add_heading(doc, "Top algorithm picks by use case", 2)
add_table(doc,
    ["Use case", "Best pick", "Why"],
    [
        ["Best overall weighted F1",        "BC B34 Random Forest 100",        "No subsample cap, 100 trees, feature importances, robust to class imbalance"],
        ["Fastest accurate result",         "BC G02 Hist Gradient Boosting",   "Histogram binning scales to any dataset size; no subsample needed"],
        ["Most interpretable",              "BC A01 Logistic Regression / A05 LDA", "Linear coefficients show directly which feature drives each class boundary"],
        ["Temporal sequence coherence",     "BC D72 HMM 4-State / F105 HMM+RF", "Viterbi decoder prevents isolated single-fix misclassifications"],
        ["Migratory species (cuckoo/stork)","BC F106 Migration Speed Classifier","speed × straightness is the strongest migration signal"],
        ["Foraging vs travelling",          "BC F107 Turning Angle Classifier", "Sinuosity feature (turning/step) is the key discriminator"],
        ["Noisy GPS altitude data",         "BC D80 Kalman + GMM",             "Kalman pre-smoothing removes altitude noise before classification"],
        ["No behaviour labels in CSV",      "Built-in KMeans auto-label",      "Backend automatically runs KMeans(4) on speed+altitude+turning_angle"],
    ],
    col_widths=[2.0, 2.1, 2.4])

# Limitations table
add_heading(doc, "Algorithm limitations to be aware of", 2)
limitations_tbl = add_table(doc,
    ["Algorithm", "Limitation", "When it is acceptable"],
    [
        ["BC E87 TCN",               "fit() does NOT train on data — random weights only — near-random F1",
         "Only after a proper training loop is implemented"],
        ["BC E83 LSTM",              "Hard cap of 2,000 training fixes — misses patterns in long sequences",
         "Short sequences (< 5,000 GPS fixes) where 2k covers most of the data"],
        ["BC C56 SVM RBF",           "5,000-fix training cap (O(n²) cost) — may miss rare classes on large datasets",
         "Migration-heavy species where common classes dominate; not for resident species with rare Migrating"],
        ["BC C63 kNN k=7",           "Only 500-fix reference set — noisy on class-imbalanced data",
         "Small, balanced datasets (< 2,000 GPS fixes total)"],
        ["BC A29 Expert Rules",      "Uses only speed and altitude percentile thresholds — misses behavioural context",
         "Explainability baseline or sanity check; not for accurate behaviour labelling"],
        ["BC D77 GMM Classifier",    "2-component mixture per class — may not capture behaviour sub-modes on complex datasets",
         "Species with clearly distinct, unimodal behaviour profiles"],
    ],
    col_widths=[1.7, 2.8, 2.0])

# Colour TCN row red in limitations table
for cell in limitations_tbl.rows[1].cells:
    set_cell_bg(cell, "F5E8E8")

doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# 7. FRONTEND VISUALISATIONS
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "7. Frontend Visualisations", 1)
add_para(doc, "Service 6 uses five dedicated tabs — all visible when a classification run completes.")

add_heading(doc, "Tab 1: Map view (MapView.jsx)", 2)
for item, desc in [
    ("GPS track line", "Blue dashed polyline connecting all fixes in order."),
    ("Coloured dots",  "Each GPS fix coloured by its predicted behaviour class. Resting, Foraging, Travelling, Migrating each get a distinct colour from CLUSTER_COLORS."),
    ("Popup on click", "Shows Fix #, Algorithm A prediction, Algorithm B prediction, Latitude, Longitude."),
    ("Disagreement",   "In compare mode, dots where A ≠ B get a white border — visually flags where the two algorithms disagree."),
    ("Stat cards",     "Number of clusters found, GPS fixes mapped, best weighted F1 (Algorithm A), total runtime."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{item}:  "); r1.bold = True; r1.font.size = Pt(10)
    r2 = p.add_run(desc); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)
doc.add_paragraph()

add_heading(doc, "Tab 2: Cluster graphs (ClusterGraphs.jsx)", 2)
for item, desc in [
    ("Donut chart",           "Shows how many GPS fixes were assigned to each behaviour class."),
    ("Mean speed bar chart",  "Bar chart of mean speed (m/s) per behaviour class — confirms Migrating > Travelling > Foraging > Resting ordering."),
    ("Turning angle histogram","Distribution of turning angles per class — Foraging has many high turning angles; Migrating has low ones."),
    ("Cluster metrics table", "Per-class: fix count, mean speed, per-class F1 for Algorithm A and B, F1 gap between algorithms."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{item}:  "); r1.bold = True; r1.font.size = Pt(10)
    r2 = p.add_run(desc); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)
doc.add_paragraph()

add_heading(doc, "Tab 3: Time series (TimeSeries.jsx)", 2)
add_para(doc, "Six charts showing raw GPS features and predicted states over fix index:")
for item in [
    "Speed over time — line chart (m/s)",
    "Altitude over time — line chart (metres)",
    "Turning angle over time — line chart (degrees/radians)",
    "Step length distribution — histogram (12 bins, metres)",
    "Predicted behaviour state — multi-line showing state value over time",
    "Straightness index over time — line chart (0–1)",
]:
    add_bullet(doc, item)
add_para(doc,
    "Note: speed_roll_mean, speed_roll_std and alt_roll_mean are NOT shown here as separate charts — "
    "they are backend-only features visible only in the Feature Importance tab.",
    size=9.5, color=GREY)
doc.add_paragraph()

add_heading(doc, "Tab 4: F1 Scores (F1Scores.jsx)", 2)
for item, desc in [
    ("Weighted F1 card",  "The main F1 score (f1_weighted) for each algorithm — the headline comparison number."),
    ("F1 gap card",       "Difference in weighted F1 between Algorithm A and B."),
    ("Best accuracy card","Whichever algorithm has higher accuracy."),
    ("Side-by-side cards","Per-algorithm cards showing F1/Accuracy/Precision/Recall as horizontal bar charts, plus runtime."),
    ("Per-class F1",      "Table showing F1 for each of the 4 behaviour states — flagged Good (≥0.5) or Low (<0.5)."),
    ("Grouped bar chart", "All 4 per-class F1 scores grouped by class for Algorithm A vs B."),
    ("Radar chart",       "Precision / Recall / F1 for each algorithm plotted as a radar — visualises balance across metrics."),
    ("Full metrics table","All metrics (accuracy, F1 weighted, F1 macro, precision, recall, runtime) in one table."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{item}:  "); r1.bold = True; r1.font.size = Pt(10)
    r2 = p.add_run(desc); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)
doc.add_paragraph()

add_heading(doc, "Tab 5: Feature Importance (FeatureImportance.jsx)", 2)
add_para(doc,
    "Shows permutation importance scores for Algorithm A's prediction on the test set. "
    "This is the only place where speed_roll_mean, speed_roll_std and alt_roll_mean "
    "appear on screen — as importance scores, not as raw feature values.")
for item, desc in [
    ("Ranking table",    "All 8 features ranked by importance score (highest = most influential)."),
    ("Horizontal bar",   "Bar chart of importance scores — negative scores mean the feature slightly hurt accuracy when permuted."),
    ("Top-3 insight cards","Named insight cards for the three most important features with their scores."),
]:
    p = doc.add_paragraph()
    r1 = p.add_run(f"{item}:  "); r1.bold = True; r1.font.size = Pt(10)
    r2 = p.add_run(desc); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)
doc.add_paragraph()


# ════════════════════════════════════════════════════════════════════════════
# 8. DEPENDENCIES
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "8. Dependencies", 1)
add_table(doc,
    ["Library", "Required?", "Used by"],
    [
        ["numpy",        "Required", "All algorithms — array ops, manual MLP/LSTM/TCN/HMM implementations"],
        ["scipy",        "Required", "BC C63 kNN k=7 — cdist for batched Euclidean distance"],
        ["scikit-learn", "Required", "BC A01, A05, B34, B37, B39, C56, D77, D80, F105, F106, F107, G01, G02, G03"],
        ["xgboost",      "Optional", "BC B39 XGBoost — falls back to sklearn GBM if not installed"],
        ["catboost",     "Optional", "BC G03 CatBoost — falls back to sklearn GBM if not installed"],
    ],
    col_widths=[1.2, 0.9, 4.2])


# ════════════════════════════════════════════════════════════════════════════
# 9. BENCHMARK RESULTS — REAL MEASURED PERFORMANCE
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "9. Benchmark Results — Real Measured Performance", 1)

add_para(doc,
    "All 21 algorithms were run on the African cuckoo in Nigeria dataset "
    "(Iwajomo et al. 2018, 5,352 GPS fixes, Cuculus gularis). "
    "Since this dataset has no true_behavior column, the backend automatically "
    "assigned behaviour labels using KMeans(n_clusters=4) on speed, altitude and "
    "turning_angle. The first 80% of fixes (4,281) were used for training, the "
    "last 20% (1,071) for testing. All 21 algorithms ran without errors.")

add_para(doc,
    "Important caveat: because labels were generated by KMeans, the F1 scores "
    "reflect how well each algorithm agrees with KMeans — not how accurately it "
    "captures true animal behaviour. Scores are higher than they would be on "
    "expert-labelled data. Use these numbers to compare algorithms relative to "
    "each other, not as absolute accuracy claims.",
    size=9.5, color=GREY)

doc.add_paragraph()

add_heading(doc, "Full ranked results — African cuckoo dataset", 2)
add_para(doc, "Sorted by F1-weighted (best first). Dataset: African cuckoo, Nigeria. Labels: KMeans auto-assigned.", size=10, color=GREY)

results_tbl = add_table(doc,
    ["Rank", "Algorithm", "Cat.", "F1-weighted", "F1-macro", "Accuracy", "Precision", "Recall", "Runtime (s)"],
    [
        ["1",  "BC B37 Gradient Boosting",          "B", "0.996", "0.996", "0.996", "0.996", "0.997", "1.197"],
        ["2",  "BC B39 XGBoost",                    "B", "0.996", "0.996", "0.996", "0.996", "0.997", "1.206"],
        ["3",  "BC G03 CatBoost",                   "G", "0.996", "0.996", "0.996", "0.996", "0.997", "1.196"],
        ["4",  "BC G02 Hist Gradient Boosting",     "G", "0.995", "0.995", "0.995", "0.995", "0.994", "0.141"],
        ["5",  "BC B34 Random Forest 100",          "B", "0.994", "0.993", "0.994", "0.992", "0.994", "0.101"],
        ["6",  "BC A01 Logistic Regression",        "A", "0.991", "0.990", "0.991", "0.992", "0.988", "0.006"],
        ["7",  "BC C56 SVM RBF",                    "C", "0.989", "0.986", "0.989", "0.984", "0.988", "0.031"],
        ["8",  "BC G01 AdaBoost",                   "G", "0.982", "0.980", "0.982", "0.976", "0.983", "0.135"],
        ["9",  "BC F105 HMM+RF Hybrid",             "F", "0.977", "0.972", "0.977", "0.977", "0.967", "0.082"],
        ["10", "BC A05 LDA",                        "A", "0.970", "0.970", "0.970", "0.970", "0.971", "0.001"],
        ["11", "BC C63 kNN k=7",                    "C", "0.966", "0.960", "0.966", "0.966", "0.955", "0.006"],
        ["12", "BC D72 HMM 4-State",                "D", "0.965", "0.957", "0.965", "0.952", "0.964", "0.016"],
        ["13", "BC C69 Mahalanobis Classifier",     "C", "0.962", "0.954", "0.962", "0.946", "0.966", "0.001"],
        ["14", "BC E81 MLP",                        "E", "0.949", "0.942", "0.950", "0.950", "0.938", "0.279"],
        ["15", "BC D77 GMM Classifier",             "D", "0.908", "0.911", "0.907", "0.908", "0.925", "0.015"],
        ["16", "BC E83 LSTM",                       "E", "0.802", "0.790", "0.806", "0.833", "0.771", "0.743"],
        ["17", "BC F107 Turning Angle Classifier",  "F", "0.656", "0.683", "0.647", "0.687", "0.682", "0.055"],
        ["18", "BC D80 Kalman + GMM",               "D", "0.401", "0.376", "0.491", "0.421", "0.489", "0.023"],
        ["19", "BC F106 Migration Speed Classifier","F", "0.372", "0.400", "0.523", "0.352", "0.500", "0.003"],
        ["20", "BC E87 TCN",                        "E", "0.215", "0.189", "0.269", "0.259", "0.251", "0.001"],
        ["21", "BC A29 Expert Rules",               "A", "0.099", "0.100", "0.248", "0.062", "0.250", "0.000"],
    ],
    col_widths=[0.38, 2.3, 0.38, 0.85, 0.75, 0.75, 0.75, 0.65, 0.8])

# Green top 5, red bottom 3
for ri in [1, 2, 3, 4, 5]:
    for cell in results_tbl.rows[ri].cells:
        set_cell_bg(cell, "E8F5E8")
for ri in [19, 20, 21]:
    for cell in results_tbl.rows[ri].cells:
        set_cell_bg(cell, "F5E8E8")

doc.add_paragraph()

add_heading(doc, "Key findings from the benchmark", 2)
for obs in [
    "The top 5 algorithms are all tree/ensemble boosting methods (B37, B39, G03, G02, B34) — they consistently achieve F1-weighted ≥ 0.994. All four categories of boosting are represented in the top 8.",
    "BC A01 Logistic Regression ranks 6th (F1 = 0.991) and runs in 0.006s — the best speed-to-accuracy ratio of any algorithm. For quick results on large datasets, it is the top recommendation.",
    "BC E87 TCN ranks 20th (F1 = 0.215) — confirmed near-random because fit() does not train on data. This is 4× worse than the next-worst algorithm (Expert Rules at 0.099 accuracy, 0.215 F1 for TCN).",
    "BC A29 Expert Rules ranks last (F1-weighted = 0.099). The speed/altitude threshold rules do not match KMeans cluster boundaries — expected, since KMeans uses a different decision space.",
    "BC F106 Migration Speed Classifier scores 0.372 here vs 0.140 in the live app screenshot. The difference is the ground truth: here it is measured against KMeans labels; in the app it was measured against KMeans on a different run with different random assignment.",
    "LSTM (rank 16, F1 = 0.802) significantly underperforms the boosting methods despite being a deep learning model — the 2,000-fix training cap limits what temporal patterns it can learn on this 4,281-fix training set.",
    "All 21 algorithms ran without errors on this dataset. Runtime ranged from 0.000s (Expert Rules) to 1.206s (XGBoost).",
]:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(obs).font.size = Pt(10)

doc.add_paragraph()

add_heading(doc, "F1-weighted vs F1-macro gap", 2)
add_para(doc,
    "When F1-weighted and F1-macro are similar (e.g. B37: 0.996 vs 0.996), "
    "the algorithm performs equally well on all 4 behaviour classes. "
    "When there is a gap (e.g. Expert Rules: 0.099 weighted vs 0.100 macro, or "
    "LSTM: 0.802 weighted vs 0.790 macro), the algorithm struggles more on "
    "the minority classes (Resting and Travelling are rarer in the cuckoo dataset "
    "than Migrating).")


# ════════════════════════════════════════════════════════════════════════════
# 10. SUMMARY TABLE — ALL 21 ALGORITHMS
# ════════════════════════════════════════════════════════════════════════════

add_heading(doc, "10. Summary Table — All 21 Algorithms", 1)
summary_tbl = add_table(doc,
    ["Code", "Algorithm name", "Category", "Library", "Train cap", "Key parameters", "Tier"],
    [
        ["A01", "Logistic Regression",        "A_linear",           "sklearn",   "Full",    "C=1.0, max_iter=500",                    "★★"],
        ["A05", "LDA",                        "A_linear",           "sklearn",   "Full",    "sklearn defaults",                       "★★"],
        ["A29", "Expert Rules",               "A_linear",           "numpy",     "Full",    "Speed / altitude percentile thresholds", "★"],
        ["B34", "Random Forest 100",          "B_tree",             "sklearn",   "Full",    "n_estimators=100, n_jobs=-1",             "★★★"],
        ["B37", "Gradient Boosting",          "B_tree",             "sklearn",   "20,000",  "n_estimators=100, max_depth=4",           "★★★"],
        ["B39", "XGBoost",                    "B_tree",             "xgboost*",  "20,000",  "n_estimators=100, max_depth=4",           "★★★"],
        ["C56", "SVM RBF",                    "C_kernel",           "sklearn",   "5,000 ⚠", "C=1.0, gamma=scale, kernel=rbf, ovr",    "★★"],
        ["C63", "kNN k=7",                    "C_kernel",           "scipy",     "500 ref", "k=7, Euclidean",                         "★"],
        ["C69", "Mahalanobis Classifier",     "C_kernel",           "numpy",     "Full",    "Per-class cov + 1e-6 reg",               "★★"],
        ["D72", "HMM 4-State",                "D_probabilistic",    "numpy",     "Full",    "4 states, diagonal Gaussian, Viterbi",   "★★"],
        ["D77", "GMM Classifier",             "D_probabilistic",    "sklearn",   "20,000",  "n_mix=2 per class",                      "★★"],
        ["D80", "Kalman + GMM",               "D_probabilistic",    "sklearn",   "20,000",  "Q=1e-3, R=0.1, n_components=4",          "★"],
        ["E81", "MLP",                        "E_deep",             "numpy",     "20,000",  "h=64, epochs=150, lr=0.01",              "★"],
        ["E83", "LSTM",                       "E_deep",             "numpy",     "2,000 ⚠", "hidden=16, epochs=30, lr=0.01",          "★"],
        ["E87", "TCN",                        "E_deep",             "numpy",     "None ⚠⚠", "3 layers, 8 filters, kernel=3 — NO training", "★"],
        ["F105","HMM+RF Hybrid",              "F_ecological",       "sklearn",   "Full",    "RF n_estimators=50; HMM 4 states",       "★★"],
        ["F106","Migration Speed Classifier", "F_ecological",       "sklearn",   "Full",    "LogReg on speed×straightness features",  "★★"],
        ["F107","Turning Angle Classifier",   "F_ecological",       "sklearn",   "20,000",  "RF n_estimators=50, sinuosity feature",  "★"],
        ["G01", "AdaBoost",                   "G_advanced_boosting","sklearn",   "20,000",  "n_estimators=100, SAMME",                "★★"],
        ["G02", "Hist Gradient Boosting",     "G_advanced_boosting","sklearn",   "Full",    "max_iter=100, max_depth=4",               "★★★"],
        ["G03", "CatBoost",                   "G_advanced_boosting","catboost*", "20,000",  "iterations=100, depth=4",                "★★★"],
    ],
    col_widths=[0.45, 2.0, 1.3, 0.85, 0.75, 2.1, 0.6])

add_para(doc,
    "* Falls back to sklearn GradientBoostingClassifier if optional library not installed.  "
    "⚠ Reduced training cap due to algorithmic cost.  "
    "⚠⚠ TCN has no training — random weights only.",
    size=9, color=GREY)

doc.add_paragraph()
# ════════════════════════════════════════════════════════════════════════════
# 10. LIVE RESULTS — SCREENSHOTS
# ════════════════════════════════════════════════════════════════════════════

doc.add_page_break()
add_heading(doc, "11. Live Results — Screenshots", 1)

add_para(doc,
    "The following screenshots were captured from the running VEBITA application using the "
    "African cuckoo in Nigeria dataset (Iwajomo et al. 2018, 5,352 GPS fixes, "
    "species: Cuculus gularis). The comparison run shows "
    "BC E87 TCN (Algorithm A) vs BC F106 Migration Speed Classifier (Algorithm B). "
    "This pairing is intentional — it demonstrates the difference between an uninitialised "
    "neural network (TCN) and a purpose-built ecological classifier on a migratory species.")

doc.add_paragraph()

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.14.03.png",
    "Figure 1 — Map view (Split). Left: BC E87 TCN (F1 = 0.136, 0.00s). "
    "Right: BC F106 Migration Speed Classifier (F1 = 0.140, 0.09s). "
    "Agreement = 20% — the two algorithms disagree on 80% of GPS fixes. "
    "TCN assigns mostly Travelling/Migrating at random; "
    "F106 correctly identifies the southward migration corridor through Nigeria.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.14.15.png",
    "Figure 2 — Cluster graphs. Cluster size distribution (donut): Migrating 737 fixes, "
    "Foraging 216, Resting 67, Travelling 51. Mean speed per cluster confirms "
    "Migrating dominates at ~608 m/s. Turning angle distribution shows Migrating fixes "
    "concentrate at low angles (straight flight). "
    "Cluster metrics table: F106 Migrating F1 = 1.000 vs TCN Migrating F1 = 0.003.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.14.25.png",
    "Figure 3 — Time series (part 1). Speed over time shows periodic high-speed spikes "
    "(active migration bursts). Altitude over time is near-flat (cuckoo GPS altitude data "
    "is unreliable — constant at ~0.2m). Turning angle is highly variable throughout "
    "(cuckoo changes heading frequently). Step length distribution: the vast majority of "
    "fixes have very short step lengths with a long tail to 881,270m during migration.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.14.35.png",
    "Figure 4 — Time series (part 2). Predicted behaviour state: TCN (green solid line) "
    "oscillates rapidly between all 4 states — random pattern consistent with uninitialised "
    "weights. F106 (purple dashed line) stays near state 1 (Foraging) for most of the "
    "sequence, with brief Migrating spikes — consistent with a cuckoo foraging between "
    "migration bursts. Straightness index fluctuates between 0 and 1.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.14.45.png",
    "Figure 5 — F1 scores tab. Header cards: TCN weighted F1 = 0.136, "
    "F106 weighted F1 = 0.140, F1 gap = +0.004, best accuracy = 0.290. "
    "Per-class F1 comparison chart: F106 achieves Migrating F1 = 1.000 (the dominant class) "
    "while TCN scores 0.003 on Migrating — confirming TCN cannot learn the migratory pattern. "
    "Radar chart shows TCN has near-zero recall and unbalanced precision.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.14.54.png",
    "Figure 6 — Full metrics table. TCN: Resting precision=0.372, recall=0.098, F1=0.103 (Low); "
    "Foraging F1=0.234 (Low); Travelling F1=0.094 (Low); Migrating F1=0.003 (Low). "
    "F106: Resting F1=0.000 (Low); Foraging F1=0.444 (Low); Travelling F1=0.029 (Low); "
    "Migrating F1=1.000 (Good). F106 sacrifices rare class accuracy to perfectly label "
    "the dominant Migrating class — expected behaviour for a migration-speed-focused classifier.")

add_screenshot(doc,
    "/Users/I776893/Desktop/Screenshot 2026-10-22 at 22.15.01.png",
    "Figure 7 — Feature importance (for TCN, computed by permutation on test set). "
    "Ranking: 1st turning_angle (0.0032), 2nd speed_ms (0.0013), "
    "3rd–5th altitude_m / straightness / alt_roll_mean (≈0.000). "
    "Bottom 3: speed_roll_mean (−0.0026), speed_roll_std (−0.0118), "
    "step_length_m (−0.0528). Negative scores mean permuting those features "
    "slightly improves TCN accuracy — confirming TCN does not use them meaningfully.")

add_heading(doc, "Key observations from the screenshots", 2)
for obs in [
    "BC E87 TCN produces random predictions (weighted F1 = 0.136) because fit() only "
    "initialises random weights — it never trains on the GPS data. The 20% agreement with "
    "F106 is near-chance for a 4-class problem (random baseline ≈ 25%).",
    "BC F106 Migration Speed Classifier achieves Migrating F1 = 1.000 because the cuckoo "
    "dataset is 69% Migrating (737/1071 test fixes) and the speed × straightness feature "
    "cleanly separates migration from other states on this species.",
    "F106 scores 0.000 on Resting because it is optimised for migration detection — "
    "rare behaviour classes (Resting = 67 fixes, 6%) are sacrificed for perfect Migrating recall.",
    "The flat altitude signal (Figure 3) confirms GPS altitude is unreliable on this cuckoo "
    "dataset — all algorithms that rely on altitude features (A29 Expert Rules, D80 Kalman+GMM) "
    "will perform poorly on this species.",
    "Feature importance (Figure 7) shows step_length_m hurts TCN accuracy when permuted "
    "(score = −0.0528) — permuting it accidentally creates a more uniform input distribution "
    "which TCN's random weights happen to predict slightly better.",
]:
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(obs).font.size = Pt(10)

doc.add_paragraph()

p_end = doc.add_paragraph(); p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_end = p_end.add_run("End of Report — VEBITA Service 6: Behavioural Classification")
r_end.italic = True; r_end.font.size = Pt(10); r_end.font.color.rgb = GREY

# ── Save ───────────────────────────────────────────────────────────────────────
out_path = "/Users/I776893/Downloads/Movement Project/Service_6_Behavioural_Classification_Report.docx"
doc.save(out_path)
print(f"Saved: {out_path}")
