import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setupPermissionDirective } from './directive/permission'
import './styles/index.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
setupPermissionDirective(app)
app.mount('#app')
