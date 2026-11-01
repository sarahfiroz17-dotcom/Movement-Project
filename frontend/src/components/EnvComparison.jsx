import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'
const COLOR_A = '#5DCAA5'
const COLOR_B = '#7F77DD'

const CATEGORY_DESCRIPTIONS = {
  statistical:          'Uses mathematical equations to find a straight-line relationship between the environment and movement.',
  time_series:          'Looks at how the environment changes over time as the animal moves along its route.',
  ml_supervised:        'Learns patterns from training data to predict how the environment influences movement.',
  deep_learning:        'Uses a neural network or probabilistic model to capture complex environmental patterns.',
  ensemble:             'Combines several algorithms and averages their answers for a more stable result.',
  causal_explainable:   'Tries to find what actually causes the movement change, not just what correlates with it.',
  feature_engineering:  'Transforms the raw GPS data into new signals before scoring environmental influence.',
}

function useChart(config, deps) {
  const ref = useRef()
  const chart = useRef()
  useEffect(() => {
    if (!ref.current) return
    if (chart.current) chart.current.destroy()
    chart.current = new Chart(ref.current, config)
    return () => { if (chart.current) chart.current.destroy() }
  }, deps)
  return ref
}

function pearson(a, b) {
  const n = Math.min(a.length, b.length)
  if (n < 2) return 0
  const meanA = a.slice(0, n).reduce((s, v) => s + v, 0) / n
  const meanB = b.slice(0, n).reduce((s, v) => s + v, 0) / n
  let num = 0, da = 0, db = 0
  for (let i = 0; i < n; i++) {
    const dA = a[i] - meanA, dB = b[i] - meanB
    num += dA * dB; da += dA * dA; db += dB * dB
  }
  return da && db ? num / Math.sqrt(da * db) : 0
}

