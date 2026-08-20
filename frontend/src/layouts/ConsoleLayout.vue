<template>
  <div class="console-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="logo-icon"><SproutIcon :size="20" variant="white" /></span>
        <div>
          <p class="logo-text">慧农宝</p>
          <p class="logo-sub">{{ roleName }}</p>
        </div>
      </div>
      <nav class="sidebar-nav">
        <button
          v-for="s in sections"
          :key="s.key"
          :class="['nav-btn', { active: active === s.key }]"
          @click="$emit('update:active', s.key)"
        >
          <el-icon :size="16"><component :is="s.icon" /></el-icon>
          <span>{{ s.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footer">
        <el-button text @click="handleLogout">
          <el-icon :size="16"><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <p class="topbar-title">{{ sections.find(s => s.key === active)?.label }}</p>
        <div class="topbar-user">
          <div class="user-info">
            <p class="user-name">{{ auth.user?.name }}</p>
            <p class="user-role">{{ roleName }}</p>
          </div>
          <span class="avatar">{{ auth.user?.name?.charAt(0) }}</span>
        </div>
      </header>
      <main class="main-body">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { SwitchButton } from '@element-plus/icons-vue'
import SproutIcon from '@/components/SproutIcon.vue'

defineProps<{
  roleName: string
  sections: { key: string; label: string; icon: string }[]
  active: string
}>()

defineEmits<{ 'update:active': [key: string] }>()

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.console-layout { display: flex; height: 100vh; overflow: hidden; background: #f5f7fa; }

.sidebar { display: none; flex-direction: column; width: 220px; background: #fff; border-right: 1px solid #e5e5e5; }
@media (min-width: 768px) { .sidebar { display: flex; } }

.sidebar-header { display: flex; align-items: center; gap: 8px; padding: 16px 20px; border-bottom: 1px solid #e5e5e5; }
.logo-icon { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; background: #16a34a; color: #fff; }
.logo-text { font-size: 14px; font-weight: 900; color: #333; line-height: 1.2; }
.logo-sub { font-size: 11px; color: #999; }

.sidebar-nav { flex: 1; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.nav-btn { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border: none; border-radius: 8px; background: none; font-size: 14px; font-weight: 500; color: #666; cursor: pointer; transition: all .2s; text-align: left; }
.nav-btn:hover { background: #f0f0f0; color: #333; }
.nav-btn.active { background: rgba(22,163,74,.1); color: #16a34a; }

.sidebar-footer { padding: 12px; border-top: 1px solid #e5e5e5; }

.main-area { flex: 1; display: flex; flex-direction: column; }

.topbar { display: flex; align-items: center; justify-content: space-between; height: 60px; padding: 0 24px; background: #fff; border-bottom: 1px solid #e5e5e5; }
.topbar-title { font-size: 14px; color: #999; }
.topbar-user { display: flex; align-items: center; gap: 8px; }
.user-info { text-align: right; }
.user-name { font-size: 14px; font-weight: 500; }
.user-role { font-size: 12px; color: #999; }
.avatar { display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 50%; background: #f0f0f0; font-weight: 700; color: #666; }

.main-body { flex: 1; padding: 24px; overflow-y: auto; overflow-x: hidden; }
</style>
