import ReactECharts from 'echarts-for-react'
import { ChartConfig, KPI } from '../../types'
import { formatNumber } from '../../utils/api'
import { TrendingUp, Hash, BarChart2, Activity } from 'lucide-react'

interface Props { charts: ChartConfig[] }

export default function ChartGrid({ charts }: Props) {
  const kpiChart = charts.find(c => c.type === 'kpi')
  const otherCharts = charts.filter(c => c.type !== 'kpi')

  return (
    <div className="space-y-4">
      {/* KPI Cards */}
      {kpiChart?.kpis && kpiChart.kpis.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {kpiChart.kpis.map((kpi, i) => (
            <KPICard key={i} kpi={kpi} index={i} />
          ))}
        </div>
      )}

      {/* Charts grid */}
      {otherCharts.length > 0 && (
        <div className={`grid gap-4 ${otherCharts.length === 1 ? '' : 'md:grid-cols-2'}`}>
          {otherCharts.map((chart, i) => (
            <div key={i} className="bg-dark-surface border border-dark-border rounded-xl p-4">
              <h4 className="text-white text-sm font-medium mb-3">{chart.title}</h4>
              {chart.config && (
                <ReactECharts
                  option={{
                    ...chart.config,
                    backgroundColor: 'transparent',
                    textStyle: { color: '#94a3b8' },
                    legend: chart.config.legend ? {
                      ...chart.config.legend,
                      textStyle: { color: '#94a3b8' }
                    } : undefined,
                  }}
                  style={{ height: 280 }}
                  theme="dark"
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function KPICard({ kpi, index }: { kpi: KPI; index: number }) {
  const colors = ['text-blue-400', 'text-green-400', 'text-purple-400', 'text-orange-400']
  const icons = [TrendingUp, Hash, BarChart2, Activity]
  const Icon = icons[index % icons.length]
  const color = colors[index % colors.length]

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-dark-muted text-xs font-medium truncate">{kpi.label}</p>
        <Icon className={`w-4 h-4 shrink-0 ${color}`} />
      </div>
      <p className={`text-2xl font-bold ${color}`}>{formatNumber(kpi.value)}</p>
      <p className="text-dark-muted text-xs mt-1">avg {formatNumber(kpi.avg)} · {kpi.count.toLocaleString()} records</p>
    </div>
  )
}
