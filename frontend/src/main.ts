import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import AdminPanel from './components/AdminPanel.vue'

const rootComponent = window.location.pathname === '/admin' ? AdminPanel : App

createApp(rootComponent).mount('#app')
