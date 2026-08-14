<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span class="title">风险与预警</span>
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
        <el-button type="primary" @click="openCreate">新增风险</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
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
          </div>
          <el-table :data="filteredRisks" border>
            <el-table-column prop="title" label="标题" min-width="140" />
            <el-table-column prop="risk_type" label="类型" width="100" />
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
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="remove(row)">删除</el-button>
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

    <!-- 新增 / 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑风险项' : '新增风险项'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="所属项目" required>
          <el-select v-model="form.project_id" placeholder="请选择项目" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="如：土方签证超报风险" />
        </el-form-item>
        <el-form-item label="类型">
          <el-input v-model="form.risk_type" placeholder="如：签证、结算、进度款" />
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="form.level" placeholder="请选择" style="width: 100%">
            <el-option label="高" value="高" />
            <el-option label="中" value="中" />
            <el-option label="低" value="低" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="请选择" style="width: 100%">
            <el-option label="未处理" value="未处理" />
            <el-option label="处理中" value="处理中" />
            <el-option label="已闭环" value="已闭环" />
          </el-select>
        </el-form-item>
        <el-form-item label="到期日">
          <el-input v-model="form.due" placeholder="如：2026-09-30" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.desc" type="textarea" :rows="3" placeholder="风险描述与应对建议" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { listRiskItemsApi, listWarningsApi, createRiskItemApi, updateRiskItemApi, deleteRiskItemApi } from '@/api/progress'
import { listProjectsApi } from '@/api/project'

const risks = ref<any[]>([])
const warnings = ref<any[]>([])
const projects = ref<any[]>([])
const fLevel = ref<string>('')
const fStatus = ref<string>('')
const fType = ref<string>('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

const chartPie = ref<HTMLElement>()
let pie: echarts.ECharts | null = null

const form = reactive({
  project_id: undefined as number | undefined,
  risk_type: '',
  level: '',
  title: '',
  desc: '',
  due: '',
  status: '未处理',
})

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

function resetForm() {
  form.project_id = undefined
  form.risk_type = ''
  form.level = ''
  form.title = ''
  form.desc = ''
  form.due = ''
  form.status = '未处理'
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  form.project_id = row.project_id
  form.risk_type = row.risk_type || ''
  form.level = row.level || ''
  form.title = row.title || ''
  form.desc = row.desc || ''
  form.due = row.due || ''
  form.status = row.status || '未处理'
  dialogVisible.value = true
}

async function submit() {
  if (!form.project_id) {
    ElMessage.warning('请选择所属项目')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, any> = {
      project_id: form.project_id,
      risk_type: form.risk_type || null,
      level: form.level || null,
      title: form.title || null,
      desc: form.desc || null,
      due: form.due || null,
      status: form.status || null,
    }
    if (editingId.value) {
      await updateRiskItemApi(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createRiskItemApi(payload)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除风险项「${row.title || row.id}」？`, '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteRiskItemApi(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
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
  try {
    projects.value = await listProjectsApi()
  } catch {
    projects.value = []
  }
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
.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.chart { height: 260px; }
</style>
