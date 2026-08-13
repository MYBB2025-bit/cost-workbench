<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">造价驻场工作台</div>
      <el-menu
        :default-active="activeMenu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1f6feb"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><Menu /></el-icon>
          <span>{{ m.name }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>当前用户：{{ realName || username }}</span>
        <el-button text type="primary" @click="onLogout">退出登录</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/store/user'
import { usePermissionStore } from '@/store/permission'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const permStore = usePermissionStore()
const { menus } = storeToRefs(permStore)
const { username, realName } = storeToRefs(userStore)

const activeMenu = computed(() => route.path)

function onLogout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background: var(--c-header);
}
.logo {
  color: #fff;
  font-weight: 700;
  padding: 16px;
  text-align: center;
  border-bottom: 1px solid #1f2937;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid var(--c-border);
}
</style>
