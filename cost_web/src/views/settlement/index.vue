<template>
  <div class="settlement-page">
    <el-card>
      <template #header>
        <div class="header">
          <span>结算</span>
          <div>
            <el-select v-model="selectedProject" placeholder="选择项目" clearable style="width: 220px; margin-right: 12px">
              <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
            <el-button type="primary" v-permission="'settlement:create'" @click="openDialog()">新增结算</el-button>
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading">
        <el-table-column prop="settlement_no" label="结算编号" />
        <el-table-column prop="settlement_name" label="名称" />
        <el-table-column prop="settlement_type" label="类型" />
        <el-table-column prop="total_amount" label="金额" />
        <el-table-column prop="status" label="状态" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button link type="primary" @click="view(row)">查看</el-button>
            <el-button link type="danger" v-permission="'settlement:delete'" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="visible" title="结算单" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目">
          <el-select v-model="form.project_id">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="编号"><el-input v-model="form.settlement_no" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.settlement_name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="form.settlement_type" /></el-form-item>
        <el-form-item label="金额"><el-input-number v-model="form.total_amount" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-input v-model="form.status" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="结算明细" width="700px">
      <p>{{ current?.settlement_name }} - 金额 {{ current?.total_amount }}</p>
      <el-table :data="currentItems" size="small">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="unit" label="单位" />
        <el-table-column prop="settle_qty" label="结算量" />
        <el-table-column prop="unit_price" label="单价" />
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
import { getSettlementListApi, getSettlementDetailApi, createSettlementApi, deleteSettlementApi } from '@/api/settlement'

const projects = ref<any[]>([])
const selectedProject = ref<number | undefined>(undefined)
const loading = ref(false)
const list = ref<any[]>([])
const visible = ref(false)
const form = ref<any>({})
const detailVisible = ref(false)
const current = ref<any>({})
const currentItems = ref<any[]>([])

async function loadProjects() {
  const res: any = await listProjectsApi()
  projects.value = res || []
  if (projects.value.length && !selectedProject.value) selectedProject.value = projects.value[0].id
}

async function loadList() {
  if (!selectedProject.value) return
  loading.value = true
  try {
    const res: any = await getSettlementListApi(selectedProject.value)
    list.value = res || []
  } finally {
    loading.value = false
  }
}

function openDialog() {
  form.value = { project_id: selectedProject.value, total_amount: 0, settlement_type: 'midterm', status: 'draft' }
  visible.value = true
}

async function submit() {
  await createSettlementApi(form.value)
  ElMessage.success('保存成功')
  visible.value = false
  loadList()
}

async function view(row: any) {
  const res: any = await getSettlementDetailApi(row.id)
  current.value = res
  currentItems.value = res.items || []
  detailVisible.value = true
}

async function remove(row: any) {
  await ElMessageBox.confirm('确认删除结算单？', '提示', { type: 'warning' })
  await deleteSettlementApi(row.id)
  ElMessage.success('删除成功')
  loadList()
}

watch(selectedProject, loadList, { immediate: true })
loadProjects()
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
