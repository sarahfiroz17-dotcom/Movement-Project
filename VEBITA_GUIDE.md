# VEBITA — Complete Plain English Guide

Animal Movement Analysis Platform · Group Project

---

## 🐦 What is VEBITA?

VEBITA is a website that watches animals move around the world using GPS trackers.

Scientists attach tiny GPS devices to birds, wolves, bears, storks etc. The device records where the animal is every few minutes — this is called a **GPS fix**.

VEBITA takes all those thousands of GPS dots and tries to figure out — *"what was the animal DOING at this moment?"*

Was it resting? Searching for food? Walking slowly? Flying fast to another country?

Two computer algorithms compete to answer that question, and we compare who does it better.

---

## 🗺️ The 4 Movement Behaviours

When your dataset has no pre-labelled behaviours, VEBITA automatically assigns one of these 4 states to every GPS fix based on **speed rank** (not absolute values):

| Behaviour | What it means | Speed rank |
|-----------|--------------|------------|
| 🛌 **Resting** | The animal is not moving. Sitting, sleeping, roosting on a branch. | Bottom 25% (slowest) |
| 🌿 **Foraging** | Moving slowly in circles or zigzags, hunting for food. | 25%–50% |
| 🚶 **Traveling** | Moving purposefully from A to B at a steady pace. | 50%–75% |
| ✈️ **Migrating** | Flying or running very fast in a straight line to a completely different country or region. | Top 25% (fastest) |

**Why rank-based and not speed thresholds?**
Because different animals have completely different speeds. A stork "migrating" at 60 km/h and a tortoise "migrating" at 0.5 km/h can't share the same speed threshold. Rank-based assignment always produces exactly 25% of fixes in each class, no matter the species.

---

## 📊 What is an Algorithm?

An algorithm is a set of rules a computer follows to make a decision.

Here, each algorithm looks at speed, altitude, and other features for each GPS fix and guesses: *"this looks like Resting"* or *"this looks like Migrating"*.

You always pick **two algorithms (A and B)** and run them at the same time — so you can compare who is more accurate.

- **Algorithm A** → always shown in **green** throughout the website
- **Algorithm B** → always shown in **purple** throughout the website

Some algorithms are simple and fast (like Logistic Regression). Others are complex and slow but more powerful (like LSTM deep learning).

---

---

# 🗂️ TABS — BEHAVIOURAL CLASSIFICATION (S6)

These tabs appear when you are using any service EXCEPT Environmental Factors.

---

## Tab 1 — 🗺️ Map View

**What it shows:** The animal's full GPS journey drawn on a real map, with every fix coloured by what behaviour the algorithm predicted.

### Every element explained:

| Element | What it means |
|---------|--------------|
| **Coloured dot** | One GPS fix. Colour = the behaviour Algorithm A predicted at that location |
| **Dashed blue line** | The raw GPS track — the actual path the animal walked/flew |
| **Green start dot** | Where the GPS data begins |
| **Purple end dot** | The most recent recorded location |
| **White ring on a dot** | Algorithm A and Algorithm B DISAGREE here — they predicted different behaviours for the same location |
| **Agreement % bar** | How often A and B agree across all GPS fixes. 90% = they mostly think alike. 50% = they see the world very differently |

### Stat cards at the top:
- **Clusters found** — how many different behaviour states were detected
- **GPS fixes mapped** — total number of dots shown (max 20,000 for performance)
- **Best F1** — the accuracy score of Algorithm A (see F1 section below)
- **Total runtime** — how many seconds both algorithms took to run

### What to look for:
- Long stretches of the same colour = the animal stayed in one behaviour for a long time (e.g. long Resting = sleeping)
- Lots of white-ringed dots = the two algorithms strongly disagree — worth investigating why
- Clusters of colour in one region = the animal spent a lot of time doing one behaviour in that area

---

## Tab 2 — 📊 Cluster Graphs

**What it shows:** Four different charts that explore how the behaviours are distributed and how each algorithm performs per behaviour.

### Chart 1 — Scatter: Speed vs Altitude by Cluster
- **X axis (left–right):** Speed
- **Y axis (up–down):** Altitude
- **Each dot:** One GPS fix, coloured by its behaviour cluster
- **What to look for:** The clusters should visually separate — Resting should cluster bottom-left (slow, low altitude), Migrating should be top-right (fast, high altitude). If all clusters overlap completely, the algorithm is having trouble distinguishing behaviours.

