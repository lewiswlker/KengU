// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// 1. 导入 Pinia
import { createPinia } from 'pinia'  
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

const app = createApp(App)

// 2. 启用 Pinia（必须在 mount 之前）
app.use(createPinia())  
app.use(router)
app.use(ElementPlus)

// 注册图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')