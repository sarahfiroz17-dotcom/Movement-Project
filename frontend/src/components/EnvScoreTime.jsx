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

  const scoresA = (results.algo_a?.scores || []).filter(v => v != null)
  const scoresB = (results.algo_b?.scores || []).filter(v => v != null)
  const nameA   = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm A'
  const nameB   = results.algo_b?.name?.replace(/^Env\s/, '') || 'Algorithm B'

  // Build cumulative distance axis from steps array (same sampling as scores)
  const stepsRaw = results.steps || []
  const MAX = 500
  const n    = scoresA.length
  const step = Math.max(1, Math.floor(n / MAX))
  const idxs = Array.from({ length: Math.ceil(n / step) }, (_, i) => i * step)
  const sampA = idxs.map(i => +(scoresA[i] ?? 0).toFixed(3))
  const sampB = idxs.map(i => +(scoresB[i] ?? 0).toFixed(3))
  const diff  = sampA.map((a, i) => +(a - sampB[i]).toFixed(3))

  // Cumulative distance label: accumulate step lengths up to each sampled index
  const useDistance = stepsRaw.length > 0
  let cumDist = []
  if (useDistance) {
    let acc = 0
    const cumAll = stepsRaw.map(s => { acc += (s || 0); return acc })
    cumDist = idxs.map(i => Math.round(cumAll[Math.min(i, cumAll.length - 1)]))
  }
  const labels = useDistance ? cumDist : idxs.map(i => i)
  const xLabel = useDistance ? 'Distance along track (m)' : 'GPS fix index'

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
             title: { display: true, text: xLabel, color: TICK, font: { size: 10 } } },
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
             title: { display: true, text: xLabel, color: TICK, font: { size: 10 } } },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: 'Score difference (A − B)', color: TICK, font: { size: 10 } } },
      },
    },
  }, [results])

  // Count high-disagreement points (diff > 0.2)
  const disagree = diff.filter(d => Math.abs(d) > 0.2).length
  const agreeRate = diff.length > 0 ? (((diff.length - disagree) / diff.length) * 100).toFixed(1) : null
  const compareMode = results?.compareMode

  // Auto-generated insight
  const insightLines = []
  if (compareMode) {
    const agreeNum = parseFloat(agreeRate)
    if (!isNaN(agreeNum)) {
      if (agreeNum > 90)
        insightLines.push(`The two algorithms agree on ${agreeRate}% of GPS fixes — their scores track closely along the route, meaning both are picking up the same environmental patterns.`)
      else if (agreeNum > 70)
        insightLines.push(`The algorithms agree on ${agreeRate}% of fixes. They mostly track together but diverge at certain points — the difference chart below shows exactly where.`)
      else
        insightLines.push(`The algorithms only agree on ${agreeRate}% of fixes, meaning they interpret the environment quite differently along this route. This is worth investigating — two algorithms sensing the same environment but reaching different conclusions could mean one is more suited to this habitat type.`)
    }
    if (disagree > 0) {
      insightLines.push(`There are ${disagree.toLocaleString()} GPS fixes where they disagree significantly (score gap > 0.2). Look for clusters of orange/purple bars in the difference chart to find those locations.`)
    }
  } else {
    const vals = sampA.filter(v => !isNaN(v))
    const meanA = vals.length > 0 ? vals.reduce((s,v)=>s+v,0)/vals.length : null
    const stdA  = vals.length > 1
      ? Math.sqrt(vals.reduce((s,v)=>s+(v-meanA)**2,0)/vals.length)
      : null

    insightLines.push(`The line shows how environmental influence changes as the animal moves along the route. Peaks mean the animal entered a zone with stronger environmental signals — a habitat edge, terrain change, or burst of energy use.`)

    if (stdA != null) {
      if (stdA > 0.2)
        insightLines.push(`There are large swings in the score (variability: ${stdA.toFixed(3)}), meaning the route passes through noticeably different environmental conditions at different points.`)
      else if (stdA < 0.07)
        insightLines.push(`The score stays relatively flat (variability: ${stdA.toFixed(3)}), suggesting the environment is consistent throughout — no dramatic habitat changes along this route.`)
    }
  }

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

      {/* Auto-generated insight */}
      <div className="panel" style={{ borderLeft: '3px solid var(--accent)', background: 'var(--surface1)' }}>
        <div className="panel-title" style={{ marginBottom: 6 }}>What the analysis shows</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7, margin: 0 }}>
          {insightLines.join(' ')}
        </p>
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
