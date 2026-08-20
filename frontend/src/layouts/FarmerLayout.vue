<template>
  <div class="farmer-layout">
    <aside class="sidebar">
      <router-link to="/" class="logo">
        <span class="logo-icon"><SproutIcon :size="24" variant="white" /></span>
        <span class="logo-text">慧农宝</span>
      </router-link>

      <nav class="nav-links">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path"
          :class="['nav-item', { active: isActive(item.path) }]">
          <el-icon v-if="item.icon !== 'sprout'" :size="20"><component :is="item.icon" /></el-icon>
          <SproutIcon v-else :size="20" variant="dark" />
          <span>{{ item.label }}</span>
          <el-badge
            v-if="item.path === '/qa' && notificationStore.unreadCount > 0"
            is-dot
            class="nav-badge"
          />
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button class="logout-btn" @click="handleLogout" title="退出登录">
          <el-icon :size="18"><SwitchButton /></el-icon>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <div class="main-area">
      <header class="top-bar">
        <span class="top-bar-spacer"></span>
        <div class="top-bar-right">
          <span class="weather-badge">
            <el-icon :size="14"><component :is="weatherIconFor(weatherStore.currentIcon)" /></el-icon>
            {{ weatherStore.loading ? '定位中' : weatherStore.shortRegion }} · {{ weatherStore.temperature }}°C {{ weatherStore.weather }}
          </span>
          <span class="top-bar-username">{{ auth.user?.name || '农户' }}</span>
          <span class="top-bar-avatar">
            <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="农户头像" />
            <span v-else>{{ (auth.user?.name || '农').charAt(0) }}</span>
          </span>
        </div>
      </header>

      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useWeatherStore } from '@/stores/weather'
import { useNotificationStore } from '@/stores/notification'
import { api } from '@/api/client'

import {
  HomeFilled, List, MapLocation, ChatDotRound, Notebook, User, SwitchButton,
  Sunny, Cloudy, MostlyCloudy, PartlyCloudy, Pouring, Lightning, Umbrella
} from '@element-plus/icons-vue'
import SproutIcon from '@/components/SproutIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const weatherStore = useWeatherStore()
const notificationStore = useNotificationStore()

// ========== 浏览器通知权限 ==========
let pushPollTimer: ReturnType<typeof setInterval> | null = null
let notificationGranted = false

async function requestNotificationPermission() {
  if (!('Notification' in window)) return
  if (Notification.permission === 'granted') {
    notificationGranted = true
    return
  }
  if (Notification.permission === 'denied') return
  const result = await Notification.requestPermission()
  notificationGranted = result === 'granted'
}

function showPushNotification(title: string, body: string) {
  // 应用内弹窗：始终可见，不依赖浏览器权限；常驻直到用户手动关闭
  ElNotification({
    title,
    message: body,
    type: 'warning',
    duration: 0,
    showClose: true,
  })
  // 浏览器原生通知：页面在后台/最小化时也能提醒（需用户授权）
  if (notificationGranted && 'Notification' in window) {
    try {
      new Notification(title, {
        body,
        icon: '/favicon.ico',
        tag: 'huinongbao-push',
      })
    } catch {
      // 忽略通知失败
    }
  }
}

// ========== 定位上报 ==========
async function reportLocation() {
  // 等待天气 store 定位完成
  if (!weatherStore.data?.adcode) return
  try {
    await api.updateLocation(weatherStore.data.adcode, weatherStore.data.city)
  } catch {
    // 静默失败，不影响用户体验
  }
}

// ========== 推送轮询 ==========
async function checkPushNotifications() {
  try {
    const notifications = await api.getLatestPush()
    for (const n of notifications) {
      showPushNotification(n.title, n.content || '')
      // 标记已弹出
      api.markPushShown(n.id).catch(() => {})
    }
  } catch {
    // 静默失败
  }
}

