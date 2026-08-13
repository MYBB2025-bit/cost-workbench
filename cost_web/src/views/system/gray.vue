<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>灰度发布配置</span>
      <el-button type="primary" v-permission="['client:gray:edit']" @click="open()">新增灰度</el-button>
    </div>

    <el-table :data="list" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="version_code" label="版本号" />
      <el-table-column prop="enable" label="启用" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enable === 1 ? 'success' : 'info'">{{ row.enable === 1 ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="user_filter" label="用户过滤规则">
        <template #default="{ row }">
          <pre style="margin: 0">{{ JSON.stringify(row.user_filter, null, 2) }}</pre>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" v-permission="['client:gray:edit']" @click="open(row)">编辑</el-button>
          <el-button link type="danger" v-permission="['client:gray:edit']" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑灰度' : '新增灰度'" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="目标版本号">
          <el-input v-model="form.version_code" placeholder="如 v2.0.0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enable" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="用户过滤 JSON">
          <el-input v-model="userFilterText" type="textarea" :rows="5" placeholder='{"user_ids": [1,2], "usernames": ["alice"]}' />
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listGrayReleasesApi,
  createGrayReleaseApi,
  updateGrayReleaseApi,
  deleteGrayReleaseApi,
} from '@/api/system'

const list = ref<any[]>([])
const visible = ref(false)
const form = reactive<any>({
  id: undefined,
  version_code: '',
  enable: 0,
  user_filter: {},
})
const userFilterText = ref('{}')

watch(() => form.user_filter, (v) => {
  try { userFilterText.value = JSON.stringify(v || {}, null, 2) } catch { /* ignore */ }
}, { immediate: true })

async function load() {
  list.value = await listGrayReleasesApi()
}
function open(row?: any) {
  Object.assign(form, {
    id: row?.id,
    version_code: row?.version_code || '',
    enable: row?.enable ?? 0,
    user_filter: row?.user_filter || {},
  })
  userFilterText.value = JSON.stringify(form.user_filter || {}, null, 2)
  visible.value = true
}
async function save() {
  let user_filter: any = {}
  try {
    user_filter = JSON.parse(userFilterText.value || '{}')
  } catch {
    return ElMessage.error('用户过滤 JSON 格式错误')
  }
  const payload = { ...form, user_filter }
  if (form.id) {
    await updateGrayReleaseApi(form.id, payload)
  } else {
    await createGrayReleaseApi(payload)
  }
  ElMessage.success('保存成功')
  visible.value = false
  await load()
}
async function remove(row: any) {
  await ElMessageBox.confirm(`删除灰度配置 ${row.version_code}？`, '提示', { type: 'warning' })
  await deleteGrayReleaseApi(row.id)
  ElMessage.success('删除成功')
  await load()
}
onMounted(load)
</script>
