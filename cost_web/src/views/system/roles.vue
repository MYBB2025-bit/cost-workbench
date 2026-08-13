<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>角色管理</span>
      <el-button type="primary" v-permission="['role:edit']" @click="open()">新增角色</el-button>
    </div>

    <el-table :data="list" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="role_code" label="角色编码" />
      <el-table-column prop="role_name" label="角色名" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'">{{ row.status === 1 ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="权限">
        <template #default="{ row }">
          <el-tag v-for="p in row.perms" :key="p.perm_code" size="small" style="margin-right: 4px">{{ p.perm_name || p.perm_code }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" v-permission="['role:edit']" @click="open(row)">编辑</el-button>
          <el-button link type="danger" v-permission="['role:edit']" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑角色' : '新增角色'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="角色编码">
          <el-input v-model="form.role_code" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="角色名">
          <el-input v-model="form.role_name" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="form.perm_ids" multiple placeholder="选择权限" style="width: 100%">
            <el-option v-for="p in permissions" :key="p.id" :label="p.perm_name || p.perm_code" :value="p.id" />
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
  listRolesApi,
  createRoleApi,
  updateRoleApi,
  deleteRoleApi,
  listPermissionsApi,
} from '@/api/system'

const list = ref<any[]>([])
const permissions = ref<any[]>([])
const visible = ref(false)
const form = reactive<any>({
  id: undefined,
  role_code: '',
  role_name: '',
  status: 1,
  perm_ids: [],
})

async function load() {
  list.value = await listRolesApi()
}
async function loadPerms() {
  permissions.value = await listPermissionsApi()
}
function open(row?: any) {
  Object.assign(form, {
    id: row?.id,
    role_code: row?.role_code || '',
    role_name: row?.role_name || '',
    status: row?.status ?? 1,
    perm_ids: row?.perms?.map((p: any) => {
      const found = permissions.value.find((x: any) => x.perm_code === p.perm_code)
      return found?.id
    }).filter(Boolean) || [],
  })
  visible.value = true
}
async function save() {
  const payload = { ...form }
  if (form.id) {
    await updateRoleApi(form.id, payload)
  } else {
    await createRoleApi(payload)
  }
  ElMessage.success('保存成功')
  visible.value = false
  await load()
}
async function remove(row: any) {
  await ElMessageBox.confirm(`删除角色 ${row.role_name}？`, '提示', { type: 'warning' })
  await deleteRoleApi(row.id)
  ElMessage.success('删除成功')
  await load()
}
onMounted(async () => {
  await loadPerms()
  await load()
})
</script>
