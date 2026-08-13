<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>权限管理</span>
      <el-button type="primary" v-permission="['perm:edit']" @click="open()">新增权限</el-button>
    </div>

    <el-table :data="list" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="perm_code" label="权限编码" />
      <el-table-column prop="perm_name" label="权限名" />
      <el-table-column prop="resource" label="资源" />
      <el-table-column prop="action" label="动作" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" v-permission="['perm:edit']" @click="open(row)">编辑</el-button>
          <el-button link type="danger" v-permission="['perm:edit']" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑权限' : '新增权限'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="权限编码">
          <el-input v-model="form.perm_code" placeholder="如 user:view" />
        </el-form-item>
        <el-form-item label="权限名">
          <el-input v-model="form.perm_name" />
        </el-form-item>
        <el-form-item label="资源">
          <el-input v-model="form.resource" placeholder="如 user" />
        </el-form-item>
        <el-form-item label="动作">
          <el-input v-model="form.action" placeholder="如 view/edit" />
        </el-form-item>
        <el-form-item label="父级ID">
          <el-input-number v-model="form.parent_id" :min="0" :controls="false" style="width: 100%" />
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
  listPermissionsApi,
  createPermissionApi,
  updatePermissionApi,
  deletePermissionApi,
} from '@/api/system'

const list = ref<any[]>([])
const visible = ref(false)
const form = reactive<any>({
  id: undefined,
  perm_code: '',
  perm_name: '',
  resource: '',
  action: '',
  parent_id: null,
})

async function load() {
  list.value = await listPermissionsApi()
}
function open(row?: any) {
  Object.assign(form, {
    id: row?.id,
    perm_code: row?.perm_code || '',
    perm_name: row?.perm_name || '',
    resource: row?.resource || '',
    action: row?.action || '',
    parent_id: row?.parent_id || null,
  })
  visible.value = true
}
async function save() {
  const payload = { ...form }
  if (!payload.parent_id) delete payload.parent_id
  if (form.id) {
    await updatePermissionApi(form.id, payload)
  } else {
    await createPermissionApi(payload)
  }
  ElMessage.success('保存成功')
  visible.value = false
  await load()
}
async function remove(row: any) {
  await ElMessageBox.confirm(`删除权限 ${row.perm_code}？`, '提示', { type: 'warning' })
  await deletePermissionApi(row.id)
  ElMessage.success('删除成功')
  await load()
}
onMounted(load)
</script>
