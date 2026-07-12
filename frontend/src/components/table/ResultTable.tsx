import { useMemo } from 'react'
import { AgGridReact } from 'ag-grid-react'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import { ColDef } from 'ag-grid-community'
import { QueryResult } from '../../types'
import { Download, Clock, Rows, CheckCircle, XCircle } from 'lucide-react'
import { formatMs } from '../../utils/api'
import api from '../../utils/api'
import toast from 'react-hot-toast'

interface Props {
  result: QueryResult
  onExport?: (format: string) => void
}

export default function ResultTable({ result, onExport }: Props) {
  const colDefs = useMemo<ColDef[]>(() => {
    if (!result.columns) return []
    return result.columns.map(col => ({
      field: col,
      headerName: col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      sortable: true,
      filter: true,
      resizable: true,
      minWidth: 100,
      flex: 1,
      valueFormatter: (p) => {
        if (p.value === null || p.value === undefined) return '—'
        if (typeof p.value === 'number') return p.value.toLocaleString()
        return p.value
      }
    }))
  }, [result.columns])

  const handleExport = async (format: string) => {
    try {
      const r = await api.post('/export', {
        rows: result.rows,
        columns: result.columns,
        format,
        title: 'Query Results',
        sql: result.sql,
      })
      window.open(`/exports/${r.data.filename}`, '_blank')
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch {
      toast.error('Export failed')
    }
  }

  const formats = ['csv', 'excel', 'pdf', 'html', 'pptx']

  return (
    <div className="flex flex-col gap-3">
      {/* Result meta */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full
          ${result.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          {result.success ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
          {result.success ? 'Success' : 'Error'}
        </span>
        <span className="flex items-center gap-1.5 text-xs text-dark-muted">
          <Rows className="w-3 h-3" /> {result.row_count?.toLocaleString()} rows
        </span>
        <span className="flex items-center gap-1.5 text-xs text-dark-muted">
          <Clock className="w-3 h-3" /> {formatMs(result.execution_time_ms)}
        </span>

        {/* Export buttons */}
        <div className="ml-auto flex items-center gap-1.5">
          <span className="text-xs text-dark-muted">Export:</span>
          {formats.map(f => (
            <button key={f} onClick={() => handleExport(f)}
              className="text-xs px-2 py-1 rounded border border-dark-border text-dark-muted
                hover:text-white hover:border-blue-400/50 transition-all uppercase font-mono">
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Error display */}
      {!result.success && result.errors?.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          {result.errors.map((e, i) => (
            <p key={i} className="text-red-400 text-sm">{e}</p>
          ))}
        </div>
      )}

      {/* Grid */}
      {result.success && result.rows?.length > 0 && (
        <div className="ag-theme-custom rounded-xl overflow-hidden border border-dark-border" style={{ height: 350 }}>
          <AgGridReact
            rowData={result.rows}
            columnDefs={colDefs}
            pagination={true}
            paginationPageSize={50}
            defaultColDef={{ sortable: true, filter: true, resizable: true }}
            animateRows={true}
          />
        </div>
      )}

      {result.success && result.rows?.length === 0 && (
        <div className="text-center py-8 text-dark-muted">No rows returned</div>
      )}
    </div>
  )
}
