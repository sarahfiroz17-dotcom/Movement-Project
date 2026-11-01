import React, { useEffect, useRef, useState } from 'react'
import { CLUSTER_COLORS } from '../constants.js'

// Green-teal heatmap for Algorithm A
function scoreColorA(t) {
  const v = Math.max(0, Math.min(1, t))
  const r = Math.round(20  + v * 80)
  const g = Math.round(150 + v * 80)
  const b = Math.round(120 - v * 80)
  return `rgb(${r},${g},${b})`
}

// Purple heatmap for Algorithm B
function scoreColorB(t) {
  const v = Math.max(0, Math.min(1, t))
  const r = Math.round(80  + v * 160)
  const g = Math.round(60  - v * 40)
  const b = Math.round(180 + v * 60)
  return `rgb(${r},${g},${b})`
}

const STAGE_COLORS = ['#378ADD', '#5DCAA5', '#EF9F27', '#D85A30']

export default function MapView({ results }) {
  const mapRef     = useRef(null)
  const leafletRef = useRef(null)

  const isRegression = results?.algo_a?.service_type === 'regression'
  const compareMode  = results?.compareMode
  const [showA, setShowA] = useState(true)
  const [showB, setShowB] = useState(true)
  const [stageMode, setStageMode] = useState(true)    // S3 only: colour by stage vs env score

  const nameA = results?.algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm A'
  const nameB = results?.algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm B'

  useEffect(() => {
    if (typeof window === 'undefined') return
    import('leaflet').then(L => {
      const Lv = L.default || L

      // Init map once
      if (!leafletRef.current) {
        leafletRef.current = Lv.map(mapRef.current, {
          center: [51.0, 9.0], zoom: 7,
          zoomControl: true, attributionControl: true,
        })
        Lv.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap',
          className: 'map-tiles',
        }).addTo(leafletRef.current)
      }

      const map = leafletRef.current

      // Clear existing layers
      map.eachLayer(layer => { if (layer instanceof Lv.Marker || layer instanceof Lv.CircleMarker || layer instanceof Lv.Polyline) map.removeLayer(layer) })

      if (!results) return

      const { lats, lons, algo_a, algo_b } = results
      if (!lats?.length) return

      const scoresAFull = algo_a?.scores || []
      const scoresBFull = algo_b?.scores || []
      const predsAFull  = algo_a?.predictions || []
      const predsBFull  = algo_b?.predictions || []
      const bounds = []

      const MAX_MAP_POINTS = 5000
      const n    = lats.length
      const step = n > MAX_MAP_POINTS ? Math.ceil(n / MAX_MAP_POINTS) : 1
      const idxs = []
      for (let k = 0; k < n; k += step) {
        // Skip any point where lat or lon is null/undefined (NaN from backend)
        if (lats[k] != null && lons[k] != null) idxs.push(k)
      }

      // GPS track line — only valid (non-null) coordinates
      const trackPoints = idxs.map(i => [lats[i], lons[i]])
      if (trackPoints.length > 1) {
        Lv.polyline(trackPoints, {
          color: '#378ADD', weight: 1.5, opacity: 0.4, dashArray: '4 3'
        }).addTo(map)
      }

      if (isRegression) {
        // Small lat/lon nudge so A and B dots sit side-by-side instead of stacking
        const OFFSET = 0.0003
        const both = showA && showB
        const envFactors  = results.env_factors
        const stages      = results.stages || []
        const labelNames  = results.label_names || []

        idxs.forEach((i) => {
          const scoreA = scoresAFull[i]
          const scoreB = scoresBFull[i]
          const lat = lats[i], lon = lons[i]
          bounds.push([lat, lon])

          // null means this fix was in the training set — skip coloured dot
          const hasA = scoreA != null
          const hasB = scoreB != null

          // Stage for this fix — indexed by i (position in full-track array)
          const stageIdx  = stages[i] ?? -1
          const stageName = stageIdx >= 0 && labelNames[stageIdx] ? labelNames[stageIdx] : ''
          const stageColor = stageIdx >= 0 ? STAGE_COLORS[stageIdx % STAGE_COLORS.length] : '#888'

          // Top env factor for popup
          let topFactor = ''
          if (envFactors?.names && envFactors.values?.[i]) {
            const row = envFactors.values[i]
            if (row) {
              let topIdx = 0, topVal = -1
              for (let j = 0; j < row.length; j++) {
                if (row[j] > topVal) { topVal = row[j]; topIdx = j }
              }
              topFactor = `${envFactors.names[topIdx].replace(/_/g, ' ')} (${topVal.toFixed(2)})`
            }
          }

          const popupHtml = `<div style="font-size:12px;line-height:1.7;min-width:180px">
            <b>Fix #${i + 1}</b><br/>
            ${hasA ? `<span style="color:#5DCAA5">A — ${nameA}: ${scoreA.toFixed(3)}</span><br/>` : '<span style="color:var(--text3)">Training fix</span><br/>'}
            ${topFactor ? `<span style="color:#aaa">Top factor: ${topFactor}</span><br/>` : ''}
            ${stageName ? `<span style="color:${stageColor}">● ${stageName}</span><br/>` : ''}
            Lat: ${lat.toFixed(4)} · Lon: ${lon.toFixed(4)}
          </div>`

          if (showA && hasA) {
            const aLon = both ? lon - OFFSET : lon
            const dotColor = stageMode && stageIdx >= 0 ? stageColor : scoreColorA(scoreA)
            Lv.circleMarker([lat, aLon], {
              radius: 5, fillColor: dotColor,
              color: 'transparent', weight: 0, fillOpacity: 0.85,
            }).bindPopup(popupHtml, { className: 'dark-popup' }).addTo(map)
          }

          if (showB && hasB) {
            const bLon = both ? lon + OFFSET : lon
            const dotColor = stageMode && stageIdx >= 0 ? stageColor : scoreColorB(scoreB)
            Lv.circleMarker([lat, bLon], {
              radius: 5, fillColor: dotColor,
              color: 'transparent', weight: 0, fillOpacity: 0.85,
            }).bindPopup(popupHtml, { className: 'dark-popup' }).addTo(map)
          }
        })

      } else {
        // Non-regression (S6): colour by predicted cluster; skip training fixes (null)
        idxs.forEach(i => {
          const clusterA = predsAFull[i]
          const clusterB = predsBFull[i]
          // null = training fix — show nothing (track line already drawn)
          if (clusterA == null) return
          const color    = CLUSTER_COLORS[clusterA % CLUSTER_COLORS.length]
          const match    = clusterA === clusterB
          const popupA   = results.label_names?.[clusterA] || `Cluster ${clusterA}`
          const popupB   = clusterB != null ? (results.label_names?.[clusterB] || `Cluster ${clusterB}`) : '—'

          const circle = Lv.circleMarker([lats[i], lons[i]], {
            radius: 4, fillColor: color, color: match ? color : '#ffffff',
            weight: match ? 0 : 1.5, fillOpacity: 0.85, opacity: 0.9,
          })
          circle.bindPopup(
            `<div style="font-size:12px;line-height:1.6;min-width:160px">
              <b>Fix #${i + 1}</b><br/>
              <span style="color:#5DCAA5">A (${nameA}): ${popupA}</span><br/>
              <span style="color:#7F77DD">B (${nameB}): ${popupB}</span><br/>
              Lat: ${lats[i].toFixed(4)} · Lon: ${lons[i].toFixed(4)}
            </div>`,
            { className: 'dark-popup' }
          )
          circle.addTo(map)
          bounds.push([lats[i], lons[i]])
        })
      }

      // Start/end markers — fit to full track so entire route is visible
      if (trackPoints.length > 0) {
        const startIcon = Lv.divIcon({ html: '<div style="width:10px;height:10px;background:#5DCAA5;border-radius:50%;border:2px solid #04342C"></div>', iconSize: [10, 10], className: '' })
        const endIcon   = Lv.divIcon({ html: '<div style="width:10px;height:10px;background:#7F77DD;border-radius:50%;border:2px solid #26215C"></div>', iconSize: [10, 10], className: '' })
        Lv.marker(trackPoints[0], { icon: startIcon }).bindTooltip('Start').addTo(map)
        Lv.marker(trackPoints[trackPoints.length - 1], { icon: endIcon }).bindTooltip('Latest').addTo(map)
        const fitPoints = trackPoints.length > 500 ? trackPoints.slice(0, 500) : trackPoints
        map.fitBounds(fitPoints, { padding: [30, 30], maxZoom: 11 })
      }
    })

    return () => {}
  }, [results, showA, showB, stageMode])

  const labelNames    = results?.label_names || []
  const predsA        = results?.algo_a?.predictions || []
  const clusterCounts = predsA.reduce((acc, p) => { acc[p] = (acc[p] || 0) + 1; return acc }, {})

  // For the legend: use label_names if available, else top-5 clusters by count
  const legendItems = labelNames.length > 0
    ? labelNames.map((name, i) => ({ label: name, color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }))
    : Object.entries(clusterCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([k, count]) => ({ label: `Cluster ${k} (${count} pts)`, color: CLUSTER_COLORS[+k % CLUSTER_COLORS.length] }))

  const clusterCount = labelNames.length > 0 ? labelNames.length : Object.keys(clusterCounts).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Metric summary */}
      {results && (
        <div className="metrics-row">
          <div className="mcard">
            <div className="mcard-val accent">
              {isRegression ? '—' : clusterCount}
            </div>
            <div className="mcard-label">{isRegression ? 'Env score' : 'Clusters found'}</div>
          </div>
          <div className="mcard">
            <div className="mcard-val">{(results.n_total || results.n_test || 0).toLocaleString()}</div>
            <div className="mcard-label">GPS fixes mapped</div>
          </div>
          <div className="mcard">
            <div className="mcard-val amber">
              {results.algo_a?.f1 != null ? results.algo_a.f1.toFixed(2) : '—'}
            </div>
            <div className="mcard-label">
              {isRegression ? 'Runtime' : `Best F1 (${results.algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'A'})`}
            </div>
          </div>
          <div className="mcard">
            <div className="mcard-val">
              {((results.algo_a?.runtime || 0) + (results.algo_b?.runtime || 0)).toFixed(1)}s
            </div>
            <div className="mcard-label">Total runtime</div>
          </div>
        </div>
      )}

      {/* Map */}
      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '12px 14px 8px', borderBottom: '1px solid var(--border)' }}>
          <div className="panel-title" style={{ marginBottom: 6 }}>
            Movement map — GPS trajectory with {isRegression ? 'environmental score overlay' : 'cluster overlay'}
          </div>
          {results && isRegression && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {/* Mode toggle */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>Colour by:</span>
                <button
                  onClick={() => setStageMode(false)}
                  style={{
                    fontSize: 11, padding: '3px 10px', borderRadius: 4, cursor: 'pointer', border: 'none',
                    background: !stageMode ? 'var(--accent)' : 'var(--surface2)',
                    color: !stageMode ? '#000' : 'var(--text2)',
                  }}>
                  Env score
                </button>
                <button
                  onClick={() => setStageMode(true)}
                  style={{
                    fontSize: 11, padding: '3px 10px', borderRadius: 4, cursor: 'pointer', border: 'none',
                    background: stageMode ? '#EF9F27' : 'var(--surface2)',
                    color: stageMode ? '#000' : 'var(--text2)',
                  }}>
                  Movement stage
                </button>
              </div>

              {/* Env score legend */}
              {!stageMode && (
                <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', userSelect: 'none' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      width: 16, height: 16, borderRadius: 4, border: '2px solid #5DCAA5',
                      background: showA ? '#5DCAA5' : 'transparent', flexShrink: 0,
                    }}>
                      {showA && <svg width="10" height="8" viewBox="0 0 10 8"><path d="M1 4l3 3 5-6" stroke="#0a0a10" strokeWidth="1.8" fill="none" strokeLinecap="round"/></svg>}
                    </span>
                    <input type="checkbox" checked={showA} onChange={e => setShowA(e.target.checked)}
                           style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                    <span style={{ fontSize: 12, color: '#5DCAA5', fontWeight: 500 }}>{nameA}</span>
                    <div style={{ width: 32, height: 6, borderRadius: 3, background: 'linear-gradient(to right, rgb(20,150,120), rgb(100,230,200))' }} />
                  </label>
                  {compareMode && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', userSelect: 'none' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        width: 16, height: 16, borderRadius: 4, border: '2px solid #a080f0',
                        background: showB ? '#a080f0' : 'transparent', flexShrink: 0,
                      }}>
                        {showB && <svg width="10" height="8" viewBox="0 0 10 8"><path d="M1 4l3 3 5-6" stroke="#0a0a10" strokeWidth="1.8" fill="none" strokeLinecap="round"/></svg>}
                      </span>
                      <input type="checkbox" checked={showB} onChange={e => setShowB(e.target.checked)}
                             style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                      <span style={{ fontSize: 12, color: '#a080f0', fontWeight: 500 }}>{nameB}</span>
                      <div style={{ width: 32, height: 6, borderRadius: 3, background: 'linear-gradient(to right, rgb(80,60,180), rgb(240,100,240))' }} />
                    </label>
                  )}
                  <span style={{ fontSize: 11, color: 'var(--text3)' }}>Low → High env score</span>
                </div>
              )}

              {/* Stage legend */}
              {stageMode && (
                <div className="legend">
                  {(results.label_names || ['Resting', 'Foraging', 'Traveling', 'Migrating']).map((lbl, i) => (
                    <div key={lbl} className="leg-item">
                      <div className="leg-dot" style={{ background: STAGE_COLORS[i % STAGE_COLORS.length] }} />
                      {lbl}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {results && !isRegression && (
            <div className="legend">
              {legendItems.map(({ label, color }) => (
                <div key={label} className="leg-item">
                  <div className="leg-dot" style={{ background: color }} />
                  {label}
                </div>
              ))}
              {compareMode && (
              <div className="leg-item">
                <div className="leg-dot" style={{ background: 'white', border: '1px solid #aaa' }} />
                Disagreement (A≠B)
              </div>
              )}
            </div>
          )}
        </div>
        <div ref={mapRef} style={{ height: 400, width: '100%', background: '#0a0a10' }} />
        {!results && (
          <div style={{ position: 'absolute', top: '50%', left: '50%',
                        transform: 'translate(-50%,-50%)', textAlign: 'center',
                        color: 'var(--text3)', pointerEvents: 'none', fontSize: 13 }}>
            Run an analysis to see GPS clusters on the map
          </div>
        )}
      </div>

      {/* Disagreement count — only meaningful in compare mode */}
      {results && compareMode && (
        <div className="panel">
          <div className="panel-title">Algorithm agreement</div>
          <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
            {(() => {
              const a = results.algo_a?.predictions || []
              const b = results.algo_b?.predictions || []
              const agree = a.filter((v, i) => v === b[i]).length
              const pct   = a.length ? Math.round(agree / a.length * 100) : 0
              return (
                <>
                  <div style={{ flex: 1 }}>
                    <div style={{ height: 8, background: 'var(--surface2)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{ height: 8, background: 'var(--accent)', width: `${pct}%`, borderRadius: 4 }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 11, color: 'var(--text3)' }}>
                      <span>{agree.toLocaleString()} agrees</span>
                      <span>{(a.length - agree).toLocaleString()} disagreements</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 500, color: pct > 80 ? 'var(--accent)' : 'var(--amber)', minWidth: 52 }}>
                    {pct}%
                  </div>
                </>
              )
            })()}
          </div>
        </div>
      )}

    </div>
  )
}