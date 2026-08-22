<template>
  <div class="qa-page">
    <section v-if="mode === null" class="qa-entry">
      <button class="mode-card ai-mode-card" type="button" @click="enterMode('ai')">
        <span class="mode-card-icon">
          <el-icon :size="30"><ChatDotRound /></el-icon>
        </span>
        <span class="mode-card-copy">
          <strong>AI 智能问答</strong>
          <small>输入农业问题，快速获取智能解答</small>
        </span>
        <el-icon class="mode-card-arrow" :size="22"><ArrowRight /></el-icon>
      </button>
      <button class="mode-card expert-mode-card" type="button" @click="enterMode('expert')">
        <span class="mode-card-icon">
          <el-icon :size="30"><User /></el-icon>
        </span>
        <span class="mode-card-copy">
          <strong>技术专家回答</strong>
          <small>按专业领域选择农业技术专家</small>
        </span>
        <el-icon class="mode-card-arrow" :size="22"><ArrowRight /></el-icon>
        <span v-if="notificationStore.unreadCount" class="mode-unread-dot"></span>
      </button>
    </section>

    <template v-else>
      <nav class="qa-tabs" aria-label="问答方式">
        <button :class="['qa-tab', { active: mode === 'ai' }]" type="button" @click="enterMode('ai')">
          <el-icon :size="18"><ChatDotRound /></el-icon>
          AI 智能问答
        </button>
        <button :class="['qa-tab', { active: mode === 'expert' }]" type="button" @click="enterMode('expert')">
          <el-icon :size="18"><User /></el-icon>
          技术专家回答
          <span v-if="notificationStore.unreadCount" class="tab-unread-dot"></span>
        </button>
      </nav>

      <section v-if="mode === 'ai'" class="ai-workspace">
        <aside class="chat-history">
          <div class="history-header">
            <h2>最近对话</h2>
            <button class="history-add" type="button" title="新建对话" @click="startNewConversation">
              <el-icon :size="19"><Plus /></el-icon>
            </button>
          </div>

          <div v-if="aiConversations.length" class="history-list">
            <div
              v-for="conversation in aiConversations"
              :key="conversation.id"
              :class="['history-item', { active: conversation.id === activeConversationId }]"
              role="button"
              tabindex="0"
              @click="selectConversation(conversation.id)"
              @keydown.enter="selectConversation(conversation.id)"
            >
              <span class="history-item-icon">
                <el-icon :size="18"><ChatDotRound /></el-icon>
              </span>
              <span class="history-item-copy">
                <strong>{{ conversation.title }}</strong>
                <small>{{ formatHistoryTime(conversation.updatedAt) }}</small>
              </span>
              <button class="history-item-delete" type="button" title="删除对话" @click.stop="confirmDeleteConversation(conversation.id)">
                <el-icon :size="15"><Delete /></el-icon>
              </button>
            </div>
          </div>
          <div v-else class="history-empty">
            <el-icon :size="28"><ChatDotRound /></el-icon>
            <span>还没有历史对话</span>
          </div>
        </aside>

        <main class="chat-panel">
          <div class="chat-panel-head">
            <div class="chat-panel-title">
              <h2>{{ currentConversationTitle }}</h2>
            </div>
            <span class="chat-status"><i></i> 在线</span>
          </div>

          <div class="chat-stream" ref="aiChatStreamRef">
            <div v-if="aiMessages.length === 0" class="chat-empty">
              <span class="chat-empty-icon"><SproutIcon :size="32" variant="white" /></span>
              <h3>请输入你的农业问题</h3>
              <div class="recommend-section">
                <span class="recommend-label">你可以这样提问</span>
                <div class="recommend-list">
                  <button
                    v-for="q in displayedQuickQuestions"
                    :key="q"
                    type="button"
                    class="recommend-card"
                    @click="askQuick(q)"
                  >
                    {{ q }}
                  </button>
                </div>
              </div>
            </div>

            <template v-else>
              <div
                v-for="message in aiMessages"
                :key="message.id"
                :class="['msg', message.role === 'user' ? 'msg-user' : 'msg-ai']"
              >
                <span v-if="message.role === 'ai'" class="msg-avatar bot-avatar">
                  <SproutIcon :size="18" variant="white" />
                </span>
                <div :class="['msg-bubble', message.role === 'user' ? 'user-bubble' : 'bot-bubble']">
                  <p v-if="message.role === 'ai'" class="bot-title">
                    <el-icon :size="17"><ChatDotRound /></el-icon>
                    AI 智能问答
                  </p>

                  <div v-if="message.role === 'user' && editingMessageId === message.id" class="msg-edit-box">
                    <textarea
                      v-model="editingContent"
                      class="msg-edit-textarea"
                      rows="3"
                      placeholder="修改后重新发送"
                      @keydown.enter.exact.prevent="submitEditMessage"
                    ></textarea>
                    <div class="msg-edit-actions">
                      <button type="button" class="msg-edit-btn cancel" @click="cancelEditMessage">取消</button>
                      <button type="button" class="msg-edit-btn send" :disabled="!editingContent.trim()" @click="submitEditMessage">发送</button>
                    </div>
                  </div>
                  <template v-else>
                    <div v-if="message.role === 'ai' && message.statusText" class="tool-status">
                      <span class="tool-status-dot"></span>{{ message.statusText }}
                    </div>
                    <div class="message-markdown" v-html="renderMarkdown(message.content || (message.role === 'ai' ? '' : ''))"></div>
                    <div v-if="message.imageUrls?.length" class="message-image-grid">
                      <img
                        v-for="(imageUrl, index) in message.imageUrls"
                        :key="imageUrl"
                        class="message-image-preview"
                        :src="imageUrl"
                        :alt="`上传图片 ${index + 1}`"
                      />
                    </div>
                  </template>
                  <details v-if="message.role === 'ai' && message.sources?.length" class="source-card">
                    <summary>参考资料 {{ message.sources.length }} 条</summary>
                    <a
                      v-for="source in message.sources"
                      :key="source.url"
                      :href="source.url"
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span>{{ source.title }}</span>
                      <small>{{ shortUrl(source.url) }}</small>
                    </a>
                  </details>

                  <div v-if="message.role === 'user' && editingMessageId !== message.id" class="user-msg-actions">
                    <button type="button" title="复制" @click="copyMessageContent(message)">
                      <el-icon :size="14"><CopyDocument /></el-icon>
                    </button>
                    <button type="button" title="编辑后重发" @click="startEditMessage(message)">
                      <el-icon :size="14"><EditPen /></el-icon>
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <div class="chat-footer">
            <div v-if="selectedImageFiles.length" class="image-preview-bar">
              <div v-for="(file, idx) in selectedImageFiles" :key="idx" class="image-preview-thumb">
                <img :src="getImagePreviewUrl(file)" :alt="`预览 ${idx + 1}`" />
                <button type="button" class="image-preview-remove" title="移除" @click="removeImageAt(idx)">×</button>
              </div>
            </div>
            <div class="input-row">
              <div class="textarea-wrap">
                <el-input
                  v-model="input"
                  type="textarea"
                  :rows="2"
                  resize="none"
                  placeholder="输入你的农业问题"
                  @keydown.enter.exact="handleAiInputEnter"
                />
                <input
                  ref="imageInput"
                  class="image-input"
                  type="file"
                  accept="image/*"
                  multiple
                  @change="handleImageChange"
                />
                <button class="im-img-btn-inner-left" type="button" title="上传图片" @click="imageInput?.click()">
                  <el-icon :size="20"><Picture /></el-icon>
                </button>
                <button
                  v-if="aiSending"
                  class="send-btn-inner stop-btn-inner"
                  type="button"
                  title="停止生成"
                  @click="stopAiMessage"
                >
                  <el-icon :size="18"><CloseBold /></el-icon>
                </button>
                <button
                  v-else
                  class="send-btn-inner"
                  type="button"
                  :class="{ 'send-btn-inner-active': input.trim() || selectedImageFiles.length }"
                  :disabled="!input.trim() && !selectedImageFiles.length"
                  title="发送问题"
                  @click="sendAiMessage"
                >
                  <el-icon :size="20"><Top /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </main>
      </section>

      <section v-else class="expert-workspace">
        <!-- 列表视图 -->
        <template v-if="expertView === 'list'">
          <div class="expert-section-heading expert-heading-right">
            <el-badge
              :value="totalUnreadForBadge"
              :max="99"
              :hidden="!totalUnreadForBadge"
              class="archive-entry-badge"
            >
              <button class="archive-entry-btn" type="button" @click="openArchive">
                <el-icon :size="18"><ChatDotRound /></el-icon>
                我的问答
              </button>
            </el-badge>
          </div>

          <div v-if="experts.length" class="expert-cards">
            <div v-for="expert in experts" :key="expert.id" class="expert-card">
              <span v-if="consultTag(expert.id) === 'recent'" class="card-tag recent">最近咨询</span>
              <span v-else-if="consultTag(expert.id) === 'visited'" class="card-tag visited">咨询过</span>
              <span class="expert-card-avatar">
                <img v-if="expert.avatar" :src="expert.avatar" :alt="expert.name" />
                <span v-else>{{ (expert.name || '专').charAt(0) }}</span>
              </span>
              <strong class="expert-card-name">{{ expert.name }}</strong>
              <small class="expert-card-title">{{ expert.title || '农业技术专家' }}</small>
              <small class="expert-card-specialty">{{ expert.specialty || '农业种植与病虫害防治' }}</small>
              <span v-if="expert.positive_rate !== null && expert.positive_rate !== undefined && expert.rating_count >= 5" class="expert-card-rating">
                <el-icon :size="13"><Star /></el-icon> 好评率 {{ expert.positive_rate }}%
                <em>·{{ expert.rating_count }}评</em>
              </span>
              <div class="expert-card-actions">
                <button class="card-btn bio" type="button" @click="showBio(expert)">个人简介</button>
                <button class="card-btn consult" type="button" @click="openChatWithExpert(expert)">咨询</button>
              </div>
            </div>
          </div>
          <div v-else class="empty-panel">暂无可咨询的技术专家</div>
        </template>

        <!-- 聊天视图 -->
        <template v-else-if="expertView === 'chat'">
          <div class="im-chat">
            <div class="im-header">
              <button class="im-back-btn" type="button" @click="exitChat">
                <el-icon :size="17"><ArrowLeft /></el-icon> 返回
              </button>
              <div class="im-header-info" v-if="activeExpert">
                <span class="expert-avatar sm">
                  <img v-if="activeExpert.avatar" :src="activeExpert.avatar" />
                  <span v-else>{{ (activeExpert.name || '专').charAt(0) }}</span>
                </span>
                <div>
                  <h2>{{ activeExpert.name }}</h2>
                  <p>{{ activeExpert.title || '农业技术专家' }} · {{ activeExpert.specialty || '' }}</p>
                </div>
              </div>
              <button
                v-if="selectedConsultation && selectedConsultation.status === '进行中'"
                class="im-end-btn" type="button" @click="confirmEndConsultation"
              >结束会话</button>
              <span v-else-if="selectedConsultation && selectedConsultation.status === '已结束'" class="im-ended-tag">
                已结束<span v-if="selectedConsultation.ended_by === 'expert'">（专家结束）</span>
              </span>
            </div>

            <div class="im-messages" ref="imMessagesRef">
              <div v-if="!consultationMessages.length" class="im-empty">
                暂无消息，在下方输入开始咨询
              </div>
              <div
                v-for="msg in consultationMessages"
                :key="msg.id"
                :class="['im-bubble', msg.sender_role === 'farmer' ? 'mine' : 'theirs']"
              >
                <div class="im-bubble-content">
                  <p v-if="msg.content" class="im-text">{{ msg.content }}</p>
                  <div v-if="msg.images" class="im-images">
                    <el-image
                      v-for="(url, i) in msg.images.split(',').filter(Boolean)"
                      :key="i"
                      :src="url"
                      :preview-src-list="msg.images.split(',').filter(Boolean)"
                      fit="cover"
                      class="im-image"
                      preview-teleported
                    />
                  </div>
                </div>
                <time class="im-time">{{ formatMsgTime(msg.created_at) }}</time>
              </div>
              <!-- 评价框：会话已结束且未评价未跳过时，嵌在最后一条对话下方 -->
              <div
                v-if="selectedConsultation && selectedConsultation.status === '已结束'
                  && (selectedConsultation.rating === null || selectedConsultation.rating === undefined)
                  && !selectedConsultation.rating_skipped_at"
                class="im-rating-card"
              >
                <button class="im-rating-close" type="button" title="跳过" @click="skipRating">×</button>
                <p class="im-rating-title">本次会话服务如何？</p>
                <el-rate
                  v-model="ratingStars"
                  :max="5"
                  size="large"
                  @change="submitRating"
                />
              </div>
            </div>

            <div class="chat-footer" v-if="!selectedConsultation || selectedConsultation.status !== '已结束'">
              <div v-if="pendingImages.length" class="image-preview-bar">
                <div v-for="(url, idx) in pendingImages" :key="idx" class="image-preview-thumb">
                  <img :src="url" :alt="`预览 ${idx + 1}`" />
                  <button type="button" class="image-preview-remove" title="移除" @click="removePendingImage(idx)">×</button>
                </div>
              </div>
              <div class="input-row">
                <div class="textarea-wrap">
                  <el-input
                    v-model="consultationInput"
                    type="textarea"
                    :rows="2"
                    resize="none"
                    placeholder="输入消息，回车发送"
                    @keydown.enter.exact.prevent="sendConsultationMessage"
                  />
                  <input
                    ref="imageInputRef"
                    class="image-input"
                    type="file"
                    accept="image/*"
                    multiple
                    @change="onPickImages"
                  />
                  <button class="im-img-btn-inner-left" type="button" title="上传图片" @click="imageInputRef?.click()">
                    <el-icon :size="20"><Picture /></el-icon>
                  </button>
                  <button
                    class="send-btn-inner"
                    type="button"
                    :class="{ 'send-btn-inner-active': consultationInput.trim() || pendingImages.length }"
                    :disabled="consultationSending || (!consultationInput.trim() && !pendingImages.length)"
                    title="发送消息"
                    @click="sendConsultationMessage"
                  >
                    <el-icon :size="20"><Top /></el-icon>
                  </button>
                </div>
              </div>
            </div>
            <div class="im-input-bar im-readonly" v-else-if="selectedConsultation">
              <span>会话已结束</span>
              <button class="im-new-btn" type="button" @click="startNewConsultation">发起新咨询</button>
            </div>
          </div>
        </template>

        <!-- 我的问答归档 -->
        <template v-else-if="expertView === 'archive'">
          <div class="expert-section-heading expert-heading-between">
            <h2>我的问答</h2>
            <button class="archive-back-btn" type="button" @click="expertView = 'list'">
              <el-icon :size="16"><ArrowLeft /></el-icon> 返回列表
            </button>
          </div>
          <div v-if="archiveList.length" class="archive-list">
            <button v-for="c in archiveList" :key="c.id" class="archive-row" type="button" @click="openHistory(c)">
              <span class="expert-avatar sm">
                <img v-if="c.expert_avatar" :src="c.expert_avatar" />
                <span v-else>{{ (c.expert_name || '专').charAt(0) }}</span>
              </span>
              <span class="archive-main">
                <span class="archive-title">
                  <strong>{{ c.expert_name || '专家' }}</strong>
                  <small :class="c.status === '已结束' ? 'tag-ended' : 'tag-ongoing'">{{ c.status === '已结束' ? '已结束' : '进行中' }}</small>
                </span>
                <span class="archive-preview">{{ c.last_preview || '点击查看详情' }}</span>
                <span class="archive-meta">
                  <time>{{ formatDateShort(c.created_at) }}</time>
                  <span v-if="c.rating !== null && c.rating !== undefined" class="archive-rated">已评 {{ c.rating }}★</span>
                </span>
              </span>
              <span v-if="c.unread_count > 0" class="archive-unread-badge">{{ c.unread_count > 99 ? '99+' : c.unread_count }}</span>
              <el-icon v-else class="expert-card-arrow" :size="20"><ArrowRight /></el-icon>
            </button>
          </div>
          <div v-else class="empty-panel">还没有咨询记录</div>
        </template>

        <!-- 专家简介弹窗 -->
        <el-dialog v-model="bioDialog.visible" title="个人简介" width="420px" :close-on-click-modal="false">
          <div v-if="bioDialog.expert" class="bio-dialog-body">
            <div class="bio-dialog-head">
              <span class="expert-avatar sm">
                <img v-if="bioDialog.expert.avatar" :src="bioDialog.expert.avatar" />
                <span v-else>{{ (bioDialog.expert.name || '专').charAt(0) }}</span>
              </span>
              <div>
                <strong>{{ bioDialog.expert.name }}</strong>
                <small>{{ bioDialog.expert.title || '农业技术专家' }} · {{ bioDialog.expert.specialty || '农业种植与病虫害防治' }}</small>
              </div>
            </div>
            <p class="bio-dialog-text">
              {{ bioDialog.expert.bio || '该专家暂未填写个人简介' }}
            </p>
          </div>
          <template #footer>
            <button class="bio-dialog-close" @click="bioDialog.visible = false">关闭</button>
            <button class="bio-dialog-consult" @click="consultFromBio">立即咨询</button>
          </template>
        </el-dialog>
      </section>

      <!-- 结束会话确认弹窗 -->
      <el-dialog v-model="endConfirmVisible" title="结束会话" width="460px" class="form-dialog confirm-dialog" :close-on-click-modal="false">
        <div class="confirm-dialog__body">确定结束本次咨询？结束后可对本次服务评价。</div>
        <template #footer>
          <el-button @click="endConfirmVisible = false">取消</el-button>
          <el-button type="primary" @click="executeEndConsultation">结束会话</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  ChatDotRound,
  CloseBold,
  CopyDocument,
  Delete,
  EditPen,
  Picture,
  Plus,
  Star,
  Top,
  User,
} from '@element-plus/icons-vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import SproutIcon from '@/components/SproutIcon.vue'

