import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/student',
    name: 'StudentDashboard',
    component: () => import('../views/StudentDashboard.vue'),
    meta: { requiresAuth: true, role: 'student' }
  },
  {
    path: '/student/holland',
    name: 'HollandAssessment',
    component: () => import('../views/HollandAssessment.vue'),
    meta: { requiresAuth: true, role: 'student' }
  },
  {
    path: '/student/gallup',
    name: 'GallupAssessment',
    component: () => import('../views/GallupAssessment.vue'),
    meta: { requiresAuth: true, role: 'student' }
  },
  {
    path: '/student/report',
    name: 'StudentReport',
    component: () => import('../views/StudentReport.vue'),
    meta: { requiresAuth: true, role: 'student' }
  },
  {
    path: '/teacher',
    name: 'TeacherDashboard',
    component: () => import('../views/TeacherDashboard.vue'),
    meta: { requiresAuth: true, role: 'teacher' }
  },
  {
    path: '/teacher/report/:studentId',
    name: 'TeacherReport',
    component: () => import('../views/TeacherReport.vue'),
    meta: { requiresAuth: true, role: 'teacher' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
  } else if (to.meta.role && to.meta.role !== auth.user?.role) {
    next('/login')
  } else {
    next()
  }
})

export default router