### Chart 2 — Donut: Cluster Size Distribution
- Shows what **percentage of all GPS fixes** fall into each behaviour
- A huge Resting slice means the animal spent most of its time sitting still — totally normal for roosting birds overnight
- A large Migrating slice means the animal was travelling long distances frequently

### Chart 3 — Bar: Mean Speed Per Cluster
- Shows the **average speed** of each behaviour group
- Migrating should always have the tallest bar (fastest)
- Resting should always have the shortest bar (nearly zero)
- If Resting and Migrating have similar bar heights, something is wrong with how the labels were assigned

### Chart 4 — Comparison Table: Algorithm A vs B Per Behaviour
- Shows the **F1 score** for each behaviour, separately for A (green) and B (purple)
- **F1 column A vs F1 column B** = which algorithm is better at detecting each specific behaviour
- **Gap column** = positive gap (green pill) means A is better for that behaviour; negative (purple pill) means B is better
- A "—" means there were not enough examples of that behaviour to compute a score

---

## Tab 3 — ⏱️ Time Series

**What it shows:** How the animal's movement features changed over the entire recording period — like a story told left to right across time.

> **Note:** This tab is not available for Environmental Factors (S3). It only works for classification services.

### Chart 1 — Speed Over Time
- **X axis:** GPS fix number (left = earlier, right = later)
- **Y axis:** Speed in metres per second
- **What to look for:** Spikes = bursts of fast movement (takeoff, chase). Flat sections near zero = long resting periods. Regular peaks = daily movement rhythm.

### Chart 2 — Altitude Over Time
- **X axis:** GPS fix number
- **Y axis:** Height above sea level in metres
- **What to look for:** Sudden jumps = the animal took off or landed. High sustained altitude = in-flight migration. Low flat line = ground activity.

### Chart 3 — Turning Angle Over Time
- **X axis:** GPS fix number
- **Y axis:** Angle in degrees (0° = straight ahead, 180° = complete U-turn)
- **What to look for:** Low values = travelling in a straight line (migration). High values = circling/zigzagging (foraging). Random variation = exploratory movement.

### Chart 4 — Step Length Distribution (Histogram)
- **X axis:** Distance per GPS step (metres)
- **Y axis:** How many steps had that distance
- **What to look for:** A spike on the left = most steps are tiny (animal mostly sitting still). A spread-out histogram = the animal regularly covers different distances. A spike on the right = frequent long jumps (migratory flights).

### Chart 5 — Predicted Behaviour State: A vs B
- **X axis:** GPS fix number
- **Y axis:** Behaviour state (0 = Resting, 1 = Foraging, 2 = Traveling, 3 = Migrating)
- **Green solid line** = Algorithm A's predictions over time
- **Purple dashed line** = Algorithm B's predictions over time
- **What to look for:** When both lines follow the same pattern = they agree on the story. When they diverge = they have very different interpretations of the same movement.

### Chart 6 — Straightness Index Over Time
- **X axis:** GPS fix number
- **Y axis:** 0.0 to 1.0 (1.0 = perfectly straight line, 0.0 = completely circling)
- **What to look for:** Values near 1.0 = the animal is moving in a straight line (migration or direct travel). Values near 0.0 = the animal is circling or doubling back (foraging, exploring).

---

## Tab 4 — 🏆 F1 Scores

**What it shows:** A detailed scorecard comparing how accurate Algorithm A and B are, broken down by behaviour and metric.

> **Note:** This tab is not available for Environmental Factors (S3).

### The score cards at the top:
- **Weighted F1 — A:** Overall accuracy score for Algorithm A (accounts for class imbalance)
- **Weighted F1 — B:** Overall accuracy score for Algorithm B
- **F1 gap:** How much better one algorithm is than the other
- **Best accuracy:** The raw percentage of GPS fixes correctly labelled by the winning algorithm

### F1 Score thresholds — what is good?