type AskMode = 'ai' | 'expert' | null
type AiMessage = {
  id: string
  role: 'user' | 'ai'
  content: string
  statusText?: string
  imageUrls?: string[]
  sources?: AiSource[]
}
type AiSource = {
  title: string
  url: string
  content?: string
}
type AiConversation = {
  id: string
  title: string
  updatedAt: number | string
  agentType?: string
}

const route = useRoute()
const notificationStore = useNotificationStore()

/**
 * 从 query.mode 推导初始问答模式：
 *   - ?mode=ai     → 直接进入「AI 智能问答」
 *   - ?mode=expert → 直接进入「技术专家回答」
 *   - 无 query      → 走模式选择页（首页"AI 智能问答"卡片直达会带 ?mode=ai，所以不会再看到选择页）
 */
function resolveInitialMode(): AskMode {
  const q = route.query.mode
  if (q === 'ai') return 'ai'
  if (q === 'expert') return 'expert'
  return null
}

const mode = ref<AskMode>(resolveInitialMode())
const input = ref('')
const imageInput = ref<HTMLInputElement | null>(null)
const selectedImageFiles = ref<File[]>([])
const aiSending = ref(false)
const aiAbortController = ref<AbortController | null>(null)
const aiMessages = ref<AiMessage[]>([])
const aiConversations = ref<AiConversation[]>([])
const activeConversationId = ref<string | null>(null)

