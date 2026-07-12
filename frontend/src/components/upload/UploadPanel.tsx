import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, CheckCircle, XCircle, Loader2, Database, Trash2 } from 'lucide-react'
import { useStore } from '../../store'
import api from '../../utils/api'
import { formatBytes } from '../../utils/api'
import { Dataset } from '../../types'
import toast from 'react-hot-toast'
import { useEffect } from 'react'

export default function UploadPanel() {
  const [uploading, setUploading] = useState(false)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loadingDatasets, setLoadingDatasets] = useState(true)
  const { setSelectedDataset, selectedDataset, setActiveTab } = useStore()

  const fetchDatasets = async () => {
    try {
      const r = await api.get('/upload/datasets')
      setDatasets(r.data)
    } catch { } finally {
      setLoadingDatasets(false)
    }
  }

  useEffect(() => { fetchDatasets() }, [])

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return
    setUploading(true)
    const form = new FormData()
    accepted.forEach(f => form.append('files', f))
    try {
      const r = await api.post('/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success(`Uploaded ${r.data.uploaded} file(s) successfully`)
      await fetchDatasets()
      if (r.data.datasets?.[0]) {
        const ds = r.data.datasets[0]
        setSelectedDataset({ ...ds, id: ds.dataset_id })
        setActiveTab('chat')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
    },
    disabled: uploading,
  })

  const deleteDataset = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this dataset?')) return
    try {
      await api.delete(`/upload/datasets/${id}`)
      setDatasets(d => d.filter(x => x.id !== id))
      if (selectedDataset?.id === id) setSelectedDataset(null)
      toast.success('Dataset deleted')
    } catch { toast.error('Delete failed') }
  }

  const selectDataset = async (ds: Dataset) => {
    try {
      const r = await api.get(`/upload/datasets/${ds.id}`)
      setSelectedDataset(r.data)
      setActiveTab('chat')
      toast.success(`Loaded: ${ds.name}`)
    } catch { toast.error('Could not load dataset') }
  }

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Upload Data</h2>
        <p className="text-dark-muted text-sm">Upload Excel or CSV files — supports multiple sheets and files</p>
      </div>

      {/* Dropzone */}
      <div {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
          ${isDragActive ? 'border-blue-400 bg-blue-500/10' : 'border-dark-border hover:border-blue-400/50 hover:bg-dark-surface/50'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4">
          {uploading ? (
            <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />
          ) : (
            <Upload className={`w-12 h-12 ${isDragActive ? 'text-blue-400' : 'text-dark-muted'}`} />
          )}
          <div>
            <p className="text-white font-semibold text-lg">
              {uploading ? 'Processing...' : isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-dark-muted text-sm mt-1">or click to browse · Excel (.xlsx, .xls) · CSV (.csv) · Max 500MB</p>
          </div>
        </div>
      </div>

      {/* Datasets List */}
      <div>
        <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-400" />
          Your Datasets ({datasets.length})
        </h3>

        {loadingDatasets ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
          </div>
        ) : datasets.length === 0 ? (
          <div className="text-center py-8 text-dark-muted">
            <Database className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p>No datasets yet. Upload your first file!</p>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {datasets.map(ds => (
              <div key={ds.id} onClick={() => selectDataset(ds)}
                className={`bg-dark-surface border rounded-xl p-4 cursor-pointer hover:border-blue-400/50 transition-all group
                  ${selectedDataset?.id === ds.id ? 'border-blue-400 bg-blue-500/5' : 'border-dark-border'}`}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <File className="w-5 h-5 text-blue-400 shrink-0" />
                    <span className="text-white font-medium text-sm truncate">{ds.name}</span>
                  </div>
                  <button onClick={(e) => deleteDataset(ds.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded text-dark-muted hover:text-red-400 transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="space-y-1 text-xs text-dark-muted">
                  <p>{ds.row_count?.toLocaleString()} rows · {formatBytes(ds.size_bytes)}</p>
                  <p className="uppercase font-mono">{ds.file_type}</p>
                  <p>{new Date(ds.created_at).toLocaleDateString()}</p>
                </div>
                {selectedDataset?.id === ds.id && (
                  <div className="mt-2 flex items-center gap-1 text-xs text-blue-400">
                    <CheckCircle className="w-3 h-3" /> Active
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
