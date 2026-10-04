import React, { useRef } from 'react'
import { SERVICES } from '../constants.js'

export default function Sidebar({
  serviceId, onServiceChange,
  dataset, onUpload, uploadPct,
  algorithms, algoA, algoB, onSelectAlgo,
  onRun, loading,
}) {
  const fileRef = useRef()

  const grouped = algorithms.reduce((acc, a) => {
    if (!acc[a.category]) acc[a.category] = []
    acc[a.category].push(a)
    return acc
  }, {})

  const getAlgoClass = name => {
    if (name === algoA) return 'algo-item selected-a'
    if (name === algoB) return 'algo-item selected-b'
    return 'algo-item'
  }

  const canRun = algoA && !loading
  const isCompare = algoA && algoB

  return (
    <aside className="sidebar">

      {/* ── Service ── */}
      <div>
        <div className="sidebar-label">Service</div>
        {Object.entries(SERVICES).map(([id, svc]) => (
          <button key={id}
            className={`svc-btn${+id === serviceId ? ' active' : ''}`}
            onClick={() => onServiceChange(+id)}>
            <span className="svc-dot" style={{ background: svc.color }} />
            {svc.name}
          </button>
        ))}
      </div>

      {/* ── Dataset ── */}
      <div>
        <div className="sidebar-label">Dataset</div>
        <div
          className={`upload-zone${dataset ? ' has-file' : ''}`}
          onClick={() => fileRef.current.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); e.dataTransfer.files[0] && onUpload(e.dataTransfer.files[0]) }}
        >
          <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }}
            onChange={e => e.target.files[0] && onUpload(e.target.files[0])} />
          {dataset ? (
            <>
              <div style={{ fontSize: 18, marginBottom: 4 }}>📄</div>
              <div className="upload-name">{dataset.name}</div>
              <div className="upload-meta">{(dataset.n_fixes || 0).toLocaleString()} fixes · {dataset.species}</div>
              <div className="upload-meta" style={{ color: 'var(--accent)', marginTop: 4, fontSize: 10 }}>
                Click to replace
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 22, color: 'var(--accent)', marginBottom: 6 }}>↑</div>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', marginBottom: 2 }}>
                Drop Movebank CSV
              </div>
              <div className="upload-meta">or click to browse</div>
            </>
          )}
          {uploadPct > 0 && uploadPct < 100 && (
            <div style={{ marginTop: 8, height: 3, background: 'var(--border2)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ height: 3, background: 'var(--accent)', width: `${uploadPct}%`, transition: 'width .2s' }} />
            </div>
          )}
        </div>
        {!dataset && (
          <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 5, textAlign: 'center' }}>
            No file? Demo data will be used
          </div>
        )}
      </div>

      {/* ── Algorithms ── */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="sidebar-label" style={{ marginBottom: 4 }}>
          Algorithms
          <span style={{ float: 'right' }}>
            {isCompare ? '2 — compare mode' : algoA ? '1 selected' : '0 selected'}
          </span>
        </div>

        {/* Selected pills */}
        {(algoA || algoB) && (
          <div style={{ marginBottom: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {algoA && (
              <div style={{ background: '#1a2a20', border: '1px solid #1D9E7540', borderRadius: 6,
                            padding: '4px 8px', fontSize: 11, color: 'var(--accent)',
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 140 }}>
                  {isCompare ? 'A: ' : ''}{algoA.replace(/^(Beh|Env)\s/, '')}
                </span>
                <span style={{ cursor: 'pointer', marginLeft: 6, opacity: 0.7, flexShrink: 0 }}
                      onClick={() => onSelectAlgo('__clear_a__')}>✕</span>
              </div>
            )}
            {algoB && (
              <div style={{ background: '#17142a', border: '1px solid #534AB740', borderRadius: 6,
                            padding: '4px 8px', fontSize: 11, color: 'var(--purple)',
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 140 }}>
                  B: {algoB.replace(/^(Beh|Env)\s/, '')}
                </span>
                <span style={{ cursor: 'pointer', marginLeft: 6, opacity: 0.7, flexShrink: 0 }}
                      onClick={() => onSelectAlgo('__clear_b__')}>✕</span>
              </div>
            )}
          </div>
        )}

        {/* Hint text */}
        {algoA && !algoB && (
          <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 8, textAlign: 'center' }}>
            Select a second algorithm to compare side-by-side
          </div>
        )}

        <div style={{ flex: 1, overflowY: 'auto', marginBottom: 10 }}>
          {algorithms.length === 0 ? (
            <div style={{ color: 'var(--text3)', fontSize: 11, textAlign: 'center', padding: '20px 0' }}>
              No algorithms loaded for this service
            </div>
          ) : (
            Object.entries(grouped).map(([cat, algos]) => (
              <div key={cat}>
                <div className="algo-group-label">{cat.replace(/_/g, ' ')}</div>
                {algos.map(a => (
                  <div key={a.name} className={getAlgoClass(a.name)}
                       onClick={() => onSelectAlgo(a.name)} title={a.description}>
                    {a.name.replace(/^Beh\s/, '')}
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        <button className="run-btn" onClick={onRun} disabled={!canRun}>
          {loading ? 'Running…' : isCompare ? 'Compare →' : canRun ? 'Run analysis →' : 'Select an algorithm'}
        </button>
      </div>

    </aside>
  )
}