const experts = ref<any[]>([])
const expertView = ref<'list' | 'chat' | 'archive'>('list')
const activeExpert = ref<any | null>(null)
const selectedConsultation = ref<any | null>(null)
const consultationMessages = ref<any[]>([])
const consultationInput = ref('')
const pendingImages = ref<string[]>([])
const consultationSending = ref(false)
const imageInputRef = ref<HTMLInputElement | null>(null)
const imMessagesRef = ref<HTMLElement | null>(null)
const aiChatStreamRef = ref<HTMLElement | null>(null)
const pollingTimer = ref<number | null>(null)
// 评价框星数（点星立即提交，提交后置空）
const ratingStars = ref(0)
const archiveList = ref<any[]>([])
// 已咨询过的专家 id 集合，用于在专家列表中标记"咨询过"
const consultedAtMap = ref<Map<number, string>>(new Map())
const bioDialog = reactive({ visible: false, expert: null as any })

// 7 天内咨询过 → 最近咨询；更早 → 咨询过
function consultTag(expertId: number): 'recent' | 'visited' | null {
  const last = consultedAtMap.value.get(expertId)
  if (!last) return null
  return Date.now() - new Date(last).getTime() < 7 * 86400000 ? 'recent' : 'visited'
}

function showBio(expert: any) {
  bioDialog.expert = expert
  bioDialog.visible = true
}

function consultFromBio() {
  const expert = bioDialog.expert
  if (!expert) return
  bioDialog.visible = false
  openChatWithExpert(expert)
}

const quickQuestions = [
  '我在长沙岳麓区，2亩地，想种点赚钱的',
  '水稻稻瘟病怎么治？',
  '现在番茄该施什么肥？',
  '生菜什么时候可以采收？',
  '蚜虫防治怎么配比？',
]

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

const displayedQuickQuestions = computed(() => shuffle(quickQuestions).slice(0, 3))
const currentConversationTitle = computed(() => {
  const current = aiConversations.value.find(item => item.id === activeConversationId.value)
  return current?.title || '新对话'
})
const totalUnreadForBadge = computed(() => notificationStore.unreadCount)

function enterMode(nextMode: Exclude<AskMode, null>) {
  mode.value = nextMode
  if (nextMode === 'expert') {
    stopPolling()
    expertView.value = 'list'
    activeExpert.value = null
    selectedConsultation.value = null
    consultationMessages.value = []
  }
}

// 监听 URL 上的 ?mode= 参数变化，处理浏览器前进/后退/直接构造 URL 场景
watch(
  () => route.query.mode,
  (q) => {
    if (q === 'ai' && mode.value !== 'ai') enterMode('ai')
    else if (q === 'expert' && mode.value !== 'expert') enterMode('expert')
    else if ((q === undefined || q === null) && mode.value !== null) {
      // URL 清空 mode 参数 → 回到模式选择页
      stopPolling()
      mode.value = null
      expertView.value = 'list'
    }
  },
)

// 旧的未读标记机制已移除，IM 改用会话状态轮询

function createId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function startNewConversation() {
  activeConversationId.value = null
  aiMessages.value = []
  input.value = ''
  clearSelectedImage()
}

async function confirmDeleteConversation(conversationId: string) {
  try {
    await ElMessageBox.confirm('删除后该对话的聊天记录不可恢复，确定删除吗？', '删除对话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await api.deleteAIConversation(conversationId)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
    return
  }
  aiConversations.value = aiConversations.value.filter(item => item.id !== conversationId)
  if (activeConversationId.value === conversationId) {
    const next = aiConversations.value[0]
    if (next) {
      await selectConversation(next.id)
    } else {
      startNewConversation()
    }
  }
  ElMessage.success('对话已删除')
}

// 农户消息：复制 / 编辑后重发（追加新消息）
const editingMessageId = ref<string | null>(null)
const editingContent = ref('')

function copyMessageContent(message: AiMessage) {
  const text = message.content || ''
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function startEditMessage(message: AiMessage) {
  editingMessageId.value = message.id
  editingContent.value = message.content || ''
}

function cancelEditMessage() {
  editingMessageId.value = null
  editingContent.value = ''
}

function submitEditMessage() {
  const text = editingContent.value.trim()
  if (!text || aiSending.value) return
  cancelEditMessage()
  input.value = text
  sendAiMessage()
}

async function selectConversation(conversationId: string) {
  const conversation = aiConversations.value.find(item => item.id === conversationId)
  if (!conversation) return
  activeConversationId.value = conversation.id
  try {
    const messages = await api.getAIMessages(conversation.id)
    aiMessages.value = messages.map((message: any) => ({
      id: String(message.id),
      role: message.role === 'assistant' ? 'ai' : 'user',
      content: message.content,
      imageUrls: message.image_urls
        ? message.image_urls.split(',').filter(Boolean)
        : undefined,
      sources: parseSources(message.sources),
    }))
    // 历史消息加载完成后滚到最新一条
    nextTick(() => scrollAiChatToBottom())
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '历史消息加载失败')
  }
}

function formatHistoryTime(timestamp: number | string) {
  const date = new Date(timestamp)
  const today = new Date()
  if (date.toDateString() === today.toDateString()) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

import { marked } from 'marked'

marked.setOptions({
  breaks: false,  // 不自动把 \n 转 <br>，保留 markdown 原生换行语义
  gfm: true,
})

function renderMarkdown(value: string) {
  if (!value) return ''
  return marked.parse(value) as string
}

function parseSources(raw: string | null | undefined): AiSource[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed)
      ? parsed.filter(item => item?.title && item?.url).map(item => ({
        title: String(item.title),
        url: String(item.url),
        content: item.content ? String(item.content) : undefined,
      }))
      : []
  } catch {
    return []
  }
}

function shortUrl(url: string) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function askQuick(question: string) {
  input.value = question
}

function handleImageChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (!files.length) return
  if (files.length > 5) {
    ElMessage.warning('一次最多上传 5 张图片')
    target.value = ''
    return
  }
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  for (const file of files) {
    if (!allowedTypes.includes(file.type)) {
      ElMessage.warning('图片仅支持 jpg、jpeg、png、webp')
      target.value = ''
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      ElMessage.warning('单张图片不能超过 5MB')
      target.value = ''
      return
    }
  }
  selectedImageFiles.value = files
  ElMessage.info(`已选择 ${files.length} 张图片，发送后会和问题一起提交`)
}

function clearSelectedImage() {
  selectedImageFiles.value = []
  if (imageInput.value) imageInput.value.value = ''
}

function removeImageAt(idx: number) {
  selectedImageFiles.value.splice(idx, 1)
  if (selectedImageFiles.value.length === 0 && imageInput.value) imageInput.value.value = ''
}

function getImagePreviewUrl(file: File): string {
  return URL.createObjectURL(file)
}

function stopAiMessage() {
  aiAbortController.value?.abort()
}

function handleAiInputEnter(event: KeyboardEvent) {
  if (event.isComposing) return
  event.preventDefault()
  sendAiMessage()
}

function upsertConversation(id: string, title: string) {
  const index = aiConversations.value.findIndex(item => item.id === id)
  const payload = { id, title, updatedAt: Date.now() }
  if (index >= 0) {
    aiConversations.value[index] = { ...aiConversations.value[index], ...payload }
  } else {
    aiConversations.value.unshift(payload)
  }
  aiConversations.value.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
}

