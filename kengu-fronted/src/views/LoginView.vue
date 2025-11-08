<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <div class="login-header">
        <el-icon class="logo-icon"><Book /></el-icon>
        <h2>KengU</h2>
        <p>Your study partner at the University of Hong Kong</p>
      </div>

      <el-form 
        ref="loginFormRef" 
        :model="loginForm" 
        :rules="loginRules" 
        class="login-form"
      >
        <el-form-item prop="email">
          <el-input 
            v-model="loginForm.email" 
            placeholder="Enter your HKU email (xxx@connect.hku.hk or xxx@hku.hk)" 
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="Enter your HKU Portal password" 
            show-password
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            class="login-btn" 
            @click="handleLogin"
            :loading="isLoading"
          >
            Log In
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { verifyHkuAuth, checkAndCreateUser } from '../services/api'
import { Book, User, Lock } from '@element-plus/icons-vue'

const loginFormRef = ref()
const isLoading = ref(false)
const router = useRouter()
const userStore = useUserStore()

const loginForm = reactive({
  email: '',
  password: ''
})

const loginRules = {
  email: [
    { required: true, message: 'Please enter your HKU email', trigger: 'blur' },
    { pattern: /@(connect\.hku\.hk|hku\.hk)$/, message: 'Please enter your HKU email (xxx@connect.hku.hk or xxx@hku.hk)', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter your HKU Portal password', trigger: 'blur' },
    { min: 1, message: 'Please enter your HKU Portal password', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  await loginFormRef.value.validate()
  
  isLoading.value = true
  try {
    const authResult = await verifyHkuAuth(loginForm.email, loginForm.password);
    if (!authResult.success) {
      alert('Please check your email and password');
      return;
    }

    const userResult = await checkAndCreateUser(loginForm.email)
    if (!userResult.success) {
      alert('System registration failed: ' + (userResult.message || 'Please contact administrator'))
      return
    }

    userStore.setLogin(loginForm.email)
    await userStore.loadCourses()
    await userStore.loadUserInfo()
    
    router.push('/query')
  } catch (error) {
    console.error('Fail to login', error)
    alert('Login failed: ' + (error.response?.data?.message || 'Please try again later'))
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background-color: #e1e5e8ff;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 600px;
  border-radius: 10px;
  overflow: hidden;
}

.login-header {
  text-align: center;
  padding: 10px 0 25px;
}

.login-page h2 {
  font-size: 40px;
  color: #073416ff;
  font-weight: 600;
  margin-bottom: 15px;
}

.login-page p {
  font-size: 20px;
  margin-bottom: 5px;
}

.login-form {
  padding: 10px 20px 10px;
}

.login-btn {
  background-color: #0a4a1fff;
  color: #fff;
  border: none;
  width: 100%;
  height: 45px;
  font-size: 20px;
}
.login-btn:hover {
  background-color: #073416ff;
}
</style>