| Score range | Grade | Meaning |
|-------------|-------|---------|
| **0.85 – 1.0** | ✅ Excellent | The algorithm almost never makes mistakes |
| **0.70 – 0.85** | 👍 Good | Solid performance, minor errors |
| **0.50 – 0.70** | ⚠️ Mediocre | Noticeable errors, usable but not great |
| **Below 0.50** | ❌ Poor | Barely better than random guessing |

**Why not just use accuracy?**
If 90% of fixes are Resting, an algorithm that just always guesses Resting gets 90% accuracy — but it never detects Foraging, Traveling, or Migrating at all. F1 score catches this cheat. Always check F1.

### Result cards (side by side):
Each algorithm gets a card showing:
- **F1 score** — the headline accuracy
- **Accuracy** — simple percentage correct
- **Precision** — when the algorithm says "this is Migrating", how often is it right?
- **Recall** — out of all actual Migrating fixes, how many did the algorithm catch?
- **Runtime** — how many seconds it took to run
- **Per-class F1** — the F1 score for each individual behaviour (Resting, Foraging, Traveling, Migrating)

**The card with a "Best model" badge = the algorithm with the higher weighted F1.**

### Chart 1 — Grouped Bar: Per-Class F1 Comparison
- **X axis:** Each behaviour (Resting, Foraging, Traveling, Migrating)
- **Y axis:** F1 score (0 to 1)
- **Green bars** = Algorithm A. **Purple bars** = Algorithm B
- **What to look for:** Which algorithm has taller bars for each behaviour? An algorithm that wins on Migrating but loses on Foraging might be better for migration studies but worse for habitat analysis.

### Chart 2 — Radar: Precision · Recall · F1 for Algorithm A
- A spider-web shaped chart with one axis per behaviour
- **Green (Precision):** How precise the algorithm is per class
- **Orange (Recall):** How many true examples it catches per class
- **Purple (F1):** The balance of precision and recall per class
- **What to look for:** A large, even shape = the algorithm performs consistently across all behaviours. A lopsided shape = it is great at some behaviours and terrible at others.

### Full Metrics Table:
Shows every number for every behaviour for both algorithms in one place.
- **Status "Good"** = F1 ≥ 0.80 for that behaviour
- **Status "Low"** = F1 < 0.80 for that behaviour

---

## Tab 5 — 🔬 Feature Importance

**What it shows:** Which movement features (speed, altitude, etc.) the algorithm relies on most to make its predictions.

### The ranked list:
Shows all features sorted from most important to least important.
- **Long bar** = the algorithm would get much worse without this feature
- **Short bar** = the algorithm barely uses this feature
- **Number on the right** = the importance score (they all add up to 1.0)