async function fetchAIConversations() {
  try {
    const conversations = await api.getAIConversations()
    aiConversations.value = conversations.map((item: any) => ({
      id: String(item.id),
      title: item.title,
      updatedAt: item.updated_at,
    }))
  } catch {
    aiConversations.value = []
  }
}

function handleStreamEvent(event: string, data: any, aiMessageId: string) {
  if (event === 'meta') {
    activeConversationId.value = String(data.conversation_id)
    upsertConversation(String(data.conversation_id), data.conversation_title || '新对话')
    return
  }
  const aiMessage = aiMessages.value.find(message => message.id === aiMessageId)
  if (!aiMessage) return
  if (event === 'status') {
    aiMessage.statusText = data.message || ''
  }
  if (event === 'chunk') {
    aiMessage.statusText = ''
    aiMessage.content += data.content || ''
    // 流式输出时节流滚动，跟随回答内容
    scheduleAiScroll()
  }
  if (event === 'done') {
    aiMessage.statusText = ''
    aiMessage.sources = Array.isArray(data.sources) ? data.sources : []
  }
  if (event === 'error') {
    aiMessage.statusText = ''
    aiMessage.content = `抱歉，${data.detail || 'AI 问答暂时不可用'}`
    ElMessage.error(data.detail || 'AI 问答暂时不可用')
  }
}

async function readEventStream(response: Response, aiMessageId: string) {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式读取')
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const raw of events) {
      const eventLine = raw.split('\n').find(line => line.startsWith('event:'))
      const dataLine = raw.split('\n').find(line => line.startsWith('data:'))
      if (!eventLine || !dataLine) continue
      const eventName = eventLine.replace('event:', '').trim()
      try {
        handleStreamEvent(eventName, JSON.parse(dataLine.replace('data:', '').trim()), aiMessageId)
      } catch {}
    }
  }
}

async function sendAiMessage() {
  const content = input.value.trim()
  const images = [...selectedImageFiles.value]
  const imageUrls = images.map(image => URL.createObjectURL(image))
  if ((!content && !images.length) || aiSending.value) return

  aiMessages.value.push({
    id: createId(),
    role: 'user',
    content: content || '请帮我识别这张农业图片',
    imageUrls,
  })
  const aiMessageId = createId()
  aiMessages.value.push({
    id: aiMessageId,
    role: 'ai',
    content: '',
    statusText: '正在思考...',
  })
  // 立即滚到底部，让用户看到自己刚发的消息
  nextTick(() => scrollAiChatToBottom())
  input.value = ''
  clearSelectedImage()
  aiSending.value = true
  const controller = new AbortController()
  aiAbortController.value = controller

  try {
    const response = await api.streamAIChat({
      message: content,
      conversationId: activeConversationId.value,
      images,
      signal: controller.signal,
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(data?.detail || 'AI 问答请求失败')
    }
    await readEventStream(response, aiMessageId)
    await fetchAIConversations()
  } catch (error: any) {
    const aiMessage = aiMessages.value.find(message => message.id === aiMessageId)
    if (controller.signal.aborted || error?.name === 'AbortError') {
      if (aiMessage) aiMessage.content = aiMessage.content
        ? `${aiMessage.content}\n\n已停止生成。`
        : '已停止生成。'
      ElMessage.info('已停止生成')
    } else {
      if (aiMessage) aiMessage.content = `抱歉，${error.message || 'AI 问答暂时不可用'}`
      ElMessage.error(error.message || 'AI 问答暂时不可用')
    }
  } finally {
    aiSending.value = false
    if (aiAbortController.value === controller) aiAbortController.value = null
  }
}

async function fetchExperts() {
  try {
    experts.value = await api.getExperts()
  } catch {
    experts.value = []
  }
  // 同时拉取咨询过的专家列表，构建"最近咨询/咨询过"标记（expert_id -> 最近咨询时间）
  try {
    const myExperts = await api.getMyExperts()
    const map = new Map<number, string>()
    for (const c of myExperts) {
      if (c.expert_id && !map.has(c.expert_id)) {
        map.set(c.expert_id, c.updated_at || c.created_at || '')
      }
    }
    consultedAtMap.value = map
  } catch {
    consultedAtMap.value = new Map()
  }
}

async function fetchArchive() {
  try {
    // 使用按专家聚合的接口：一个专家一个会话栏
    archiveList.value = await api.getMyExperts()
  } catch {
    archiveList.value = []
  }
}

async function openArchive() {
  await fetchArchive()
  expertView.value = 'archive'
}

function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

function scrollToBottom() {
  if (imMessagesRef.value) imMessagesRef.value.scrollTop = imMessagesRef.value.scrollHeight
}

/** AI 聊天滚动到底部（发送消息、切会话、回答流式输出时调用） */
function scrollAiChatToBottom() {
  if (aiChatStreamRef.value) aiChatStreamRef.value.scrollTop = aiChatStreamRef.value.scrollHeight
}

// 流式输出滚动节流：每 200ms 最多滚一次，避免每个 chunk 都触发 reflow
let aiScrollTimer: number | null = null
function scheduleAiScroll() {
  if (aiScrollTimer !== null) return
  aiScrollTimer = window.setTimeout(() => {
    aiScrollTimer = null
    scrollAiChatToBottom()
  }, 200)
}

function formatMsgTime(ts: string) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatDateShort(ts: string) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

async function openChatWithExpert(expert: any) {
  activeExpert.value = expert
  consultationMessages.value = []
  consultationInput.value = ''
  pendingImages.value = []
  expertView.value = 'chat'

  // 通过聚合接口获取与该专家的会话状态：有进行中就续接，没有就返回占位（id=0）
  let consultation: any = null
  try {
    consultation = await api.getOrCreateConsultation(expert.id)
  } catch {
    consultation = null
  }
  selectedConsultation.value = consultation || null

  // 加载与该专家的所有历史消息（跨会话合并）
  await loadMessagesWithExpert(expert.id)

  // 标记该专家所有会话的未读通知为已读（含已结束的旧会话）
  if (notificationStore.unreadCount > 0) {
    notificationStore.markExpertRead(expert.id)
  }

  // 启动按专家聚合的轮询
  startPollingByExpert(expert.id)
}

async function loadMessagesWithExpert(expertId: number) {
  try {
    consultationMessages.value = await api.listMessagesWithExpert(expertId, 0)
    await nextTick()
    scrollToBottom()
  } catch {
    consultationMessages.value = []
  }
}

function startPollingByExpert(expertId: number) {
  stopPolling()
  pollingTimer.value = window.setInterval(async () => {
    try {
      const lastId = consultationMessages.value.length
        ? Math.max(...consultationMessages.value.map(m => m.id))
        : 0
      // 拉取该专家的新消息（跨会话合并）
      const newMsgs = await api.listMessagesWithExpert(expertId, lastId)
      if (newMsgs.length) {
        consultationMessages.value.push(...newMsgs)
        await nextTick()
        scrollToBottom()
      }
      // 刷新会话状态（用于检测专家是否结束会话）
      const fresh = await api.getMyExperts()
      archiveList.value = fresh
      const cur = fresh.find((c: any) => c.expert_id === expertId)
      // 仅当当前会话是"进行中"且被专家结束时才更新——
      // 不要用旧的"已结束"会话覆盖"待发起"占位，否则用户发消息会报"会话已结束"
      if (cur && cur.status === '已结束' && selectedConsultation.value?.status === '进行中') {
        selectedConsultation.value = cur
        stopPolling()
        if (cur.ended_by === 'expert') ElMessage.info('专家已结束会话，可对本次咨询评价')
      }
    } catch {}
  }, 3000)
}

function exitChat() {
  stopPolling()
  selectedConsultation.value = null
  activeExpert.value = null
  consultationMessages.value = []
  consultationInput.value = ''
  pendingImages.value = []
  expertView.value = 'list'
  fetchArchive()
}

function startNewConsultation() {
  if (!activeExpert.value) return
  // 重置为占位会话（id=0, status=待发起），让用户可以输入新消息
  selectedConsultation.value = {
    id: 0,
    expert_id: activeExpert.value.id,
    status: '待发起',
    rating: null,
  }
  consultationInput.value = ''
  pendingImages.value = []
  // 重启轮询
  startPollingByExpert(activeExpert.value.id)
}

async function onPickImages(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files) return
  for (const file of Array.from(target.files)) {
    try {
      const res = await api.uploadConsultationImage(file)
      pendingImages.value.push(res.url)
    } catch {
      ElMessage.error('图片上传失败')
    }
  }
  target.value = ''
}

function removePendingImage(i: number) {
  pendingImages.value.splice(i, 1)
}

