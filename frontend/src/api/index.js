import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export default api

export function setAuthHeader(token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

export async function login(credentials) {
  const res = await api.post('/auth/login', credentials)
  return res.data
}

export async function register(data) {
  const res = await api.post('/auth/register', data)
  return res.data
}

export async function getMe() {
  const res = await api.get('/auth/me')
  return res.data
}

export async function getProgress() {
  const res = await api.get('/assessments/progress')
  return res.data
}

export async function getQuestions(type) {
  const res = await api.get('/assessments/questions', { params: { assessment_type: type } })
  return res.data
}

export async function submitHolland(answers) {
  const res = await api.post('/assessments/holland', { answers })
  return res.data
}

export async function submitGallup(answers) {
  const res = await api.post('/assessments/gallup', { answers })
  return res.data
}

export async function getStudentReport() {
  const res = await api.get('/reports/student')
  return res.data
}

export async function getTeacherStudents() {
  const res = await api.get('/teacher/students')
  return res.data
}

export async function getProfessionalReport(studentId) {
  const res = await api.get(`/reports/professional/${studentId}`)
  return res.data
}

export async function getStudentReportById(studentId) {
  const res = await api.get(`/reports/student/${studentId}`)
  return res.data
}
