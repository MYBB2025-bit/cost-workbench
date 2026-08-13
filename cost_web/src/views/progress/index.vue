<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span class="title">进度款审核</span>
      <el-button type="primary" v-permission="['progress:create']" @click="dialog = true">新增进度款</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="pid" placeholder="选择项目" style="width: 220px" @change="loadStats">
        <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
      </el-select>
      <el-button @click="loadStats">查询汇总</el-button>
    </div>

    <!-- 汇总统计 + 执行率仪表 -->
    <el-row :gutter="16" class="summary">
      <el-col :span="6">
        <el-statistic title="估算总额" :value="summary?.total_estimate || 0" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="申报总额" :value="summary?.total_applied || 0" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="审核总额" :value="summary?.total_audited || 0" />
      </el-col>
      <el-col :span="6">
        <el-card class="gauge-card" shadow="never">
          <div ref="chartGauge" class="gauge"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="14">
        <el-card class="page-card" shadow="never">
          <div class="chart-title">估算 / 申报 / 审核 对比</div>
          <div ref="chartBar" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="page-card" shadow="never">
          <div class="chart-title">进度款状态分布</div>
          <div ref="chartStatus" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-divider />
    <div class="toolbar"><span>进度款清单</span></div>
    <el-table :data="list" border>
      <el-table-column prop="period_name" label="期次" />
      <el-table-column prop="apply_amount" label="申报金额" />
      <el-table-column prop="audit_amount" label="审核金额" />
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status || '待审核' }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-divider />
    <div class="toolbar"><span>WBS 进度款统计（父/子累加）</span></div>
    <el-table v-if="statsTree.length" :data="statsTree" row-key="id" default-expand-all
              :tree-props="{ children: 'children' }" border class="mt">
      <el-table-column prop="name" label="节点" />
      <el-table-column prop="own_estimate" label="自身估算" width="110" />
      <el-table-column prop="own_applied" label="自身申报" width="110" />
      <el-table-column prop="own_audited" label="自身审核" width="110" />
      <el-table-column prop="total_estimate" label="累计估算" width="110" />
      <el-table-column prop="total_applied" label="累计申报" width="110" />
      <el-table-column prop="total_audited" label="累计审核" width="110" />
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>

    <el-dialog v-model="dialog" title="新增进度款">
      <el-form :model="form">
        <el-form-item label="项目">
          <el-select v-model="form.project_id" placeholder="选择项目" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="期次"><el-input v-model="form.period_name" /></el-form-item>
        <el-form-item label="申报金额"><el-input v-model="form.apply_amount" /></el-form-item>
        <el-form-item label="审核金额"><el-input v-model="form.audit_amount" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="选择状态" style="width: 100%">
            <el-option label="待审核" value="待审核" />
            <el-option label="已申报" value="已申报" />
            <el-option label="已审核" value="已审核" />
            <el-option label="已支付" value="已支付" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="onCreate">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { listProjectsApi } from '@/api/project'
import { listProgressApi, createProgressApi, paymentStatsApi } from '@/api/progress'

const projects = ref<any[]>([])
const list = ref<any[]>([])
const dialog = ref(false)
const pid = ref<number | undefined>(undefined)
const statsTree = ref<any[]>([])
const summary = ref<any>(null)

const chartGauge = ref<HTMLElement>()
const chartBar = ref<HTMLElement>()
const chartStatus = ref<HTMLElement>()
const charts: echarts.ECharts[] = []

const form = reactive({ project_id: undefined as number | undefined, period_name: '', apply_amount: '', audit_amount: '', status: '待审核' })

function statusType(s: string) {
  if (s === '已支付' || s === '已审核') return 'success'
  if (s === '已申报') return 'warning'
  return 'info'
}
function statusColor(s: string) {
  if (s === '已支付' || s === '已审核') return '#67c23a'
  if (s === '已申报') return '#e6a23c'
  return '#909399'
}

function initCharts() {
  for (const el of [chartGauge.value, chartBar.value, chartStatus.value]) {
    if (el) charts.push(echarts.init(el))
  }
  window.addEventListener('resize', resize)
}
function resize() {
  charts.forEach((c) => c.resize())
}

function renderCharts() {
  const s = summary.value || {}
  const est = Number(s.total_estimate || 0)
  const aud = Number(s.total_audited || 0)
  const rate = est > 0 ? Math.round((aud / est) * 1000) / 10 : 0

  // 执行率仪表
  charts[0]?.setOption({
    series: [{
      type: 'gauge', min: 0, max: 100, progress: { show: true },
      detail: { formatter: '{value}%', fontSize: 18 }, data: [{ value: rate }],
      title: { offsetCenter: [0, '70%'], fontSize: 12 },
    }],
  })
  // 估算/申报/审核 对比
  charts[1]?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: ['估算', '申报', '审核'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [est, Number(s.total_applied || 0), aud],
      itemStyle: { color: '#409eff' },
    }],
  })
  // 状态分布
  const counts: Record<string, number> = {}
  for (const r of list.value) {
    const k = r.status || '待审核'
    counts[k] = (counts[k] || 0) + 1
  }
  charts[2]?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: Object.entries(counts).map(([k, v]) => ({ name: k, value: v, itemStyle: { color: statusColor(k) } })),
    }],
  })
}

async function load() {
  list.value = await listProgressApi()
}
async function loadStats() {
  if (!pid.value) return
  const res: any = await paymentStatsApi(Number(pid.value))
  statsTree.value = res.tree || []
  summary.value = res.summary || null
  renderCharts()
}
async function loadProjects() {
  const res: any = await listProjectsApi()
  projects.value = res || []
  if (!pid.value && projects.value.length) {
    pid.value = projects.value[0].id
    form.project_id = pid.value
  }
  if (pid.value) await loadStats()
}
async function onCreate() {
  if (!form.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  await createProgressApi({ ...form })
  ElMessage.success('创建成功')
  dialog.value = false
  await load()
  if (pid.value) await loadStats()
}
onMounted(async () => {
  initCharts()
  await loadProjects()
  await load()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; }
.title { font-weight: 600; font-size: 16px; }
.summary { margin: 12px 0; align-items: center; }
.gauge-card { padding: 0; }
.gauge { height: 90px; }
.mt { margin-top: 12px; }
.chart-title { font-weight: 600; margin-bottom: 8px; }
.chart { height: 260px; }
</style>
