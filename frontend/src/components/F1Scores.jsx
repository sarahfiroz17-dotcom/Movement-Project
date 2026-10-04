import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'

export default function F1Scores({ results }) {
  const barRef    = useRef()
  const radarRef  = useRef()
  const barChart  = useRef()
  const radarChart = useRef()

  if (results?.algo_a?.service_type === 'regression') return (
    <div className="empty-state">
      <div style={{ fontSize: 28 }}>📈</div>
      <p style={{ maxWidth: 340, textAlign: 'center' }}>
        F1 scores are not applicable for Environmental Factors — these algorithms output continuous scores, not behaviour labels. Check the <b>Map view</b> to see the heatmap.
      </p>
    </div>
  )

  useEffect(() => {
    if (!results) return
    const { algo_a, algo_b, label_names, compareMode } = results
    const classes  = label_names?.length
      ? label_names
      : Object.keys(algo_a?.per_class_f1 || {})
    const nameA = algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'A'
    const nameB = algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'B'

    const f1aVals = classes.map(c => algo_a?.per_class_f1?.[c] ?? null)
    const f1bVals = classes.map(c => algo_b?.per_class_f1?.[c] ?? null)

    // Grouped bar
    if (barRef.current) {
      if (barChart.current) barChart.current.destroy()
      barChart.current = new Chart(barRef.current, {
        type: 'bar',
        data: {
          labels: classes,
          datasets: [
            { label: nameA, data: f1aVals, backgroundColor: '#1D9E75cc',
              borderRadius: 3, borderSkipped: false },
            ...(compareMode ? [{ label: nameB, data: f1bVals, backgroundColor: '#7F77DD99',
              borderRadius: 3, borderSkipped: false }] : []),
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } } },
            y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 },
                 callback: v => v != null ? v.toFixed(2) : '' }, min: 0, max: 1 },
          },
        },
      })
    }

    // Radar for algo_a — precision / recall / f1 per class
    if (radarRef.current && classes.length >= 3) {
      if (radarChart.current) radarChart.current.destroy()
      radarChart.current = new Chart(radarRef.current, {
        type: 'radar',
        data: {
          labels: classes,
          datasets: [
            { label: 'Precision', data: classes.map(() => algo_a?.precision ?? 0),
              borderColor: '#5DCAA5', backgroundColor: '#5DCAA522',
              pointBackgroundColor: '#5DCAA5', borderWidth: 2, pointRadius: 3 },
            { label: 'Recall', data: classes.map(() => algo_a?.recall ?? 0),
              borderColor: '#EF9F27', backgroundColor: '#EF9F2722',
              pointBackgroundColor: '#EF9F27', borderWidth: 2, pointRadius: 3 },
            { label: 'F1', data: f1aVals.map(v => v ?? 0),
              borderColor: '#7F77DD', backgroundColor: '#7F77DD22',
              pointBackgroundColor: '#7F77DD', borderWidth: 2, pointRadius: 3 },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            r: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 },
                 backdropColor: 'transparent', stepSize: 0.2 },
                 pointLabels: { color: '#9a9ab0', font: { size: 10 } },
                 min: 0, max: 1 },
          },
        },
      })
    }

    return () => {
      barChart.current?.destroy()
      radarChart.current?.destroy()
    }
  }, [results])

  if (!results) return (
    <div className="empty-state">
      <div style={{ fontSize: 32 }}>🎯</div>
      <p>Run an analysis to see F1 scores</p>
    </div>
  )

  const { algo_a, algo_b, label_names, compareMode } = results
  const nameA   = algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm A'
  const nameB   = algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm B'
  const classes = label_names?.length
    ? label_names
    : Object.keys(algo_a?.per_class_f1 || {})

  const winnerA = (algo_a?.f1 ?? 0) >= (algo_b?.f1 ?? 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Summary cards */}
      <div className="metrics-row">
        <div className="mcard">
          <div className="mcard-val accent">{algo_a?.f1 != null ? algo_a.f1.toFixed(3) : '—'}</div>
          <div className="mcard-label">{nameA} — weighted F1</div>
        </div>
        {compareMode && (
        <div className="mcard">
          <div className="mcard-val purple">{algo_b?.f1 != null ? algo_b.f1.toFixed(3) : '—'}</div>
          <div className="mcard-label">{nameB} — weighted F1</div>
        </div>
        )}
        {compareMode && (
        <div className="mcard">
          <div className="mcard-val amber">
            {algo_a?.f1 != null && algo_b?.f1 != null
              ? '+' + Math.abs(algo_a.f1 - algo_b.f1).toFixed(3)
              : '—'}
          </div>
          <div className="mcard-label">F1 gap</div>
        </div>
        )}
        <div className="mcard">
          <div className="mcard-val">{(winnerA ? algo_a?.accuracy : algo_b?.accuracy)?.toFixed(3) ?? '—'}</div>
          <div className="mcard-label">{compareMode ? 'Best accuracy' : 'Accuracy'}</div>
        </div>
      </div>

      {/* Side-by-side result cards — compare mode only */}
      {compareMode && (
      <div className="compare-grid">
        <div className={`result-card${winnerA ? ' winner' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div className="result-name">{nameA}</div>
            {winnerA && <div className="winner-badge">Best model</div>}
          </div>
          {[['F1 score', algo_a?.f1, '#1D9E75'],
            ['Accuracy', algo_a?.accuracy, '#1D9E75'],
            ['Precision', algo_a?.precision, '#5DCAA5'],
            ['Recall', algo_a?.recall, '#5DCAA5'],
            ['Runtime', algo_a?.runtime ? algo_a.runtime / 30 : null, '#2a4a3a', `${algo_a?.runtime}s`]
          ].map(([lbl, val, color, override]) => (
            <div key={lbl} className="score-row">
              <span className="score-lbl">{lbl}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${((val || 0) * 100)}%`, background: color }} />
              </div>
              <span className="score-num">{override || (val != null ? val.toFixed(2) : '—')}</span>
            </div>
          ))}
          {/* Per-class breakdown */}
          {Object.keys(algo_a?.per_class_f1 || {}).length > 0 && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 6 }}>Per-class F1</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {Object.entries(algo_a.per_class_f1).map(([cls, val]) => (
                  <div key={cls} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: 'var(--text3)' }}>{cls}</div>
                    <div style={{ fontSize: 12, color: 'var(--accent)' }}>{val?.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className={`result-card${!winnerA ? ' winner' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div className="result-name">{nameB}</div>
            {!winnerA && <div className="winner-badge">Best model</div>}
          </div>
          {[['F1 score', algo_b?.f1, '#534AB7'],
            ['Accuracy', algo_b?.accuracy, '#534AB7'],
            ['Precision', algo_b?.precision, '#7F77DD'],
            ['Recall', algo_b?.recall, '#7F77DD'],
            ['Runtime', algo_b?.runtime ? algo_b.runtime / 30 : null, '#2a2a3e', `${algo_b?.runtime}s`]
          ].map(([lbl, val, color, override]) => (
            <div key={lbl} className="score-row">
              <span className="score-lbl">{lbl}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${((val || 0) * 100)}%`, background: color }} />
              </div>
              <span className="score-num">{override || (val != null ? val.toFixed(2) : '—')}</span>
            </div>
          ))}
          {Object.keys(algo_b?.per_class_f1 || {}).length > 0 && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 6 }}>Per-class F1</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {Object.entries(algo_b.per_class_f1).map(([cls, val]) => (
                  <div key={cls} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: 'var(--text3)' }}>{cls}</div>
                    <div style={{ fontSize: 12, color: 'var(--purple)' }}>{val?.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      )}

      {/* Bar chart + radar */}
      <div className="compare-grid">
        <div className="panel">
          <div className="panel-title">
            Per-class F1 comparison
            <span style={{ display: 'flex', gap: 10 }}>
              <span className="leg-item"><div className="leg-dot" style={{ background: '#1D9E75' }} />{nameA}</span>
              <span className="leg-item"><div className="leg-dot" style={{ background: '#7F77DD' }} />{nameB}</span>
            </span>
          </div>
          <div style={{ position: 'relative', height: 220 }}>
            <canvas ref={barRef} role="img" aria-label="Grouped bar chart of F1 per class" />
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">
            Precision · Recall · F1 — {nameA}
            <span style={{ display: 'flex', gap: 8 }}>
              <span className="leg-item"><div className="leg-dot" style={{ background: '#5DCAA5' }} />P</span>
              <span className="leg-item"><div className="leg-dot" style={{ background: '#EF9F27' }} />R</span>
              <span className="leg-item"><div className="leg-dot" style={{ background: '#7F77DD' }} />F1</span>
            </span>
          </div>
          <div style={{ position: 'relative', height: 220 }}>
            <canvas ref={radarRef} role="img" aria-label="Radar chart of precision recall F1" />
          </div>
        </div>
      </div>

      {/* Full table */}
      <div className="panel">
        <div className="panel-title">Full metrics table</div>
        <table className="vtable">
          <thead>
            <tr><th>Algorithm</th><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Status</th></tr>
          </thead>
          <tbody>
            {[{ algo: algo_a, name: nameA, color: 'var(--accent)', pillClass: 'pill-green' },
              ...(compareMode ? [{ algo: algo_b, name: nameB, color: 'var(--purple)', pillClass: 'pill-purple' }] : [])]
              .flatMap(({ algo, name, color, pillClass }) =>
                classes.map(cls => {
                  const f1 = algo?.per_class_f1?.[cls]
                  return (
                    <tr key={name + cls}>
                      <td style={{ color }}>{name}</td>
                      <td>{cls}</td>
                      <td>{algo?.precision?.toFixed(3) ?? '—'}</td>
                      <td>{algo?.recall?.toFixed(3) ?? '—'}</td>
                      <td style={{ color }}>{f1?.toFixed(3) ?? '—'}</td>
                      <td>
                        {f1 != null && f1 >= 0.8
                          ? <span className={`pill ${pillClass}`}>Good</span>
                          : f1 != null
                          ? <span className="pill" style={{ background: 'var(--surface2)', color: 'var(--text3)' }}>Low</span>
                          : '—'}
                      </td>
                    </tr>
                  )
                })
              )}
          </tbody>
        </table>
      </div>

    </div>
  )
}