async function sendConsultationMessage() {
  const content = consultationInput.value.trim()
  const images = pendingImages.value.length ? pendingImages.value.join(',') : null
  if (!content && !images) return
  if (!activeExpert.value) return
  consultationSending.value = true
  try {
    let cid = selectedConsultation.value?.id
    const cstatus = selectedConsultation.value?.status
    // 占位会话(id=0/无会话)或已结束会话 → 首条消息触发创建新会话
    if (!cid || cstatus === '已结束' || cstatus === '待发起') {
      const c = await api.startConsultation({ expert_id: activeExpert.value.id, content, images })
      selectedConsultation.value = c
      cid = c.id
      // 创建后用聚合接口加载该专家的全部历史（包含刚发的那条）
      await loadMessagesWithExpert(activeExpert.value.id)
      // 切换为按专家轮询
      startPollingByExpert(activeExpert.value.id)
    } else {
      const msg = await api.sendMessage(cid, { content, images })
      consultationMessages.value.push(msg)
    }
    consultationInput.value = ''
    pendingImages.value = []
    await nextTick()
    scrollToBottom()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    consultationSending.value = false
  }
}

const endConfirmVisible = ref(false)

function confirmEndConsultation() {
  endConfirmVisible.value = true
}

async function executeEndConsultation() {
  if (!selectedConsultation.value) return
  endConfirmVisible.value = false
  try {
    await api.endConsultation(selectedConsultation.value.id)
    // 刷新归档（按专家聚合）
    const fresh = await api.getMyExperts()
    archiveList.value = fresh
    // 刷新当前会话状态（含 rating/rating_skipped_at 字段）
    if (activeExpert.value) {
      try {
        const cur = await api.getOrCreateConsultation(activeExpert.value.id)
        selectedConsultation.value = cur
      } catch {}
    }
    stopPolling()
    ratingStars.value = 0
    // 评价框会自动显示在最后一条消息下方（v-if 条件满足），不需要手动弹窗
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '结束失败')
  }
}

async function submitRating(rating: number) {
  if (!selectedConsultation.value || !rating) return
  try {
    await api.rateConsultation(selectedConsultation.value.id, rating)
    ElMessage.success('感谢评价')
    // 本地立即更新 rating 字段，评价框 v-if 条件失效 → 自动隐藏
    selectedConsultation.value = { ...selectedConsultation.value, rating }
    // 刷新归档（按专家聚合）
    const fresh = await api.getMyExperts()
    archiveList.value = fresh
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '评价失败')
  }
}

async function skipRating() {
  if (!selectedConsultation.value) return
  try {
    await api.skipConsultationRating(selectedConsultation.value.id)
    // 本地立即标记跳过，评价框 v-if 条件失效 → 自动隐藏
    selectedConsultation.value = { ...selectedConsultation.value, rating_skipped_at: new Date().toISOString() }
    // 刷新归档（按专家聚合），让"待评价"badge 同步消失
    const fresh = await api.getMyExperts()
    archiveList.value = fresh
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function openHistory(c: any) {
  // 标记该专家所有会话的未读通知为已读（含已结束的旧会话）
  if (notificationStore.unreadCount > 0) {
    notificationStore.markExpertRead(c.expert_id)
  }
  const expert = experts.value.find(e => e.id === c.expert_id) || {
    id: c.expert_id,
    name: c.expert_name,
    avatar: c.expert_avatar,
    title: c.expert_title,
    specialty: c.expert_specialty,
  }
  activeExpert.value = expert
  // 通过聚合接口拿到该专家的最新会话状态（可能是进行中、已结束、或待发起占位）
  try {
    const fresh = await api.getOrCreateConsultation(c.expert_id)
    selectedConsultation.value = fresh
  } catch {
    // getOrCreateConsultation 失败时不要回退到归档项（可能是"已结束"的旧会话），
    // 设为 null 让 sendConsultationMessage 走创建新会话的路径
    selectedConsultation.value = null
  }
  consultationInput.value = ''
  pendingImages.value = []
  // 加载与该专家的全部历史消息（跨会话合并）
  await loadMessagesWithExpert(c.expert_id)
  expertView.value = 'chat'
  // 启动按专家轮询
  startPollingByExpert(c.expert_id)
}

onMounted(async () => {
  await Promise.all([fetchAIConversations(), fetchExperts(), fetchArchive()])
})

onBeforeUnmount(() => {
  aiAbortController.value?.abort()
  stopPolling()
})
</script>

<style scoped>
.qa-page {
  width: 100%;
  height: 100%;         /* 跟随 main-content 的内容区高度自适应，不再用 calc(100vh - X) */
  min-height: 0;
  overflow: hidden;     /* 阻止任何超出 main-content 的内容溢出，避免外层出现滚动条 */
  display: flex;
  flex-direction: column;
  color: var(--farm-text);
}

.qa-page button {
  appearance: none;
  -webkit-appearance: none;
  font-family: inherit;
}

.qa-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  color: var(--farm-text);
  font-size: 32px;
  font-weight: 900;
  letter-spacing: 0;
}

.page-desc {
  margin: 10px 0 0;
  color: var(--farm-muted);
  font-size: 18px;
}

.qa-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 42px;
  padding: 0 15px;
  border: 1px solid var(--farm-line);
  border-radius: 14px;
  background: #fff;
  color: var(--farm-muted);
  font-family: inherit;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
}

.qa-back:hover {
  border-color: #a9cfb3;
  color: var(--farm-green);
}

.qa-entry {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  max-width: 920px;
  margin: 82px auto 0;
}

.mode-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 18px;
  min-height: 190px;
  padding: 30px;
  border: 1px solid var(--farm-line);
  border-radius: 24px;
  background: #fff;
  color: var(--farm-text);
  font-family: inherit;
  text-align: left;
  box-shadow: var(--farm-shadow);
  cursor: pointer;
  transition: transform .2s, border-color .2s, box-shadow .2s;
}

.mode-card:hover {
  transform: translateY(-3px);
  border-color: #a9cfb3;
  box-shadow: 0 12px 28px rgba(28, 80, 43, .14);
}

.ai-mode-card .mode-card-icon {
  background: #e4f3e8;
  color: var(--farm-green);
}

.expert-mode-card .mode-card-icon {
  background: #e9f0e6;
  color: #597161;
}

.mode-card-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 66px;
  height: 66px;
  border-radius: 20px;
}

.mode-card-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 9px;
}

.mode-card-copy strong {
  font-size: 23px;
  font-weight: 900;
}

.mode-card-copy small {
  color: var(--farm-muted);
  font-size: 16px;
  line-height: 1.5;
}

.mode-card-arrow {
  margin-left: auto;
  color: #9aaa9f;
}

.mode-unread-badge,
.tab-unread-badge,
.expert-unread-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 21px;
  height: 21px;
  padding: 0 6px;
  border-radius: 999px;
  background: #ee4f4f;
  color: #fff;
  font-size: 12px;
  font-weight: 900;
  line-height: 21px;
}

.mode-unread-dot,
.tab-unread-dot {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ee4f4f;
  border: 2px solid #fff;
}

.mode-unread-dot {
  top: 18px;
  right: 18px;
}

.mode-unread-badge {
  position: absolute;
  top: 18px;
  right: 18px;
}

.qa-tabs {
  display: inline-flex;
  gap: 12px;
  margin: 0 auto 22px;
  padding: 6px;
  border-radius: 18px;
  background: #e9f1e5;
  flex-shrink: 0;
}

.qa-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 320px;
  height: 64px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #5f7068;
  font-size: 20px;
  font-weight: 800;
  cursor: pointer;
}

.qa-tab.active {
  background: #fff;
  color: var(--farm-text);
  box-shadow: 0 3px 10px rgba(18, 46, 31, .12);
}

.tab-unread-dot {
  top: 8px;
  right: 12px;
}

.tab-unread-badge {
  position: absolute;
  top: 5px;
  right: 12px;
}

.ai-workspace {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  flex: 1 1 0;
  min-height: 0;
  height: auto;
  max-height: calc(100vh - 240px);
  min-height: 480px;
  overflow: hidden;
  border: 1px solid var(--farm-line);
  border-radius: 22px;
  background: #fff;
  box-shadow: var(--farm-shadow);
}

.chat-history {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid var(--farm-line);
  background: #f7fbf7;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 24px 18px 20px;
  border-bottom: 1px solid #e1ece3;
}

.history-header h2 {
  margin: 0;
  flex: 1;
  text-align: center;
  font-size: 20px;
  font-weight: 900;
}

.history-header span {
  display: block;
  margin-top: 5px;
  color: var(--farm-muted);
  font-size: 13px;
}

.history-add {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid #c8dfcd;
  border-radius: 12px;
  background: #fff;
  color: var(--farm-green);
  cursor: pointer;
  flex-shrink: 0;
}

.history-add:hover {
  background: #eaf6ec;
}

.history-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  padding: 12px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 66px;
  padding: 10px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: var(--farm-text);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.history-item:hover,
.history-item.active {
  background: #eaf5ec;
}

.history-item-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 11px;
  background: #dcefe0;
  color: var(--farm-green);
}

