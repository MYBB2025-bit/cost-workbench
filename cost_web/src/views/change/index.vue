<template>
  <div class="change-page">
    <el-card>
      <template #header>
        <div class="header">
          <span>变更签证</span>
          <div>
            <el-select v-model="selectedProject" placeholder="选择项目" clearable style="width: 220px; margin-right: 12px">
              <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
            <el-button type="primary" v-permission="'change:create'" @click="openChangeDialog()">新增变更</el-button>
            <el-button type="primary" v-permission="'change:create'" @click="openVisaDialog()">新增签证</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="变更单" name="change">
          <el-table :data="changeList" v-loading="loading">
            <el-table-column prop="change_no" label="变更编号" />
            <el-table-column prop="change_name" label="名称" />
            <el-table-column prop="change_type" label="类型" />
            <el-table-column prop="amount" label="金额" />
            <el-table-column prop="status" label="状态" />
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button link type="primary" @click="viewChange(row)">查看</el-button>
                <el-button link type="danger" v-permission="'change:delete'" @click="removeChange(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="签证" name="visa">
          <el-table :data="visaList" v-loading="loading">
            <el-table-column prop="visa_no" label="签证编号" />
            <el-table-column prop="visa_date" label="日期" />
            <el-table-column prop="content" label="内容" show-overflow-tooltip />
            <el-table-column prop="amount" label="金额" />
            <el-table-column prop="status" label="状态" />
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button link type="danger" v-permission="'change:delete'" @click="removeVisa(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="changeVisible" title="变更单" width="600px">
      <el-form :model="changeForm" label-width="80px">
        <el-form-item label="项目">
          <el-select v-model="changeForm.project_id">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="编号"><el-input v-model="changeForm.change_no" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="changeForm.change_name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="changeForm.change_type" /></el-form-item>
        <el-form-item label="金额"><el-input-number v-model="changeForm.amount" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-input v-model="changeForm.status" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeVisible = false">取消</el-button>
        <el-button type="primary" @click="submitChange">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="visaVisible" title="签证" width="500px">
      <el-form :model="visaForm" label-width="80px">
        <el-form-item label="项目">
          <el-select v-model="visaForm.project_id">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="编号"><el-input v-model="visaForm.visa_no" /></el-form-item>
        <el-form-item label="日期"><el-input v-model="visaForm.visa_date" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="visaForm.content" type="textarea" /></el-form-item>
        <el-form-item label="金额"><el-input-number v-model="visaForm.amount" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visaVisible = false">取消</el-button>
        <el-button type="primary" @click="submitVisa">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="变更明细" width="700px">
      <p>{{ currentChange?.change_name }} - 金额 {{ currentChange?.amount }}</p>
      <el-table :data="currentItems" size="small">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="unit" label="单位" />
        <el-table-column prop="before_qty" label="变更前" />
        <el-table-column prop="after_qty" label="变更后" />
        <el-table-column prop="delta_qty" label="差量" />
        <el-table-column prop="amount" label="金额" />
      </el-table>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listProjectsApi } from '@/api/project'
import {
  getChangeListApi, getChangeDetailApi, createChangeApi, deleteChangeApi,
  getVisaListApi, createVisaApi, deleteVisaApi
} from '@/api/change'

const projects = ref<any[]>([])
const selectedProject = ref<number | undefined>(undefined)
const activeTab = ref('change')
const loading = ref(false)
const changeList = ref<any[]>([])
const visaList = ref<any[]>([])

const changeVisible = ref(false)
const changeForm = ref<any>({})
const visaVisible = ref(false)
const visaForm = ref<any>({})
const detailVisible = ref(false)
const currentChange = ref<any>({})
const currentItems = ref<any[]>([])

async function loadProjects() {
  const res: any = await listProjectsApi()
  projects.value = res || []
  if (projects.value.length && !selectedProject.value) selectedProject.value = projects.value[0].id
}

async function loadData() {
  if (!selectedProject.value) return
  loading.value = true
  try {
    const [c, v]: any = await Promise.all([
      getChangeListApi(selectedProject.value),
      getVisaListApi(selectedProject.value)
    ])
    changeList.value = c || []
    visaList.value = v || []
  } finally {
    loading.value = false
  }
}

function openChangeDialog() {
  changeForm.value = { project_id: selectedProject.value, amount: 0, status: 'draft' }
  changeVisible.value = true
}

async function submitChange() {
  await createChangeApi(changeForm.value)
  ElMessage.success('保存成功')
  changeVisible.value = false
  loadData()
}

async function viewChange(row: any) {
  const res: any = await getChangeDetailApi(row.id)
  currentChange.value = res
  currentItems.value = res.items || []
  detailVisible.value = true
}

async function removeChange(row: any) {
  await ElMessageBox.confirm('确认删除变更单？', '提示', { type: 'warning' })
  await deleteChangeApi(row.id)
  ElMessage.success('删除成功')
  loadData()
}

function openVisaDialog() {
  visaForm.value = { project_id: selectedProject.value, amount: 0, status: 'draft' }
  visaVisible.value = true
}

async function submitVisa() {
  await createVisaApi(visaForm.value)
  ElMessage.success('保存成功')
  visaVisible.value = false
  loadData()
}

async function removeVisa(row: any) {
  await ElMessageBox.confirm('确认删除签证？', '提示', { type: 'warning' })
  await deleteVisaApi(row.id)
  ElMessage.success('删除成功')
  loadData()
}

watch(selectedProject, loadData, { immediate: true })
loadProjects()
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
