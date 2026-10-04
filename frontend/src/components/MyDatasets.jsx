import React, { useState, useEffect, useRef } from 'react'
import { listDatasets, uploadDataset, deleteDataset } from '../api.js'
import { ANIMALS } from '../constants.js'

const ANIMAL_ICONS = {
  red_kite: '🦅', black_stork: '🦢', mongolian_gazelle: '🦌',
  elk: '🦌', wolf: '🐺', brown_bear: '🐻', cheetah: '🐆', white_stork: '🦢',
}

export default function MyDatasets({ onSelect, activeId }) {
  const [datasets,  setDatasets]  = useState([])
  const [loading,   setLoading]   = useState(true)
  const [uploading, setUploading] = useState(false)
  const [pct,       setPct]       = useState(0)
  const [error,     setError]     = useState(null)
  const fileRef = useRef()

  const refresh = () => {
    setLoading(true)
    listDatasets()
      .then(r => setDatasets(r.data))
      .catch(() => setError('Could not load datasets'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])

  const handleUpload = async file => {
    if (!file) return
    setUploading(true); setError(null); setPct(0)
    try {
      await uploadDataset(file, p => setPct(p))
      refresh()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Upload failed')
    } finally { setUploading(false); setPct(0) }
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (!confirm('Remove this dataset record?')) return
    await deleteDataset(id)
    refresh()
  }

  const formatDate = ts => {
    if (!ts) return ''
    try { return new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) }
    catch { return ts }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Upload zone */}
      <div className="panel">
        <div className="panel-title">
          Upload new dataset
          <span className="badge badge-gray">Movebank CSV</span>
        </div>
        <div
          className="upload-zone"
          style={{ marginBottom: 0 }}
          onClick={() => fileRef.current.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); e.dataTransfer.files[0] && handleUpload(e.dataTransfer.files[0]) }}
        >
          <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }}
                 onChange={e => e.target.files[0] && handleUpload(e.target.files[0])} />
          <div style={{ fontSize: 24, color: 'var(--accent)', marginBottom: 8 }}>↑</div>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', marginBottom: 4 }}>
            {uploading ? `Uploading… ${pct}%` : 'Drop Movebank CSV here'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text3)' }}>
            Required columns: timestamp · location-lat · location-long · ground-speed · height-above-msl
          </div>
          {uploading && (
            <div style={{ marginTop: 10, height: 4, background: 'var(--border2)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ height: 4, background: 'var(--accent)', width: `${pct}%`, transition: 'width .2s' }} />
            </div>
          )}
        </div>
        {error && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#f09595', background: '#1a0a0a',
                        border: '1px solid #7a2020', borderRadius: 6, padding: '6px 10px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Dataset list */}
      <div className="panel">
        <div className="panel-title">
          Your datasets
          <span className="badge badge-gray">{datasets.length} files</span>
        </div>

        {loading ? (
          <div className="spinner" />
        ) : datasets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text3)', fontSize: 13 }}>
            No datasets yet — upload a Movebank CSV above
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {datasets.map(ds => {
              const icon = Object.entries(ANIMAL_ICONS)
                .find(([k]) => ds.species?.toLowerCase().includes(k))?.[1] || '📄'
              return (
                <div key={ds.id}
                     className={`ds-card${ds.id === activeId ? ' active' : ''}`}
                     onClick={() => onSelect({
                       id: ds.id, name: ds.original_name,
                       species: ds.species, n_fixes: ds.n_fixes,
                     })}>
                  <div className="ds-icon"
                       style={{ background: ds.id === activeId ? '#1a2a20' : 'var(--surface2)', fontSize: 18 }}>
                    {icon}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="ds-name">{ds.original_name}</div>
                    <div className="ds-meta">
                      {(ds.n_fixes || 0).toLocaleString()} fixes · {ds.species} · {ds.file_size_kb?.toFixed(0)} KB
                    </div>
                    <div className="ds-meta">{formatDate(ds.uploaded_at)}</div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                    {ds.id === activeId && <span className="badge badge-green">Active</span>}
                    <span style={{ fontSize: 11, color: 'var(--text3)', cursor: 'pointer',
                                   padding: '2px 6px', borderRadius: 4 }}
                          onClick={e => handleDelete(e, ds.id)}>
                      Remove
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Supported animals reference */}
      <div className="panel">
        <div className="panel-title">Supported animal profiles (for demo mode)</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {ANIMALS.map(a => (
            <div key={a} style={{ background: 'var(--surface2)', border: '1px solid var(--border)',
                                  borderRadius: 6, padding: '4px 10px', fontSize: 11, color: 'var(--text2)' }}>
              {ANIMAL_ICONS[a] || '🐾'} {a.replace(/_/g, ' ')}
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}