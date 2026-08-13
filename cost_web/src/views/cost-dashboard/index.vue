<template>
  <div class="cost-dashboard">
    <el-card class="page-card">
      <div class="toolbar">
        <span class="title">造价总览看板</span>
        <div class="toolbar-right">
          <el-select v-model="projectId" placeholder="全部项目" clearable style="width: 220px">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
          <el-button @click="load">刷新</el-button>
          <el-button type="primary" @click="onPrint">打印 / 导出报表</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="mt">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">预算合价总额</div>
          <div class="stat-value money">{{ fmt(data.budget_total) }}</div>
          <div class="stat-sub">清单项 {{ data.budget_count }} 条</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">变更金额合计</div>
          <div class="stat-value money warning">{{ fmt(data.change_total) }}</div>
          <div class="stat-sub">变更单 {{ data.change_count }} 份</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">结算金额合计</div>
          <div class="stat-value money success">{{ fmt(data.settlement_total) }}</div>
          <div class="stat-sub">结算单 {{ data.settlement_count }} 份</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">结算/预算比</div>
          <div class="stat-value">{{ ratio }}%</div>
          <div class="stat-sub">结算额 ÷ 预算额</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 风险概览 -->
    <el-row :gutter="16" class="mt">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">风险总数</div>
          <div class="stat-value">{{ riskTotal }}</div>
          <div class="stat-sub">需关注事项</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">高风险</div>
          <div class="stat-value" style="color:#f56c6c">{{ riskHigh }}</div>
          <div class="stat-sub">需优先处理</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">中风险</div>
          <div class="stat-value" style="color:#e6a23c">{{ riskMid }}</div>
          <div class="stat-sub">持续跟踪</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">临期预警</div>
          <div class="stat-value" style="color:#909399">{{ warningTotal }}</div>
          <div class="stat-sub">资料即将到期</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="12">
        <el-card class="page-card">
          <div class="chart-title">预算合价 · 按项目</div>
          <div ref="chartProject" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="page-card">
          <div class="chart-title">预算合价 · 按科目</div>
          <div ref="chartCategory" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="12">
        <el-card class="page-card">
          <div class="chart-title">变更金额 TOP</div>
          <div ref="chartChange" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="page-card">
          <div class="chart-title">结算金额 · 按状态</div>
          <div ref="chartSettle" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="12">
        <el-card class="page-card">
          <div class="chart-title">项目进度款执行率{{ projectId ? '' : '（选择项目查看）' }}</div>
          <div ref="chartGauge" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="page-card">
          <div class="chart-title">风险等级分布</div>
          <div ref="chartRiskPie" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { listProjectsApi } from '@/api/project'
import { getCostOverviewApi } from '@/api/stats'
import { listRiskItemsApi, listWarningsApi, paymentStatsApi } from '@/api/progress'

const projects = ref<any[]>([])
const projectId = ref<number | undefined>(undefined)
const data = ref<any>({
  budget_total: 0, budget_count: 0, by_category: [], by_project: [],
  change_total: 0, change_count: 0, change_top: [],
  settlement_total: 0, settlement_count: 0, by_settlement_status: [],
})
const ratio = ref('0.0')
const charts: echarts.ECharts[] = []
const chartProject = ref<HTMLElement>()
const chartCategory = ref<HTMLElement>()
const chartChange = ref<HTMLElement>()
const chartSettle = ref<HTMLElement>()
const chartGauge = ref<HTMLElement>()
const chartRiskPie = ref<HTMLElement>()

const risks = ref<any[]>([])
const warnings = ref<any[]>([])
const riskTotal = computed(() => risks.value.length)
const riskHigh = computed(() => risks.value.filter((r) => r.level === '高').length)
const riskMid = computed(() => risks.value.filter((r) => r.level === '中').length)
const warningTotal = computed(() => warnings.value.length)

function fmt(n: number) {
  return '¥' + Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function initCharts() {
  for (const el of [chartProject.value, chartCategory.value, chartChange.value, chartSettle.value, chartGauge.value, chartRiskPie.value]) {
    if (el) charts.push(echarts.init(el))
  }
  window.addEventListener('resize', resize)
}
function resize() {
  charts.forEach((c) => c.resize())
}
function render() {
  const d = data.value
  // 按项目
  charts[0]?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: d.by_project.map((p: any) => p.project_name), axisLabel: { interval: 0, rotate: 20 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: d.by_project.map((p: any) => p.total), itemStyle: { color: '#409eff' } }],
  })
  // 按科目
  charts[1]?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: d.by_category.map((c: any) => ({ name: c.category, value: c.total })),
    }],
  })
  // 变更 TOP
  charts[2]?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: d.change_top.map((c: any) => c.change_no || c.name).reverse() },
    series: [{ type: 'bar', data: d.change_top.map((c: any) => c.amount).reverse(), itemStyle: { color: '#e6a23c' } }],
  })
  // 结算状态
  charts[3]?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: d.by_settlement_status.map((s: any) => ({ name: s.status, value: s.total })),
    }],
  })
  // 执行率仪表
  const g = gaugeData.value
  const rate = g && g.total_estimate > 0 ? Math.round((g.total_audited / g.total_estimate) * 1000) / 10 : 0
  charts[4]?.setOption({
    series: [{
      type: 'gauge', min: 0, max: 100, progress: { show: true },
      detail: { formatter: '{value}%', fontSize: 20 }, data: [{ value: rate }],
      title: { offsetCenter: [0, '72%'], fontSize: 12 },
    }],
  })
  // 风险等级分布
  charts[5]?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    color: ['#f56c6c', '#e6a23c', '#909399'],
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { name: '高', value: riskHigh.value },
        { name: '中', value: riskMid.value },
        { name: '低', value: risks.value.filter((r) => r.level === '低').length },
      ],
    }],
  })
}

const gaugeData = ref<any>(null)

async function loadRisks() {
  risks.value = await listRiskItemsApi()
  warnings.value = await listWarningsApi()
  if (charts[5]) render()
}
async function loadGauge() {
  if (!projectId.value) {
    gaugeData.value = null
    return
  }
  const res: any = await paymentStatsApi(Number(projectId.value))
  gaugeData.value = res.summary || null
  if (charts[4]) render()
}

async function load() {
  const res: any = await getCostOverviewApi(projectId.value)
  data.value = res
  const b = Number(res.budget_total || 0)
  const s = Number(res.settlement_total || 0)
  ratio.value = b > 0 ? ((s / b) * 100).toFixed(1) : '0.0'
  render()
}

function onPrint() {
  window.print()
}

watch(projectId, async () => {
  await load()
  await loadGauge()
})
onMounted(async () => {
  initCharts()
  const res: any = await listProjectsApi()
  projects.value = res || []
  await load()
  await loadRisks()
  await loadGauge()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
})
</script>

<style scoped>
.mt { margin-top: 16px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.title { font-weight: 600; font-size: 16px; }
.stat-card { text-align: center; }
.stat-title { color: #909399; font-size: 13px; }
.stat-value { font-size: 26px; font-weight: 700; margin: 8px 0; }
.stat-value.money { color: #409eff; }
.stat-value.warning { color: #e6a23c; }
.stat-value.success { color: #67c23a; }
.stat-sub { color: #909399; font-size: 12px; }
.chart-title { font-weight: 600; margin-bottom: 8px; }
.chart { height: 300px; }
@media print {
  .toolbar-right { display: none; }
}
</style>