.history-item-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.history-item-copy strong {
  overflow: hidden;
  font-size: 15px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-copy small {
  color: #829088;
  font-size: 12px;
}

.history-item-delete {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  margin-left: auto;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #829088;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s ease;
}

.history-item:hover .history-item-delete,
.history-item-delete:focus-visible {
  opacity: 1;
}

.history-item-delete:hover {
  background: #fdeaea;
  color: #d9534f;
}

.history-empty {
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 10px;
  padding: 72px 20px;
  color: #8a9990;
  font-size: 14px;
  text-align: center;
}

.chat-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-width: 0;
  height: 100%;
  min-height: 0;
  background: #fbfdfb;
}

.chat-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 80px;
  padding: 0 30px;
  border-bottom: 1px solid var(--farm-line);
}

.chat-panel-title {
  display: flex;
  align-items: center;
  flex: 1;
}

.chat-panel-title h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 900;
}

.ai-avatar-small,
.chat-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--farm-green);
}

.chat-empty-icon {
  width: 64px;
  height: 64px;
}

.chat-status {
  color: #809087;
  font-size: 14px;
}

.chat-status i,
.reply-notice i {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 5px;
  border-radius: 50%;
  background: #35a762;
}

.chat-stream {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  gap: 28px;
  overflow-y: auto;
  padding: 34px 42px;
  background: #fbfdfb;
}

.chat-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  flex-direction: column;
  min-height: 350px;
  text-align: center;
}

.chat-empty-icon {
  width: 70px;
  height: 70px;
  margin-bottom: 18px;
}

.chat-empty h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 900;
}

.chat-empty p {
  margin: 9px 0 0;
  color: var(--farm-muted);
  font-size: 16px;
}

.recommend-section {
  margin-top: 32px;
  width: 100%;
  max-width: 560px;
}

.recommend-label {
  display: block;
  text-align: left;
  color: var(--farm-muted);
  font-size: 15px;
  margin-bottom: 14px;
}

.recommend-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommend-card {
  display: block;
  width: 100%;
  text-align: left;
  padding: 18px 22px;
  border: 1px solid #e1ece3;
  border-radius: 16px;
  background: #fff;
  color: var(--farm-text);
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.recommend-card:hover {
  border-color: #a9cfb3;
  box-shadow: 0 2px 8px rgba(22, 163, 74, 0.08);
}

.msg {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.msg-user {
  justify-content: flex-end;
  width: 100%;
}

.msg-ai {
  justify-content: flex-start;
  width: 100%;
}

.msg-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  font-size: 17px;
  font-weight: 900;
}

.user-avatar {
  background: #e9f1e5;
}

.bot-avatar {
  background: var(--farm-green);
}

.msg-bubble {
  max-width: min(760px, 76%);
  padding: 16px 20px;
  border-radius: 19px;
  font-size: 17px;
  line-height: 1.7;
}

.msg-bubble p,
.message-markdown :deep(p) {
  margin: 0;
}

.user-bubble {
  border: 1px solid #dcebe0;
  background: #e8f3ea;
  color: #06150d;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(28, 80, 43, .06);
}

.user-bubble .message-markdown {
  color: #06150d;
}

/* 农户消息 hover 操作条（复制 / 编辑重发） */
.msg-user {
  position: relative;
}

.user-msg-actions {
  position: absolute;
  bottom: -30px;
  right: 4px;
  display: flex;
  gap: 6px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.msg-user:hover .user-msg-actions {
  opacity: 1;
  pointer-events: auto;
}

.user-msg-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 8px;
  background: rgba(6, 21, 13, 0.06);
  color: #5c7466;
  cursor: pointer;
}

.user-msg-actions button:hover {
  background: rgba(6, 21, 13, 0.14);
  color: #06150d;
}

/* 编辑重发输入框 */
.msg-edit-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: min(420px, 60vw);
}

.msg-edit-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cfe4d4;
  border-radius: 10px;
  background: #fff;
  color: #06150d;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.55;
  resize: vertical;
  outline: none;
}

.msg-edit-textarea:focus {
  border-color: var(--farm-green);
}

.msg-edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.msg-edit-btn {
  padding: 6px 16px;
  border: 0;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.msg-edit-btn.cancel {
  background: #eef2ef;
  color: #5c7466;
}

.msg-edit-btn.send {
  background: var(--farm-green);
  color: #fff;
}

.msg-edit-btn.send:disabled {
  background: #c8d6cc;
  cursor: not-allowed;
}

.bot-bubble {
  border: 1px solid #e1ece5;
  background: #fff;
  color: var(--farm-text);
  box-shadow: 0 8px 18px rgba(28, 80, 43, .08);
}

.bot-title {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 7px !important;
  color: var(--farm-green);
  font-weight: 900;
}

.message-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
  max-width: min(360px, 100%);
  margin-top: 12px;
}

.message-image-preview {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  border: 1px solid rgba(28, 80, 43, .14);
  border-radius: 16px;
  object-fit: cover;
  background: #fff;
}

.message-markdown {
  word-break: break-word;
  white-space: normal;
}

.tool-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #7aa88b;
  padding: 2px 0 8px;
}

.tool-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--farm-green, #3fae5a);
  animation: tool-status-pulse 1.2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes tool-status-pulse {
  0%, 100% { opacity: 0.35; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1.15); }
}

.message-markdown :deep(h1),
.message-markdown :deep(h2),
.message-markdown :deep(h3) {
  margin: 14px 0 8px;
  color: #07170e;
  font-weight: 900;
  line-height: 1.35;
}

.message-markdown :deep(h1) {
  font-size: 22px;
}

.message-markdown :deep(h2) {
  font-size: 20px;
}

.message-markdown :deep(h3) {
  font-size: 18px;
}

.message-markdown :deep(strong) {
  font-weight: 900;
}

.message-markdown :deep(a) {
  color: var(--farm-green);
  font-weight: 800;
  text-decoration: none;
}

.message-markdown :deep(a:hover) {
  text-decoration: underline;
}

.message-markdown :deep(ul),
.message-markdown :deep(ol) {
  margin: 8px 0 0;
  padding-left: 22px;
}

.message-markdown :deep(li) {
  margin: 4px 0;
}

/* 列表项内的 <br> 不要撑开间距 */
.message-markdown :deep(li br) {
  display: none;
}

/* 段落间距收紧 */
.message-markdown :deep(p) {
  margin: 6px 0;
  line-height: 1.6;
}

.source-card {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e2eee5;
}

.source-card summary {
  color: #64766d;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
}

.source-card a {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
  margin-top: 9px;
  padding: 10px 12px;
  border: 1px solid #dbe9df;
  border-radius: 12px;
  background: #f8fbf7;
  color: var(--farm-text);
  text-decoration: none;
}

.source-card a:hover {
  border-color: #b8d9c0;
  background: #f1f8f3;
}

.source-card span {
  overflow: hidden;
  font-size: 14px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-card small {
  overflow: hidden;
  color: #7c8c84;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-footer {
  position: relative;
  z-index: 2;
  display: block;
  flex-shrink: 0;
  width: 100%;
  box-sizing: border-box;
  min-height: 120px;
  padding: 0 28px 24px;
  background: #fbfdfb;
}

.image-preview-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 0;
}

.image-preview-thumb {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e1ece3;
}

.image-preview-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-preview-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 0;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview-remove:hover {
  background: rgba(0, 0, 0, 0.8);
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 8px 0 0;
}

.textarea-wrap {
  position: relative;
  flex: 1;
}

.textarea-wrap :deep(.el-textarea__inner) {
  min-height: 64px !important;
  padding: 10px 52px 50px 14px !important;
  border: 1px solid #e0e8e2;
  border-radius: 14px;
  box-shadow: none;
  font-size: 17px;
  line-height: 1.55;
}

.im-img-btn-inner-left {
  position: absolute;
  left: 8px;
  bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #87978e;
  cursor: pointer;
}

.im-img-btn-inner-left:hover {
  background: rgba(22, 163, 74, 0.08);
  color: var(--farm-green);
}

.image-upload-row {
  padding: 8px 0 0 14px;
}

.im-img-btn-below {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #87978e;
  cursor: pointer;
  padding: 0;
}

.im-img-btn-below:hover {
  background: rgba(22, 163, 74, 0.08);
  color: var(--farm-green);
}

.send-btn-inner {
  position: absolute;
  right: 8px;
  bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 10px;
  background: #c8d6cc;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
}

.send-btn-inner-active {
  background: var(--farm-green);
}

.send-btn-inner-active:hover:not(:disabled) {
  background: #148a4a;
}

.send-btn-inner:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.stop-btn-inner {
  background: #eef7f0;
  color: var(--farm-green);
  border: 1px solid rgba(45, 111, 65, 0.18);
}

.stop-btn-inner:hover:not(:disabled) {
  background: #e0f0e5;
  color: #1e5a35;
}

.image-input {
  display: none;
}

.selected-image-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px 12px;
  color: var(--farm-green);
  font-size: 13px;
}

.selected-image-bar > button {
  border: 0;
  background: transparent;
  color: #87978e;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.send-btn,
.stop-btn,
.expert-send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  background: #c8d6cc;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
}

