import React, { useState } from 'react'

const SECTIONS = [
  {
    title: '🐦 What is VEBITA?',
    tag: 'Overview', tagClass: 'badge-green',
    content: [
      'VEBITA is a website that watches animals move around the world using GPS trackers.',
      'Scientists attach tiny GPS devices to birds, wolves, bears, storks etc. The device records where the animal is every few minutes — this is called a "GPS fix".',
      'VEBITA takes all those thousands of GPS dots and tries to figure out — "what was the animal DOING at this moment?"',
      'Was it resting? Searching for food? Walking slowly? Flying fast to another country?',
      'Two computer algorithms compete to answer that question, and we compare who does it better.',
    ],
  },
  {
    title: '🗺️ The 4 movement behaviours',
    tag: 'Behaviours', tagClass: 'badge-green',
    content: [
      '🛌 RESTING — The animal is not moving at all. Sitting, sleeping, roosting on a branch. Speed is very low or zero. → Bottom 25% of speeds.',
      '🌿 FORAGING — Moving slowly in circles or zigzags, searching for food. Speed is low-to-medium. → 25%–50% of speeds.',
      '🚶 TRAVELING — Moving purposefully from A to B at a steady pace. Speed is medium. → 50%–75% of speeds.',
      '✈️ MIGRATING — Flying or running very fast in a straight line to a completely different location — often hundreds of km away. → Top 25% (fastest).',
      'Labels are assigned by SPEED RANK not speed value — so each behaviour always gets exactly 25% of fixes regardless of species. A stork migrating at 60 km/h and a tortoise migrating at 0.5 km/h both get the top 25%.',
    ],
  },
  {
    title: '📊 What is an Algorithm?',
    tag: 'Concepts', tagClass: 'badge-purple',
    content: [
      'An algorithm is a set of rules a computer follows to make a decision.',
      'Here, each algorithm looks at speed, altitude, and other features for each GPS fix and guesses: "this looks like Resting" or "this looks like Migrating".',
      'You always pick TWO algorithms (A and B) and run them at the same time — so you can compare who is more accurate.',
      'Algorithm A is always shown in GREEN. Algorithm B is always shown in PURPLE throughout the whole website.',
      'Simple algorithms (Logistic Regression) draw straight lines between classes — fast and easy to understand but miss complex patterns.',
      'Complex algorithms (Random Forest, LSTM) learn curved boundaries — can tell "slow at 800m altitude" is different from "slow at 10m altitude".',
    ],
  },
  {
    title: '🗺️ Map view — every element explained',
    tag: 'Charts', tagClass: 'badge-amber',
    content: [
      'Every coloured dot = one GPS fix = the animal was HERE at this moment.',
      'The colour of the dot = what behaviour Algorithm A predicted at that location.',
      'The dashed blue line = the raw GPS track — the actual path the animal walked or flew.',
      'Green start dot = where the GPS data begins. Purple end dot = most recent recorded location.',
      'A dot with a white ring = Algorithms A and B DISAGREE about what the animal was doing there.',
      'Agreement % bar = how often A and B agree across all fixes. 90% = mostly the same opinion. 50% = very different.',
      'Stat cards: Clusters found, GPS fixes mapped (max 20,000), Best F1 score, Total runtime.',
      'FOR ENVIRONMENTAL FACTORS: dots are coloured by score instead — dark = bad habitat, bright = excellent habitat.',
      'FOR ENV FACTORS: two checkboxes let you show/hide Algorithm A (green) and B (purple) dots separately.',
    ],
  },
  {
    title: '📊 Cluster graphs — all 4 charts explained',
    tag: 'Charts', tagClass: 'badge-amber',
    content: [
      'SCATTER (speed vs altitude): Each dot is one GPS fix, coloured by behaviour. Resting = bottom-left (slow, low). Migrating = top-right (fast, high). Overlapping clusters = algorithm is struggling to separate behaviours.',
      'DONUT (cluster sizes): Shows what % of all GPS fixes fall into each behaviour. Big Resting slice = animal spent most time sitting still — normal for roosting birds overnight.',
      'BAR (mean speed): Average speed per behaviour. Migrating should always have the tallest bar. Resting should be nearly zero. If they are the same height, labels may be wrong.',
      'COMPARISON TABLE: F1 score per behaviour for A (green) vs B (purple). Gap column shows who wins each behaviour. "—" means not enough examples of that behaviour to compute a score.',
    ],
  },
  {
    title: '⏱️ Time series — all 6 charts explained',
    tag: 'Charts', tagClass: 'badge-amber',
    content: [
      'Not available for Environmental Factors — use the Score over time tab instead.',
      'SPEED OVER TIME: Spikes = bursts of fast movement. Flat sections near zero = long resting. Regular peaks = daily rhythm.',
      'ALTITUDE OVER TIME: Sudden jumps = animal took off or landed. Sustained high altitude = in-flight migration. Low flat line = ground activity.',
      'TURNING ANGLE: Low values = straight-line travel (migration). High values = circling/zigzagging (foraging). Unit = degrees, 0° = straight, 180° = U-turn.',
      'STEP LENGTH HISTOGRAM: Spike on the left = mostly tiny steps (animal sitting still). Spread out = varied distances. Spike on the right = frequent long migratory flights.',
      'BEHAVIOUR STATE A vs B: Green solid line = Algorithm A. Purple dashed line = Algorithm B. When lines match = they agree. When they diverge = different interpretations of the same movement.',
      'STRAIGHTNESS INDEX: 1.0 = perfectly straight line (migration/direct travel). 0.0 = circling (foraging). Watch for drops from 1.0 to 0.0 — those are behaviour transitions.',
    ],
  },
  {
    title: '🏆 F1 scores — what each number means',
    tag: 'Charts', tagClass: 'badge-amber',
    content: [
      'Not available for Environmental Factors.',
      'F1 SCORE is like a school grade: 0.85–1.0 = Excellent ✅ | 0.70–0.85 = Good 👍 | 0.50–0.70 = Mediocre ⚠️ | Below 0.50 = Poor ❌',
      'WHY NOT JUST ACCURACY? If 90% of fixes are Resting, always guessing Resting = 90% accuracy but useless. F1 catches this cheat.',
      'RESULT CARDS: F1 score, Accuracy (raw % correct), Precision (when it says Migrating — how often right?), Recall (of all true Migrating fixes — how many caught?), Runtime, Per-class F1.',
      'The card with "Best model" badge = the algorithm with the higher weighted F1.',
      'GROUPED BAR CHART: Green = Algorithm A, Purple = Algorithm B, one group per behaviour. Taller bar = better for that behaviour.',
      'RADAR CHART: Spider-web shape for Algorithm A only. Green = Precision, Orange = Recall, Purple = F1 per class. Big even shape = consistent across all behaviours. Lopsided = great at some, terrible at others.',
      'FULL METRICS TABLE: Status "Good" = F1 ≥ 0.80. Status "Low" = F1 < 0.80.',
    ],
  },
  {
    title: '🔬 Feature importance — what each chart shows',
    tag: 'Charts', tagClass: 'badge-amber',
    content: [
      'Feature importance answers: "if we removed this feature, how much dumber would the algorithm get?"',
      'RANKED LIST: Features sorted from most to least important. Long bar = very important. Short bar = barely used. Numbers add up to 1.0.',
      'Typical bird ranking: 1. speed_ms  2. altitude_m  3. turn_angle  4. step_length  5. straightness  6. terrain_ruggedness',
      'HORIZONTAL BAR CHART: Same as ranked list in visual form.',
      'SHAP MARGINAL EFFECTS: X axis = feature value (low to high). Y axis = how much it pushes the prediction. Rising green line (altitude) = higher altitude → algorithm predicts Migrating. Falling purple line (terrain) = rougher terrain → predicts Resting/Foraging.',
      'INSIGHT CARDS (bottom 3): Top 3 features and their % contribution to predictive power.',
    ],
  },
  {
    title: '🌿 Env Profiles tab — what each chart shows',
    tag: 'Env Factors', tagClass: 'badge-green',
    content: [
      'Only available for Environmental Factors (S3).',
      'STAT CARDS: Mean score A/B = average habitat quality across all fixes. High mean = animal spent most time in good habitat. Std dev = how varied the habitat quality was — high std dev = huge range experienced.',
      'SCORE DISTRIBUTION HISTOGRAM: X = score 0.0 (bad) to 1.0 (good). Y = number of GPS fixes (log scale). Tall bar LEFT = most time in poor habitat. Tall bar RIGHT = most time in excellent habitat. If A and B bars line up = they agree.',
      'SCORE vs LATITUDE SCATTER: X = latitude (north-south position). Y = environmental score. Upward trend = northern locations are better (typical for summer-breeding birds in Europe). Downward = southern locations better (wintering birds in Africa).',
      'SCORE RANGE TABLE: Shows min, max, mean, std dev for both algorithms side by side. If A mean = 0.65 and B mean = 0.31, they are measuring completely different things.',
    ],
  },
  {
    title: '🌿 Score over time tab — what each chart shows',
    tag: 'Env Factors', tagClass: 'badge-green',
    content: [
      'Only available for Environmental Factors (S3).',
      'STAT CARDS: Agreement rate = % of fixes where A and B score within 0.2 of each other. High-disagreement fixes = locations where they differ by more than 0.2.',
      'LINE CHART (score over time): X = GPS fix index (left = start of journey, right = most recent). Y = score 0.0–1.0. Green = Algorithm A, Purple = Algorithm B (both smoothed). Peaks = excellent habitat zones. Troughs = poor habitat (crossing desert, open water). Where lines diverge = algorithms interpret that location very differently.',
      'DIFFERENCE BAR CHART: X = fix index. Y = A score minus B score. Green bars = A scored higher here. Purple bars = B scored higher. All bars near zero = they almost always agree. Large scattered bars = they frequently give completely different answers.',
      'Agreement threshold: |A − B| > 0.2 counts as a "high disagreement" fix.',
    ],
  },
  {
    title: '🔬 Algorithm comparison tab — what each chart shows',
    tag: 'Env Factors', tagClass: 'badge-green',
    content: [
      'Only available for Environmental Factors (S3).',
      'PEARSON CORRELATION: +0.9 to +1.0 = strongly agree (when A says good, B says good). +0.5 to +0.9 = moderately agree. 0.0 to +0.5 = weak agreement. Negative = they actively disagree.',
      'ALGORITHM DESCRIPTION PANELS: Two side-by-side panels showing what each algorithm actually measures and how it computes its score.',
      'SCORE A vs SCORE B SCATTER: X = Algorithm A score. Y = Algorithm B score. Each dot = one GPS fix. Dots along the diagonal = perfect agreement. Wide cloud = they frequently disagree. Clustered in one corner = both give extreme scores for most locations.',
      'DIFFERENCE DISTRIBUTION HISTOGRAM: X = A minus B (from −1.0 to +1.0). Y = number of fixes. Tall spike at 0 = they almost always agree. Spike shifted right = A consistently scores higher. Spike shifted left = B consistently scores higher. Wide flat spread = they measure fundamentally different things.',
    ],
  },
  {
    title: '🌿 Environmental score thresholds',
    tag: 'Env Factors', tagClass: 'badge-green',
    content: [
      'Scores are RELATIVE to the animal\'s own dataset — 0.8 means this location was better than 80% of all locations the animal visited. It does NOT mean objectively excellent in absolute terms.',
      '🟢 0.8 – 1.0 = Excellent habitat — rich wetland, abundant prey, ideal temperature, no disturbance.',
      '🟡 0.6 – 0.8 = Good habitat — adequate resources, minor constraints.',
      '🟠 0.4 – 0.6 = Moderate habitat — some limitations, food scarce, terrain difficult, weather poor.',
      '🔴 0.2 – 0.4 = Poor habitat — hostile conditions, sparse resources, high energy cost to be here.',
      '⚫ 0.0 – 0.2 = Very bad habitat — desert, polluted area, extreme weather, no food or water.',
    ],
  },
  {
    title: '📡 Other services',
    tag: 'Services', tagClass: 'badge-gray',
    content: [
      'S1 — Time Series Patterns: Does this animal have regular daily or seasonal rhythms? Charts show periodic patterns in speed/altitude.',
      'S2 — Movement Patterns: Does this animal return to the same places repeatedly? Charts show recurring routes and territory maps.',
      'S4 — Anomaly Detection: Are there GPS fixes that seem completely wrong or unusual? Shows anomaly scores per fix and outlier maps.',
      'S5 — Trajectory Segmentation: Can we split this journey into meaningful segments? Shows segment boundaries on the map and breakpoint detection.',
      'S6 — Behavioural Classification: Classifies every GPS fix into Resting / Foraging / Traveling / Migrating. The main service — all the tabs above apply here.',
    ],
  },
  {
    title: '📁 CSV format and demo mode',
    tag: 'Data', tagClass: 'badge-gray',
    content: [
      'Required columns: timestamp, location-lat, location-long, ground-speed, height-above-msl',
      'Download real data from movebank.org — search for a study, export as CSV.',
      'Large files up to 3.5 GB are supported. Processing may take a few minutes.',
      'The dataset stays available until you restart the backend.',
      'No CSV? Just click Run without uploading — demo animal data will be used automatically.',
      'Demo animals: red kite, black stork, mongolian gazelle, elk, wolf, brown bear, cheetah, white stork.',
    ],
  },
  {
    title: '🚀 How to start the app',
    tag: 'Setup', tagClass: 'badge-gray',
    content: [
      'Open TWO terminal windows.',
      'Terminal 1 (backend): cd "Movement Project/backend" → uvicorn main:app --reload --port 8000',
      'Terminal 2 (frontend): cd "Movement Project/frontend" → npm run dev',
      'Open your browser at: http://localhost:5173',
      'If the backend stops (Ctrl+C), just run the uvicorn command again.',
      'The frontend can stay running — you only ever need to restart the backend.',
    ],
  },
]

