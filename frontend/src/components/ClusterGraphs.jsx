import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'
import { CLUSTER_COLORS } from '../constants.js'

function useChart(id, config, deps) {
  const ref = useRef()
  const chartRef = useRef()
  useEffect(() => {
    if (!ref.current) return
    if (chartRef.current) chartRef.current.destroy()
    chartRef.current = new Chart(ref.current, config)
    return () => { if (chartRef.current) chartRef.current.destroy() }
  }, deps)
  return ref
}

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'

function computeClusterMeans(preds, values, labelNames) {
  if (!preds.length || !values.length) return []
  const sums = {}, counts = {}
  preds.forEach((p, i) => {
    if (i >= values.length) return
    const k = labelNames?.[p] || `Cluster ${p}`
    sums[k]   = (sums[k]   || 0) + values[i]
    counts[k] = (counts[k] || 0) + 1
  })
  return Object.entries(sums).map(([k, s]) => ({ label: k, mean: s / counts[k] }))
}

function computeTurnHistogram(preds, turns, labelNames, clusterLabels, colors) {
  if (!preds.length || !turns.length) return []
  const bins = 9
  const binEdges = Array.from({ length: bins }, (_, i) => i * 20)
  const datasets = clusterLabels.map((label, ci) => {
    const counts = Array(bins).fill(0)
    preds.forEach((p, i) => {
      if (i >= turns.length) return
      const k = labelNames?.[p] || `Cluster ${p}`
      if (k !== label) return
      const bin = Math.min(Math.floor(turns[i] / 20), bins - 1)
      counts[bin]++
    })
    return {
      label,
      data: counts,
      backgroundColor: colors[ci % colors.length] + '99',
      borderColor: colors[ci % colors.length],
      borderWidth: 1,
      borderRadius: 2,
      borderSkipped: false,
    }
  })
  return { binLabels: binEdges.map(e => `${e}°`), datasets }
}

