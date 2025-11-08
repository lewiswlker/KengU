import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import QueryView from '../views/QueryView.vue'
import ProfileView from '../views/ProfileView.vue'

const routes = [
  {
    path: '/',
    name: 'login',
    component: LoginView
  },
  {
    path: '/query',
    name: 'query',
    component: QueryView,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: ProfileView,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const isLogin = localStorage.getItem('userEmail')
  if (to.meta.requiresAuth && !isLogin) {
    next('/')
  } else {
    next()
  }
})

export default router