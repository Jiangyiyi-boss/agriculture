import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * AI 问答会话状态 store
 *
 * 用途：记住用户当前正在进行的 AI 对话，切换页面再回到 AI 问答页时
 * 自动恢复上次会话（除非用户主动新建会话或登出）。
 *
 * 不持久化到 localStorage：登出时 auth store 会调用 clear()，
 * 下次登录进来是空状态 = 新会话，避免跨登录串话。
 */
export const useAiChatStore = defineStore('aiChat', () => {
  const activeConversationId = ref<string | null>(null)

  function setConversation(id: string | null) {
    activeConversationId.value = id
  }

  function clear() {
    activeConversationId.value = null
  }

  return { activeConversationId, setConversation, clear }
})
