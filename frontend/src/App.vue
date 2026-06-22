<template>
  <div id="app">
    <nav class="navbar" v-if="auth.isLoggedIn">
      <div class="nav-brand">测评平台</div>
      <div class="nav-user">
        <span>{{ auth.user?.display_name || auth.user?.username }}</span>
        <span class="role-tag">{{ auth.user?.role === 'teacher' ? '老师' : '学生' }}</span>
        <button @click="logout">退出</button>
      </div>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

onMounted(() => {
  auth.init()
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
  color: #333;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.nav-brand {
  font-weight: 600;
  font-size: 18px;
  color: #2563eb;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.role-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #e0e7ff;
  color: #3730a3;
}

button {
  cursor: pointer;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  font-size: 14px;
}

button:hover {
  background: #1d4ed8;
}

button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

h1, h2, h3 {
  margin-top: 0;
}
</style>
