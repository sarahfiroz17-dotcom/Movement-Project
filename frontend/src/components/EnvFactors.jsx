import React, { useEffect, useRef } from 'react'
import { Chart } from 'chart.js/auto'

const GRID = '#1e1e2e'
const TICK = '#4a4a6a'

const STAGE_COLORS = ['#378ADD', '#5DCAA5', '#EF9F27', '#D85A30']

// Canvas-drawn stage ribbon — no Chart.js, full control over height + labels
function StageRibbon({ stages, labelNames }) {
  const canvasRef = useRef()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !stages.length) return
    const ctx   = canvas.getContext('2d')
    const W     = canvas.offsetWidth || 900
    const H     = 40
    canvas.width  = W
    canvas.height = H

    ctx.clearRect(0, 0, W, H)

    const n       = stages.length
    const cellW   = W / n

    // Draw each stage cell as a filled rectangle
    stages.forEach((s, i) => {
      const color = STAGE_COLORS[s % STAGE_COLORS.length]
      ctx.fillStyle = color
      ctx.fillRect(Math.floor(i * cellW), 0, Math.ceil(cellW) + 1, H)
    })

    // Detect transitions and label each run of the same stage
    let runStart = 0
    for (let i = 1; i <= n; i++) {
      if (i === n || stages[i] !== stages[runStart]) {
        const runLen  = i - runStart
        const midPx   = (runStart + runLen / 2) * cellW
        const s       = stages[runStart]
        const label   = labelNames[s] || `Stage ${s}`

        // Only draw label if the run is wide enough to hold it
        const minWidth = label.length * 6 + 12
        if (runLen * cellW >= minWidth) {
          ctx.font      = 'bold 10px system-ui, sans-serif'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          // Dark shadow for readability on any colour
          ctx.fillStyle = 'rgba(0,0,0,0.55)'
          ctx.fillText(label, midPx + 1, H / 2 + 1)
          ctx.fillStyle = '#fff'
          ctx.fillText(label, midPx, H / 2)
        }
        runStart = i
      }
    }
  }, [stages, labelNames])

  return <canvas ref={canvasRef} style={{ width: '100%', height: 40, display: 'block', borderRadius: 4 }} />
}

// 3 thematic groups — indices into the 12-factor array
const GROUPS = [
  {
    label: 'Terrain',
    color: '#EF9F27',
    indices: [0, 1, 9, 10],   // terrain_ruggedness, slope, elevation_gradient, habitat_boundary
  },
  {
    label: 'Climate & Habitat',
    color: '#5DCAA5',
    indices: [2, 3, 5, 7],    // ndvi_proxy, land_cover, temperature_proxy, solar_radiation
  },
  {
    label: 'Animal Activity',
    color: '#378ADD',
    indices: [4, 6, 8, 11],   // wind_proxy, proximity_water, resource_score, energy_expenditure
  },
]

function useChart(config, deps) {
  const ref  = useRef()
  const inst = useRef()
  useEffect(() => {
    if (!ref.current) return
    if (inst.current) inst.current.destroy()
    inst.current = new Chart(ref.current, config)
    return () => { if (inst.current) inst.current.destroy() }
  }, deps)
  return ref
}

