import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000' })

// Separate instance for large-file uploads — no timeout cap
const uploadApi = axios.create({ baseURL: 'http://localhost:8000', timeout: 0 })

export const uploadDataset     = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return uploadApi.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress?.(Math.round(e.loaded * 100 / e.total)),
  })
}
export const listDatasets      = ()             => api.get('/datasets')
export const deleteDataset     = id            => api.delete(`/datasets/${id}`)
export const listAlgorithms    = serviceId     => api.get(`/algorithms/${serviceId}`)
export const listAllAlgorithms = ()            => api.get('/algorithms')
export const runComparison     = (datasetId, serviceId, algoA, algoB) =>
  api.post('/run', { dataset_id: datasetId, service_id: serviceId, algo_a: algoA, algo_b: algoB }, { timeout: 0 })
export const runDemo           = (animal, algoA, algoB, serviceId) =>
  api.post('/demo', { animal, algo_a: algoA, algo_b: algoB, service_id: serviceId })
export const getHistory        = (limit = 50)  => api.get(`/history?limit=${limit}`)
export const getResult         = id            => api.get(`/history/${id}`)
export const healthCheck       = ()            => api.get('/health')