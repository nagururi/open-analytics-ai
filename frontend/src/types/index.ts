export interface User {
  username: string
  email: string
  role: string
}

export interface Dataset {
  id: string
  name: string
  original_filename: string
  file_type: string
  row_count: number
  size_bytes: number
  created_at: string
  tables_json?: { tables: TableInfo[]; relationships: Relationship[] }
}

export interface TableInfo {
  table_name: string
  display_name: string
  row_count: number
  column_count: number
  columns: ColumnInfo[]
  profile: DataProfile
}

export interface ColumnInfo {
  name: string
  dtype: string
  null_count: number
  null_pct: number
  unique_count: number
  sample_values: any[]
  is_numeric: boolean
  is_datetime: boolean
  is_categorical: boolean
  min?: number
  max?: number
  mean?: number
  std?: number
}

export interface DataProfile {
  total_rows: number
  total_columns: number
  null_cells: number
  null_pct: number
  duplicate_rows: number
  duplicate_pct: number
  quality_score: number
  memory_mb: number
}

export interface Relationship {
  from_table: string
  to_table: string
  column: string
  confidence: string
}

export interface QueryResult {
  query_id: string
  success: boolean
  sql: string
  generated_sql?: string
  explanation?: string
  columns: string[]
  rows: Record<string, any>[]
  row_count: number
  execution_time_ms: number
  errors: string[]
  charts?: ChartConfig[]
  model?: string
}

export interface ChartConfig {
  type: string
  title: string
  config?: Record<string, any>
  kpis?: KPI[]
}

export interface KPI {
  label: string
  value: number
  avg: number
  count: number
}

export interface QueryHistoryItem {
  id: string
  natural_language: string
  generated_sql: string
  row_count: number
  execution_time_ms: number
  is_valid: number
  is_favorite: number
  created_at: string
  dataset_id: string
}

export interface Dashboard {
  id: string
  name: string
  description: string
  config_json: any
  created_by: string
  is_public: number
  created_at: string
}
