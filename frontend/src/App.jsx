import React, { useState, useEffect, useCallback } from 'react'
import { SERVICES, TABS_ANALYSIS, TABS_ENV, TABS_ACCOUNT } from './constants.js'
import { listAlgorithms, uploadDataset, runComparison, runDemo,
         listDatasets } from './api.js'

import Sidebar           from './components/Sidebar.jsx'
import MapView           from './components/MapView.jsx'
import SplitMapView      from './components/SplitMapView.jsx'
import ClusterGraphs     from './components/ClusterGraphs.jsx'
import TimeSeries        from './components/TimeSeries.jsx'
import F1Scores          from './components/F1Scores.jsx'
import FeatureImportance from './components/FeatureImportance.jsx'
import MyDatasets        from './components/MyDatasets.jsx'
import History           from './components/History.jsx'
import Docs              from './components/Docs.jsx'
import EnvProfiles       from './components/EnvProfiles.jsx'
import EnvScoreTime      from './components/EnvScoreTime.jsx'
import EnvComparison     from './components/EnvComparison.jsx'

export default function App() {
  const [activeTab,    setActiveTab]    = useState('Map view')
  const [serviceId,    setServiceId]    = useState(3)
  const [dataset,      setDataset]      = useState(null)   // {id, name, species, n_fixes}
  const [algorithms,   setAlgorithms]   = useState([])
  const [algoA,        setAlgoA]        = useState(null)
  const [algoB,        setAlgoB]        = useState(null)
  const [results,      setResults]      = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [uploadPct,    setUploadPct]    = useState(0)
  const [error,        setError]        = useState(null)
  const [backendOk,    setBackendOk]    = useState(true)

  // Load algorithm list whenever service changes
  useEffect(() => {
    setAlgoA(null); setAlgoB(null); setAlgorithms([])
    listAlgorithms(serviceId)
      .then(r => setAlgorithms(Array.isArray(r.data) ? r.data : r.data.algorithms || []))
      .catch(() => setAlgorithms([]))
  }, [serviceId])

  // Upload handler
  const handleUpload = useCallback(async file => {
    setError(null)
    setUploadPct(0)
    try {
      const r = await uploadDataset(file, p => setUploadPct(p))
      setDataset({
        id:      r.data.dataset_id,
        name:    r.data.filename,
        species: r.data.species,
        n_fixes: r.data.n_fixes,
      })
      setResults(null)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Upload failed')
    }
  }, [])

  // Run analysis handler
  // Single algo selected → run it against itself (solo mode)
  // Two algos selected → compare side by side
  const handleRun = useCallback(async () => {
    if (!algoA) { setError('Please select an algorithm'); return }
    const b = algoB || algoA
    setLoading(true); setError(null)
    try {
      let r
      if (dataset) {
        r = await runComparison(dataset.id, serviceId, algoA, b)
      } else {
        r = await runDemo('red_kite', algoA, b, serviceId)
      }
      setResults({ ...r.data, compareMode: !!algoB })
      if (!TABS_ACCOUNT.includes(activeTab)) setActiveTab('Map view')
    } catch (e) {
      setError(e?.response?.data?.detail || 'Analysis failed — check backend is running')
    } finally {
      setLoading(false)
    }
  }, [algoA, algoB, dataset, serviceId, activeTab])

  // Which tab list to use — depends on selected service
  const isEnv = serviceId === 3
  const analysisTabs = isEnv ? TABS_ENV : TABS_ANALYSIS

  // Keep active tab valid when switching services
  useEffect(() => {
    if (!analysisTabs.includes(activeTab) && !TABS_ACCOUNT.includes(activeTab)) {
      setActiveTab('Map view')
    }
  }, [serviceId])

  const renderPage = () => {
    const props = { results, serviceId }
    switch (activeTab) {
      case 'Map view':              return results?.compareMode ? <SplitMapView results={results} /> : <MapView {...props} />
      case 'Cluster graphs':        return <ClusterGraphs {...props} />
      case 'Time series':           return <TimeSeries {...props} />
      case 'F1 scores':             return <F1Scores {...props} />
      case 'Env profiles':          return <EnvProfiles results={results} />
      case 'Score over time':       return <EnvScoreTime results={results} />
      case 'Algorithm comparison':  return <EnvComparison results={results} />
      case 'Feature importance':    return <FeatureImportance {...props} />
      case 'My datasets':           return <MyDatasets onSelect={ds => { setDataset(ds); setResults(null) }} activeId={dataset?.id} />
      case 'History':               return <History onLoad={r => { setResults(r); setActiveTab('Map view') }} />
      case 'Docs':                  return <Docs />
      default:                      return <MapView {...props} />
    }
  }

  return (
    <div className="app-shell">
      {/* ── Topbar ── */}
      <header className="topbar">
        <div className="logo">Ve<span>bita</span>
          <span style={{ fontSize: 11, color: 'var(--text3)', fontWeight: 400, marginLeft: 12 }}>
            {SERVICES[serviceId]?.name} · {dataset?.species || 'no dataset'}
          </span>
        </div>

        <nav className="nav-tabs">
          {analysisTabs.map(t => (
            <button key={t} className={`nav-tab${activeTab === t ? ' active' : ''}`}
                    onClick={() => setActiveTab(t)}>{t}</button>
          ))}
          <div className="nav-sep" />
          {TABS_ACCOUNT.map(t => (
            <button key={t} className={`nav-tab${activeTab === t ? ' active' : ''}`}
                    onClick={() => setActiveTab(t)}>{t}</button>
          ))}
        </nav>

        <div className="user-pill">Group · VEBITA</div>
      </header>

      <div className="main-area">
        {/* ── Sidebar ── */}
        <Sidebar
          serviceId={serviceId}   onServiceChange={id => { setServiceId(id); setResults(null) }}
          dataset={dataset}       onUpload={handleUpload}   uploadPct={uploadPct}
          algorithms={algorithms} algoA={algoA}   algoB={algoB}
          onSelectAlgo={(name) => {
            if (name === '__clear_a__') { setAlgoA(null); return }
            if (name === '__clear_b__') { setAlgoB(null); return }
            if (!algoA)               { setAlgoA(name); return }
            if (name === algoA)       { setAlgoA(null); return }
            if (!algoB)               { setAlgoB(name); return }
            if (name === algoB)       { setAlgoB(null); return }
            // Both slots full — replace A, clear B
            setAlgoA(name); setAlgoB(null)
          }}
          onRun={handleRun}  loading={loading}  error={error}
        />

        {/* ── Main content ── */}
        <main className="content-area">
          {loading && (
            <div style={{
              background: '#0d1f17', border: '1px solid var(--accent-d)', borderRadius: 8,
              padding: '12px 16px', fontSize: 12, color: 'var(--accent)',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <div style={{
                width: 14, height: 14, borderRadius: '50%',
                border: '2px solid var(--accent)', borderTopColor: 'transparent',
                animation: 'spin 0.8s linear infinite', flexShrink: 0,
              }} />
              Processing — this may take a few minutes for large datasets. Do not close the page.
            </div>
          )}
          {error && (
            <div style={{ background: '#1a0a0a', border: '1px solid #7a2020', borderRadius: 8,
                          padding: '10px 14px', fontSize: 12, color: '#f09595' }}>
              {error}
            </div>
          )}
          {renderPage()}
        </main>
      </div>
    </div>
  )
}