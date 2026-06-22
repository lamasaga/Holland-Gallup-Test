<template>
  <div class="container">
    <div v-if="loading" class="card">报告生成中...</div>
    <div v-else-if="report" class="card" v-html="report.report_html"></div>
    <div v-else class="card">暂无报告数据</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStudentReport } from '../api'

const report = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    report.value = await getStudentReport()
  } catch (err) {
    alert(err.response?.data?.detail || '加载报告失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.container {
  max-width: 100%;
}
</style>
