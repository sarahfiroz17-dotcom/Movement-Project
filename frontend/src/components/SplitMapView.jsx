import React, { useEffect, useRef } from 'react'
import { CLUSTER_COLORS } from '../constants.js'

function scoreColor(t, variant) {
  const v = Math.max(0, Math.min(1, t))
  if (variant === 'b') {
    const r = Math.round(80  + v * 160)
    const g = Math.round(60  - v * 40)
    const b = Math.round(180 + v * 60)
    return `rgb(${r},${g},${b})`
  }
  const r = Math.round(20  + v * 80)
  const g = Math.round(150 + v * 80)
  const b = Math.round(120 - v * 80)
  return `rgb(${r},${g},${b})`
}

function AlgoMap({ results, which }) {
  const mapRef     = useRef(null)
  const leafletRef = useRef(null)

  const algo        = which === 'a' ? results?.algo_a : results?.algo_b
  const name        = algo?.name?.replace(/^(Beh|Env)\s/, '') || (which === 'a' ? 'Algorithm A' : 'Algorithm B')
  const accentColor = which === 'a' ? '#5DCAA5' : '#7F77DD'
  const isRegression = algo?.service_type === 'regression'

  useEffect(() => {
    if (typeof window === 'undefined') return
    import('leaflet').then(L => {
      const Lv = L.default || L

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
      map.eachLayer(layer => {
        if (layer instanceof Lv.Marker || layer instanceof Lv.CircleMarker || layer instanceof Lv.Polyline)
          map.removeLayer(layer)
      })

      if (!results) return

      const { lats, lons } = results
      if (!lats?.length) return

      const scores = algo?.scores || []
      const preds  = algo?.predictions || []
      const bounds = []

      const MAX_MAP_POINTS = 5000
      const n    = lats.length
      const step = n > MAX_MAP_POINTS ? Math.ceil(n / MAX_MAP_POINTS) : 1
      const idxs = []
      for (let k = 0; k < n; k += step) {
        if (lats[k] != null && lons[k] != null) idxs.push(k)
      }

      // Track line
      const trackPoints = idxs.map(i => [lats[i], lons[i]])
      if (trackPoints.length > 1) {
        Lv.polyline(trackPoints, { color: '#378ADD', weight: 1.5, opacity: 0.3, dashArray: '4 3' }).addTo(map)
      }

      if (isRegression) {
        idxs.forEach(i => {
          const score = scores[i] ?? 0
          bounds.push([lats[i], lons[i]])
          const circle = Lv.circleMarker([lats[i], lons[i]], {
            radius: 5,
            fillColor: scoreColor(score, which),
            color: 'transparent', weight: 0, fillOpacity: 0.85,
          })
          circle.bindPopup(
            `<div style="font-size:12px;line-height:1.6;min-width:140px">
              <b>Fix #${i + 1}</b><br/>
              <span style="color:${accentColor}">${name}: ${score.toFixed(3)}</span><br/>
              Lat: ${lats[i].toFixed(4)} · Lon: ${lons[i].toFixed(4)}
            </div>`,
            { className: 'dark-popup' }
          )
          circle.addTo(map)
        })
      } else {
        const labelNames = results.label_names || []
        idxs.forEach(i => {
          const cluster = preds[i] ?? 0
          const color   = CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]
          const label   = labelNames[cluster] || `Cluster ${cluster}`
          bounds.push([lats[i], lons[i]])
          const circle = Lv.circleMarker([lats[i], lons[i]], {
            radius: 4, fillColor: color, color: 'transparent', weight: 0, fillOpacity: 0.85,
          })
          circle.bindPopup(
            `<div style="font-size:12px;line-height:1.6;min-width:140px">
              <b>Fix #${i + 1}</b><br/>
              <span style="color:${accentColor}">${name}: ${label}</span><br/>
              Lat: ${lats[i].toFixed(4)} · Lon: ${lons[i].toFixed(4)}
            </div>`,
            { className: 'dark-popup' }
          )
          circle.addTo(map)
        })
      }

      if (bounds.length > 0) {
        const startIcon = Lv.divIcon({
          html: `<div style="width:10px;height:10px;background:${accentColor};border-radius:50%;border:2px solid #04342C"></div>`,
          iconSize: [10, 10], className: '',
        })
        Lv.marker(bounds[0], { icon: startIcon }).bindTooltip('Start').addTo(map)
        const fitBounds = bounds.length > 300 ? bounds.slice(0, 300) : bounds
        map.fitBounds(fitBounds, { padding: [20, 20], maxZoom: 11 })
      }
    })
    return () => {}
  }, [results, which])

  // Stats
  const f1  = algo?.f1
  const rt  = algo?.runtime

  // Cluster legend (classification only)
  const labelNames = results?.label_names || []
  const preds      = algo?.predictions || []
  const clusterCounts = preds.reduce((acc, p) => { acc[p] = (acc[p] || 0) + 1; return acc }, {})
  const legendItems = !isRegression
    ? (labelNames.length > 0
        ? labelNames.map((nm, i) => ({ label: nm, color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }))
        : Object.entries(clusterCounts).sort((a,b)=>b[1]-a[1]).slice(0,5)
            .map(([k,ct]) => ({ label: `Cluster ${k} (${ct})`, color: CLUSTER_COLORS[+k % CLUSTER_COLORS.length] })))
    : []

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0,
                  border: `1px solid ${which === 'a' ? '#1D9E7540' : '#534AB740'}`,
                  borderRadius: 10, overflow: 'hidden', background: 'var(--surface)' }}>

      {/* Header */}
      <div style={{ padding: '10px 14px 8px', borderBottom: '1px solid var(--border)',
                    background: which === 'a' ? '#0d1f17' : '#100d21' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: accentColor }}>
            {which === 'a' ? 'A' : 'B'} — {name}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            {!isRegression && f1 != null && (
              <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                F1 <b style={{ color: accentColor }}>{f1.toFixed(3)}</b>
              </span>
            )}
            {rt != null && (
              <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                {rt.toFixed(2)}s
              </span>
            )}
          </div>
        </div>

        {/* Regression gradient bar */}
        {isRegression && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 10, color: 'var(--text3)' }}>Low</span>
            <div style={{ flex: 1, height: 5, borderRadius: 3,
                          background: which === 'a'
                            ? 'linear-gradient(to right, rgb(20,150,120), rgb(100,230,200))'
                            : 'linear-gradient(to right, rgb(80,60,180), rgb(240,100,240))' }} />
            <span style={{ fontSize: 10, color: 'var(--text3)' }}>High</span>
          </div>
        )}

        {/* Classification legend */}
        {!isRegression && legendItems.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px' }}>
            {legendItems.map(({ label, color }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--text2)' }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0 }} />
                {label}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Map */}
      <div ref={mapRef} style={{ flex: 1, minHeight: 340, background: '#0a0a10' }} />
    </div>
  )
}