.send-btn {
  width: 48px;
  height: 42px;
  border-radius: 13px;
}

.send-btn-active {
  background: var(--farm-green);
}

.send-btn-active:hover:not(:disabled) {
  background: #148a4a;
}

.stop-btn {
  min-width: 78px;
  height: 42px;
  padding: 0 14px;
  border: 1px solid rgba(45, 111, 65, .18);
  border-radius: 13px;
  background: #eef7f0;
  color: var(--farm-green);
  font-size: 14px;
  font-weight: 800;
}

.stop-btn:hover:not(:disabled) {
  border-color: rgba(45, 111, 65, .28);
  background: #e0f0e5;
  color: #1e5a35;
}

.expert-send-btn:hover:not(:disabled) {
  background: #2b83dd;
}

.send-btn:disabled,
.stop-btn:disabled,
.expert-send-btn:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.expert-workspace {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;          /* 兜底防溢出 */
  display: flex;
  flex-direction: column;
}

.expert-section-heading {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 18px;
  margin-bottom: 22px;
}
.expert-heading-between {
  justify-content: space-between;
}

.expert-section-heading h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.expert-section-heading h2::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 22px;
  background: var(--farm-green);
  border-radius: 2px;
}

.expert-section-heading p {
  margin: 8px 0 0;
  color: var(--farm-muted);
  font-size: 16px;
}

.reply-notice {
  flex-shrink: 0;
  padding: 10px 14px;
  border-radius: 999px;
  background: #fff0f0;
  color: #d84d4d;
  font-size: 14px;
  font-weight: 800;
}

.reply-notice i {
  background: #ee4f4f;
}

.expert-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.expert-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
  padding: 22px;
  border: 1px solid var(--farm-line);
  border-radius: 20px;
  background: #fff;
  color: var(--farm-text);
  font-family: inherit;
  text-align: left;
  box-shadow: var(--farm-shadow);
  cursor: pointer;
  transition: border-color .2s, transform .2s, box-shadow .2s;
}

.expert-card:hover,
.expert-card.selected {
  transform: translateY(-2px);
  border-color: #a9cfb3;
  box-shadow: 0 10px 24px rgba(28, 80, 43, .13);
}

.expert-card.selected {
  background: #f6fbf6;
}

.expert-avatar,
.selected-expert-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 50%;
  background: #e9f1e5;
  color: #52665a;
  font-weight: 900;
}

.expert-avatar {
  width: 58px;
  height: 58px;
  font-size: 23px;
}
.expert-avatar.sm { width: 44px; height: 44px; font-size: 18px; }

.expert-avatar img,
.selected-expert-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.expert-card-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 6px;
}

.expert-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.expert-card-title strong {
  font-size: 20px;
  font-weight: 900;
}

.expert-card-main small {
  color: var(--farm-muted);
  font-size: 14px;
}

.expert-specialty {
  color: #52665a;
  font-size: 15px;
  line-height: 1.5;
}

.expert-specialty b {
  color: var(--farm-green);
}

.expert-bio {
  display: -webkit-box;
  overflow: hidden;
  color: #839188;
  font-size: 14px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.expert-card-arrow {
  flex-shrink: 0;
  margin-top: 18px;
  color: #a3b1a8;
}

.empty-panel {
  padding: 72px 20px;
  border: 1px solid var(--farm-line);
  border-radius: 20px;
  background: #fff;
  color: var(--farm-muted);
  font-size: 17px;
  text-align: center;
}

.expert-chat-panel {
  margin-top: 24px;
  border: 1px solid var(--farm-line);
  border-radius: 22px;
  background: #fff;
  box-shadow: var(--farm-shadow);
}

.selected-expert-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 26px;
  border-bottom: 1px solid var(--farm-line);
}

.selected-expert-copy {
  display: flex;
  align-items: center;
  gap: 13px;
}

.selected-expert-avatar {
  width: 54px;
  height: 54px;
  font-size: 21px;
}

.selected-expert-copy h2 {
  margin: 0;
  font-size: 21px;
  font-weight: 900;
}

.selected-expert-copy p {
  margin: 6px 0 0;
  color: var(--farm-muted);
  font-size: 14px;
}

.close-expert-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--farm-line);
  border-radius: 12px;
  background: #fff;
  color: var(--farm-muted);
  font-family: inherit;
  cursor: pointer;
}

.expert-thread-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 24px 26px 4px;
}

.expert-thread {
  padding: 18px;
  border-radius: 16px;
  background: #f7fbf7;
}

.thread-question,
.thread-answer {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.thread-answer {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #deebe1;
}

.thread-label {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 900;
}

.farmer-label {
  background: #e5f0e6;
  color: #52665a;
}

.expert-label {
  background: #d9f0df;
  color: var(--farm-green);
}

.thread-question > div,
.thread-answer > div {
  min-width: 0;
  flex: 1;
}

.thread-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #819088;
  font-size: 13px;
}

.thread-meta strong {
  color: var(--farm-green);
  font-size: 14px;
}

.thread-meta time {
  margin-left: auto;
}

.thread-question h3 {
  margin: 7px 0 4px;
  font-size: 18px;
  font-weight: 900;
}

.thread-question p,
.thread-answer p {
  margin: 0;
  color: #63736a;
  font-size: 15px;
  line-height: 1.7;
}

.thread-answer p {
  margin-top: 6px;
  color: var(--farm-text);
}

.thread-pending {
  margin: 14px 0 0 46px;
  color: #b0823c;
  font-size: 14px;
}

.thread-empty {
  padding: 42px 20px 20px;
  color: var(--farm-muted);
  text-align: center;
}

.thread-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: #e7f3e9;
  color: var(--farm-green);
}

.thread-empty strong {
  display: block;
  color: var(--farm-text);
  font-size: 18px;
}

.thread-empty p {
  margin: 7px 0 0;
  font-size: 14px;
}

.expert-question-form {
  margin: 20px 26px 26px;
  padding: 20px;
  border: 1px solid #d8e9dc;
  border-radius: 17px;
  background: #f7fbf7;
}

.expert-question-form h3 {
  margin: 0 0 15px;
  font-size: 18px;
  font-weight: 900;
}

.expert-form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(180px, .6fr);
  gap: 14px;
  margin-bottom: 14px;
}

.expert-question-form :deep(.el-input__wrapper),
.expert-question-form :deep(.el-select__wrapper),
.expert-question-form :deep(.el-textarea__inner) {
  min-height: 50px;
  border-radius: 12px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 16px;
}

.expert-question-form :deep(.el-textarea__inner) {
  padding: 13px 15px;
  line-height: 1.55;
}

.expert-form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
}

.expert-form-footer > span {
  color: var(--farm-muted);
  font-size: 13px;
}

.expert-send-btn {
  min-height: 42px;
  padding: 0 17px;
  border-radius: 13px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 800;
}

@media (max-width: 1100px) {
  .expert-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .ai-workspace {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .chat-stream {
    padding: 28px 24px;
  }
}

@media (max-width: 720px) {
  .qa-header {
    align-items: stretch;
    flex-direction: column;
  }

  .qa-back {
    align-self: flex-start;
  }

  .qa-entry {
    grid-template-columns: 1fr;
    margin-top: 42px;
  }

  .qa-tabs {
    display: flex;
  }

  .qa-tab {
    flex: 1;
    width: auto;
    font-size: 16px;
  }

  .ai-workspace {
    display: flex;
    min-height: 0;
    flex-direction: column;
  }

  .chat-history {
    border-right: 0;
    border-bottom: 1px solid var(--farm-line);
  }

  .history-list {
    max-height: 148px;
    overflow-y: auto;
  }

  .chat-panel {
    min-height: 620px;
  }

  .chat-stream {
    min-height: 340px;
    padding: 24px 18px;
  }

  .msg-bubble {
    max-width: 78%;
    font-size: 16px;
  }

  .chat-footer {
    padding: 0 14px 16px;
  }

  .expert-grid {
    grid-template-columns: 1fr;
  }

  .expert-section-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .selected-expert-head {
    align-items: flex-start;
    flex-direction: column;
    padding: 18px;
  }

  .close-expert-btn {
    align-self: flex-start;
  }

  .expert-thread-list {
    padding: 18px 14px 4px;
  }

  .expert-question-form {
    margin: 18px 14px 14px;
    padding: 16px;
  }

  .expert-form-grid {
    grid-template-columns: 1fr;
  }

  .expert-form-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .expert-send-btn {
    width: 100%;
  }
}

@media (max-height: 760px) {
  .ai-workspace {
    min-height: 420px;
  }

  .input-row :deep(.el-textarea__inner) {
    min-height: 50px !important;
    padding-top: 10px;
  }

  .input-row {
    padding: 10px 10px;
  }
}

/* ========== 专家咨询 IM ========== */
.archive-entry-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: 0;
  background: var(--farm-green);
  color: #fff;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(22, 163, 74, 0.2);
  transition: all 0.2s;
}
.archive-entry-btn:hover {
  background: #148a4a;
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3);
  transform: translateY(-1px);
}

