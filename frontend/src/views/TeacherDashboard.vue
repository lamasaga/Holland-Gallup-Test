<template>
  <div class="container">
    <h1>{{ auth.isAdmin ? '学生测评管理' : '老师工作台' }}</h1>
    <p class="subtitle">查看学生测评完成情况，管理学生账号，生成双版本解读报告</p>

    <div class="card filters">
      <div class="filter-row">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索姓名或用户名"
          class="search-input"
        />
        <select v-model="filterStatus" class="filter-select">
          <option value="all">全部</option>
          <option value="completed">已完成</option>
          <option value="incomplete">未完成</option>
        </select>
        <select v-model="filterCode" class="filter-select">
          <option value="all">全部 Holland 代码</option>
          <option v-for="code in hollandCodes" :key="code" :value="code">{{ code }}</option>
        </select>
        <button @click="showCreate = true">新建学生</button>
        <button class="btn-secondary" @click="exportCSV">导出 CSV</button>
      </div>
    </div>

    <div v-if="loading" class="card">加载中...</div>

    <div v-else class="card">
      <p class="count">共 {{ filteredStudents.length }} 位学生 / {{ filteredStudents.length }} students</p>
      <table class="student-table">
        <thead>
          <tr>
            <th>学生姓名</th>
            <th>用户名</th>
            <th>学校/年级</th>
            <th>Holland</th>
            <th>Gallup</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="student in filteredStudents" :key="student.id">
            <td>{{ student.display_name || student.username }}</td>
            <td>{{ student.username }}</td>
            <td>{{ student.school || '—' }} {{ student.grade || '' }}</td>
            <td>
              <span :class="['status', student.holland_done ? 'done' : 'pending']">
                {{ student.holland_done ? '已完成' : '未完成' }}
              </span>
              <span v-if="student.holland_code" class="code">{{ student.holland_code }}</span>
            </td>
            <td>
              <span :class="['status', student.gallup_done ? 'done' : 'pending']">
                {{ student.gallup_done ? '已完成' : '未完成' }}
              </span>
              <span v-if="student.gallup_domain" class="code">{{ student.gallup_domain }}</span>
            </td>
            <td>
              <span v-if="student.holland_done && student.gallup_done" class="status done">可生成报告</span>
              <span v-else class="status pending">待完成</span>
              <span v-if="!student.is_active" class="status pending">已停用</span>
            </td>
            <td class="action-cell">
              <button
                v-if="student.holland_done && student.gallup_done"
                @click="viewReport(student.id)"
              >报告</button>
              <button class="btn-secondary btn-sm" @click="resetPassword(student)">重置密码</button>
              <button class="btn-secondary btn-sm" @click="toggleStudent(student)">
                {{ student.is_active ? '停用' : '启用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="student-cards">
        <div v-for="student in filteredStudents" :key="student.id" class="student-card">
          <div class="student-card-header">
            <div>
              <strong>{{ student.display_name || student.username }}</strong>
              <span class="student-username">{{ student.username }}</span>
            </div>
            <span v-if="!student.is_active" class="status pending">已停用</span>
          </div>
          <div class="student-card-body">
            <div v-if="student.school || student.grade" class="card-row">
              <span class="card-label">学校/年级</span>
              <span>{{ student.school || '—' }} {{ student.grade || '' }}</span>
            </div>
            <div class="card-row">
              <span class="card-label">Holland</span>
              <span>
                <span :class="['status', student.holland_done ? 'done' : 'pending']">
                  {{ student.holland_done ? '已完成' : '未完成' }}
                </span>
                <span v-if="student.holland_code" class="code">{{ student.holland_code }}</span>
              </span>
            </div>
            <div class="card-row">
              <span class="card-label">Gallup</span>
              <span>
                <span :class="['status', student.gallup_done ? 'done' : 'pending']">
                  {{ student.gallup_done ? '已完成' : '未完成' }}
                </span>
                <span v-if="student.gallup_domain" class="code">{{ student.gallup_domain }}</span>
              </span>
            </div>
            <div class="card-row">
              <span class="card-label">状态</span>
              <span v-if="student.holland_done && student.gallup_done" class="status done">可生成报告</span>
              <span v-else class="status pending">待完成</span>
            </div>
          </div>
          <div class="student-card-actions">
            <button
              v-if="student.holland_done && student.gallup_done"
              @click="viewReport(student.id)"
            >报告</button>
            <button class="btn-secondary btn-sm" @click="resetPassword(student)">重置密码</button>
            <button class="btn-secondary btn-sm" @click="toggleStudent(student)">
              {{ student.is_active ? '停用' : '启用' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <div class="modal card">
        <h3>新建学生账号</h3>
        <div class="form-group">
          <label>用户名 *</label>
          <input v-model="createForm.username" />
        </div>
        <div class="form-group">
          <label>初始密码（留空自动生成）</label>
          <input v-model="createForm.password" type="password" placeholder="需含大小写/数字/符号" />
        </div>
        <div class="form-group">
          <label>姓名</label>
          <input v-model="createForm.display_name" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>学校</label>
            <input v-model="createForm.school" />
          </div>
          <div class="form-group">
            <label>年级</label>
            <input v-model="createForm.grade" />
          </div>
        </div>
        <div class="modal-actions">
          <button @click="handleCreate">创建</button>
          <button class="btn-secondary" @click="showCreate = false">取消</button>
        </div>
        <p v-if="createMsg" class="create-msg">{{ createMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  getTeacherStudents,
  createStudent,
  resetStudentPassword,
  deactivateStudent,
  activateStudent,
} from '../api'

const router = useRouter()
const auth = useAuthStore()
const students = ref([])
const loading = ref(true)
const searchQuery = ref('')
const filterStatus = ref('all')
const filterCode = ref('all')
const showCreate = ref(false)
const createMsg = ref('')
const createForm = ref({
  username: '',
  password: '',
  display_name: '',
  school: '',
  grade: '',
  class_name: '',
})

onMounted(async () => {
  try {
    students.value = await getTeacherStudents()
  } catch (err) {
    alert(err.response?.data?.detail || '加载学生列表失败')
  } finally {
    loading.value = false
  }
})

const hollandCodes = computed(() => {
  const codes = new Set()
  students.value.forEach(s => {
    if (s.holland_code) codes.add(s.holland_code)
  })
  return Array.from(codes).sort()
})

const filteredStudents = computed(() => {
  return students.value.filter(s => {
    const query = searchQuery.value.trim().toLowerCase()
    const matchesSearch = !query ||
      (s.display_name || '').toLowerCase().includes(query) ||
      (s.username || '').toLowerCase().includes(query)

    let matchesStatus = true
    if (filterStatus.value === 'completed') {
      matchesStatus = s.holland_done && s.gallup_done
    } else if (filterStatus.value === 'incomplete') {
      matchesStatus = !s.holland_done || !s.gallup_done
    }

    let matchesCode = true
    if (filterCode.value !== 'all') {
      matchesCode = s.holland_code === filterCode.value
    }

    return matchesSearch && matchesStatus && matchesCode
  })
})

function viewReport(studentId) {
  router.push(`/teacher/report/${studentId}`)
}

function exportCSV() {
  const headers = ['姓名', '用户名', '学校', '年级', 'Holland完成', 'Holland代码', 'Gallup完成', 'Gallup领域', '账号状态']
  const rows = filteredStudents.value.map(s => [
    s.display_name || s.username,
    s.username,
    s.school || '',
    s.grade || '',
    s.holland_done ? '是' : '否',
    s.holland_code || '',
    s.gallup_done ? '是' : '否',
    s.gallup_domain || '',
    s.is_active ? '正常' : '停用',
  ])
  const csv = [headers, ...rows].map(r => r.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `students_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function handleCreate() {
  createMsg.value = ''
  try {
    const payload = { ...createForm.value }
    if (!payload.password) delete payload.password
    const user = await createStudent(payload)
    let msg = `已创建 ${user.username}`
    if (!createForm.value.password) {
      const res = await resetStudentPassword(user.id)
      msg += `，初始密码：${res.new_password}（需首次登录修改）`
    }
    createMsg.value = msg
    students.value = await getTeacherStudents()
    createForm.value = { username: '', password: '', display_name: '', school: '', grade: '', class_name: '' }
  } catch (err) {
    createMsg.value = err.response?.data?.detail || '创建失败'
  }
}

async function resetPassword(student) {
  const custom = prompt(`为 ${student.username} 设置新密码（留空自动生成）`, '')
  if (custom === null) return
  try {
    const res = await resetStudentPassword(student.id, custom || null)
    alert(`密码已重置\n用户名：${res.username}\n新密码：${res.new_password}`)
  } catch (err) {
    alert(err.response?.data?.detail || '重置失败')
  }
}

async function toggleStudent(student) {
  try {
    if (student.is_active) {
      await deactivateStudent(student.id)
    } else {
      await activateStudent(student.id)
    }
    students.value = await getTeacherStudents()
  } catch (err) {
    alert(err.response?.data?.detail || '操作失败')
  }
}
</script>

<style scoped>
.subtitle {
  color: #666;
}

.filters {
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
}

.count {
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 12px;
}

.student-table {
  width: 100%;
  border-collapse: collapse;
}

.student-table th,
.student-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.student-table th {
  font-weight: 600;
  color: #4b5563;
  background: #f9fafb;
}

.status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 6px;
}

.status.done {
  background: #dcfce7;
  color: #166534;
}

.status.pending {
  background: #fee2e2;
  color: #991b1b;
}

.code {
  font-weight: 600;
  color: #2563eb;
}

.btn-secondary {
  background: #6b7280;
}

.action-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}

.modal { width: 100%; max-width: 480px; }

.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; font-size: 14px; }
.form-group input {
  width: 100%; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px;
}

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.modal-actions { display: flex; gap: 8px; margin-top: 12px; }

.create-msg { margin-top: 10px; font-size: 13px; color: #16a34a; }

.student-cards { display: none; }

@media (max-width: 640px) {
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input,
  .filter-select,
  .filter-row button {
    width: 100%;
  }

  .student-table { display: none; }

  .student-cards {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .student-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }

  .student-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .student-card-header strong {
    display: block;
    font-size: 16px;
    color: #111827;
  }

  .student-username {
    font-size: 13px;
    color: #6b7280;
  }

  .student-card-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
  }

  .card-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
  }

  .card-label {
    color: #6b7280;
    font-size: 13px;
  }

  .student-card-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .student-card-actions button {
    flex: 1;
    min-width: 80px;
    padding: 8px 12px;
    font-size: 13px;
  }
}
</style>
