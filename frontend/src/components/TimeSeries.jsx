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

  const speedData      = (results.speeds        || []).filter(v => v != null)
  const altData        = (results.altitudes      || []).filter(v => v != null)
  const turnData       = (results.turns          || []).filter(v => v != null)
  const stepData       = (results.steps          || []).filter(v => v != null)
  const straightData   = (results.straightness   || []).filter(v => v != null)

  const nameA = results.algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'A'
  const nameB = results.algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'B'
  const compareMode = results?.compareMode

  
  const tsInsightLines = []
  if (speedData.length > 0) {
    const meanSpeed = speedData.reduce((s, v) => s + v, 0) / speedData.length
    const stdSpeed  = Math.sqrt(speedData.reduce((s, v) => s + (v - meanSpeed) ** 2, 0) / speedData.length)
    if (meanSpeed < 0.2)
      tsInsightLines.push(`Average movement speed is very low (${meanSpeed.toFixed(2)} m/s), consistent with an animal that spends most time stationary or foraging slowly.`)
    else if (meanSpeed < 1.0)
      tsInsightLines.push(`Average movement speed is ${meanSpeed.toFixed(2)} m/s — typical of walking or exploratory movement. The animal is active but not in sustained travel.`)
    else
      tsInsightLines.push(`Average movement speed is high (${meanSpeed.toFixed(2)} m/s), indicating active, purposeful travel or migration for much of the recorded period.`)
    if (stdSpeed > 0.5 * meanSpeed)
      tsInsightLines.push(`Speed varies considerably (std dev: ${stdSpeed.toFixed(2)} m/s), suggesting the animal alternates between resting and active movement phases — watch for step changes in the speed chart.`)
  }
  if (straightData.length > 0) {
    const meanStraight = straightData.reduce((s, v) => s + v, 0) / straightData.length
    if (meanStraight > 0.7)
      tsInsightLines.push(`The straightness index is high (mean: ${meanStraight.toFixed(2)}), meaning the animal moves in relatively direct paths — this is typical of directed travel or migration.`)
    else if (meanStraight < 0.35)
      tsInsightLines.push(`The straightness index is low (mean: ${meanStraight.toFixed(2)}), meaning movement is tortuous and winding — typical of foraging, searching, or territorial patrol.`)
  }
  if (compareMode) {
    const predsA = (results.algo_a?.predictions || []).filter(v => v != null)
    const predsB = (results.algo_b?.predictions || []).filter(v => v != null)
    const n = Math.min(predsA.length, predsB.length)
    if (n > 0) {
      const agree = predsA.slice(0, n).filter((v, i) => v === predsB[i]).length
      const pct = Math.round(agree / n * 100)
      tsInsightLines.push(`The two algorithms assign the same behaviour label for ${pct}% of GPS fixes in the time series. Sections where the lines diverge are where they disagree on which behaviour is occurring.`)
    }
  }

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

      
      {tsInsightLines.length > 0 && (
        <div className="panel" style={{ borderLeft: '3px solid var(--accent)', background: 'var(--surface1)' }}>
          <div className="panel-title" style={{ marginBottom: 6 }}>What the analysis shows</div>
          <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7, margin: 0 }}>
            {tsInsightLines.join(' ')}
          </p>
        </div>
      )}

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
