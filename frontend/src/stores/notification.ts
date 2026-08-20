import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'

export const useNotificationStore = defineStore('notification', () => {
  const unreadCount = ref(0)
  let pollingTimer: number | null = null

  async function fetchUnreadCount() {
    try {
      const res = await api.getNotificationUnreadCount()
      unreadCount.value = res.count || 0
    } catch {
      // 静默失败，避免影响页面正常使用
    }
  }

  async function markAllRead() {
    if (unreadCount.value === 0) return
    try {
      await api.markNotificationsRead()
      unreadCount.value = 0
    } catch {
      // ignore
    }
  }

  async function markConsultationRead(questionId: number) {
    try {
      await api.markConsultationRead(questionId)
      await fetchUnreadCount()
    } catch {
      // ignore
    }
  }

  async function markExpertRead(expertId: number) {
    try {
      await api.markExpertRead(expertId)
      await fetchUnreadCount()
    } catch {
      // ignore
    }
  }

  function startPolling(intervalMs = 30000) {
    stopPolling()
    fetchUnreadCount()
    pollingTimer = window.setInterval(fetchUnreadCount, intervalMs)
  }

  function stopPolling() {
    if (pollingTimer !== null) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }

  return {
    unreadCount,
    fetchUnreadCount,
    markAllRead,
    markConsultationRead,
    markExpertRead,
    startPolling,
    stopPolling,
  }
})
