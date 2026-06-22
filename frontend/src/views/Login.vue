<template>
  <div class="container login-container">
    <div class="card login-card">
      <h1>RIASEC × CliftonStrengths</h1>
      <p class="subtitle">双维度职业兴趣与优势测评平台</p>
      
      <div class="role-toggle">
        <button 
          :class="{ active: role === 'student' }" 
          @click="role = 'student'"
        >学生登录</button>
        <button 
          :class="{ active: role === 'teacher' }" 
          @click="role = 'teacher'"
        >老师登录</button>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入用户名" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" required />
        </div>
        <button type="submit" :disabled="loading" class="login-btn">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p v-if="error" class="error">{{ error }}</p>
      
      <div class="demo-hint">
        <p>演示账号：</p>
        <p>学生：student / student123</p>
        <p>老师：teacher / teacher123</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { login } from '../api'

const router = useRouter()
const auth = useAuthStore()

const role = ref('student')
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const res = await login({
      username: username.value,
      password: password.value,
      role: role.value
    })
    auth.setAuth(res)
    if (res.role === 'teacher') {
      router.push('/teacher')
    } else {
      router.push('/student')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

.login-card {
  width: 100%;
  max-width: 420px;
  text-align: center;
}

.subtitle {
  color: #666;
  margin-bottom: 24px;
}

.role-toggle {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.role-toggle button {
  flex: 1;
  background: #e5e7eb;
  color: #374151;
}

.role-toggle button.active {
  background: #2563eb;
  color: white;
}

.form-group {
  text-align: left;
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #4b5563;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  font-size: 16px;
}

.error {
  color: #dc2626;
  margin-top: 12px;
  font-size: 14px;
}

.demo-hint {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
  font-size: 13px;
  color: #6b7280;
}

.demo-hint p {
  margin: 4px 0;
}
</style>
