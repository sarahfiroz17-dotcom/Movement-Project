import React, { useState, useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'
import { getHistory } from '../api.js'
import { SERVICES } from '../constants.js'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'

export default function History({ onLoad }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const chartRef  = useRef()
  const chart     = useRef()

  useEffect(() => {
    setLoading(true)
    getHistory(50)
      .then(r => setHistory(r.data))
      .catch(() => setError('Could not load history — is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!chartRef.current || history.length === 0) return
    if (chart.current) chart.current.destroy()
    const rows    = [...history].reverse()
    const labels  = rows.map((_, i) => `Run ${i + 1}`)
    // null = regression run (no F1) — Chart.js renders these as gaps in the line
    const f1aVals = rows.map(r => r.f1_a ?? null)
    const f1bVals = rows.map(r => r.f1_b ?? null)
    chart.current = new Chart(chartRef.current, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Algo A', data: f1aVals, borderColor: '#5DCAA5', borderWidth: 2,
            pointBackgroundColor: '#5DCAA5', pointRadius: 4, tension: 0.3,
            fill: true, backgroundColor: '#5DCAA512' },
          { label: 'Algo B', data: f1bVals, borderColor: '#7F77DD', borderWidth: 2,
            borderDash: [4, 3], pointBackgroundColor: '#7F77DD', pointRadius: 4, tension: 0.3 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 } } },
          y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 10 },
               callback: v => v != null ? v.toFixed(2) : '' },
               min: 0, max: 1,
               title: { display: true, text: 'Weighted F1', color: TICK, font: { size: 10 } } },
        },
      },
    })
    return () => { if (chart.current) chart.current.destroy() }
  }, [history])

  const formatDate = ts => {
    if (!ts) return ''
    try {
      const d = new Date(ts)
      const now = new Date()
      const diff = Math.floor((now - d) / 1000)
      if (diff < 60)     return 'just now'
      if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`
      if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`
      if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
    } catch { return ts }
  }

  const winner = row => {
    if (row.f1_a == null && row.f1_b == null) return '—'
    if (row.f1_a == null) return row.algo_b
    if (row.f1_b == null) return row.algo_a
    return row.f1_a >= row.f1_b ? row.algo_a : row.algo_b
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Trend chart */}
      <div className="panel">
        <div className="panel-title">
          F1 score trend — classification runs (regression runs show as gaps)
          <span style={{ display: 'flex', gap: 10 }}>
            <span className="leg-item"><div className="leg-line" style={{ background: '#5DCAA5' }} />Algo A</span>
            <span className="leg-item">
              <div style={{ width: 14, height: 0, borderTop: '2px dashed #7F77DD' }} />Algo B
            </span>
          </span>
        </div>
        {history.length === 0 && !loading ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text3)', fontSize: 13 }}>
            No runs yet — run an analysis first
          </div>
        ) : (
          <div style={{ position: 'relative', height: 180 }}>
            <canvas ref={chartRef} role="img" aria-label="F1 score trend over all runs" />
          </div>
        )}
      </div>

      {/* History table */}
      <div className="panel">
        <div className="panel-title">
          All analysis runs
          <span className="badge badge-gray">{history.length} runs</span>
        </div>

        {loading ? (
          <div className="spinner" />
        ) : error ? (
          <div style={{ color: '#f09595', fontSize: 12, padding: '16px 0', textAlign: 'center' }}>{error}</div>
        ) : history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text3)', fontSize: 13 }}>
            No history yet
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="vtable">
              <thead>
                <tr>
                  <th>Dataset</th><th>Service</th><th>Algorithm A</th><th>Algorithm B</th>
                  <th>F1 — A</th><th>F1 — B</th><th>Winner</th><th>Runtime</th><th>When</th>
                </tr>
              </thead>
              <tbody>
                {history.map(row => {
                  const w = winner(row)
                  const totalRt = ((row.runtime_a || 0) + (row.runtime_b || 0)).toFixed(1)
                  return (
                    <tr key={row.id} style={{ cursor: 'pointer' }}
                        onClick={() => {/* could load result detail */}}>
                      <td style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {row.dataset_name}
                      </td>
                      <td>
                        <span style={{ color: SERVICES[row.service_id]?.color || 'var(--text2)',
                                       fontSize: 11 }}>
                          {row.service_name}
                        </span>
                      </td>
                      <td style={{ color: 'var(--accent)', maxWidth: 120, overflow: 'hidden',
                                   textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {row.algo_a?.replace(/^(Beh|Env)\s/, '')}
                      </td>
                      <td style={{ color: 'var(--purple)', maxWidth: 120, overflow: 'hidden',
                                   textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {row.algo_b?.replace(/^(Beh|Env)\s/, '')}
                      </td>
                      <td style={{ color: 'var(--accent)' }}>
                        {row.f1_a != null ? row.f1_a.toFixed(3) : row.error_a ? '⚠' : '—'}
                      </td>
                      <td style={{ color: 'var(--purple)' }}>
                        {row.f1_b != null ? row.f1_b.toFixed(3) : row.error_b ? '⚠' : '—'}
                      </td>
                      <td>
                        {w !== '—'
                          ? <span className="pill pill-green"
                                  style={{ maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis',
                                           display: 'inline-block', whiteSpace: 'nowrap' }}>
                              {w?.replace(/^(Beh|Env)\s/, '')}
                            </span>
                          : '—'}
                      </td>
                      <td style={{ color: 'var(--text3)' }}>{totalRt}s</td>
                      <td style={{ color: 'var(--text3)', whiteSpace: 'nowrap' }}>
                        {formatDate(row.run_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  )
}