const navItems = [
  { path: '/', label: '首页', icon: 'HomeFilled' },
  { path: '/crops', label: '作物管理', icon: 'sprout' },
  { path: '/lands', label: '地块管理', icon: 'MapLocation' },
  { path: '/qa', label: '技术问答', icon: 'ChatDotRound' },
  { path: '/news', label: '三农资讯', icon: 'Notebook' },
  { path: '/profile', label: '个人中心', icon: 'User' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function weatherIconFor(icon: string) {
  const map: Record<string, any> = {
    sunny: Sunny,
    cloudy: PartlyCloudy,
    overcast: MostlyCloudy,
    rain: Pouring,
    thunder: Lightning,
    snow: Umbrella,
    fog: Cloudy,
  }
  return map[icon] || Cloudy
}

onMounted(() => {
  if (auth.token && !auth.user) {
    auth.fetchUser()
  }
  weatherStore.init()
  notificationStore.startPolling()

  // 请求浏览器通知权限
  requestNotificationPermission()

  // 天气定位完成后上报位置（已有 adcode 就直接上报，否则监听一次）
  if (weatherStore.data?.adcode) {
    reportLocation()
  } else {
    const stopWatch = watch(
      () => weatherStore.data?.adcode,
      (adcode) => {
        if (adcode) {
          reportLocation()
          stopWatch()
        }
      }
    )
  }

  // 每 5 分钟检查一次推送通知
  pushPollTimer = setInterval(checkPushNotifications, 5 * 60 * 1000)
  // 首次 10 秒后检查一次
  setTimeout(checkPushNotifications, 10000)
})

onBeforeUnmount(() => {
  notificationStore.stopPolling()
  if (pushPollTimer) {
    clearInterval(pushPollTimer)
    pushPollTimer = null
  }
})
</script>

<style scoped>
.farmer-layout {
  height: 100vh;
  overflow: hidden;
  background: #f5fbf6;
  display: flex;
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
}

/* ============ 侧边栏 ============ */
.sidebar {
  width: 340px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid rgba(34, 94, 56, .08);
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px 18px;
  text-decoration: none;
  flex-shrink: 0;
}
.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: #178844;
  color: #fff;
  flex-shrink: 0;
}
.logo-text {
  font-size: 26px;
  font-weight: 900;
  color: #111827;
}

.nav-links {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 14px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 52px;
  padding: 0 18px;
  border-radius: 12px;
  font-size: 20px;
  font-weight: 700;
  color: #52635a;
  text-decoration: none;
  transition: all .2s;
  position: relative;
}
.nav-item:hover {
  background: #edf7ee;
  color: #178844;
}
.nav-item.active {
  background: #e6f4e9;
  color: #178844;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: #178844;
  border-radius: 0 3px 3px 0;
}

.nav-badge {
  position: absolute;
  top: 10px;
  right: 14px;
}
.nav-badge :deep(.el-badge__dot) {
  border: 2px solid #fff;
}

.sidebar-footer {
  padding: 14px 14px 20px;
  border-top: 1px solid rgba(34, 94, 56, .06);
  flex-shrink: 0;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  height: 52px;
  padding: 0 18px;
  border: none;
  background: transparent;
  border-radius: 12px;
  font-size: 20px;
  font-weight: 700;
  color: #52635a;
  cursor: pointer;
  transition: all .2s;
  font-family: inherit;
}
.logout-btn:hover {
  background: #edf7ee;
  color: #178844;
}

/* ============ 主区域 ============ */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
}

.top-bar {
  height: 64px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, .96);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(34, 94, 56, .08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
}

.weather-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 22px;
  background: #edf7e8;
  font-size: 14px;
  color: #233329;
  font-weight: 700;
  white-space: nowrap;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.top-bar-username {
  font-size: 15px;
  font-weight: 700;
  color: #52635a;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.top-bar-spacer {
  flex: 1;
}

.top-bar-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #e6f4e9;
  color: #178844;
  font-size: 18px;
  font-weight: 900;
  overflow: hidden;
  flex-shrink: 0;
}

.top-bar-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.main-content {
  flex: 1;
  min-height: 0;
  padding: 28px 40px;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
