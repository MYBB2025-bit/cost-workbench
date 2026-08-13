<template>
  <el-card class="page-card">
    <div class="toolbar">
      <span>客户端版本 & 补丁管理</span>
      <div>
        <el-input v-model="localVer" placeholder="本地版本号" style="width: 160px" />
        <el-button @click="onCheck">检测更新</el-button>
      </div>
    </div>

    <el-form :model="form" label-width="90px">
      <el-form-item label="版本号">
        <el-input v-model="form.version_code" placeholder="例如 v2.0.0" />
      </el-form-item>
      <el-form-item label="强制更新">
        <el-switch v-model="form.force_update" />
      </el-form-item>
      <el-form-item label="更新说明">
        <el-input v-model="form.version_desc" type="textarea" />
      </el-form-item>
      <el-button type="primary" v-permission="['client:version:publish']" @click="publish">发布版本</el-button>
    </el-form>

    <el-alert v-if="checkResult" :title="JSON.stringify(checkResult)" type="info" :closable="false" />

    <el-divider />
    <div class="toolbar"><span>已发布版本</span></div>
    <el-table :data="versions" border>
      <el-table-column prop="version_code" label="版本号" />
      <el-table-column prop="version_desc" label="说明" />
      <el-table-column prop="force_update" label="强制" />
      <el-table-column prop="publish_time" label="发布时间" />
    </el-table>

    <div class="toolbar"><span>补丁文件</span></div>
    <el-upload
      :auto-upload="false"
      :on-change="onPatchChange"
      :limit="1"
      accept=".bsdiff"
    >
      <el-button>选择补丁(.bsdiff)</el-button>
    </el-upload>
    <div v-if="patchMeta.from_version">
      从 {{ patchMeta.from_version }} → {{ patchMeta.to_version }}
      <el-button type="primary" @click="onUploadPatch">上传补丁</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  checkVersionApi,
  publishVersionApi,
  uploadPatchApi,
  listVersionsApi,
  listPatchesApi,
} from '@/api/client'

const form = ref({
  version_code: '',
  force_update: false,
  version_desc: '',
})
const localVer = ref('v1.0.0')
const checkResult = ref<any>(null)
const versions = ref<any[]>([])
const patches = ref<any[]>([])
const patchFile = ref<File | null>(null)
const patchMeta = reactive({ from_version: '', to_version: '' })

async function onCheck() {
  checkResult.value = await checkVersionApi(localVer.value)
}
async function publish() {
  if (!form.value.version_code) return ElMessage.warning('请输入版本号')
  await publishVersionApi(form.value)
  ElMessage.success('发布成功')
  await load()
}
function onPatchChange(file: any) {
  patchFile.value = file.raw
  // 简单约定文件名：from_to.bsdiff
  const m = file.name.match(/^(.+?)__to__(.+?)\.bsdiff$/)
  if (m) {
    patchMeta.from_version = m[1]
    patchMeta.to_version = m[2]
  } else {
    patchMeta.from_version = 'v1.0.0'
    patchMeta.to_version = form.value.version_code || 'v2.0.0'
  }
}
async function onUploadPatch() {
  if (!patchFile.value) return
  await uploadPatchApi(patchMeta.from_version, patchMeta.to_version, patchFile.value)
  ElMessage.success('补丁上传成功')
  await load()
}
async function load() {
  versions.value = await listVersionsApi()
  patches.value = await listPatchesApi()
}
onMounted(load)
</script>
