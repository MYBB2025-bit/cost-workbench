<template>
  <el-card class="page-card">
    <div class="toolbar"><span>核价库（总价 = 单价 × 工程量）</span></div>
    <el-table :data="list" border>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="spec" label="规格" />
      <el-table-column prop="unit" label="单位" />
      <el-table-column prop="price" label="单价" />
      <el-table-column prop="qty" label="工程量" />
      <el-table-column prop="total" label="总价" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listPricingApi } from '@/api/progress'

const list = ref<any[]>([])
onMounted(async () => {
  list.value = await listPricingApi()
})
</script>