### Typical feature ranking for birds:
1. **speed_ms** — speed in metres per second (almost always #1)
2. **altitude_m** — height above sea level (almost always #2)
3. **turn_angle** — how sharply the animal is turning
4. **step_length** — distance between consecutive GPS fixes
5. **time_delta** — time gap between fixes
6. **straightness** — how straight the movement path is
7. **dist_to_colony** — distance from the nest/roost
8. **terrain_ruggedness** — how hilly the terrain is

### Chart 1 — Horizontal Bar Chart:
Same information as the ranked list, in visual form. Green = highest importance, fading to darker colours lower down.

### Chart 2 — SHAP-style Marginal Effects:
- **X axis:** Feature value (normalised 0–1, low to high)
- **Y axis:** How much that feature pushes the prediction up or down
- **Green line (altitude_m):** Rising line = higher altitude → algorithm predicts higher behaviour state (Migrating)
- **Orange line (speed_ms):** Rising line = faster speed → algorithm predicts Migrating
- **Purple line (terrain_ruggedness):** Falling line = rougher terrain → algorithm predicts lower behaviour state (Resting/Foraging)
- **What to look for:** Steep rising lines = the algorithm strongly links that feature to migration. Flat lines = the feature doesn't change the prediction much.

### Insight cards (bottom 3):
Show the top 3 most important features and what percentage of predictive power each one contributes.

---

---

# 🌿 TABS — ENVIRONMENTAL FACTORS (S3 — Sarah's Service)

These tabs ONLY appear when you select **Environmental Factors** from the service list.

Instead of classifying behaviour, this service asks: *"How good is this location for this animal right now?"*
Each GPS fix gets a **score from 0.0 to 1.0**.

### Score thresholds — what is good?

| Score range | Meaning | Example |
|-------------|---------|---------|
| **0.8 – 1.0** | 🟢 Excellent habitat | Rich wetland, abundant prey, ideal temperature, no disturbance |
| **0.6 – 0.8** | 🟡 Good habitat | Adequate resources, minor constraints |
| **0.4 – 0.6** | 🟠 Moderate habitat | Some limitations — food scarce, terrain difficult, weather poor |
| **0.2 – 0.4** | 🔴 Poor habitat | Hostile conditions, sparse resources, high energy cost to be here |
| **0.0 – 0.2** | ⚫ Very bad habitat | Desert, polluted area, extreme weather, no food or water |

**Important:** These scores are **relative to the animal's own dataset** — a score of 0.8 means this location was better than 80% of all locations the animal visited during the recording period. It does NOT mean the environment is objectively excellent in absolute terms.

---

## Tab 1 — 🗺️ Map View (Environmental Factors version)

**What it shows:** The GPS track with dots coloured by environmental score instead of behaviour.

### Dot colours:
- **Dark green / teal dots** = Algorithm A's score at that location (dark = low score, bright = high score)
- **Dark purple dots** = Algorithm B's score at that location (dark = low score, bright = vivid purple = high score)

### Checkboxes:
- ☑ **Algorithm A** (green) — show/hide Algorithm A's score dots
- ☑ **Algorithm B** (purple) — show/hide Algorithm B's score dots
- When both are shown, A dots are shifted slightly west and B dots slightly east so they don't overlap

### What to look for:
- Bright clusters = locations the animal repeatedly chose that score high — these are preferred habitats
- Dark stretches along the route = the animal passed through poor habitat to reach a better area
- Where A and B dots are different colours at the same location = the two algorithms disagree on whether that spot is good

### Stat cards:
- **GPS fixes mapped** — total dots visible
- **Best F1** — not applicable here (shows "—" because there are no behaviour classes)
- **Total runtime** — how many seconds both algorithms took

---

## Tab 2 — 🌿 Env Profiles

**What it shows:** A statistical summary of how each algorithm scores the entire dataset — are most locations good or bad?

### Stat cards at the top:
- **Mean score — A:** The average environmental score across all GPS fixes for Algorithm A. Higher = the animal spent time in good habitat on average.
- **Std dev — A:** How spread out Algorithm A's scores are. High std dev = the animal experienced a huge range of habitat quality. Low = all locations were similarly rated.
- **Mean score — B:** Same but for Algorithm B.
- **Std dev — B:** Same but for Algorithm B.

### Chart 1 — Score Distribution Histogram:
- **X axis:** Score from 0.0 (bad) to 1.0 (good)
- **Y axis:** Number of GPS fixes (shown on a log scale — because many datasets have thousands of low-scoring fixes and only a few high-scoring ones, so a normal scale would make the chart unreadable)
- **Green bars** = Algorithm A. **Purple bars** = Algorithm B.
- **What to look for:**
  - A tall bar on the LEFT (near 0.0) = most of the animal's time was in poor habitat — e.g. migrating through desert
  - A tall bar on the RIGHT (near 1.0) = the animal spent most time in excellent habitat — e.g. breeding near a rich wetland
  - A flat, spread-out distribution = the animal experienced a wide variety of habitat quality
  - If A and B bars line up = the two algorithms agree. If they don't = they measure different things.

### Chart 2 — Score vs Latitude Scatter:
- **X axis:** Latitude (how far north/south the location is)
- **Y axis:** Environmental score at that location
- **Green dots** = Algorithm A. **Purple dots** = Algorithm B.
- **What to look for:**
  - Upward trend = northern locations (higher latitude) score better — typical for birds summering in northern Europe
  - Downward trend = southern locations score better — typical for wintering birds in Africa
  - No trend (random cloud) = habitat quality is not related to latitude for this animal

### Table — Score Range Summary:
Shows the minimum, maximum, mean, and standard deviation of scores for both algorithms side by side.
Use this to quickly compare: does Algorithm A give higher scores overall than B? If A's mean is 0.65 and B's mean is 0.31, they are measuring the environment very differently.

---

## Tab 3 — ⏱️ Score Over Time

**What it shows:** How the environmental score changes fix by fix as the animal moves through its journey — like a heartbeat of habitat quality.

### Stat cards at the top:
- **Agreement rate:** The percentage of GPS fixes where A and B score within 0.2 of each other. 90% = they mostly agree on which places are good or bad. 50% = very different opinions.
- **High-disagreement fixes:** Number of GPS fixes where A and B scores differ by more than 0.2 — these are the locations worth investigating.
- **Total GPS fixes:** How many fixes are in the analysis.
- **Total runtime:** How long both algorithms took to run.

### Chart 1 — Score Over Time (Line Chart):
- **X axis:** GPS fix index (fix #1 on the left = start of recording, last fix on the right = most recent)
- **Y axis:** Environmental score from 0.0 to 1.0
- **Green line** = Algorithm A's score over time (smoothed with a 5-point rolling average to reduce noise)
- **Purple line** = Algorithm B's score over time (also smoothed)
- **What to look for:**
  - **Peaks** = moments when the animal was in excellent habitat — could be arriving at a feeding ground or migrating through a rich valley
  - **Troughs** = moments in poor habitat — crossing open water, desert, urban areas
  - **Flat line near 0** = the animal spent a long time in consistently bad habitat (e.g. traversing the Sahara)
  - **Where green and purple lines diverge** = the two algorithms interpret that location very differently

### Chart 2 — Score Difference Bar Chart (A minus B):
- **X axis:** GPS fix index
- **Y axis:** Score difference (A minus B). Positive = A scored higher. Negative = B scored higher.
- **Green bars** = Algorithm A thinks this location is better than B does
- **Purple bars** = Algorithm B thinks this location is better than A does
- **What to look for:**
  - All bars close to zero = algorithms almost always agree
  - Large bars in one direction = one algorithm consistently scores everything higher or lower — may indicate a calibration difference
  - Large bars scattered randomly = they agree on average but disagree wildly on individual locations

---

## Tab 4 — 🔬 Algorithm Comparison

**What it shows:** A deep comparison of whether Algorithm A and B produce similar scores — are they measuring the same thing, or completely different aspects of the environment?

### Stat cards at the top:
- **Pearson correlation:** A number from -1.0 to +1.0 measuring how similar the two algorithms' scores are across all GPS fixes.
  - **+0.9 to +1.0** = Strongly agree — when A says a place is good, B also says it's good
  - **+0.5 to +0.9** = Moderately agree
  - **0.0 to +0.5** = Weak agreement — they measure somewhat different things
  - **Negative** = They actively disagree — when A says good, B says bad
- **Correlation strength label:** "Strong positive", "Moderate positive", "Weak positive", or "Weak/negative"
- **Runtime — A:** How many seconds Algorithm A took
- **Runtime — B:** How many seconds Algorithm B took

### Algorithm description panels:
Two side-by-side text panels describing what each algorithm actually measures — what environmental features it uses and how it computes its score.

### Chart 1 — Score A vs Score B Scatter:
- **X axis:** Algorithm A's score for each GPS fix
- **Y axis:** Algorithm B's score for the same GPS fix
- Each dot = one GPS fix
- **What to look for:**
  - **Dots along the diagonal (bottom-left to top-right)** = the two algorithms agree perfectly on every fix
  - **Dots spread in a wide cloud** = they disagree frequently — they measure different aspects of the environment
  - **Dots clustered in one corner** = both algorithms give extreme scores (both very low or both very high) for most locations

### Chart 2 — Score Difference Distribution Histogram:
- **X axis:** Score difference (A minus B), ranging from -1.0 to +1.0
- **Y axis:** Number of GPS fixes with that difference
- **Purple bars** = fixes where B scored higher (left side, negative differences)
- **Green bars** = fixes where A scored higher (right side, positive differences)
- **What to look for:**
  - **Tall spike at 0** = algorithms almost always agree — very reliable comparison
  - **Spike shifted to the right** = Algorithm A consistently gives higher scores than B (A is more optimistic about habitat quality)
  - **Spike shifted to the left** = Algorithm B consistently gives higher scores than A
  - **Wide, flat spread** = they frequently give very different answers — they are measuring fundamentally different things

---

## Tab 5 — 🔬 Feature Importance (Environmental Factors version)

**What it shows:** Which environmental features the algorithm relies on most when deciding whether a location scores high or low.

> This works the same as the Feature Importance tab for Behavioural Classification, but the features are interpreted differently — here they tell you what makes a location environmentally good or bad, rather than what behaviour is happening.

### Typical feature ranking for environmental scoring:
1. **altitude_m** — height above sea level. Many species prefer specific altitude bands.
2. **speed_ms** — how fast the animal is moving at that location (proxy for terrain accessibility)
3. **terrain_ruggedness** — how hilly/rough the terrain is. Many species avoid very rugged terrain.
4. **turn_angle** — how much the animal turns here (high turning = interesting foraging area)
5. **step_length** — distance per GPS step (proxy for habitat openness)
6. **straightness** — straight movement through a location = just passing through (probably low quality)
7. **dist_to_colony** — how far from the nest/roost. Closer = potentially more important habitat.
8. **time_delta** — time between fixes (longer gaps = animal stayed longer = good habitat?)

### Chart 1 — Feature Importance Bar Chart:
Same as for behavioural classification — long bar = this feature strongly determines the environmental score.

### Chart 2 — SHAP Marginal Effects:
- Shows how changing one feature's value pushes the score up or down
- **Rising green line (altitude)** = higher altitude → higher environmental score (e.g. algorithm favours upland habitats)
- **Falling purple line (terrain_ruggedness)** = rougher terrain → lower score (algorithm penalises inaccessible terrain)

### Insight cards:
Bottom 3 most important features with their percentage contribution to the overall score.

---

---

# 📡 Other Services (Brief)

| Service | Question it answers | What the charts show |
|---------|--------------------|--------------------|
| **S1 — Time Series Patterns** | Does this animal have regular daily or seasonal rhythms? | Periodic patterns in speed/altitude, autocorrelation charts |
| **S2 — Movement Patterns** | Does this animal return to the same places repeatedly? | Recurring routes, territory maps, revisit frequency |
| **S4 — Anomaly Detection** | Are there any GPS fixes that seem completely wrong or unusual? | Anomaly scores per fix, outlier maps, which fixes stand out |
| **S5 — Trajectory Segmentation** | Can we split this journey into meaningful segments? | Segment boundaries on the map, segment statistics, breakpoint detection |

---

## 📁 Using Your Own CSV File

1. Go to **movebank.org**, find a study, download data as CSV
2. Required columns: `timestamp`, `location-lat`, `location-long`, `ground-speed`, `height-above-msl`
3. Drag and drop the CSV into the sidebar upload box, or click to browse
4. Large files (up to 3.5 GB) are supported — processing may take a few minutes for huge datasets
5. The dataset stays available until you restart the backend server

**No CSV?** Just click Run without uploading — demo animal data will be used automatically.

---

## 🚀 How to Start the App

Open **two terminal windows**:

**Terminal 1 — Backend:**
```
cd "Movement Project/backend"
uvicorn main:app --reload --port 8000
```
Wait until you see: `✓ Service 6 (Behavioural Classification) loaded` and `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 — Frontend:**
```
cd "Movement Project/frontend"
npm run dev
```

Then open your browser: **http://localhost:5173**

- If the backend stops → run the `uvicorn` command again in Terminal 1
- The frontend can stay running — you only need to restart the backend
- API docs (interactive): http://localhost:8000/docs

---

## ❓ Why Do Algorithms Disagree?

Different algorithms have different "opinions" about which patterns matter.

**Simple algorithms** (Logistic Regression, Nearest Centroid) draw straight dividing lines between classes — fast = migrating, slow = resting. Easy to understand, but misses complex patterns like "slow at high altitude" vs "slow at low altitude".

**Complex algorithms** (Random Forest, LSTM, Gradient Boosting) learn curved, twisting decision boundaries. They can figure out that a bird going slowly at 800m altitude is DIFFERENT from a bird going slowly at 10m altitude, even at the same speed.

**Neither is always better:**
- Simple = faster, easier to explain, works well on small datasets
- Complex = higher F1 scores on large datasets, but slower and harder to interpret

That's why VEBITA compares two — to see if the extra complexity is worth it for the specific animal and dataset you are analysing.

---

*VEBITA Group Project · Animal Movement Analysis Platform*
