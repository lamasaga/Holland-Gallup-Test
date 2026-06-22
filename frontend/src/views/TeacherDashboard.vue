<template>
  <div class="container">
    <h1>老师工作台</h1>
    <p class="subtitle">查看学生测评完成情况，生成双版本解读报告</p>

    <div class="card filters">
      <div class="filter-row">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索姓名或用户名 / Search name or username"
          class="search-input"
        />
        <select v-model="filterStatus" class="filter-select">
          <option value="all">全部 / All</option>
          <option value="completed">已完成 / Completed</option>
          <option value="incomplete">未完成 / Incomplete</option>
        </select>
        <select v-model="filterCode" class="filter-select">
          <option value="all">全部 Holland 代码 / All codes</option>
          <option v-for="code in hollandCodes" :key="code" :value="code">{{ code }}</option>
        </select>
        <button class="btn-secondary" @click="exportCSV">导出 CSV / Export</button>
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
            <th>Holland</th>
            <th>Gallup</th>
            <th>测评结果</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="student in filteredStudents" :key="student.id">
            <td>{{ student.display_name || student.username }}</td>
            <td>{{ student.username }}</td>
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
              <span v-if="student.gallup_secondary_domain" class="code">{{ student.gallup_secondary_domain }}</span>
            </td>
            <td>
              <span v-if="student.holland_done && student.gallup_done" class="status done">可生成报告</span>
              <span v-else class="status pending">待完成</span>
            </td>
            <td>
              <button 
                v-if="student.holland_done && student.gallup_done" 
                @click="viewReport(student.id)"
              >
                查看报告
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTeacherStudents } from '../api'

const router = useRouter()
const students = ref([])
const loading = ref(true)
const searchQuery = ref('')
const filterStatus = ref('all')
const filterCode = ref('all')

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
  const headers = ['姓名', '用户名', 'Holland完成', 'Holland代码', 'Gallup完成', 'Gallup主要领域', 'Gallup次要领域']
  const rows = filteredStudents.value.map(s => [
    s.display_name || s.username,
    s.username,
    s.holland_done ? '是' : '否',
    s.holland_code || '',
    s.gallup_done ? '是' : '否',
    s.gallup_domain || '',
    s.gallup_secondary_domain || ''
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
</style>