export default function ClusterGraphs({ results }) {
  if (!results) return (
    <div className="empty-state">
      <div style={{ fontSize: 32 }}>📊</div>
      <p>Run an analysis to see cluster graphs</p>
    </div>
  )

  if (results.algo_a?.service_type === 'regression') return (
    <div className="empty-state">
      <div style={{ fontSize: 28 }}>🌿</div>
      <p style={{ maxWidth: 340, textAlign: 'center' }}>
        Cluster graphs are not available for Environmental Factors — these algorithms score each GPS fix on a continuous scale rather than grouping into clusters. Check the <b>Map view</b> for the heatmap.
      </p>
    </div>
  )

  if (results.algo_a?.error || results.algo_b?.error) return (
    <div className="empty-state">
      <div style={{ fontSize: 28 }}>⚠️</div>
      <p style={{ maxWidth: 400, textAlign: 'center', fontSize: 12, color: 'var(--amber)' }}>
        {results.algo_a?.error && <><b>{results.algo_a.name}:</b> {results.algo_a.error}<br/></>}
        {results.algo_b?.error && <><b>{results.algo_b.name}:</b> {results.algo_b.error}</>}
      </p>
    </div>
  )

  const { algo_a, algo_b, label_names, compareMode } = results
  const predsA  = algo_a?.predictions || []
  const speeds  = results.speeds      || []
  const turns   = results.turns       || []
  const nameA   = algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm A'
  const nameB   = algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm B'

  const hasLabels = label_names?.length > 0
  const clusterCounts = predsA.reduce((acc, p) => {
    const k = label_names?.[p] || `Cluster ${p}`
    acc[k] = (acc[k] || 0) + 1
    return acc
  }, {})

  const allEntries = Object.entries(clusterCounts).sort((a, b) => b[1] - a[1])
  const visibleEntries = hasLabels
    ? allEntries.filter(([k]) => label_names.includes(k))
    : allEntries.slice(0, 6)

  const clusterLabels = visibleEntries.map(([k]) => k)
  const clusterVals   = visibleEntries.map(([, v]) => v)
  const totalAll      = predsA.length
  const hiddenCount   = totalAll - clusterVals.reduce((s, v) => s + v, 0)

  // Real mean speeds per cluster
  const meanSpeedData = computeClusterMeans(predsA, speeds, label_names)
  const meanSpeedOrdered = clusterLabels.map(l => {
    const entry = meanSpeedData.find(e => e.label === l)
    return entry ? +entry.mean.toFixed(3) : 0
  })

  // Turning angle histogram per cluster
  const turnHist = computeTurnHistogram(predsA, turns, label_names, clusterLabels,
    clusterLabels.map((_, i) => CLUSTER_COLORS[i % CLUSTER_COLORS.length]))

  const donutRef = useChart('donut', {
    type: 'doughnut',
    data: {
      labels: clusterLabels,
      datasets: [{ data: clusterVals,
        backgroundColor: clusterLabels.map((_, i) => CLUSTER_COLORS[i % CLUSTER_COLORS.length] + 'cc'),
        borderColor: '#13131a', borderWidth: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      cutout: '63%',
    },
  }, [results])

  const speedBarRef = useChart('speedbar', {
    type: 'bar',
    data: {
      labels: clusterLabels,
      datasets: [{
        data: meanSpeedOrdered,
        backgroundColor: clusterLabels.map((_, i) => CLUSTER_COLORS[i % CLUSTER_COLORS.length] + 'cc'),
        borderRadius: 4, borderSkipped: false,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 11 } } },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } },
             title: { display: true, text: 'm/s', color: TICK, font: { size: 10 } } },
      },
    },
  }, [results])

  const turnHistRef = useChart('turnhist', {
    type: 'bar',
    data: {
      labels: turnHist.binLabels || [],
      datasets: turnHist.datasets || [],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } },
             title: { display: true, text: 'Turning angle (degrees)', color: TICK, font: { size: 10 } },
             stacked: false },
        y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } },
             title: { display: true, text: 'GPS fixes', color: TICK, font: { size: 10 } } },
      },
    },
  }, [results])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Donut + mean speed row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="panel">
          <div className="panel-title">Cluster size distribution</div>
          <div style={{ position: 'relative', height: 180 }}>
            <canvas ref={donutRef} role="img" aria-label="Donut chart of cluster sizes" />
          </div>
          <div className="legend" style={{ marginTop: 10 }}>
            {clusterLabels.map((l, i) => (
              <div key={l} className="leg-item">
                <div className="leg-dot" style={{ background: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }} />
                {l} ({clusterVals[i].toLocaleString()})
              </div>
            ))}
            {hiddenCount > 0 && (
              <div className="leg-item" style={{ color: 'var(--text3)', fontSize: 11 }}>
                + {hiddenCount.toLocaleString()} pts in minor clusters
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">Mean speed per cluster</div>
          <div style={{ position: 'relative', height: 200 }}>
            <canvas ref={speedBarRef} role="img" aria-label="Mean speed per cluster bar chart" />
          </div>
        </div>
      </div>

      {/* Turning angle distribution */}
      <div className="panel">
        <div className="panel-title">
          Turning angle distribution per cluster
          <span style={{ display: 'flex', gap: 10 }}>
            {clusterLabels.map((l, i) => (
              <span key={l} className="leg-item">
                <div className="leg-dot" style={{ background: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }} />{l}
              </span>
            ))}
          </span>
        </div>
        <div style={{ position: 'relative', height: 200 }}>
          <canvas ref={turnHistRef} role="img" aria-label="Turning angle distribution per cluster" />
        </div>
      </div>

      {/* Comparison table */}
      <div className="panel">
        <div className="panel-title">
          Cluster metrics{compareMode ? ` — ${nameA} vs ${nameB}` : ` — ${nameA}`}
        </div>
        <table className="vtable">
          <thead>
            <tr>
              <th>Cluster</th><th>Fixes</th><th>Mean speed</th>
              <th>F1 — {nameA}</th>
              {compareMode && <th>F1 — {nameB}</th>}
              {compareMode && <th>Gap</th>}
            </tr>
          </thead>
          <tbody>
            {clusterLabels.map((label, i) => {
              const f1a = algo_a?.per_class_f1?.[label]
              const f1b = algo_b?.per_class_f1?.[label]
              const gap = compareMode && f1a != null && f1b != null ? (f1a - f1b).toFixed(3) : '—'
              return (
                <tr key={label}>
                  <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%',
                                   background: CLUSTER_COLORS[i % CLUSTER_COLORS.length],
                                   display: 'inline-block' }} />
                    {label}
                  </span></td>
                  <td>{clusterVals[i].toLocaleString()}</td>
                  <td style={{ color: 'var(--text2)' }}>
                    {meanSpeedOrdered[i] != null ? `${meanSpeedOrdered[i].toFixed(3)} m/s` : '—'}
                  </td>
                  <td style={{ color: 'var(--accent)' }}>{f1a != null ? f1a.toFixed(3) : '—'}</td>
                  {compareMode && <td style={{ color: 'var(--purple)' }}>{f1b != null ? f1b.toFixed(3) : '—'}</td>}
                  {compareMode && (
                    <td>
                      {gap !== '—'
                        ? <span className={`pill ${+gap >= 0 ? 'pill-green' : 'pill-purple'}`}>
                            {+gap >= 0 ? '+' : ''}{gap}
                          </span>
                        : '—'}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

    </div>
  )
}
