<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2>造价驻场工作台</h2>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="onSubmit">
          登录
        </el-button>
      </el-form>
      <p class="hint">默认管理员：admin / admin123</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.replace('/')
  } catch (e) {
    // 错误已在拦截器提示
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f6feb, #0b2447);
}
.login-card {
  width: 360px;
  text-align: center;
}
.hint {
  margin-top: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
