<template>
  <div class="budget-page">
    <el-card>
      <template #header>
        <div class="header">
          <span>预算清单</span>
          <div>
            <el-select v-model="selectedProject" placeholder="选择项目" clearable style="width: 220px; margin-right: 12px">
              <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
            <el-button v-permission="'budget:create'" @click="onPickFile">Excel 批量导入</el-button>
            <el-button v-permission="'budget:create'" @click="openAsync">异步导入（大文件）</el-button>
            <el-button type="primary" v-permission="'budget:create'" @click="openDialog()">新增清单</el-button>
            <input ref="fileInput" type="file" accept=".xlsx" style="display: none" @change="onFile" />
          </div>
        </div>
      </template>
      <el-table :data="tableData" row-key="id" default-expand-all :tree-props="{ children: 'children' }">
        <el-table-column prop="item_no" label="编号" width="120" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="spec" label="规格" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="qty" label="工程量" width="100" />
        <el-table-column prop="unit_price" label="综合单价" width="120" />
        <el-table-column prop="total_price" label="合价" width="120" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link type="primary" v-permission="'budget:update'" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" v-permission="'budget:delete'" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="visible" :title="form.id ? '编辑清单' : '新增清单'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目">
          <el-select v-model="form.project_id" placeholder="选择项目">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="编号">
          <el-input v-model="form.item_no" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.spec" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" />
        </el-form-item>
        <el-form-item label="工程量">
          <el-input-number v-model="form.qty" :min="0" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="form.unit_price" :min="0" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 异步导入（大文件） -->
    <el-dialog v-model="asyncVisible" title="异步导入预算清单（大文件）" width="460px">
      <div v-if="!asyncJobId">
        <el-button @click="pickAsyncFile">选择 Excel(.xlsx)</el-button>
        <span v-if="asyncFileName" style="margin-left: 8px">{{ asyncFileName }}</span>
        <p class="tip">大文件先落盘再由后台 worker 处理，不阻塞页面；可关闭弹窗稍后查看进度。</p>
      </div>
      <div v-else>
        <el-progress :percentage="asyncProgress" :status="progressStatus" />
        <p>状态：<b>{{ asyncStatus }}</b></p>
        <p v-if="asyncResult">新增 {{ asyncResult.created ?? 0 }} 条，跳过 {{ asyncResult.skipped ?? 0 }} 条</p>
        <p v-if="asyncMsg" class="err">{{ asyncMsg }}</p>
      </div>
      <template #footer>
        <el-button v-if="!asyncJobId" type="primary" :disabled="!asyncFile" @click="startAsync">开始导入</el-button>
        <el-button @click="closeAsync">{{ asyncJobId ? '关闭并刷新' : '取消' }}</el-button>
      </template>
    </el-dialog>
    <input ref="asyncFileInput" type="file" accept=".xlsx" style="display: none" @change="onAsyncFile" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listProjectsApi } from '@/api/project'
import { getBudgetTreeApi, createBudgetApi, updateBudgetApi, deleteBudgetApi, importBudgetApi, importBudgetAsyncApi } from '@/api/budget'
import { getTaskStatusApi } from '@/api/task'

const projects = ref<any[]>([])
const selectedProject = ref<number | undefined>(undefined)
const tableData = ref<any[]>([])
const visible = ref(false)
const form = ref<any>({})
const fileInput = ref<HTMLInputElement>()

// 异步导入（大文件）
const asyncVisible = ref(false)
const asyncFileInput = ref<HTMLInputElement>()
const asyncFile = ref<File | null>(null)
const asyncFileName = ref('')
const asyncJobId = ref('')
const asyncStatus = ref('')
const asyncProgress = ref(0)
const asyncResult = ref<any>(null)
const asyncMsg = ref('')
let asyncTimer: ReturnType<typeof setInterval> | null = null
const progressStatus = computed(() =>
  asyncStatus.value === 'failed' ? 'exception' : asyncStatus.value === 'success' ? 'success' : undefined,
)

async function loadProjects() {
  const res: any = await listProjectsApi()
  projects.value = res || []
  if (projects.value.length && !selectedProject.value) {
    selectedProject.value = projects.value[0].id
  }
}

async function loadBudget() {
  if (!selectedProject.value) return
  const res: any = await getBudgetTreeApi(selectedProject.value)
  tableData.value = res || []
}

function onPickFile() {
  if (!selectedProject.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  fileInput.value?.click()
}

async function onFile(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  try {
    const res: any = await importBudgetApi(selectedProject.value as number, file)
    ElMessage.success(`导入完成：新增 ${res.created} 条，跳过 ${res.skipped} 条`)
    if (res.errors && res.errors.length) {
      console.warn('导入异常行：', res.errors)
    }
    loadBudget()
  } catch (err: any) {
    ElMessage.error('导入失败：' + (err?.message || '未知错误'))
  } finally {
    target.value = ''
  }
}

function openDialog(row?: any) {
  form.value = row ? { ...row } : { project_id: selectedProject.value, qty: 0, unit_price: 0 }
  visible.value = true
}

async function submit() {
  if (form.value.id) {
    await updateBudgetApi(form.value.id, form.value)
  } else {
    await createBudgetApi(form.value)
  }
  ElMessage.success('保存成功')
  visible.value = false
  loadBudget()
}

async function remove(row: any) {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await deleteBudgetApi(row.id)
  ElMessage.success('删除成功')
  loadBudget()
}

// ---------- 异步导入 ----------
function openAsync() {
  if (!selectedProject.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  asyncFile.value = null
  asyncFileName.value = ''
  asyncJobId.value = ''
  asyncStatus.value = ''
  asyncProgress.value = 0
  asyncResult.value = null
  asyncMsg.value = ''
  asyncVisible.value = true
}

function pickAsyncFile() {
  asyncFileInput.value?.click()
}

function onAsyncFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) {
    asyncFile.value = f
    asyncFileName.value = f.name
  }
  ;(e.target as HTMLInputElement).value = ''
}

async function startAsync() {
  if (!asyncFile.value || !selectedProject.value) return
  try {
    const res: any = await importBudgetAsyncApi(selectedProject.value as number, asyncFile.value)
    asyncJobId.value = res.job_id
    asyncStatus.value = res.status
    pollAsync()
  } catch {
    /* 错误由响应拦截器统一提示 */
  }
}

function pollAsync() {
  if (!asyncJobId.value) return
  asyncTimer = setInterval(async () => {
    try {
      const r: any = await getTaskStatusApi(asyncJobId.value)
      asyncStatus.value = r.status
      asyncProgress.value = r.progress || 0
      if (r.status === 'success') {
        asyncResult.value = r.result
        if (asyncTimer) clearInterval(asyncTimer)
        asyncTimer = null
      } else if (r.status === 'failed') {
        asyncMsg.value = r.error || '导入失败'
        if (asyncTimer) clearInterval(asyncTimer)
        asyncTimer = null
      }
    } catch {
      /* 轮询异常忽略 */
    }
  }, 1200)
}

function closeAsync() {
  if (asyncTimer) {
    clearInterval(asyncTimer)
    asyncTimer = null
  }
  asyncVisible.value = false
  if (asyncStatus.value === 'success') loadBudget()
}

watch(selectedProject, loadBudget, { immediate: true })
loadProjects()
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tip {
  color: #909399;
  font-size: 12px;
  margin-top: 12px;
}
.err {
  color: #f56c6c;
}
</style>
