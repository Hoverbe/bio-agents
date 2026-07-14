import { createApp } from 'vue';
import './style.css';
import App from './App.vue';
import AdminPanel from './components/AdminPanel.vue';
const adminPaths = ['/admin', '/bio-agent/admin'];
const rootComponent = adminPaths.includes(window.location.pathname) ? AdminPanel : App;
createApp(rootComponent).mount('#app');
