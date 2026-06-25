<template>
  <div class="container">
    <div class="report-header">
      <h1>专业版报告</h1>
      <div class="toggle">
        <button :class="{ active: view === 'pro' }" @click="view = 'pro'">专业版</button>
        <button :class="{ active: view === 'student' }" @click="view = 'student'">学生版</button>
      </div>
    </div>

    <div v-if="loading" class="card">报告加载中...</div>

    <template v-else>
      <div v-if="error" class="card error-card">
        <p>{{ error }}</p>
        <button @click="loadReports">重试 / Retry</button>
      </div>

      <template v-else>
        <div v-if="view === 'pro' && report" class="card header-card">
          <h2>{{ report.student_name }}</h2>
          <div class="badges">
            <span class="badge holland">Holland: {{ report.holland_code }}</span>
            <span class="badge gallup">主要: {{ report.gallup_domain }}</span>
            <span v-if="report.gallup_secondary_domain" class="badge gallup">次要: {{ report.gallup_secondary_domain }}</span>
          </div>
        </div>

        <div v-if="view === 'student' && studentReport" class="card header-card">
          <h2>{{ studentReport.student_name }} 的双维度画像</h2>
          <div class="badges">
            <span class="badge holland">Holland: {{ studentReport.holland_code }}</span>
            <span class="badge gallup">主要: {{ studentReport.gallup_domain }}</span>
            <span v-if="studentReport.gallup_secondary_domain" class="badge gallup">次要: {{ studentReport.gallup_secondary_domain }}</span>
          </div>
        </div>

        <div v-if="qualityWarnings.length" class="card warning-card">
          <h3>⚠️ 作答质量提示 / Response Quality</h3>
          <ul>
            <li v-for="(msg, idx) in qualityWarnings" :key="idx">{{ msg }}</li>
          </ul>
        </div>

        <div v-if="view === 'pro' && report" class="card" v-html="report.report_html"></div>
        <div v-else-if="view === 'student' && studentReport" class="card" v-html="studentReport.report_html"></div>
        <div v-else class="card">报告数据不可用</div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getProfessionalReport, getStudentReportById } from '../api'

const route = useRoute()
const studentId = route.params.studentId

const view = ref('pro')
const report = ref(null)
const studentReport = ref(null)
const loading = ref(true)
const error = ref('')

const qualityWarnings = computed(() => {
  const warnings = []
  const sources = [report.value, studentReport.value].filter(Boolean)
  for (const src of sources) {
    const hq = src.holland_quality?.response_quality
    const gq = src.gallup_quality?.response_quality
    if (hq && hq.risk_level !== 'low' && hq.message_zh) {
      warnings.push(hq.message_zh)
    }
    if (gq && gq.risk_level !== 'low' && gq.message_zh) {
      warnings.push(gq.message_zh)
    }
  }
  return [...new Set(warnings)]
})

onMounted(() => {
  loadReports()
})

async function loadReports() {
  loading.value = true
  error.value = ''
  report.value = null
  studentReport.value = null

  try {
    const proRes = await getProfessionalReport(studentId)
    report.value = proRes
  } catch (err) {
    console.error('Professional report error:', err)
    error.value = (error.value ? error.value + '\n' : '') + (err.response?.data?.detail || '专业版报告加载失败')
  }

  try {
    const stuRes = await getStudentReportById(studentId)
    studentReport.value = stuRes
  } catch (err) {
    console.error('Student report error:', err)
    error.value = (error.value ? error.value + '\n' : '') + (err.response?.data?.detail || '学生版报告加载失败')
  }

  loading.value = false
}
</script>

<style scoped>
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toggle {
  display: flex;
  gap: 8px;
}

.toggle button {
  background: #e5e7eb;
  color: #374151;
}

.toggle button.active {
  background: #2563eb;
  color: white;
}

.header-card {
  text-align: center;
}

.badges {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}

.badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
}

.badge.holland {
  background: #dbeafe;
  color: #1e40af;
}

.badge.gallup {
  background: #f3e8ff;
  color: #6b21a8;
}

.error-card {
  color: #991b1b;
  text-align: center;
}

.error-card p {
  white-space: pre-line;
  margin-bottom: 16px;
}

.warning-card {
  background: #fffbeb;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.warning-card h3 {
  margin-top: 0;
  color: #b45309;
}

.warning-card ul {
  margin: 0;
  padding-left: 20px;
}

.warning-card li {
  margin: 8px 0;
  line-height: 1.6;
}

@media (max-width: 640px) {
  .report-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .toggle {
    width: 100%;
  }

  .toggle button {
    flex: 1;
  }
}
</style>