// Solo mode: bar chart of mean score per dominant env factor
function SoloView({ results }) {
  const nameA   = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm'
  const descA   = results.algo_a?.score_label || ''
  const catA    = results.algo_a?.category || ''
  const scoresA = (results.algo_a?.scores || []).filter(v => v != null)
  const envFactors = results.env_factors
  const labelNames = results.label_names || []
  const stages = results.stages || []

  // Mean score per dominant env factor
  const factorBarRef = useRef()
  const factorBarChart = useRef()
  useEffect(() => {
    if (!factorBarRef.current || !envFactors?.names || !scoresA.length) return
    if (factorBarChart.current) factorBarChart.current.destroy()

    const names = envFactors.names
    const values = envFactors.values  // n × 12
    const n = Math.min(scoresA.length, values.length)

    // Group: for each fix find which factor is highest, accumulate score
    const factorScoreSum = new Array(names.length).fill(0)
    const factorCount    = new Array(names.length).fill(0)
    for (let i = 0; i < n; i++) {
      const row = values[i]
      let topIdx = 0, topVal = -1
      for (let j = 0; j < row.length; j++) {
        if (row[j] > topVal) { topVal = row[j]; topIdx = j }
      }
      factorScoreSum[topIdx] += scoresA[i] ?? 0
      factorCount[topIdx]++
    }
    const meanScores = factorScoreSum.map((s, i) => factorCount[i] > 0 ? +(s / factorCount[i]).toFixed(3) : 0)

    factorBarChart.current = new Chart(factorBarRef.current, {
      type: 'bar',
      data: {
        labels: names.map(n => n.replace(/_/g, ' ')),
        datasets: [{
          label: 'Mean env score when factor is dominant',
          data: meanScores,
          backgroundColor: COLOR_A + 'bb',
          borderRadius: 3,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } } },
          y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
               title: { display: true, text: 'Mean score (0–1)', color: TICK, font: { size: 10 } },
               min: 0, max: 1 },
        },
      },
    })
    return () => { factorBarChart.current?.destroy() }
  }, [results])

  // Stage breakdown
  const stageColors = ['#378ADD', '#5DCAA5', '#EF9F27', '#D85A30']
  const stageCounts = labelNames.map((_, i) => stages.filter(s => s === i).length)
  const total = stages.length || 1

  // Auto-generated insight
  const soloInsightLines = []
  const vals   = scoresA.filter(v => !isNaN(v))
  const meanSc = vals.length > 0 ? vals.reduce((s,v)=>s+v,0)/vals.length : null
  const stdSc  = vals.length > 1
    ? Math.sqrt(vals.reduce((s,v)=>s+(v-meanSc)**2,0)/vals.length)
    : null

  if (stdSc != null) {
    if (stdSc > 0.2)
      soloInsightLines.push(`${nameA} finds large variation in environmental influence along this route (score variability: ${stdSc.toFixed(3)}) — the animal clearly passes through zones of very different environmental intensity.`)
    else if (stdSc < 0.07)
      soloInsightLines.push(`${nameA} gives consistent scores throughout the route (variability: ${stdSc.toFixed(3)}), suggesting it sees the environment as fairly uniform here. Try a different algorithm category to see if another approach picks up more variation.`)
    else
      soloInsightLines.push(`${nameA} finds moderate variation in environmental scores along this route (variability: ${stdSc.toFixed(3)}) — conditions change somewhat but there are no extreme hotspots.`)
  }
  if (catA) {
    soloInsightLines.push(`This is a ${catA.replace(/_/g, ' ')} algorithm — ${CATEGORY_DESCRIPTIONS[catA] || ''} Try comparing it with a different category to see if the approach changes the result.`)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Stat cards */}
      <div className="metrics-row">
        <div className="mcard">
          <div className="mcard-val accent">{scoresA.length > 0 ? (scoresA.reduce((s,v)=>s+v,0)/scoresA.length).toFixed(3) : '—'}</div>
          <div className="mcard-label">Mean score</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{results.algo_a?.runtime != null ? results.algo_a.runtime.toFixed(2) + 's' : '—'}</div>
          <div className="mcard-label">Runtime</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{scoresA.length.toLocaleString()}</div>
          <div className="mcard-label">GPS fixes scored</div>
        </div>
      </div>

      {/* Auto-generated insight */}
      <div className="panel" style={{ borderLeft: '3px solid var(--accent)', background: 'var(--surface1)' }}>
        <div className="panel-title" style={{ marginBottom: 6 }}>What the analysis shows</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7, margin: 0 }}>
          {soloInsightLines.join(' ')}
        </p>
      </div>
      <div className="panel">
        <div className="panel-title" style={{ color: COLOR_A }}>{nameA}</div>
        <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.7, marginBottom: catA ? 8 : 0 }}>{descA}</div>
        {catA && (
          <div style={{ fontSize: 11, color: 'var(--text3)', borderTop: '1px solid var(--border)', paddingTop: 8, lineHeight: 1.6 }}>
            <span className="badge badge-gray" style={{ marginRight: 6 }}>{catA.replace(/_/g, ' ')}</span>
            {CATEGORY_DESCRIPTIONS[catA] || ''}
          </div>
        )}
      </div>

      {/* Mean score per dominant factor */}
      {envFactors?.names && (
        <div className="panel">
          <div className="panel-title">Mean score by dominant environmental factor</div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
            Each bar shows the average environmental score for GPS fixes where that factor was the strongest signal.
            Tall bars = this algorithm scores that factor type highly.
          </div>
          <div style={{ position: 'relative', height: 200 }}>
            <canvas ref={factorBarRef} />
          </div>
        </div>
      )}

      {/* Stage breakdown */}
      {labelNames.length > 0 && stages.length > 0 && (
        <div className="panel">
          <div className="panel-title">Movement stage breakdown</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 4 }}>
            {labelNames.map((lbl, i) => (
              <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: stageColors[i % stageColors.length] }} />
                <span style={{ fontSize: 12, color: 'var(--text2)' }}>{lbl}</span>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                  {stageCounts[i]} ({Math.round(stageCounts[i] / total * 100)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function EnvComparison({ results }) {
  if (!results) return (
    <div className="empty-state">
      <p>Run an Environmental Factors analysis to compare algorithms</p>
    </div>
  )

  const compareMode = results?.compareMode
  if (!compareMode) return <SoloView results={results} />

  const scoresA = (results.algo_a?.scores || []).filter(v => v != null)
  const scoresB = (results.algo_b?.scores || []).filter(v => v != null)
  const nameA   = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm A'
  const nameB   = results.algo_b?.name?.replace(/^Env\s/, '') || 'Algorithm B'
  const descA   = results.algo_a?.score_label || ''
  const descB   = results.algo_b?.score_label || ''
  const catA    = results.algo_a?.category || ''
  const catB    = results.algo_b?.category || ''

  // Pearson correlation
  const corr = pearson(scoresA, scoresB).toFixed(3)

  // Score difference distribution (20 bins, range -1 to 1)
  const BINS = 20
  const diffBins = new Array(BINS).fill(0)
  const n = Math.min(scoresA.length, scoresB.length)
  for (let i = 0; i < n; i++) {
    const d = (scoresA[i] - scoresB[i] + 1) / 2  // map -1..1 → 0..1
    diffBins[Math.min(Math.floor(d * BINS), BINS - 1)]++
  }
  const diffLabels = Array.from({ length: BINS }, (_, i) => ((i / BINS * 2) - 1).toFixed(1))

  const diffHistRef = useChart({
    type: 'bar',
    data: {
      labels: diffLabels,
      datasets: [{
        label: 'Number of fixes',
        data: diffBins,
        backgroundColor: diffBins.map((_, i) =>
          i < BINS / 2 ? COLOR_B + 'aa' : COLOR_A + 'aa'
        ),
        borderRadius: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 10 },
             title: { display: true, text: 'Score difference (A − B)', color: TICK, font: { size: 10 } } },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: 'Number of GPS fixes', color: TICK, font: { size: 10 } } },
      },
    },
  }, [results])

  // Score A vs Score B scatter (sampled)
  const MAX = 400
  const step = Math.max(1, Math.floor(n / MAX))
  const scatter = []
  for (let i = 0; i < n; i += step) {
    scatter.push({ x: +(scoresA[i] ?? 0).toFixed(3), y: +(scoresB[i] ?? 0).toFixed(3) })
  }

  const scatterRef = useChart({
    type: 'scatter',
    data: {
      datasets: [{
        label: `${nameA} vs ${nameB}`,
        data: scatter,
        backgroundColor: '#EF9F2799',
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } },
             title: { display: true, text: `${nameA} score`, color: COLOR_A, font: { size: 10 } }, min: 0, max: 1 },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: `${nameB} score`, color: COLOR_B, font: { size: 10 } }, min: 0, max: 1 },
      },
    },
  }, [results])

  const corrStrength = Math.abs(+corr) > 0.7 ? 'Strong' : Math.abs(+corr) > 0.4 ? 'Moderate' : 'Weak'
  const corrDir = +corr >= 0 ? 'positive' : 'negative'

  // Auto-generated insight
  const compInsightLines = []
  const corrNum = parseFloat(corr)
  if (Math.abs(corrNum) > 0.7)
    compInsightLines.push(`These two algorithms agree strongly on where environmental influence is high and low (correlation: ${corr}). Points along the diagonal in the scatter chart below confirm they produce nearly the same scores for each GPS fix.`)
  else if (Math.abs(corrNum) > 0.4)
    compInsightLines.push(`The algorithms have moderate agreement (correlation: ${corr}). They share the same general picture but differ on specific locations — the difference histogram will show whether those disagreements are random or concentrated in certain parts of the route.`)
  else
    compInsightLines.push(`The algorithms disagree substantially (correlation: ${corr}). Each is finding different environmental patterns in the same data. This is not necessarily wrong — different algorithm types (e.g. statistical vs. neural) naturally weight features differently.`)

  if (catA && catB && catA !== catB)
    compInsightLines.push(`${nameA} is a ${catA.replace(/_/g, ' ')} approach while ${nameB} is a ${catB.replace(/_/g, ' ')} approach — comparing them shows how the choice of method affects environmental scoring, not just the numbers.`)
  else if (catA && catA === catB)
    compInsightLines.push(`Both algorithms belong to the same category (${catA.replace(/_/g, ' ')}), so differences in their scores reflect implementation details rather than fundamentally different approaches.`)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Stat cards */}
      <div className="metrics-row">
        <div className="mcard">
          <div className="mcard-val accent">{corr}</div>
          <div className="mcard-label">Pearson correlation</div>
        </div>
        <div className="mcard">
          <div className="mcard-val" style={{ color: Math.abs(+corr) > 0.7 ? 'var(--accent)' : 'var(--amber)' }}>
            {corrStrength}
          </div>
          <div className="mcard-label">{corrDir} agreement</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{results.algo_a?.runtime?.toFixed(3) ?? '—'}s</div>
          <div className="mcard-label">Runtime — A</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{results.algo_b?.runtime?.toFixed(3) ?? '—'}s</div>
          <div className="mcard-label">Runtime — B</div>
        </div>
      </div>

      {/* Auto-generated insight */}
      <div className="panel" style={{ borderLeft: '3px solid var(--accent)', background: 'var(--surface1)' }}>
        <div className="panel-title" style={{ marginBottom: 6 }}>What the analysis shows</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7, margin: 0 }}>
          {compInsightLines.join(' ')}
        </p>
      </div>

      {/* Algorithm descriptions with category explanation */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="panel">
          <div className="panel-title" style={{ color: COLOR_A }}>A — {nameA}</div>
          <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.7, marginBottom: catA ? 8 : 0 }}>{descA}</div>
          {catA && (
            <div style={{ fontSize: 11, color: 'var(--text3)', borderTop: '1px solid var(--border)', paddingTop: 8, lineHeight: 1.6 }}>
              <span className="badge badge-gray" style={{ marginRight: 6 }}>{catA.replace(/_/g, ' ')}</span>
              {CATEGORY_DESCRIPTIONS[catA] || ''}
            </div>
          )}
        </div>
        <div className="panel">
          <div className="panel-title" style={{ color: COLOR_B }}>B — {nameB}</div>
          <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.7, marginBottom: catB ? 8 : 0 }}>{descB}</div>
          {catB && (
            <div style={{ fontSize: 11, color: 'var(--text3)', borderTop: '1px solid var(--border)', paddingTop: 8, lineHeight: 1.6 }}>
              <span className="badge badge-gray" style={{ marginRight: 6 }}>{catB.replace(/_/g, ' ')}</span>
              {CATEGORY_DESCRIPTIONS[catB] || ''}
            </div>
          )}
        </div>
      </div>

      {/* Score A vs B scatter */}
      <div className="panel">
        <div className="panel-title">Score A vs Score B — do they agree per GPS fix?</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
          Points along the diagonal = both algorithms agree. Points off the diagonal = they interpret the environment differently at that location.
          Correlation: <b style={{ color: 'var(--accent)' }}>{corr}</b> ({corrStrength} {corrDir})
        </div>
        <div style={{ position: 'relative', height: 220 }}>
          <canvas ref={scatterRef} />
        </div>
      </div>

      {/* Difference histogram */}
      <div className="panel">
        <div className="panel-title">Score difference distribution</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
          Centred at 0 = algorithms mostly agree. Spread wide = they frequently disagree on how to score the environment.
        </div>
        <div style={{ position: 'relative', height: 180 }}>
          <canvas ref={diffHistRef} />
        </div>
      </div>

    </div>
  )
}