.archive-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid #e0e8e2;
  background: #fff;
  color: #64766d;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.archive-back-btn:hover {
  border-color: var(--farm-green);
  color: var(--farm-green);
  background: #f6fbf7;
}
.archive-entry-badge :deep(.el-badge__content) {
  border: 0;
  background: #f56c6c;
}
.archive-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #f56c6c;
  color: #fff;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* 专家卡片网格 */
.expert-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
@media (max-width: 1200px) { .expert-cards { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 760px) { .expert-cards { grid-template-columns: 1fr; } }
.expert-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 22px 16px 16px;
  background: #fff;
  border: 1px solid rgba(34, 94, 56, .10);
  border-radius: 16px;
  text-align: center;
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.expert-card:hover {
  border-color: rgba(22, 163, 74, .4);
  box-shadow: 0 6px 16px rgba(26, 71, 43, .10);
  transform: translateY(-2px);
}
.card-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  font-size: 15px;
  font-weight: 700;
  padding: 5px 14px;
  border-radius: 999px;
}
.card-tag.recent { color: #16a34a; background: rgba(22, 163, 74, .12); }
.card-tag.visited { color: #6b7c70; background: #eef2ef; }
.expert-card-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  overflow: hidden;
  background: #e9f0e6;
  color: #49624e;
  font-size: 26px;
  font-weight: 900;
}
.expert-card-avatar img { width: 100%; height: 100%; object-fit: cover; }
.expert-card-name { margin-top: 12px; font-size: 17px; font-weight: 800; color: #0f1f16; }
.expert-card-title { margin-top: 5px; font-size: 13px; color: #6b7c70; font-weight: 600; }
.expert-card-specialty {
  margin-top: 8px;
  font-size: 13px;
  color: #4a5a50;
  background: #f0f7f2;
  padding: 3px 10px;
  border-radius: 999px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.expert-card-rating {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 12px;
  font-size: 13px;
  color: #ca8a04;
  font-weight: 700;
  background: rgba(234, 179, 8, .12);
  padding: 2px 9px;
  border-radius: 999px;
}
.expert-card-rating em { font-style: normal; color: #9ca3a0; font-weight: 600; }
.expert-card-actions {
  display: flex;
  gap: 10px;
  width: 100%;
  margin-top: 14px;
}
.card-btn {
  flex: 1;
  border-radius: 10px;
  padding: 11px 0;
  font-family: inherit;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background .15s, color .15s, border-color .15s;
}
.card-btn.bio {
  border: 1px solid rgba(22, 163, 74, .45);
  background: #fff;
  color: #178844;
}
.card-btn.bio:hover { background: rgba(22, 163, 74, .08); }
.card-btn.consult {
  border: 0;
  background: var(--farm-green, #178844);
  color: #fff;
}
.card-btn.consult:hover { filter: brightness(1.07); }

/* 专家简介弹窗 */
.bio-dialog-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.bio-dialog-head strong { display: block; font-size: 17px; font-weight: 800; color: #0f1f16; }
.bio-dialog-head small { display: block; margin-top: 3px; font-size: 13px; color: #6b7c70; font-weight: 600; }
.bio-dialog-text {
  margin: 14px 0 0;
  font-size: 14px;
  color: #4a5a50;
  line-height: 1.7;
  white-space: pre-wrap;
}
.bio-dialog-close {
  border: 1px solid #d4e3d8;
  background: #fff;
  color: #4a5a50;
  border-radius: 10px;
  padding: 8px 18px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  margin-right: 10px;
}
.bio-dialog-close:hover { background: #f0f7f2; }
.bio-dialog-consult {
  border: 0;
  background: var(--farm-green, #178844);
  color: #fff;
  border-radius: 10px;
  padding: 8px 18px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}
.bio-dialog-consult:hover { filter: brightness(1.07); }

/* 聊天视图 */
.im-chat {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  height: 100%;              /* 跟随 expert-workspace，不再写死 */
  min-height: 0;             /* 关键：允许在低高度屏幕下收缩，不撑破外层 */
  background: #f6f8f6;
  border: 1px solid rgba(34, 94, 56, .10);
  border-radius: 18px;
  overflow: hidden;
}
.im-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #eef0ee;
}
.im-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: #16a34a;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  padding: 6px 8px;
}
.im-header-info { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.im-header-info h2 { margin: 0; font-size: 17px; font-weight: 800; color: #0f1f16; }
.im-header-info p { margin: 2px 0 0; font-size: 13px; color: #6b7c70; }
.im-end-btn {
  padding: 7px 14px;
  border: 1px solid #f56c6c;
  background: #fff;
  color: #f56c6c;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.im-end-btn:hover { background: #f56c6c; color: #fff; }
.im-ended-tag { font-size: 13px; color: #909399; font-weight: 700; }

.im-messages {
  flex: 1;
  min-height: 0;             /* 配合 flex 收缩，让消息区老实待在 im-chat 内部 */
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.im-empty { margin: auto; color: #9ca3a0; font-size: 14px; }
.im-bubble { display: flex; flex-direction: column; max-width: 78%; }
.im-bubble.mine { align-self: flex-end; align-items: flex-end; }
.im-bubble.theirs { align-self: flex-start; align-items: flex-start; }
.im-bubble-content {
  padding: 10px 13px;
  border-radius: 14px;
  font-size: 15px;
  line-height: 1.5;
  word-break: break-word;
}
.im-bubble.mine .im-bubble-content { background: #16a34a; color: #fff; border-bottom-right-radius: 4px; }
.im-bubble.theirs .im-bubble-content { background: #fff; color: #152117; border: 1px solid #eef0ee; border-bottom-left-radius: 4px; }
.im-text { margin: 0; }
.im-images { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.im-bubble.mine .im-images { margin-top: 0; }
.im-image { width: 120px; height: 120px; border-radius: 10px; object-fit: cover; cursor: zoom-in; }
.im-time { font-size: 11px; color: #9ca3a0; margin-top: 4px; padding: 0 4px; }

.im-input-bar {
  padding: 10px 12px;
  background: #fff;
  border-top: 1px solid #eef0ee;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.im-attached { display: flex; flex-wrap: wrap; gap: 6px; }
.im-attached-item { position: relative; }
.im-attached-item img { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; border: 1px solid #eef0ee; }
.im-attached-item button {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: #f56c6c;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.im-input-row { display: flex; align-items: flex-end; gap: 8px; }
.im-img-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid #eef0ee;
  background: #f6f8f6;
  color: #16a34a;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.im-img-btn:hover { background: rgba(22, 163, 74, .10); }
.im-input-row :deep(.el-textarea__inner) { border-radius: 12px; resize: none; }
.im-send-btn {
  padding: 9px 18px;
  border: none;
  background: #16a34a;
  color: #fff;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}
.im-send-btn:disabled { background: #c8d6cc; cursor: not-allowed; }
.im-readonly { flex-direction: row; align-items: center; justify-content: center; gap: 14px; color: #909399; font-size: 14px; }
/* 评价框：嵌在最后一条对话下方 */
.im-rating-card {
  position: relative;
  margin: 14px 0 4px;
  padding: 14px 20px 16px;
  background: #fafdfb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  text-align: center;
}
.im-rating-close {
  position: absolute;
  top: 6px;
  right: 10px;
  width: 22px;
  height: 22px;
  border: none;
  background: none;
  font-size: 18px;
  line-height: 1;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 4px;
}
.im-rating-close:hover { color: #4b5563; background: #f3f4f6; }
.im-rating-title { margin: 0 0 8px; font-size: 13px; color: #4b5563; }
.im-new-btn {
  padding: 7px 16px;
  border: 1px solid #16a34a;
  background: rgba(22, 163, 74, .08);
  color: #16a34a;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.im-new-btn:hover { background: #16a34a; color: #fff; }

/* 我的问答归档 */
.archive-list { display: flex; flex-direction: column; gap: 10px; }
.archive-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid rgba(34, 94, 56, .10);
  border-radius: 14px;
  cursor: pointer;
}
.archive-row:hover { border-color: rgba(22, 163, 74, .35); }
.archive-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.archive-title { display: flex; align-items: center; gap: 8px; }
.archive-title strong { font-size: 16px; font-weight: 800; color: #0f1f16; }
.archive-title small { font-size: 11px; padding: 1px 7px; border-radius: 999px; font-weight: 700; }
.tag-ended { background: #f0f0f0; color: #909399; }
.tag-ongoing { background: rgba(22, 163, 74, .12); color: #16a34a; }
.archive-preview {
  font-size: 14px;
  color: #4a5a50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.archive-meta { display: flex; gap: 10px; font-size: 12px; color: #9ca3a0; }
.archive-rated { color: #ca8a04; font-weight: 700; }
.archive-unread-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  background: #f56c6c;
  color: #fff;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* ========== 统一圆角规范 ========== */
:deep(.el-dialog) {
  border-radius: 20px;
}
</style>
