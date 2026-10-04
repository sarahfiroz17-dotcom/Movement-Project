import React, { useEffect, useRef, useMemo } from 'react'
import { Chart } from 'chart.js/auto'
import { FEATURE_NAMES } from '../constants.js'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'

const IMPORTANCE_COLORS = [
  '#1D9E75', '#5DCAA5', '#5DCAA590',
  '#7F77DD', '#7F77DD90', '#EF9F27',
  '#EF9F2790', '#D85A30',
]

export default function FeatureImportance({ results }) {
  const hbarRef   = useRef()
  const hbarChart = useRef()

  const isRegression = results?.algo_a?.service_type === 'regression'
  const importancesRaw = results?.algo_a?.feature_importances || {}
  const hasImportances = Object.keys(importancesRaw).length > 0

  const ranked = useMemo(() => {
    return FEATURE_NAMES
      .map(name => ({ name, value: importancesRaw[name] ?? 0 }))
      .sort((a, b) => b.value - a.value)
  }, [results])

  useEffect(() => {
    if (!hbarRef.current || !hasImportances) return
    if (hbarChart.current) hbarChart.current.destroy()
    hbarChart.current = new Chart(hbarRef.current, {
      type: 'bar',
      data: {
        labels: ranked.map(r => r.name),
        datasets: [{
          data: ranked.map(r => r.value),
          backgroundColor: ranked.map((_, i) => IMPORTANCE_COLORS[i % IMPORTANCE_COLORS.length]),
          borderRadius: 3, borderSkipped: false,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 },
               callback: v => v.toFixed(3) } },
          y: { grid: { color: 'transparent' }, ticks: { color: TICK, font: { size: 10 } } },
        },
      },
    })
    return () => { hbarChart.current?.destroy() }
  }, [results])

  if (!results) return (
    <div className="empty-state">
      <div style={{ fontSize: 32 }}>🎯</div>
      <p>Run an analysis to see feature importances</p>
    </div>
  )

  if (isRegression || !hasImportances) return (
    <div className="empty-state">
      <div style={{ fontSize: 28 }}>🌿</div>
      <p style={{ maxWidth: 360, textAlign: 'center' }}>
        {isRegression
          ? 'Feature importance is not available for Environmental Factors (regression service).'
          : 'Feature importance was not computed for this run.'}
      </p>
    </div>
  )

  const maxVal = ranked[0]?.value || 1

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>

        {/* Ranked list */}
        <div className="panel">
          <div className="panel-title">
            Feature importance ranking
            <span className="badge badge-gray">permutation</span>
          </div>
          <div>
            {ranked.map((r, i) => (
              <div key={r.name} className="fi-row">
                <div className="fi-num">{i + 1}</div>
                <div className="fi-name">{r.name}</div>
                <div className="fi-bar">
                  <div className="fi-fill"
                       style={{ width: `${(r.value / maxVal * 100).toFixed(1)}%`,
                                background: IMPORTANCE_COLORS[i % IMPORTANCE_COLORS.length] }} />
                </div>
                <div className="fi-val">{r.value.toFixed(4)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Horizontal bar chart */}
        <div className="panel">
          <div className="panel-title">Feature importance chart</div>
          <div style={{ position: 'relative', height: 300 }}>
            <canvas ref={hbarRef} role="img" aria-label="Horizontal bar chart of feature importances" />
          </div>
        </div>
      </div>

      {/* Top-3 insight cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        {ranked.slice(0, 3).map((r, i) => (
          <div key={r.name} className="panel" style={{ padding: 12 }}>
            <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 4 }}>
              #{i + 1} most important
            </div>
            <div style={{ fontSize: 14, fontWeight: 500, color: IMPORTANCE_COLORS[i], marginBottom: 4 }}>
              {r.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text3)' }}>
              Importance score: {r.value.toFixed(4)}
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}
