<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span class="title">风险与预警</span>
      <el-button @click="load">刷新</el-button>
    </div>

    <!-- 风险统计 -->
    <el-row :gutter="16" class="summary">
      <el-col :span="6">
        <el-statistic title="风险总数" :value="risks.length" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="高风险" :value="countByLevel('高')" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="中风险" :value="countByLevel('中')" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="临期预警" :value="warnings.length" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="14">
        <el-card class="page-card" shadow="never">
          <div class="toolbar">
            <span class="chart-title">风险项</span>
            <div class="filters">
              <el-select v-model="fLevel" placeholder="等级" clearable style="width: 110px">
                <el-option label="高" value="高" />
                <el-option label="中" value="中" />
                <el-option label="低" value="低" />
              </el-select>
              <el-select v-model="fStatus" placeholder="状态" clearable style="width: 120px">
                <el-option label="未处理" value="未处理" />
                <el-option label="处理中" value="处理中" />
                <el-option label="已闭环" value="已闭环" />
              </el-select>
              <el-input v-model="fType" placeholder="类型" clearable style="width: 130px" />
            </div>
          </div>
          <el-table :data="filteredRisks" border>
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="risk_type" label="类型" />
            <el-table-column prop="level" label="等级" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.level)" effect="dark">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="due" label="到期" width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="page-card" shadow="never">
          <div class="chart-title">风险等级分布</div>
          <div ref="chartPie" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-divider />
    <div class="toolbar"><span class="chart-title">临期预警</span></div>
    <el-table :data="warnings" border>
      <el-table-column prop="name" label="资料" />
      <el-table-column prop="category" label="类别" />
      <el-table-column prop="owner" label="负责人" />
      <el-table-column prop="due" label="到期" width="120" />
      <el-table-column prop="days_left" label="剩余天数" width="110">
        <template #default="{ row }">
          <el-tag :type="daysType(row.days_left)" effect="dark">{{ row.days_left }} 天</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { listRiskItemsApi, listWarningsApi } from '@/api/progress'

const risks = ref<any[]>([])
const warnings = ref<any[]>([])
const fLevel = ref<string>('')
const fStatus = ref<string>('')
const fType = ref<string>('')

const chartPie = ref<HTMLElement>()
let pie: echarts.ECharts | null = null

const filteredRisks = computed(() =>
  risks.value.filter(
    (r) =>
      (!fLevel.value || r.level === fLevel.value) &&
      (!fStatus.value || r.status === fStatus.value) &&
      (!fType.value || (r.risk_type || '').includes(fType.value)),
  ),
)

function countByLevel(level: string) {
  return risks.value.filter((r) => r.level === level).length
}
function levelType(l: string) {
  if (l === '高') return 'danger'
  if (l === '中') return 'warning'
  return 'info'
}
function statusType(s: string) {
  if (s === '已闭环') return 'success'
  if (s === '处理中') return 'warning'
  return 'info'
}
function daysType(d: number) {
  if (d <= 7) return 'danger'
  if (d <= 14) return 'warning'
  return 'success'
}

function renderPie() {
  const counts = { 高: countByLevel('高'), 中: countByLevel('中'), 低: countByLevel('低') }
  pie?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    color: ['#f56c6c', '#e6a23c', '#909399'],
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { name: '高', value: counts.高 },
        { name: '中', value: counts.中 },
        { name: '低', value: counts.低 },
      ],
    }],
  })
}

async function load() {
  risks.value = await listRiskItemsApi()
  warnings.value = await listWarningsApi()
  renderPie()
}

function resize() {
  pie?.resize()
}
onMounted(async () => {
  if (chartPie.value) pie = echarts.init(chartPie.value)
  window.addEventListener('resize', resize)
  await load()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  pie?.dispose()
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; }
.title { font-weight: 600; font-size: 16px; }
.summary { margin: 12px 0; }
.mt { margin-top: 12px; }
.chart-title { font-weight: 600; }
.filters { display: flex; gap: 8px; }
.chart { height: 260px; }
</style>