// One horizontal bar chart for a group of 4 factors
function GroupBar({ group, factorNames, perFactor }) {
  const means = group.indices.map(fi => {
    const col = perFactor[fi]
    return +(col.reduce((s, v) => s + v, 0) / (col.length || 1)).toFixed(3)
  })
  const labels = group.indices.map(fi =>
    (factorNames[fi] || '').replace(/_/g, ' ')
  )

  const ref = useChart({
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: group.label,
        data: means,
        backgroundColor: group.color + 'cc',
        borderColor: group.color,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` Intensity: ${ctx.raw}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: GRID },
          ticks: { color: TICK, font: { size: 10 } },
          title: { display: true, text: 'Mean intensity (0–1)', color: TICK, font: { size: 10 } },
          min: 0, max: 1,
        },
        y: {
          grid: { display: false },
          ticks: { color: '#ccc', font: { size: 11 } },
        },
      },
    },
  }, [perFactor])

  return (
    <div className="panel" style={{ flex: 1 }}>
      <div className="panel-title" style={{ color: group.color }}>{group.label}</div>
      <div style={{ position: 'relative', height: 160 }}>
        <canvas ref={ref} />
      </div>
    </div>
  )
}

// ── Auto-generated plain-English insight ─────────────────────────────────────
function generateInsight({ factorMeans, stageCounts, labelNames, n }) {
  const top    = factorMeans[0]
  const second = factorMeans[1]
  const sentences = []

  // 1. Top factor — use relative gap between top and bottom to assess concentration
  const FACTOR_PLAIN = {
    terrain_ruggedness: 'uneven, hilly terrain',
    slope:              'steep slopes',
    ndvi_proxy:         'vegetation density — greener, lusher areas',
    land_cover:         'the type of land surface (open ground vs. forest or scrub)',
    wind_proxy:         'wind exposure',
    temperature_proxy:  'temperature variation along the route',
    proximity_water:    'closeness to water sources',
    solar_radiation:    'solar energy and sun exposure',
    resource_score:     'food and resource availability',
    elevation_gradient: 'active climbing or descending',
    habitat_boundary:   'crossing between different habitat types',
    energy_expenditure: 'energy cost of movement',
  }

  const topMean    = top?.mean ?? 0
  const bottomMean = factorMeans[factorMeans.length - 1]?.mean ?? 0
  const gap        = topMean - bottomMean

  if (top) {
    const plain = FACTOR_PLAIN[top.name] || top.name.replace(/_/g, ' ')
    if (gap > 0.15) {
      sentences.push(`The standout factor for this route is ${top.name.replace(/_/g, ' ')} — it scores noticeably higher than the others, meaning the animal's movement is closely tied to ${plain}.`)
    } else if (gap > 0.05) {
      sentences.push(`${top.name.replace(/_/g, ' ')} comes out on top, but the difference between factors is modest — several environmental signals are active at once rather than one dominating.`)
    } else {
      sentences.push(`All 12 environmental factors score similarly, which typically means the habitat is uniform — no single terrain type, vegetation change, or weather pattern stands out along this route.`)
    }
    if (second && second.mean > 0.05 && gap > 0.05) {
      const plain2 = FACTOR_PLAIN[second.name] || second.name.replace(/_/g, ' ')
      sentences.push(`${second.name.replace(/_/g, ' ')} is the next strongest signal, suggesting ${plain2} also shapes where and how the animal moves.`)
    }
  }

  // 2. Terrain group check — compare terrain to non-terrain average
  const terrainNames = ['terrain_ruggedness', 'slope', 'elevation_gradient']
  const terrainMeans = factorMeans.filter(f => terrainNames.includes(f.name)).map(f => f.mean)
  const nonTerrainMeans = factorMeans.filter(f => !terrainNames.includes(f.name)).map(f => f.mean)
  const avgTerrain    = terrainMeans.reduce((s, v) => s + v, 0) / (terrainMeans.length || 1)
  const avgNonTerrain = nonTerrainMeans.reduce((s, v) => s + v, 0) / (nonTerrainMeans.length || 1)

  if (avgTerrain < avgNonTerrain * 0.5) {
    sentences.push(`Terrain factors (ruggedness, slope, elevation) are well below the other signals, suggesting relatively flat or uniform ground — the animal is not navigating significant hills.`)
  } else if (avgTerrain > avgNonTerrain * 1.5) {
    sentences.push(`Terrain factors score higher than most other signals, suggesting the landscape shape is a key driver — the animal is actively responding to hills, slopes, or elevation changes.`)
  }

  // 4. Dominant movement stage
  const total = stageCounts.reduce((s, v) => s + v, 0) || 1
  const domIdx = stageCounts.indexOf(Math.max(...stageCounts))
  const domPct = Math.round((stageCounts[domIdx] / total) * 100)
  const domName = labelNames[domIdx] || 'unknown'

  const STAGE_PLAIN = {
    Resting:   'spending most of its time resting — minimal active movement detected',
    Foraging:  'largely foraging — slow, exploratory movement typical of an animal searching for food',
    Traveling: 'mainly traveling — sustained, directed movement from one place to another',
    Migrating: 'in a migratory pattern — long-distance, fast, directional movement',
  }
  const stagePlain = STAGE_PLAIN[domName] || `mostly in the "${domName}" stage`
  sentences.push(`Looking at movement stages, the animal is ${stagePlain} (${domPct}% of the route).`)

  // 5. Fragmentation check — are stages evenly spread?
  const total2 = stageCounts.reduce((s, v) => s + v, 0) || 1
  const spread = Math.max(...stageCounts) / total2
  if (n > 10 && spread < 0.5) {
    sentences.push(`The movement stages are spread fairly evenly across the route, indicating the animal frequently switches between behaviours rather than settling into one activity for long periods.`)
  }

  return sentences.join(' ')
}