export default function Docs() {
  const [open, setOpen] = useState(null)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

      <div style={{ padding: '0 0 10px', borderBottom: '1px solid var(--border)', marginBottom: 4 }}>
        <div style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', marginBottom: 4 }}>
          VEBITA — Plain English Guide
        </div>
        <div style={{ fontSize: 12, color: 'var(--text3)' }}>
          Everything explained simply. Click any card to expand it.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {SECTIONS.map((sec, i) => (
          <div key={sec.title}
               className="panel"
               style={{ cursor: 'pointer', transition: 'border-color .15s',
                        borderColor: open === i ? 'var(--accent-d)' : 'var(--border)' }}
               onClick={() => setOpen(open === i ? null : i)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', marginBottom: 6 }}>
                  {sec.title}
                </div>
                <span className={`badge ${sec.tagClass}`}>{sec.tag}</span>
              </div>
              <span style={{ color: 'var(--text3)', fontSize: 16, marginTop: 2, flexShrink: 0, marginLeft: 8 }}>
                {open === i ? '−' : '+'}
              </span>
            </div>
            {open === i && (
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {sec.content.map((line, j) => (
                  <div key={j} style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.7,
                                        paddingLeft: 10, borderLeft: '2px solid var(--border2)' }}>
                    {line}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="panel" style={{ borderColor: 'var(--accent-d)', background: '#0d1f17' }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--accent)', marginBottom: 10 }}>
          Quick start
        </div>
        {[
          ['Terminal 1 — backend', 'uvicorn main:app --reload --port 8000'],
          ['Terminal 2 — frontend', 'npm run dev'],
          ['Open browser', 'http://localhost:5173'],
          ['API docs', 'http://localhost:8000/docs'],
        ].map(([label, cmd]) => (
          <div key={label} style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 3 }}>{label}</div>
            <div style={{ background: '#0a0a10', border: '1px solid var(--border)', borderRadius: 6,
                          padding: '6px 10px', fontSize: 12, fontFamily: 'monospace',
                          color: 'var(--accent)', wordBreak: 'break-all' }}>
              {cmd}
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}
