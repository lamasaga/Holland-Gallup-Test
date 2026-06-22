<template>
  <div class="container">
    <h1>Gallup 优势测评</h1>
    <p class="subtitle">根据你的第一直觉，在每道题的 A/B 描述中选择最符合你的一项</p>

    <div v-if="loading" class="card">题目加载中...</div>

    <div v-else>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        <span>{{ currentIndex + 1 }} / {{ questions.length }}</span>
      </div>

      <div class="question-nav">
        <button
          v-for="(_, idx) in questions"
          :key="idx"
          :class="{ answered: answers[idx] !== null, current: idx === currentIndex }"
          @click="goToQuestion(idx)"
        >
          {{ idx + 1 }}
        </button>
      </div>

      <div class="card question-card" v-if="currentQuestion">
        <h3>第 {{ currentQuestion.question_num }} 题</h3>
        <div class="statements">
          <div class="statement-a" :class="{ selected: answers[currentIndex] > 0 }">
            <strong>A:</strong> {{ currentQuestion.statement_a }}
          </div>
          <div class="statement-b" :class="{ selected: answers[currentIndex] < 0 }">
            <strong>B:</strong> {{ currentQuestion.statement_b }}
          </div>
        </div>
        <p class="scenario" v-if="currentQuestion.scenario_hint">💡 {{ currentQuestion.scenario_hint }}</p>
        <div class="option-prompt">请选择你的倾向：</div>
        <div class="options">
          <button 
            v-for="opt in options" 
            :key="opt.value"
            :class="{ selected: answers[currentIndex] !== null && answers[currentIndex] === opt.value }"
            @click="selectAnswer(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <div class="settings">
        <label class="toggle-label">
          <input type="checkbox" v-model="autoAdvance" />
          选择后自动下一题 / Auto-advance after selection
        </label>
      </div>

      <div class="nav-buttons">
        <button @click="prev" :disabled="currentIndex === 0">上一题</button>
        <button @click="next" :disabled="answers[currentIndex] === null" v-if="currentIndex < questions.length - 1">下一题</button>
        <button @click="showReview" :disabled="answers[currentIndex] === null || submitting" v-else>
          回顾并提交
        </button>
      </div>
    </div>

    <!-- Review Modal -->
    <div v-if="reviewVisible" class="modal-overlay" @click.self="reviewVisible = false">
      <div class="modal">
        <h2>提交前回顾 / Review Before Submit</h2>
        <p>共 {{ questions.length }} 题，已答 {{ answeredCount }} 题，未答 {{ questions.length - answeredCount }} 题。</p>
        <div v-if="unansweredIndices.length" class="unanswered-list">
          <p>未答题号 / Unanswered：</p>
          <button
            v-for="idx in unansweredIndices"
            :key="idx"
            class="nav-pill"
            @click="goToQuestion(idx); reviewVisible = false"
          >
            {{ idx + 1 }}
          </button>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="reviewVisible = false">继续检查 / Keep Checking</button>
          <button @click="submit" :disabled="submitting">
            {{ submitting ? '提交中...' : '确认提交 / Submit' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getQuestions, submitGallup } from '../api'

const router = useRouter()
const questions = ref([])
const answers = ref([])
const currentIndex = ref(0)
const loading = ref(true)
const submitting = ref(false)
const autoAdvance = ref(true)
const reviewVisible = ref(false)

const options = [
  { value: 2, label: '非常认同A' },
  { value: 1, label: '比较认同A' },
  { value: 0, label: '两者居中' },
  { value: -1, label: '比较认同B' },
  { value: -2, label: '非常认同B' },
]

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
const progressPercent = computed(() => ((currentIndex.value + 1) / questions.value.length) * 100)
const answeredCount = computed(() => answers.value.filter(a => a !== null).length)
const unansweredIndices = computed(() => {
  return answers.value.map((a, i) => a === null ? i : -1).filter(i => i !== -1)
})

let advanceTimer = null

onMounted(async () => {
  try {
    questions.value = await getQuestions('gallup')
    answers.value = new Array(questions.value.length).fill(null)
  } catch (err) {
    console.error('Failed to load questions', err)
  } finally {
    loading.value = false
  }
})

function selectAnswer(value) {
  clearTimeout(advanceTimer)
  answers.value = answers.value.map((v, i) => i === currentIndex.value ? value : v)
  if (autoAdvance.value && currentIndex.value < questions.value.length - 1) {
    advanceTimer = setTimeout(() => {
      currentIndex.value++
    }, 400)
  }
}

function goToQuestion(idx) {
  clearTimeout(advanceTimer)
  if (idx >= 0 && idx < questions.value.length) {
    currentIndex.value = idx
  }
}

function prev() {
  clearTimeout(advanceTimer)
  if (currentIndex.value > 0) currentIndex.value--
}

function next() {
  clearTimeout(advanceTimer)
  if (currentIndex.value < questions.value.length - 1) currentIndex.value++
}

function showReview() {
  reviewVisible.value = true
}

function formatError(err) {
  if (err?.response?.data?.detail) {
    const detail = err.response.data.detail
    if (Array.isArray(detail)) {
      return detail.map(d => (typeof d === 'string' ? d : (d.msg || d.message || JSON.stringify(d)))).join('\n')
    }
    return typeof detail === 'string' ? detail : JSON.stringify(detail)
  }
  return err?.message || '提交失败，请稍后重试'
}

async function submit() {
  if (answers.value.some(a => a === null)) {
    alert('请完成所有题目后再提交')
    return
  }
  submitting.value = true
  reviewVisible.value = false
  const payload = questions.value.map((q, i) => ({
    question_num: q.question_num,
    choice: answers.value[i]
  }))
  try {
    await submitGallup(payload)
    router.push('/student')
  } catch (err) {
    console.error('Submit error:', err)
    alert(formatError(err))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.subtitle {
  color: #666;
}

.progress-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.progress-bar span {
  font-size: 14px;
  color: #6b7280;
  white-space: nowrap;
}

.progress-fill {
  height: 8px;
  background: #2563eb;
  border-radius: 4px;
  transition: width 0.3s;
}

.question-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
  max-height: 120px;
  overflow-y: auto;
  padding: 8px;
  background: #f9fafb;
  border-radius: 8px;
}

.question-nav button {
  width: 32px;
  height: 32px;
  padding: 0;
  font-size: 12px;
  background: #fff;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.question-nav button.answered {
  background: #22c55e;
  color: white;
}

.question-nav button.current {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px #bfdbfe;
}

.question-card {
  text-align: center;
}

.statements {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 24px 0;
  text-align: left;
}

@media (max-width: 640px) {
  .statements {
    grid-template-columns: 1fr;
  }
}

.statement-a, .statement-b {
  padding: 16px;
  border-radius: 8px;
  background: #f9fafb;
  border: 2px solid transparent;
}

.statement-a.selected {
  border-color: #2563eb;
  background: #eff6ff;
}

.statement-b.selected {
  border-color: #7c3aed;
  background: #f5f3ff;
}

.scenario {
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 12px;
  line-height: 1.6;
}

.option-prompt {
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  margin: 20px 0 12px;
  padding-top: 16px;
  border-top: 1px dashed #e5e7eb;
}

.options {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.options button {
  background: #f3f4f6;
  color: #374151;
  border: 2px solid transparent;
  min-width: 90px;
  font-size: 13px;
}

.options button.selected {
  background: #2563eb;
  color: white;
  border-color: #1d4ed8;
}

.settings {
  margin: 16px 0;
  text-align: center;
}

.toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
}

.nav-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
}

.nav-buttons button:first-child {
  background: #9ca3af;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 24px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.unanswered-list {
  margin: 16px 0;
}

.unanswered-list p {
  margin-bottom: 8px;
  font-weight: 600;
}

.nav-pill {
  margin: 4px;
  padding: 4px 10px;
  font-size: 13px;
  background: #fee2e2;
  color: #991b1b;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.btn-secondary {
  background: #9ca3af;
}
</style>
