<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>最终资料台账</span>
      <div>
        <el-select v-model="projectId" placeholder="全部项目" clearable style="width: 200px; margin-right: 12px">
          <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
        </el-select>
        <el-button type="primary" v-permission="'ledger:view'" @click="onExport">导出 CSV</el-button>
        <el-button v-permission="'ledger:view'" @click="openAsyncExport">异步导出</el-button>
      </div>
    </div>

    <el-dialog v-model="expVisible" title="异步导出台账" width="460px">
      <div v-if="!expJobId">
        <p class="tip">大数据量导出将交由后台 worker 处理，不阻塞页面。</p>
      </div>
      <div v-else>
        <el-progress :percentage="expProgress" :status="expStatus === 'failed' ? 'exception' : expStatus === 'success' ? 'success' : undefined" />
        <p>状态：<b>{{ expStatus }}</b></p>
        <p v-if="expResult">共 {{ expResult.count ?? 0 }} 条</p>
        <p v-if="expMsg" class="err">{{ expMsg }}</p>
        <el-button v-if="expStatus === 'success'" type="primary" @click="onDownload">下载文件</el-button>
      </div>
      <template #footer>
        <el-button v-if="!expJobId" type="primary" @click="startAsyncExport">开始导出</el-button>
        <el-button @click="closeAsyncExport">{{ expJobId ? '关闭' : '取消' }}</el-button>
      </template>
    </el-dialog>
    <el-table :data="list" border>
      <el-table-column prop="project_name" label="项目" width="160" />
      <el-table-column prop="category" label="类别" width="120" />
      <el-table-column prop="name" label="资料名称" />
      <el-table-column prop="owner" label="负责人" width="100" />
      <el-table-column prop="due" label="截止" width="120" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'done' ? 'success' : 'warning'">{{ row.status === 'done' ? '已完成' : '待处理' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="finished_at" label="完成时间" width="120" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { listProjectsApi } from '@/api/project'
import { listLedgerApi, exportLedgerApi, exportLedgerAsyncApi } from '@/api/ledger'
import { getTaskStatusApi, downloadTaskApi } from '@/api/task'

const projects = ref<any[]>([])
const projectId = ref<number | undefined>(undefined)
const list = ref<any[]>([])

// 异步导出
const expVisible = ref(false)
const expJobId = ref('')
const expStatus = ref('')
const expProgress = ref(0)
const expResult = ref<any>(null)
const expMsg = ref('')
let expTimer: ReturnType<typeof setInterval> | null = null

async function load() {
  const res: any = await listLedgerApi(projectId.value)
  list.value = res || []
}
async function onExport() {
  try {
    const blob: any = await exportLedgerApi(projectId.value)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'ledger_export.csv'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

function openAsyncExport() {
  expJobId.value = ''
  expStatus.value = ''
  expProgress.value = 0
  expResult.value = null
  expMsg.value = ''
  expVisible.value = true
}
async function startAsyncExport() {
  try {
    const res: any = await exportLedgerAsyncApi(projectId.value)
    expJobId.value = res.job_id
    expStatus.value = res.status
    pollExport()
  } catch {
    /* 拦截器统一提示 */
  }
}
function pollExport() {
  if (!expJobId.value) return
  expTimer = setInterval(async () => {
    try {
      const r: any = await getTaskStatusApi(expJobId.value)
      expStatus.value = r.status
      expProgress.value = r.progress || 0
      if (r.status === 'success') {
        expResult.value = r.result
        if (expTimer) clearInterval(expTimer)
        expTimer = null
      } else if (r.status === 'failed') {
        expMsg.value = r.error || '导出失败'
        if (expTimer) clearInterval(expTimer)
        expTimer = null
      }
    } catch {
      /* 忽略轮询异常 */
    }
  }, 1200)
}
async function onDownload() {
  if (!expJobId.value) return
  const fname = expResult.value?.filename || 'ledger_export.csv'
  await downloadTaskApi(expJobId.value, fname)
}
function closeAsyncExport() {
  if (expTimer) {
    clearInterval(expTimer)
    expTimer = null
  }
  expVisible.value = false
}

watch(projectId, load)
onMounted(async () => {
  const res: any = await listProjectsApi()
  projects.value = res || []
  await load()
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tip { color: #909399; font-size: 12px; margin-top: 12px; }
.err { color: #f56c6c; }
</style>