export default function EnvFactors({ results }) {
  if (!results) return (
    <div className="empty-state">
      <p>Run an Environmental Factors analysis to see what is influencing movement</p>
    </div>
  )

  const envFactors = results.env_factors
  const stages     = results.stages || []
  const labelNames = results.label_names || ['Resting', 'Foraging', 'Traveling', 'Migrating']
  const stepsRaw   = results.steps || []
  const scoresA    = results.algo_a?.scores || []
  const nameA      = results.algo_a?.name?.replace(/^Env\s/, '') || 'Algorithm A'

  if (!envFactors?.names || !envFactors.values?.length) return (
    <div className="empty-state">
      <p>Environmental factor breakdown not available — re-run the analysis to generate this data.</p>
    </div>
  )

  const factorNames = envFactors.names
  const values      = envFactors.values   // n_vis × 12 (nulls for training fixes)

  // Filter out null entries (training fixes have no env factor data)
  const testValues = values.filter(row => row != null)
  const testStages = stages.filter(s => s != null)
  const n = testValues.length

  if (n === 0) return (
    <div className="empty-state">
      <p>Environmental factor breakdown not available — re-run the analysis to generate this data.</p>
    </div>
  )

  // x-axis labels — cumulative distance or fix index
  const useDistance = stepsRaw.length > 0
  let xLabels = []
  if (useDistance) {
    let acc = 0
    const cumAll = stepsRaw.map(s => { acc += (s || 0); return Math.round(acc) })
    const step = Math.max(1, Math.floor(cumAll.length / n))
    xLabels = Array.from({ length: n }, (_, i) => cumAll[Math.min(i * step, cumAll.length - 1)])
  } else {
    xLabels = Array.from({ length: n }, (_, i) => i)
  }

  // Transpose: one array per factor (test fixes only)
  const perFactor = factorNames.map((_, fi) => testValues.map(row => +(row[fi] ?? 0).toFixed(3)))

  // Factor means for stat cards + ranking
  const factorMeans = factorNames.map((name, fi) => {
    const col  = perFactor[fi]
    const mean = col.reduce((s, v) => s + v, 0) / (col.length || 1)
    return { name, fi, mean: +mean.toFixed(3) }
  }).sort((a, b) => b.mean - a.mean)

  const topFactor = factorMeans[0]
  const stageCounts = labelNames.map((_, i) => testStages.filter(s => s === i).length)
  const dominantStageIdx = stageCounts.indexOf(Math.max(...stageCounts))
  const dominantStage = labelNames[dominantStageIdx] || '—'
  const meanScore = scoresA.filter(v => v != null).length > 0
    ? (scoresA.filter(v => v != null).reduce((s, v) => s + v, 0) / scoresA.filter(v => v != null).length).toFixed(3) : '—'

  const insight = generateInsight({ factorMeans, stageCounts, labelNames, n })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Stat cards */}
      <div className="metrics-row">
        <div className="mcard">
          <div className="mcard-val accent" style={{ fontSize: 14, textTransform: 'none' }}>
            {topFactor?.name.replace(/_/g, ' ')}
          </div>
          <div className="mcard-label">Dominant env factor</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{topFactor?.mean ?? '—'}</div>
          <div className="mcard-label">Factor intensity</div>
        </div>
        <div className="mcard">
          <div className="mcard-val amber" style={{ fontSize: 14, textTransform: 'none' }}>
            {dominantStage}
          </div>
          <div className="mcard-label">Most common stage</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{meanScore}</div>
          <div className="mcard-label">Mean env score ({nameA})</div>
        </div>
      </div>

      {/* Auto-generated insight */}
      <div className="panel" style={{ borderLeft: '3px solid var(--accent)', background: 'var(--surface1)' }}>
        <div className="panel-title" style={{ marginBottom: 6 }}>What the analysis shows</div>
        <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7, margin: 0 }}>
          {insight}
        </p>
      </div>

      {/* Stage ribbon */}
      {testStages.length > 0 && (
        <div className="panel">
          <div className="panel-title">Movement stage along the route</div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 8, flexWrap: 'wrap' }}>
            {labelNames.map((l, i) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#ccc' }}>
                <span style={{
                  display: 'inline-block', width: 12, height: 12, borderRadius: 3,
                  background: STAGE_COLORS[i % STAGE_COLORS.length],
                }} />
                {l}
              </span>
            ))}
          </div>
          <StageRibbon stages={testStages} labelNames={labelNames} />
        </div>
      )}

      {/* 3 grouped bar charts side by side */}
      <div style={{ display: 'flex', gap: 12 }}>
        {GROUPS.map(g => (
          <GroupBar
            key={g.label}
            group={g}
            factorNames={factorNames}
            perFactor={perFactor}
          />
        ))}
      </div>

      {/* Factor ranking table */}
      <div className="panel">
        <div className="panel-title">All factors ranked by average intensity — {nameA}</div>
        <table className="vtable">
          <thead>
            <tr>
              <th>#</th>
              <th>Factor</th>
              <th>Avg intensity</th>
              <th>What it means</th>
            </tr>
          </thead>
          <tbody>
            {factorMeans.map((f, i) => {
              const group = GROUPS.find(g => g.indices.includes(f.fi))
              return (
                <tr key={f.name}>
                  <td style={{ color: 'var(--text3)' }}>{i + 1}</td>
                  <td>
                    <span style={{
                      display: 'inline-block', width: 8, height: 8, borderRadius: 2,
                      background: group?.color || '#888',
                      marginRight: 6, verticalAlign: 'middle',
                    }} />
                    {f.name.replace(/_/g, ' ')}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 6, background: 'var(--surface2)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{
                          height: 6, width: `${(f.mean * 100).toFixed(0)}%`,
                          background: group?.color || '#888', borderRadius: 3,
                        }} />
                      </div>
                      <span style={{ minWidth: 38, fontSize: 11, color: 'var(--text2)' }}>{f.mean}</span>
                    </div>
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text3)' }}>{FACTOR_MEANINGS[f.name] || ''}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

    </div>
  )
}

const FACTOR_MEANINGS = {
  terrain_ruggedness:  'How uneven the ground is — high = hilly or rocky terrain',
  slope:               'How steeply the land rises or falls along the route',
  ndvi_proxy:          'Vegetation density proxy — high = green, lush habitat',
  land_cover:          'Type of land surface (open, scrub, forest, high ground)',
  wind_proxy:          'Estimated wind exposure based on speed variability',
  temperature_proxy:   'Estimated temperature — lower at high altitude',
  proximity_water:     'How close the animal is to water sources',
  solar_radiation:     'Estimated solar energy received — affects thermals and activity',
  resource_score:      'Food or resource availability proxy',
  elevation_gradient:  'Rate of altitude change — high = actively climbing or descending',
  habitat_boundary:    'Whether the animal is crossing between habitat types',
  energy_expenditure:  'Estimated energy cost of movement at this point',
}