export default function SplitMapView({ results }) {
  if (!results) return (
    <div className="empty-state">
      <p>Run a comparison to see the split view</p>
    </div>
  )

  const nameA = results.algo_a?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm A'
  const nameB = results.algo_b?.name?.replace(/^(Beh|Env)\s/, '') || 'Algorithm B'
  const isRegression = results.algo_a?.service_type === 'regression'

  // Agreement / difference stats
  const predsA = results.algo_a?.predictions || []
  const predsB = results.algo_b?.predictions || []
  const agree  = predsA.filter((v, i) => v === predsB[i]).length
  const pct    = predsA.length ? Math.round(agree / predsA.length * 100) : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

      {/* Metric summary row */}
      <div className="metrics-row" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="mcard">
          <div className="mcard-val accent">
            {isRegression
              ? (results.algo_a?.runtime != null ? results.algo_a.runtime.toFixed(2) + 's' : '—')
              : (results.algo_a?.f1 != null ? results.algo_a.f1.toFixed(3) : '—')}
          </div>
          <div className="mcard-label">{nameA} {isRegression ? 'runtime' : 'F1'}</div>
        </div>
        <div className="mcard">
          <div className="mcard-val purple">
            {isRegression
              ? (results.algo_b?.runtime != null ? results.algo_b.runtime.toFixed(2) + 's' : '—')
              : (results.algo_b?.f1 != null ? results.algo_b.f1.toFixed(3) : '—')}
          </div>
          <div className="mcard-label">{nameB} {isRegression ? 'runtime' : 'F1'}</div>
        </div>
        <div className="mcard">
          <div className="mcard-val">{(results.n_test || 0).toLocaleString()}</div>
          <div className="mcard-label">GPS fixes</div>
        </div>
        <div className="mcard">
          {pct != null && !isRegression ? (
            <>
              <div className="mcard-val" style={{ color: pct > 80 ? 'var(--accent)' : 'var(--amber)' }}>{pct}%</div>
              <div className="mcard-label">Agreement</div>
            </>
          ) : (
            <>
              <div className="mcard-val">
                {((results.algo_a?.runtime || 0) + (results.algo_b?.runtime || 0)).toFixed(1)}s
              </div>
              <div className="mcard-label">Total runtime</div>
            </>
          )}
        </div>
      </div>

      {/* Split maps */}
      <div style={{ display: 'flex', gap: 10, height: 460 }}>
        <AlgoMap results={results} which="a" />
        <AlgoMap results={results} which="b" />
      </div>

    </div>
  )
}
