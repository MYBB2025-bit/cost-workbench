<template>
  <el-row :gutter="16">
    <el-col :span="6" v-for="c in cards" :key="c.title">
      <el-card class="page-card">
        <div class="stat-title">{{ c.title }}</div>
        <div class="stat-value">{{ c.value }}</div>
      </el-card>
    </el-col>
  </el-row>
  <el-card class="page-card">
    <div class="toolbar"><span>欢迎使用造价驻场工作台</span></div>
    <p>左侧菜单由后端按角色权限动态生成；按钮级权限通过 <code>v-permission</code> 指令控制。</p>
  </el-card>
</template>

<script setup lang="ts">
const cards = [
  { title: '项目总数', value: '—' },
  { title: '待处理进度款', value: '—' },
  { title: '风险项', value: '—' },
  { title: '临期预警', value: '—' },
]
</script>

<style scoped>
.stat-title {
  color: #909399;
  font-size: 13px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
}
</style>
