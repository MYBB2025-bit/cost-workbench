<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>用户管理</span>
      <el-button type="primary" v-permission="['user:edit']" @click="open()">新增用户</el-button>
    </div>

    <el-table :data="list" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'">{{ row.status === 1 ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_super" label="超管" width="80">
        <template #default="{ row }">
          {{ row.is_super ? '是' : '否' }}
        </template>
      </el-table-column>
      <el-table-column label="角色">
        <template #default="{ row }">
          <el-tag v-for="r in row.roles" :key="r.role_code" size="small" style="margin-right: 4px">{{ r.role_name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" v-permission="['user:edit']" @click="open(row)">编辑</el-button>
          <el-button link type="danger" v-permission="['user:edit']" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑用户' : '新增用户'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" placeholder="不填则默认 123456" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="超管">
          <el-switch v-model="form.is_super" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="可见项目">
          <el-select v-model="form.project_ids" multiple placeholder="造价数据隔离范围" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listUsersApi,
  createUserApi,
  updateUserApi,
  deleteUserApi,
  listRolesApi,
  listSystemProjectsApi,
} from '@/api/system'

const list = ref<any[]>([])
const roles = ref<any[]>([])
const projects = ref<any[]>([])
const visible = ref(false)
const form = reactive<any>({
  id: undefined,
  username: '',
  real_name: '',
  password: '',
  status: 1,
  is_super: false,
  role_ids: [],
  project_ids: [],
})

async function load() {
  list.value = await listUsersApi()
}
async function loadOptions() {
  roles.value = await listRolesApi()
  projects.value = await listSystemProjectsApi()
}
function open(row?: any) {
  Object.assign(form, {
    id: row?.id,
    username: row?.username || '',
    real_name: row?.real_name || '',
    password: '',
    status: row?.status ?? 1,
    is_super: row?.is_super || false,
    role_ids: row?.roles?.map((r: any) => r.role_code ? roles.value.find((x: any) => x.role_code === r.role_code)?.id : r.id)?.filter(Boolean) || [],
    project_ids: row?.project_ids || [],
  })
  // 重新计算 role_ids：后端返回 role_code，需要匹配当前 roles 列表
  if (row?.roles) {
    form.role_ids = row.roles.map((r: any) => {
      const found = roles.value.find((x: any) => x.role_code === r.role_code)
      return found?.id
    }).filter(Boolean)
  }
  visible.value = true
}
async function save() {
  const payload = { ...form }
  if (form.id) {
    await updateUserApi(form.id, payload)
  } else {
    await createUserApi(payload)
  }
  ElMessage.success('保存成功')
  visible.value = false
  await load()
}
async function remove(row: any) {
  await ElMessageBox.confirm(`删除用户 ${row.username}？`, '提示', { type: 'warning' })
  await deleteUserApi(row.id)
  ElMessage.success('删除成功')
  await load()
}
onMounted(async () => {
  await loadOptions()
  await load()
})
</script>
