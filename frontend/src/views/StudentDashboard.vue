<template>
  <div class="container">
    <h1>学生仪表盘</h1>
    <p class="subtitle">完成 Holland 兴趣测评与 Gallup 优势测评，解锁你的专属报告</p>

    <div class="card">
      <div class="progress-grid">
        <div class="progress-item" :class="{ done: progress.holland_done }">
          <div class="progress-icon">📊</div>
          <h3>Holland 兴趣测评</h3>
          <p>{{ progress.holland_done ? '已完成' : '未开始' }}</p>
          <p v-if="progress.holland_code" class="result-tag">{{ progress.holland_code }}</p>
          <div v-if="progress.holland_done && progress.holland_scores" class="detail">
            <span v-for="(score, type) in progress.holland_scores" :key="type">{{ type }}:{{ score }}</span>
          </div>
          <button v-if="!progress.holland_done" @click="startHolland">开始测评</button>
          <button v-else class="btn-secondary" @click="confirmRetake('holland')">重新测评</button>
        </div>

        <div class="progress-item" :class="{ done: progress.gallup_done }">
          <div class="progress-icon">💪</div>
          <h3>Gallup 优势测评</h3>
          <p>{{ progress.gallup_done ? '已完成' : '未开始' }}</p>
          <p v-if="progress.gallup_domain" class="result-tag">{{ progress.gallup_domain }}</p>
          <p v-if="progress.gallup_secondary_domain" class="result-tag" style="background:#f3e8ff;color:#6b21a8;">{{ progress.gallup_secondary_domain }}</p>
          <div v-if="progress.gallup_done && progress.gallup_top5" class="detail">
            <span>Top 5: {{ progress.gallup_top5.slice(0, 5).join('、') }}</span>
          </div>
          <button v-if="!progress.gallup_done" @click="startGallup">开始测评</button>
          <button v-else class="btn-secondary" @click="confirmRetake('gallup')">重新测评</button>
        </div>
      </div>
    </div>

    <div class="card summary-card" v-if="progress.holland_done && progress.gallup_done">
      <h2>🎉 测评完成</h2>
      <p>你已经完成了全部测评，可以查看你的专属解读报告。</p>
      <button @click="$router.push('/student/report')">查看报告</button>
    </div>

    <div class="card" v-if="progress.holland_done || progress.gallup_done">
      <h3>核心结果摘要 | Core Results</h3>
      <div class="summary-grid">
        <div v-if="progress.holland_code">
          <strong>Holland 三码 / Code</strong>
          <p class="result-tag">{{ progress.holland_code }}</p>
        </div>
        <div v-if="progress.gallup_domain">
          <strong>优势领域 / Strength Domain</strong>
          <p class="result-tag">{{ progress.gallup_domain }}</p>
          <p v-if="progress.gallup_secondary_domain" class="result-tag" style="background:#f3e8ff;color:#6b21a8;">{{ progress.gallup_secondary_domain }}</p>
        </div>
        <div v-if="progress.gallup_top5 && progress.gallup_top5.length">
          <strong>Top 5 主题 / Top 5 Themes</strong>
          <p>{{ progress.gallup_top5.slice(0, 5).join('、') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getProgress } from '../api'

const router = useRouter()
const progress = ref({
  holland_done: false,
  gallup_done: false,
  holland_code: '',
  gallup_top5: [],
  gallup_domain: '',
  gallup_secondary_domain: '',
  holland_scores: null,
  gallup_coverage: null,
  holland_quality: null
})

onMounted(async () => {
  try {
    progress.value = await getProgress()
  } catch (err) {
    console.error('Failed to load progress', err)
  }
})

function startHolland() {
  router.push('/student/holland')
}

function startGallup() {
  router.push('/student/gallup')
}

function confirmRetake(type) {
  const name = type === 'holland' ? 'Holland 兴趣测评' : 'Gallup 优势测评'
  if (confirm(`你已经完成过 ${name}，重新测评会覆盖之前的结果。是否继续？\nYou have already completed the ${name}. Retaking will overwrite your previous results. Continue?`)) {
    router.push(`/student/${type}`)
  }
}
</script>

<style scoped>
.subtitle {
  color: #666;
  margin-bottom: 24px;
}

.progress-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.progress-item {
  text-align: center;
  padding: 24px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  transition: all 0.2s;
}

.progress-item.done {
  border-color: #22c55e;
  background: #f0fdf4;
}

.progress-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.result-tag {
  display: inline-block;
  background: #dbeafe;
  color: #1e40af;
  padding: 4px 12px;
  border-radius: 16px;
  font-weight: 600;
  margin: 8px 0;
}

.detail {
  font-size: 13px;
  color: #6b7280;
  margin: 8px 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.btn-secondary {
  background: #9ca3af;
}

.summary-card {
  text-align: center;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.summary-grid strong {
  display: block;
  margin-bottom: 6px;
  color: #4b5563;
}
</style>
