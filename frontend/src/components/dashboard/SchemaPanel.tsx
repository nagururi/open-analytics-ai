import { useEffect, useState } from 'react'
import { useStore } from '../../store'
import api from '../../utils/api'
import { Database, Table, ChevronDown, ChevronRight, AlertCircle, CheckCircle2, Hash, Type, Calendar } from 'lucide-react'
import { TableInfo, Dataset } from '../../types'

export default function SchemaPanel() {
  const { selectedDataset } = useStore()
  const [schema, setSchema] = useState<Dataset | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (selectedDataset?.id) {
      setLoading(true)
      api.get(`/schema/${selectedDataset.id}`)
        .then(r => { setSchema(r.data); })
        .catch(() => {})
        .finally(() => setLoading(false))
    }
  }, [selectedDataset?.id])

  if (!selectedDataset) return (
    <div className="flex items-center justify-center h-full text-dark-muted">
      <div className="text-center">
        <Database className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Select a dataset to explore its schema</p>
      </div>
    </div>
  )

  const tables = schema?.tables_json?.tables || []
  const rels = schema?.tables_json?.relationships || []

  const toggle = (name: string) => setExpanded(e => ({ ...e, [name]: !e[name] }))

  const dtypeIcon = (col: any) => {
    if (col.is_numeric) return <Hash className="w-3 h-3 text-blue-400 shrink-0" />
    if (col.is_datetime) return <Calendar className="w-3 h-3 text-purple-400 shrink-0" />
    return <Type className="w-3 h-3 text-green-400 shrink-0" />
  }

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Schema Explorer</h2>
        <p className="text-dark-muted text-sm">{selectedDataset.name} · {tables.length} table(s)</p>
      </div>

      {/* Quality overview */}
      {tables.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Tables', value: tables.length, color: 'text-blue-400' },
            { label: 'Total Rows', value: tables.reduce((a, t) => a + t.row_count, 0).toLocaleString(), color: 'text-green-400' },
            { label: 'Relationships', value: rels.length, color: 'text-purple-400' },
            { label: 'Quality', value: `${Math.round(tables.reduce((a, t) => a + (t.profile?.quality_score || 0), 0) / Math.max(tables.length, 1))}%`, color: 'text-orange-400' },
          ].map((item, i) => (
            <div key={i} className="bg-dark-surface border border-dark-border rounded-xl p-4">
              <p className="text-dark-muted text-xs mb-1">{item.label}</p>
              <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tables */}
      <div className="space-y-3">
        {tables.map(table => (
          <div key={table.table_name} className="bg-dark-surface border border-dark-border rounded-xl overflow-hidden">
            {/* Table header */}
            <button onClick={() => toggle(table.table_name)}
              className="w-full flex items-center justify-between p-4 hover:bg-dark-bg/30 transition-colors">
              <div className="flex items-center gap-3">
                <Table className="w-5 h-5 text-blue-400" />
                <div className="text-left">
                  <p className="text-white font-medium">{table.display_name}</p>
                  <p className="text-dark-muted text-xs font-mono">{table.table_name}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right text-xs text-dark-muted hidden md:block">
                  <p>{table.row_count?.toLocaleString()} rows</p>
                  <p>{table.column_count} cols</p>
                </div>
                {table.profile && (
                  <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full
                    ${table.profile.quality_score >= 80 ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                    {table.profile.quality_score >= 80
                      ? <CheckCircle2 className="w-3 h-3" />
                      : <AlertCircle className="w-3 h-3" />}
                    {table.profile.quality_score}%
                  </div>
                )}
                {expanded[table.table_name] ? <ChevronDown className="w-4 h-4 text-dark-muted" /> : <ChevronRight className="w-4 h-4 text-dark-muted" />}
              </div>
            </button>

            {/* Columns */}
            {expanded[table.table_name] && (
              <div className="border-t border-dark-border">
                {/* Profile summary */}
                {table.profile && (
                  <div className="px-4 py-3 bg-dark-bg/30 grid grid-cols-3 md:grid-cols-6 gap-3 text-xs">
                    {[
                      ['Rows', table.profile.total_rows.toLocaleString()],
                      ['Null %', `${table.profile.null_pct}%`],
                      ['Duplicates', table.profile.duplicate_rows.toLocaleString()],
                      ['Dup %', `${table.profile.duplicate_pct}%`],
                      ['Quality', `${table.profile.quality_score}%`],
                      ['Size', `${table.profile.memory_mb} MB`],
                    ].map(([label, val]) => (
                      <div key={label}>
                        <p className="text-dark-muted">{label}</p>
                        <p className="text-white font-medium">{val}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Column list */}
                <div className="divide-y divide-dark-border">
                  {table.columns?.map(col => (
                    <div key={col.name} className="px-4 py-2.5 flex items-center gap-3 hover:bg-dark-bg/20">
                      {dtypeIcon(col)}
                      <span className="text-white text-sm font-mono w-40 truncate">{col.name}</span>
                      <span className="text-dark-muted text-xs font-mono w-20 hidden md:block">{col.dtype}</span>
                      <div className="flex-1 hidden md:block">
                        <div className="h-1.5 bg-dark-bg rounded-full overflow-hidden w-24">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${100 - col.null_pct}%` }} />
                        </div>
                      </div>
                      <span className="text-dark-muted text-xs ml-auto">{col.null_pct}% null</span>
                      <span className="text-dark-muted text-xs w-16 text-right hidden md:block">{col.unique_count} uniq</span>
                      <div className="text-xs text-dark-muted/60 max-w-xs truncate hidden lg:block">
                        {col.sample_values?.slice(0, 3).join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Relationships */}
      {rels.length > 0 && (
        <div>
          <h3 className="text-white font-semibold mb-3">Detected Relationships</h3>
          <div className="space-y-2">
            {rels.map((rel, i) => (
              <div key={i} className="bg-dark-surface border border-dark-border rounded-lg px-4 py-3 flex items-center gap-3 text-sm">
                <span className="text-blue-400 font-mono truncate">{rel.from_table}</span>
                <span className="text-dark-muted">→ <span className="font-mono text-xs bg-dark-bg px-1.5 py-0.5 rounded">{rel.column}</span> →</span>
                <span className="text-green-400 font-mono truncate">{rel.to_table}</span>
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full
                  ${rel.confidence === 'high' ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                  {rel.confidence}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
