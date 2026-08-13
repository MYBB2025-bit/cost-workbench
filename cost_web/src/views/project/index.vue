<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>工程项目</span>
      <el-button type="primary" v-permission="['project:create']" @click="dialog = true">新建项目</el-button>
    </div>
    <el-table :data="list" border>
      <el-table-column prop="project_code" label="项目编号" />
      <el-table-column prop="project_name" label="项目名称" />
      <el-table-column prop="contract_amount" label="合同金额" />
      <el-table-column prop="status" label="状态" />
    </el-table>

    <el-dialog v-model="dialog" title="新建项目">
      <el-form :model="form">
        <el-form-item label="项目名称"><el-input v-model="form.project_name" /></el-form-item>
        <el-form-item label="项目编号"><el-input v-model="form.project_code" /></el-form-item>
        <el-form-item label="合同金额"><el-input v-model="form.contract_amount" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="onCreate">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listProjectsApi, createProjectApi } from '@/api/project'

const list = ref<any[]>([])
const dialog = ref(false)
const form = reactive({ project_name: '', project_code: '', contract_amount: '' })

async function load() {
  list.value = await listProjectsApi()
}
async function onCreate() {
  await createProjectApi({ ...form })
  ElMessage.success('创建成功')
  dialog.value = false
  await load()
}
onMounted(load)
</script>
