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

export default function EnvProfiles({ results }) {
  if (!results) return (
    <div className="empty-state">
      <p>Run an Environmental Factors analysis to see profiles</p>
    </div>
  )

  const scoresA = results.algo_a?.scores || []
  const scoresB = results.algo_b?.scores || []
  const nameA   = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm A'
  const nameB   = results.algo_b?.name?.replace(/^Env\s/, '') || 'Algorithm B'
  const compareMode = results?.compareMode

  // Build histogram bins (20 buckets 0–1)
  const BINS = 20
  const binsA = new Array(BINS).fill(0)
  const binsB = new Array(BINS).fill(0)
  scoresA.forEach(v => { binsA[Math.min(Math.floor(v * BINS), BINS - 1)]++ })
  scoresB.forEach(v => { binsB[Math.min(Math.floor(v * BINS), BINS - 1)]++ })
  const binLabels = Array.from({ length: BINS }, (_, i) => (i / BINS).toFixed(2))

  const histRef = useChart({
    type: 'bar',
    data: {
      labels: binLabels,
      datasets: [
        { label: nameA, data: binsA, backgroundColor: COLOR_A + 'aa', borderRadius: 2 },
        { label: nameB, data: binsB, backgroundColor: COLOR_B + 'aa', borderRadius: 2 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#aaa', font: { size: 11 } } } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 10 },
             title: { display: true, text: 'Normalised score (0 = low, 1 = high)', color: TICK, font: { size: 10 } } },
        y: {
          type: 'logarithmic',
          grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
          title: { display: true, text: 'Number of GPS fixes (log scale)', color: TICK, font: { size: 10 } },
        },
      },
    },
  }, [results])

  // Score vs altitude scatter — sample every Nth point for performance
  const n = scoresA.length
  const lats = results.lats || []
  const step = Math.max(1, Math.floor(n / 300))
  const scatterA = [], scatterB = []
  for (let i = 0; i < n; i += step) {
    // Use lat as a proxy for position (north = higher lat = different terrain)
    const latVal = lats[i] ?? i / n
    scatterA.push({ x: +latVal.toFixed(4), y: +(scoresA[i] ?? 0).toFixed(3) })
    if (scoresB[i] != null) scatterB.push({ x: +latVal.toFixed(4), y: +(scoresB[i]).toFixed(3) })
  }

  const scatterRef = useChart({
    type: 'scatter',
    data: {
      datasets: [
        { label: nameA, data: scatterA, backgroundColor: COLOR_A + '99', pointRadius: 3 },
        ...(compareMode ? [{ label: nameB, data: scatterB, backgroundColor: COLOR_B + '99', pointRadius: 3 }] : []),
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#aaa', font: { size: 11 } } } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } },
             title: { display: true, text: 'Latitude', color: TICK, font: { size: 10 } } },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: 'Environmental score', color: TICK, font: { size: 10 } } },
      },
    },
  }, [results])

  // Summary stats — avoid Math.min/max spread which stack-overflows on 20k items
  const stats = (scores) => {
    if (!scores.length) return { mean: '—', std: '—', min: '—', max: '—' }
    let sum = 0, mn = scores[0], mx = scores[0]
    for (let i = 0; i < scores.length; i++) {
      sum += scores[i]
      if (scores[i] < mn) mn = scores[i]
      if (scores[i] > mx) mx = scores[i]
    }
    const mean = sum / scores.length
    let variance = 0
    for (let i = 0; i < scores.length; i++) variance += (scores[i] - mean) ** 2
    const std = Math.sqrt(variance / scores.length)
    return {
      mean: mean.toFixed(3),
      std:  std.toFixed(3),
      min:  mn.toFixed(3),
      max:  mx.toFixed(3),
    }
  }
  const sA = stats(scoresA)
  const sB = stats(scoresB)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Stat cards */}
      <div className="metrics-row">
        {compareMode ? (
          <>
            <div className="mcard" key="ma"><div className="mcard-val" style={{ color: 'var(--accent)' }}>{sA.mean}</div><div className="mcard-label">Mean score — A</div></div>
            <div className="mcard" key="sa"><div className="mcard-val" style={{ color: 'var(--accent)' }}>{sA.std}</div><div className="mcard-label">Std dev — A</div></div>
            <div className="mcard" key="mb"><div className="mcard-val" style={{ color: 'var(--purple)' }}>{sB.mean}</div><div className="mcard-label">Mean score — B</div></div>
            <div className="mcard" key="sb"><div className="mcard-val" style={{ color: 'var(--purple)' }}>{sB.std}</div><div className="mcard-label">Std dev — B</div></div>
          </>
        ) : (
          <>
            <div className="mcard" key="ma"><div className="mcard-val accent">{sA.mean}</div><div className="mcard-label">Mean score</div></div>
            <div className="mcard" key="sa"><div className="mcard-val">{sA.std}</div><div className="mcard-label">Std deviation</div></div>
            <div className="mcard" key="mna"><div className="mcard-val">{sA.min}</div><div className="mcard-label">Min score</div></div>
            <div className="mcard" key="mxa"><div className="mcard-val">{sA.max}</div><div className="mcard-label">Max score</div></div>
          </>
        )}
      </div>

      {/* Score distribution histogram */}
      <div className="panel">
        <div className="panel-title">Score distribution — how scores are spread across all GPS fixes</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
          A tall bar at the left means most fixes have low environmental scores; at the right means most are high.
        </div>
        <div style={{ position: 'relative', height: 200 }}>
          <canvas ref={histRef} />
        </div>
      </div>

      {/* Score vs latitude scatter */}
      <div className="panel">
        <div className="panel-title">Score vs latitude — how environment changes across the route</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
          Each dot is one GPS fix. Upward trend = higher-latitude locations have higher environmental scores.
        </div>
        <div style={{ position: 'relative', height: 220 }}>
          <canvas ref={scatterRef} />
        </div>
      </div>

      {/* Min/max table */}
      <div className="panel">
        <div className="panel-title">Score range summary</div>
        <table className="vtable">
          <thead>
            <tr>
              <th>Metric</th>
              <th style={{ color: 'var(--accent)' }}>{nameA}</th>
              {compareMode && <th style={{ color: 'var(--purple)' }}>{nameB}</th>}
            </tr>
          </thead>
          <tbody>
            {[['Mean', sA.mean, sB.mean], ['Std dev', sA.std, sB.std],
              ['Min', sA.min, sB.min], ['Max', sA.max, sB.max]].map(([m, a, b]) => (
              <tr key={m}>
                <td>{m}</td>
                <td style={{ color: 'var(--accent)' }}>{a}</td>
                {compareMode && <td style={{ color: 'var(--purple)' }}>{b}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  )
}
