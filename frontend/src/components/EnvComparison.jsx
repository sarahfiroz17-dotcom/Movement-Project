import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'
const COLOR_A = '#5DCAA5'
const COLOR_B = '#7F77DD'

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

export default function EnvComparison({ results }) {
  if (!results) return (
    <div className="empty-state">
      <p>Run an Environmental Factors analysis to compare algorithms</p>
    </div>
  )

  const scoresA = results.algo_a?.scores || []
  const scoresB = results.algo_b?.scores || []
  const nameA   = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm A'
  const nameB   = results.algo_b?.name?.replace(/^Env\s/, '') || 'Algorithm B'
  const descA   = results.algo_a?.score_label || ''
  const descB   = results.algo_b?.score_label || ''

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

      {/* Algorithm descriptions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="panel">
          <div className="panel-title" style={{ color: COLOR_A }}>A — {nameA}</div>
          <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.6 }}>{descA}</div>
        </div>
        <div className="panel">
          <div className="panel-title" style={{ color: COLOR_B }}>B — {nameB}</div>
          <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.6 }}>{descB}</div>
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
