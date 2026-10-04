import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'
const COLOR_A = '#5DCAA5'
const COLOR_B = '#7F77DD'
const COLOR_DIFF = '#EF9F27'

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

export default function EnvScoreTime({ results }) {
  if (!results) return (
    <div className="empty-state">
      <p>Run an Environmental Factors analysis to see score over time</p>
    </div>
  )

  const scoresA = results.algo_a?.scores || []
  const scoresB = results.algo_b?.scores || []
  const nameA   = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm A'
  const nameB   = results.algo_b?.name?.replace(/^Env\s/, '') || 'Algorithm B'

  // Downsample to max 500 points for chart performance
  const MAX = 500
  const n    = scoresA.length
  const step = Math.max(1, Math.floor(n / MAX))
  const idxs = Array.from({ length: Math.ceil(n / step) }, (_, i) => i * step)
  const sampA = idxs.map(i => +(scoresA[i] ?? 0).toFixed(3))
  const sampB = idxs.map(i => +(scoresB[i] ?? 0).toFixed(3))
  const diff  = sampA.map((a, i) => +(a - sampB[i]).toFixed(3))
  const labels = idxs.map(i => i)

  // Smooth using a simple rolling average (window=5)
  const smooth = (arr, w = 5) => arr.map((_, i) => {
    const sl = arr.slice(Math.max(0, i - w), i + w + 1)
    return +(sl.reduce((a, b) => a + b, 0) / sl.length).toFixed(3)
  })

  const lineRef = useChart({
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: nameA,
          data: smooth(sampA),
          borderColor: COLOR_A, borderWidth: 2,
          pointRadius: 0, tension: 0.3,
          fill: false,
        },
        {
          label: nameB,
          data: smooth(sampB),
          borderColor: COLOR_B, borderWidth: 2,
          pointRadius: 0, tension: 0.3,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#aaa', font: { size: 11 } } } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 10 },
             title: { display: true, text: 'GPS fix index', color: TICK, font: { size: 10 } } },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: 'Environmental score', color: TICK, font: { size: 10 } },
             min: 0, max: 1 },
      },
    },
  }, [results])

  const diffRef = useChart({
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: `${nameA} − ${nameB}`,
        data: diff,
        backgroundColor: diff.map(v => v >= 0 ? COLOR_A + '99' : COLOR_B + '99'),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#aaa', font: { size: 11 } } } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 10 },
             title: { display: true, text: 'GPS fix index', color: TICK, font: { size: 10 } } },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: 'Score difference (A − B)', color: TICK, font: { size: 10 } } },
      },
    },
  }, [results])

  // Count high-disagreement points (diff > 0.2)
  const disagree = diff.filter(d => Math.abs(d) > 0.2).length
  const agreeRate = diff.length > 0 ? (((diff.length - disagree) / diff.length) * 100).toFixed(1) : null
  const compareMode = results?.compareMode

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Stat cards */}
      <div className="metrics-row">
        {compareMode ? (
          <>
            <div className="mcard">
              <div className="mcard-val accent">{agreeRate != null ? agreeRate + '%' : '—'}</div>
              <div className="mcard-label">Agreement rate</div>
            </div>
            <div className="mcard">
              <div className="mcard-val amber">{disagree.toLocaleString()}</div>
              <div className="mcard-label">High-disagreement fixes</div>
            </div>
          </>
        ) : (
          <>
            <div className="mcard">
              <div className="mcard-val accent">{results.algo_a?.runtime != null ? results.algo_a.runtime.toFixed(2) + 's' : '—'}</div>
              <div className="mcard-label">Runtime</div>
            </div>
            <div className="mcard">
              <div className="mcard-val">
                {scoresA.length > 0 ? (scoresA.reduce((s,v)=>s+v,0)/scoresA.length).toFixed(3) : '—'}
              </div>
              <div className="mcard-label">Mean score</div>
            </div>
          </>
        )}
        <div className="mcard">
          <div className="mcard-val">{n.toLocaleString()}</div>
          <div className="mcard-label">Total GPS fixes</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">
            {((results.algo_a?.runtime || 0) + (results.algo_b?.runtime || 0)).toFixed(1)}s
          </div>
          <div className="mcard-label">Total runtime</div>
        </div>
      </div>

      {/* Score over time */}
      <div className="panel">
        <div className="panel-title">Environmental score over time — {nameA} vs {nameB}</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
          Shows how each algorithm scores the environment as the animal moves along its route. Peaks = high environmental influence zones.
        </div>
        <div style={{ position: 'relative', height: 220 }}>
          <canvas ref={lineRef} />
        </div>
      </div>

      {/* Difference chart — only meaningful in compare mode */}
      {compareMode && (
      <div className="panel">
        <div className="panel-title">Score difference (A − B) — where the two algorithms disagree</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>
          Green bars = Algorithm A scores higher. Purple bars = Algorithm B scores higher. Large bars = the two algorithms interpret the environment very differently at that location.
        </div>
        <div style={{ position: 'relative', height: 180 }}>
          <canvas ref={diffRef} />
        </div>
      </div>
      )}

    </div>
  )
}
