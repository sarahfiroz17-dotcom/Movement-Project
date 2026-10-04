import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'
import { CLUSTER_COLORS } from '../constants.js'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'

function LineChart({ id, label, data, color, yLabel, height = 160 }) {
  const ref = useRef()
  const chart = useRef()
  useEffect(() => {
    if (!ref.current) return
    if (chart.current) chart.current.destroy()
    chart.current = new Chart(ref.current, {
      type: 'line',
      data: {
        labels: data.map((_, i) => i),
        datasets: [{
          data,
          borderColor: color, borderWidth: 2,
          pointRadius: 0, tension: 0.4,
          fill: true,
          backgroundColor: color + '18',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 10 },
               title: { display: true, text: 'GPS fix index', color: TICK, font: { size: 10 } } },
          y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } },
               title: { display: true, text: yLabel, color: TICK, font: { size: 10 } } },
        },
      },
    })
    return () => { if (chart.current) chart.current.destroy() }
  }, [data, color])
  return (
    <div style={{ position: 'relative', height }}>
      <canvas ref={ref} role="img" aria-label={label} />
    </div>
  )
}

function MultiLineChart({ datasets, yLabel, height = 200 }) {
  const ref  = useRef()
  const chart = useRef()
  useEffect(() => {
    if (!ref.current) return
    if (chart.current) chart.current.destroy()
    const n = datasets[0]?.data?.length || 0
    chart.current = new Chart(ref.current, {
      type: 'line',
      data: {
        labels: Array.from({ length: n }, (_, i) => i),
        datasets: datasets.map(ds => ({
          label: ds.label, data: ds.data,
          borderColor: ds.color, borderWidth: 2,
          borderDash: ds.dashed ? [4, 3] : undefined,
          pointRadius: 0, tension: 0.4,
        })),
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 10 } },
          y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } },
               title: { display: true, text: yLabel, color: TICK, font: { size: 10 } } },
        },
      },
    })
    return () => { if (chart.current) chart.current.destroy() }
  }, [datasets])
  return (
    <div style={{ position: 'relative', height }}>
      <canvas ref={ref} role="img" aria-label="Multi-line chart" />
    </div>
  )
}

function StepHistogram({ data, label, color }) {
  const ref  = useRef()
  const chart = useRef()
  useEffect(() => {
    if (!ref.current || !data.length) return
    if (chart.current) chart.current.destroy()
    const min   = Math.min(...data)
    const max   = Math.max(...data)
    const bins  = 12
    const width = (max - min) / bins || 1
    const counts = Array(bins).fill(0)
    data.forEach(v => {
      const idx = Math.min(Math.floor((v - min) / width), bins - 1)
      counts[idx]++
    })
    const binLabels = counts.map((_, i) => (min + i * width).toFixed(1))
    chart.current = new Chart(ref.current, {
      type: 'bar',
      data: {
        labels: binLabels,
        datasets: [{ data: counts, backgroundColor: color + 'bb', borderRadius: 3, borderSkipped: false }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 }, maxTicksLimit: 8 } },
          y: { grid: { color: GRID }, ticks: { color: TICK, font: { size: 9 } } },
        },
      },
    })
    return () => { if (chart.current) chart.current.destroy() }
  }, [data, color])
  return (
    <div style={{ position: 'relative', height: 150 }}>
      <canvas ref={ref} role="img" aria-label={label} />
    </div>
  )
}

export default function TimeSeries({ results }) {
  if (results?.algo_a?.service_type === 'regression') return (
    <div className="empty-state">
      <div style={{ fontSize: 28 }}>🌍</div>
      <p style={{ maxWidth: 340, textAlign: 'center' }}>
        Time series predictions are not available for Environmental Factors — these algorithms produce a continuous environmental score per GPS fix. Check the <b>Map view</b> for the heatmap overlay.
      </p>
    </div>
  )

  if (!results) return (
    <div className="empty-state">
      <div style={{ fontSize: 32 }}>📈</div>
      <p>Run an analysis to see time series charts</p>
    </div>
  )

  const speedData      = results.speeds        || []
  const altData        = results.altitudes      || []
  const turnData       = results.turns          || []
  const stepData       = results.steps          || []
  const straightData   = results.straightness   || []

  const nameA = results.algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'A'
  const nameB = results.algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'B'
  const compareMode = results?.compareMode

  const comparisonDatasets = compareMode
    ? [
        { label: nameA, data: results.algo_a?.predictions || [], color: '#5DCAA5' },
        { label: nameB, data: results.algo_b?.predictions || [], color: '#7F77DD', dashed: true },
      ]
    : [
        { label: nameA, data: results.algo_a?.predictions || [], color: '#5DCAA5' },
      ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      <div className="panel">
        <div className="panel-title">Speed over time</div>
        <LineChart id="speed" label="Speed time series" data={speedData}
                   color="#5DCAA5" yLabel="m/s" height={170} />
      </div>

      <div className="panel">
        <div className="panel-title">Altitude over time</div>
        <LineChart id="alt" label="Altitude time series" data={altData}
                   color="#7F77DD" yLabel="metres" height={170} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="panel">
          <div className="panel-title">Turning angle over time</div>
          <LineChart id="turn" label="Turning angle series" data={turnData}
                     color="#D85A30" yLabel="degrees" height={150} />
        </div>
        <div className="panel">
          <div className="panel-title">Step length distribution</div>
          <StepHistogram data={stepData} label="Step length histogram" color="#EF9F27" />
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">
          Predicted behaviour state — {compareMode ? `${nameA} vs ${nameB}` : nameA}
          {compareMode && (
          <span style={{ display: 'flex', gap: 10 }}>
            <span className="leg-item"><div className="leg-dot" style={{ background: '#5DCAA5' }} />{nameA}</span>
            <span className="leg-item">
              <div style={{ width: 14, height: 0, borderTop: '2px dashed #7F77DD' }} />{nameB}
            </span>
          </span>
          )}
        </div>
        <MultiLineChart datasets={comparisonDatasets} yLabel="Behaviour state" height={160} />
      </div>

      <div className="panel">
        <div className="panel-title">Straightness index over time</div>
        <LineChart id="straight" label="Straightness index" data={straightData}
                   color="#378ADD" yLabel="0–1 (1=straight)" height={140} />
      </div>

    </div>
  )
}
