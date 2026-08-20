<template>
  <div class="expert-shell">
    <aside class="expert-sidebar">
      <div class="brand">
        <span class="brand-mark"><SproutIcon :size="24" variant="white" /></span>
        <div class="brand-copy">
          <strong>慧农宝</strong>
          <span>专家工作台</span>
        </div>
      </div>

      <nav class="side-nav" aria-label="专家工作台导航">
        <button
          v-for="section in sections"
          :key="section.key"
          type="button"
          :class="['side-nav-item', { active: active === section.key }]"
          @click="active = section.key"
        >
          <el-icon :size="22"><component :is="section.icon" /></el-icon>
          <span>{{ section.label }}</span>
        </button>
      </nav>

      <button class="sidebar-logout" type="button" @click="handleLogout">
        <el-icon :size="22"><SwitchButton /></el-icon>
        <span>退出登录</span>
      </button>
    </aside>

    <section class="expert-workspace">
      <header class="expert-topbar">
        <span class="topbar-spacer"></span>
        <div class="topbar-user">
          <span class="topbar-user-copy">
            <strong>{{ auth.user?.name || '专家' }}</strong>
          </span>
          <span class="topbar-avatar">
            <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="专家头像" />
            <span v-else>{{ (auth.user?.name || '张').charAt(0) }}</span>
          </span>
        </div>
      </header>

      <main class="expert-content">
        <template v-if="active === 'overview'">
          <div class="stats-grid">
            <article v-for="card in statCards" :key="card.label" class="stat-card">
              <span :class="['stat-icon', card.tone]">
                <el-icon :size="30"><component :is="card.icon" /></el-icon>
              </span>
              <strong class="stat-value">{{ card.value }}</strong>
              <span class="stat-label">{{ card.label }}</span>
            </article>
          </div>

          <section class="panel overview-panel">
            <div class="panel-heading">
              <h2>进行中的咨询</h2>
              <button class="text-action" type="button" @click="active = 'questions'">
                查看全部
                <el-icon :size="18"><ArrowRight /></el-icon>
              </button>
            </div>

            <div v-if="ongoingConsultations.length" class="overview-question-list">
              <button
                v-for="c in ongoingConsultations.slice(0, 4)"
                :key="c.id"
                class="overview-question"
                type="button"
                @click="openConsultation(c)"
              >
                <div>
                  <strong>{{ c.farmer_name || '农户' }}</strong>
                  <span>{{ c.last_preview || c.title || '点击查看会话' }}</span>
                </div>
                <span class="status-chip pending">进行中</span>
              </button>
            </div>
            <div v-else class="empty-state">暂无进行中的咨询</div>
          </section>
        </template>

        <template v-else-if="active === 'works'">
          <div v-if="groupedWorks.length" class="batch-group-list">
            <section v-for="group in groupedWorks" :key="group.batchId" class="batch-group">
              <!-- 批次头 -->
              <div class="batch-header">
                <div class="batch-header-left">
                  <span class="batch-crop-icon">{{ cropEmoji(group.cropName) }}</span>
                  <div class="batch-title">
                    <h2>{{ group.cropName }}<span v-if="group.cropVariety" class="batch-variety"> · {{ group.cropVariety }}</span></h2>
                    <div class="batch-meta">
                      <span class="batch-farmer-name">{{ group.farmerName }}</span>
                      <span class="batch-sep">·</span>
                      <span class="batch-no-tag">{{ group.batchNo }}</span>
                      <span class="batch-sep">·</span>
                      <span class="batch-land"><el-icon :size="15"><Location /></el-icon>{{ group.landName }}</span>
                      <span class="batch-sep">·</span>
                      <span>{{ group.plantDate }}种</span>
                      <span v-if="group.cropStatus === '已采收'" class="batch-harvested-tag">已采收</span>
                    </div>
                  </div>
                </div>

              </div>

              <!-- 该批次的农事作业时间线 -->
              <div class="batch-works">
                <article v-for="work in group.works" :key="work.id" class="work-timeline-item">
                  <div class="work-timeline-dot" :class="work.work_type"></div>
                  <div class="work-timeline-content">
                    <div class="work-timeline-top">
                      <span class="work-type-chip">{{ work.work_type }}</span>
                      <span v-if="work.has_photo" class="photo-chip">
                        <el-icon :size="14"><Picture /></el-icon>
                        有照片
                      </span>
                      <time>{{ work.work_date }}</time>
                    </div>
                    <p class="work-description">{{ work.description }}</p>
                    <div v-if="work.photos" class="work-photos">
                      <el-image
                        v-for="(url, i) in work.photos.split(',').filter(Boolean)"
                        :key="i"
                        :src="url"
                        :preview-src-list="work.photos.split(',').filter(Boolean)"
                        fit="cover"
                        class="work-photo"
                        preview-teleported
                      />
                    </div>
                    <div v-if="work.advice" class="advice-box">
                      <strong>我的建议：</strong>
                      <span>{{ work.advice }}</span>
                    </div>
                    <div v-else class="advice-editor">
                      <el-input
                        v-model="adviceContents[work.id]"
                        placeholder="填写专业指导建议..."
                        @keyup.enter="submitAdvice(work.id)"
                      />
                      <button
                        class="green-action compact"
                        type="button"
                        :disabled="advising === work.id"
                        @click="submitAdvice(work.id)"
                      >
                        <el-icon :size="18"><Promotion /></el-icon>
                        {{ advising === work.id ? '提交中' : '提交' }}
                      </button>
                    </div>
                  </div>
                </article>
              </div>
            </section>
          </div>
          <div v-else class="panel empty-state">暂无农事作业记录</div>
        </template>

        <template v-else-if="active === 'questions'">
          <div class="consult-workspace">
            <!-- 左侧：会话列表 -->
            <aside class="consult-sessions">
              <div class="sessions-header">
                <h2>会话列表</h2>
                <div class="session-tabs">
                  <button
                    v-for="tab in sessionTabs"
                    :key="tab.value"
                    :class="['session-tab', { active: sessionFilter === tab.value }]"
                    type="button"
                    @click="sessionFilter = tab.value"
                  >{{ tab.label }}</button>
                </div>
              </div>

              <div v-if="groupedConsultations.length" class="session-list">
                <div v-for="group in groupedConsultations" :key="group.farmerId" class="farmer-group">
                  <button
                    type="button"
                    :class="['farmer-group-header', { expanded: expandedFarmer === group.farmerId }]"
                    @click="toggleFarmer(group.farmerId)"
                  >
                    <img v-if="group.avatar" :src="group.avatar" class="farmer-avatar-img" />
                    <span v-else class="farmer-avatar-text">{{ group.farmerName.charAt(0) }}</span>
                    <span class="farmer-group-info">
                      <strong>{{ group.farmerName }}</strong>
                      <small>{{ group.sessions.length }} 次咨询</small>
                    </span>
                    <el-icon :size="16" :class="['farmer-chevron', { rotated: expandedFarmer === group.farmerId }]"><ArrowDown /></el-icon>
                  </button>
                  <div v-show="expandedFarmer === group.farmerId" class="farmer-sessions">
                    <button
                      v-for="c in group.sessions"
                      :key="c.id"
                      :class="['session-item', { active: selectedConsultation?.id === c.id }]"
                      type="button"
                      @click="openConsultation(c)"
                    >
                      <span class="session-main">
                        <span class="session-top">
                          <span class="session-title">{{ c.title }}</span>
                          <small>{{ formatSessionTime(c.updated_at || c.created_at) }}</small>
                        </span>
                        <span class="session-preview">{{ c.last_preview || '点击查看会话' }}</span>
                        <span class="session-meta">
                          <span :class="['session-status', c.status === '进行中' ? 'ongoing' : 'ended']">{{ c.status }}</span>
                          <span v-if="c.rating" class="session-rated">已评 {{ c.rating }}★</span>
                        </span>
                        <!-- 软提示：农户已 N 分钟未回复（不自动结束、不打断、不弹窗） -->
                        <span v-if="c.farmer_idle_minutes" class="session-idle-hint">
                          农户已 {{ c.farmer_idle_minutes }} 分钟未回复
                        </span>
                      </span>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="session-empty">暂无{{ sessionFilter === '全部' ? '' : sessionFilter }}咨询会话</div>
            </aside>

            <!-- 右侧：聊天面板 -->
            <section class="consult-chat">
              <template v-if="selectedConsultation">
                <div class="chat-header">
                  <div class="chat-farmer">
                    <img v-if="selectedConsultation.farmer_avatar" :src="selectedConsultation.farmer_avatar" class="farmer-avatar-img chat-header-avatar" />
                    <span v-else class="farmer-avatar">{{ (selectedConsultation.farmer_name || '农').charAt(0) }}</span>
                    <div>
                      <h2>{{ selectedConsultation.farmer_name || '农户' }}</h2>
                      <p>咨询主题：{{ selectedConsultation.title }}</p>
                    </div>
                  </div>
                  <div class="chat-actions">
                    <button
                      v-if="selectedConsultation.status === '进行中'"
                      class="end-btn" type="button" @click="confirmEndConsultation"
                    >结束会话</button>
                    <span v-else class="ended-tag">
                      已结束<span v-if="selectedConsultation.ended_by === 'farmer'">（农户结束）</span><span v-if="selectedConsultation.rating"> · 已评 {{ selectedConsultation.rating }}★</span>
                    </span>
                  </div>
                </div>

                <div class="chat-messages" ref="chatMessagesRef">
                  <div v-if="!consultationMessages.length" class="messages-empty">暂无消息</div>
                  <div
                    v-for="msg in consultationMessages"
                    :key="msg.id"
                    :class="['msg-bubble', msg.sender_role === 'expert' ? 'mine' : 'theirs']"
                  >
                    <div class="msg-content">
                      <p v-if="msg.content" class="msg-text">{{ msg.content }}</p>
                      <div v-if="msg.images" class="msg-images">
                        <el-image
                          v-for="(url, i) in msg.images.split(',').filter(Boolean)"
                          :key="i"
                          :src="url"
                          :preview-src-list="msg.images.split(',').filter(Boolean)"
                          fit="cover"
                          class="msg-image"
                          preview-teleported
                        />
                      </div>
                    </div>
                    <time class="msg-time">{{ formatMsgTime(msg.created_at) }}</time>
                  </div>
                </div>

                <div class="chat-input-box" v-if="selectedConsultation.status === '进行中'">
                  <div v-if="pendingImages.length" class="image-preview-bar">
                    <div v-for="(url, idx) in pendingImages" :key="idx" class="image-preview-thumb">
                      <img :src="url" :alt="`预览 ${idx + 1}`" />
                      <button type="button" class="image-preview-remove" title="移除" @click="removePendingImage(idx)">×</button>
                    </div>
                  </div>
                  <div class="textarea-wrap">
                    <el-input
                      v-model="consultationInput"
                      type="textarea"
                      :rows="2"
                      resize="none"
                      placeholder="输入回复，回车发送"
                      @keydown.enter.exact.prevent="sendMessage"
                    />
                    <input ref="imageInputRef" type="file" accept="image/*" multiple @change="onPickImages" hidden />
                    <button class="im-img-btn-inner-left" type="button" title="上传图片" @click="imageInputRef?.click()">
                      <el-icon :size="20"><Picture /></el-icon>
                    </button>
                    <button
                      class="send-btn-inner" type="button"
                      :class="{ 'send-btn-inner-active': consultationInput.trim() || pendingImages.length }"
                      :disabled="sending || (!consultationInput.trim() && !pendingImages.length)"
                      title="发送回复"
                      @click="sendMessage"
                    >
                      <el-icon :size="20"><Top /></el-icon>
                    </button>
                  </div>
                </div>
                <div class="chat-input-box chat-readonly" v-else>
                  <span>会话已结束</span>
                </div>
              </template>
              <div v-else class="chat-placeholder">
                <el-icon :size="48"><ChatDotRound /></el-icon>
                <p>从左侧选择农户会话开始回复</p>
              </div>
            </section>
          </div>
        </template>

        <template v-else-if="active === 'articles'">
          <div class="page-heading page-heading-row">
            <div></div>
            <button class="green-action" type="button" @click="openArticle()">
              <el-icon :size="20"><Plus /></el-icon>
              发布文章
            </button>
          </div>

          <section class="panel article-panel">
            <div v-if="myArticles.length" class="article-table-wrap">
              <table class="article-table">
                <thead>
                  <tr>
                    <th>标题</th>
                    <th>分类</th>
                    <th>状态</th>
                    <th>日期</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="article in myArticles" :key="article.id">
                    <td class="article-title-cell">{{ article.title }}</td>
                    <td><span class="category-chip">{{ article.category }}</span></td>
                    <td>
                      <div class="status-stack">
                        <span :class="['status-chip', articleStatusClass(article.review_status)]">
                          {{ articleStatusText(article.review_status) }}
                        </span>
                        <small v-if="article.review_status === 'rejected' && article.review_reason" class="reject-reason">
                          <span class="reject-reason-label">拒绝原因：</span>{{ article.review_reason }}
                        </small>
                      </div>
                    </td>
                    <td class="article-date-cell">{{ article.date }}</td>
                    <td>
                      <div class="table-actions">
                        <button type="button" class="table-action" @click="openArticle(article)">
                          编辑
                        </button>
                        <button type="button" class="table-action danger" @click="removeArticle(article)">删除</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state">暂无文章，点击右上角提交第一篇文章</div>
          </section>
        </template>

        <template v-else>
          <div class="profile-workbench profile-workbench--single">
            <section class="panel profile-card">
              <div class="profile-avatar-row">
                <div class="profile-avatar">
                  <img v-if="profileForm.avatar" :src="profileForm.avatar" alt="专家头像" />
                  <span v-else>{{ (profileForm.name || auth.user?.name || '专').charAt(0) }}</span>
                </div>
                <div>
                  <h2>{{ profileForm.name || '农业专家' }}</h2>
                  <p>{{ profileForm.title || '完善职称后展示在专家资料中' }}</p>
                  <el-upload
                    accept="image/*"
                    :auto-upload="false"
                    :show-file-list="false"
                    :on-change="handleAvatarChange"
                  >
                    <button class="outline-action" type="button" :disabled="avatarUploading">
                      {{ avatarUploading ? '上传中' : '更换头像' }}
                    </button>
                  </el-upload>
                </div>
              </div>

              <el-form label-position="top" class="profile-form">
                <div class="form-grid">
                  <el-form-item label="姓名">
                    <el-input v-model="profileForm.name" placeholder="请输入专家姓名" />
                  </el-form-item>
                  <el-form-item label="职称">
                    <el-input
                      v-model="profileForm.title"
                      placeholder="由管理员维护"
                      readonly
                      :title="'职称由管理员维护，如需修改请联系管理员'"
                    />
                  </el-form-item>
                </div>
                <el-form-item label="专业领域">
                  <el-input
                    v-model="profileForm.specialty"
                    placeholder="由管理员维护"
                    readonly
                    :title="'专业领域由管理员维护，如需修改请联系管理员'"
                  />
                </el-form-item>
                <el-form-item label="个人简介">
                  <el-input v-model="profileForm.bio" type="textarea" :rows="5" placeholder="介绍您的研究方向、擅长作物和服务经验" maxlength="200" show-word-limit />
                </el-form-item>
                <div class="profile-save-row">
                  <button class="green-action" type="button" :disabled="profileSaving" @click="saveProfile">
                    {{ profileSaving ? '保存中' : '保存资料' }}
                  </button>
                </div>
              </el-form>
            </section>
          </div>
        </template>
      </main>
    </section>

    <!-- 全屏写文章覆盖层（固定定位，不随页面滚动） -->
    <div v-if="articleEditorVisible" class="article-overlay">
      <div class="article-overlay-bar">
        <button type="button" class="article-overlay-back" @click="closeArticleEditor">
          <el-icon :size="20"><Back /></el-icon>
          返回文章列表
        </button>
        <strong>{{ editingArticleId ? '编辑文章' : '发布文章' }}</strong>
        <div class="article-overlay-actions">
          <button type="button" class="article-overlay-btn cancel" @click="closeArticleEditor">取消</button>
          <button type="button" class="article-overlay-btn submit" :disabled="articleSaving" @click="saveArticle">
            {{ articleSaving ? '提交中' : (editingArticleId ? '保存并重新提交' : '提交审核') }}
          </button>
        </div>
      </div>
      <div class="article-overlay-body">
        <el-form label-position="top" class="article-form">
          <el-form-item label="文章标题">
            <el-input v-model="articleForm.title" placeholder="请输入文章标题" maxlength="50" show-word-limit />
          </el-form-item>
          <el-form-item label="文章分类">
            <el-select
              v-model="articleForm.category"
              placeholder="请选择文章分类"
              popper-class="expert-category-popper"
              style="width: 100%"
            >
              <el-option v-for="category in articleCategories" :key="category" :label="category" :value="category" />
            </el-select>
          </el-form-item>
          <el-form-item label="文章来源">
            <el-input v-model="articleForm.source" placeholder="如：农业农村部信息中心（选填，原创不填）" />
          </el-form-item>
          <el-form-item label="原文作者">
            <el-input v-model="articleForm.original_author" placeholder="如：新华社记者 张三（选填，转载时填写）" />
          </el-form-item>
          <el-form-item label="封面图">
            <div class="cover-upload-row">
              <el-upload
                :show-file-list="false"
                accept="image/jpeg,image/png,image/webp,image/gif"
                :auto-upload="false"
                :on-change="handleArticleCoverChange"
              >
                <button type="button" class="editor-tool-btn" :disabled="articleCoverUploading">
                  <el-icon :size="18"><Picture /></el-icon>
                  {{ articleCoverUploading ? '上传中...' : '上传封面' }}
                </button>
              </el-upload>
              <div v-if="articleForm.cover" class="cover-preview">
                <img :src="articleForm.cover" alt="封面预览" />
                <button type="button" class="cover-remove" @click="articleForm.cover = ''">
                  <el-icon :size="14"><CloseBold /></el-icon>
                </button>
              </div>
              <span class="cover-hint">建议 16:9 比例，农户端资讯页展示（选填）</span>
            </div>
          </el-form-item>
          <el-form-item label="文章正文">
            <div class="article-editor-wrap">
              <div class="article-editor-toolbar">
                <button type="button" class="editor-tool-btn" :disabled="articleImageUploading" @mousedown.prevent @click="triggerArticleImage">
                  <el-icon :size="18"><Picture /></el-icon>
                  <span>{{ articleImageUploading ? '上传中...' : '插入图片' }}</span>
                </button>
                <input ref="articleImageInputRef" type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden @change="onPickArticleImage" />
                <span class="editor-tool-hint">图片会插入到光标位置，发布后农户端正常显示</span>
                <div class="editor-tabs">
                  <button type="button" :class="['editor-tab', { active: editorMode === 'edit' }]" @mousedown.prevent @click="editorMode = 'edit'">编辑</button>
                  <button type="button" :class="['editor-tab', { active: editorMode === 'preview' }]" @mousedown.prevent @click="editorMode = 'preview'">预览</button>
                </div>
              </div>
              <el-input
                v-show="editorMode === 'edit'"
                v-model="articleForm.content"
                type="textarea"
                :rows="18"
                ref="articleContentRef"
                placeholder="请输入文章正文内容，可点击上方按钮在正文中插入图片"
                maxlength="10000"
                show-word-limit
              />
              <div v-show="editorMode === 'preview'" class="article-preview-body" v-html="articlePreviewHtml"></div>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 删除文章确认弹窗 -->
    <el-dialog v-model="deleteDialogVisible" title="删除文章" width="460px" class="form-dialog confirm-dialog danger" :close-on-click-modal="false">
      <div class="confirm-dialog__body">确定删除《{{ deletingArticle?.title }}》吗？</div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleteSaving" @click="confirmDelete">确定删除</el-button>
      </template>
    </el-dialog>

    <!-- 结束会话确认弹窗 -->
    <el-dialog v-model="endConfirmVisible" title="结束会话" width="460px" class="form-dialog confirm-dialog" :close-on-click-modal="false">
      <div class="confirm-dialog__body">确定结束本次咨询？结束后农户可对本次服务评价。</div>
      <template #footer>
        <el-button @click="endConfirmVisible = false">取消</el-button>
        <el-button type="primary" @click="executeEndConsultation">结束会话</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  ArrowRight,
  Back,
  ChatDotRound,
  CircleCheck,
  Clock,
  CloseBold,
  SwitchButton,
  DataAnalysis,
  Document,
  List,
  Location,
  Notebook,
  Picture,
  Plus,
  Promotion,
  Star,
  User,
  ArrowDown,
  Top,
} from '@element-plus/icons-vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import SproutIcon from '@/components/SproutIcon.vue'

type SectionKey = 'overview' | 'works' | 'questions' | 'articles' | 'profile'

const router = useRouter()
const auth = useAuthStore()
const active = ref<SectionKey>('overview')

const sections = [
  { key: 'overview' as SectionKey, label: '数据看板', icon: DataAnalysis },
  { key: 'works' as SectionKey, label: '农事指导', icon: List },
  { key: 'questions' as SectionKey, label: '农户咨询', icon: ChatDotRound },
  { key: 'articles' as SectionKey, label: '文章管理', icon: Document },
  { key: 'profile' as SectionKey, label: '个人中心', icon: User },
]

const currentSection = computed(() => sections.find(section => section.key === active.value) || sections[0])

const works = ref<any[]>([])
const consultations = ref<any[]>([])
const articles = ref<any[]>([])
const adviceContents = reactive<Record<number, string>>({})
const advising = ref<number | null>(null)

// 会话 IM 状态
const sessionFilter = ref<'进行中' | '已结束' | '全部'>('进行中')
const sessionTabs = [
  { label: '进行中', value: '进行中' as const },
  { label: '已结束', value: '已结束' as const },
]
const expandedFarmer = ref<number | null>(null)
const selectedConsultation = ref<any | null>(null)
const consultationMessages = ref<any[]>([])
const consultationInput = ref('')
const pendingImages = ref<string[]>([])
const sending = ref(false)
const imageInputRef = ref<HTMLInputElement | null>(null)
const chatMessagesRef = ref<HTMLElement | null>(null)
const pollingTimer = ref<number | null>(null)

const articleEditorVisible = ref(false)
const articleSaving = ref(false)
const articleCoverUploading = ref(false)
const articleImageUploading = ref(false)
const articleImageInputRef = ref<HTMLInputElement | null>(null)
const articleContentRef = ref<any>(null)
const editingArticleId = ref<number | null>(null)
const deleteDialogVisible = ref(false)
const deletingArticle = ref<any>(null)
const deleteSaving = ref(false)
const articleCategories = ['农业要闻', '政策解读', '种植技术', '病虫害防治', '市场行情']
const articleForm = reactive({
  title: '',
  category: '',
  source: '',
  original_author: '',
  summary: '',
  content: '',
  cover: '',
})
const editorMode = ref<'edit' | 'preview'>('edit')

// 文章正文预览（渲染 Markdown 图片语法，与管理员端/农户端保持一致）
const articlePreviewHtml = computed(() => renderArticlePreview(articleForm.content))

function renderArticlePreview(content: string): string {
  if (!content) return '<div class="preview-empty">暂无内容，开始写文章后可切换到预览查看效果</div>'
  const lines = content.split('\n')
  const html: string[] = []
  let paragraph: string[] = []
  const flushParagraph = () => {
    if (paragraph.length) {
      const text = paragraph.join('<br>').trim()
      if (text) html.push(`<p>${text}</p>`)
      paragraph = []
    }
  }
  const imgRegex = /^!\[([^\]]*)\]\(([^)]+)\)\s*$/
  for (const rawLine of lines) {
    const line = rawLine.trim()
    const imgMatch = line.match(imgRegex)
    if (imgMatch) {
      flushParagraph()
      const alt = escapeHtml(imgMatch[1])
      const url = escapeAttr(imgMatch[2])
      html.push(`<figure class="article-img"><img src="${url}" alt="${alt}" /><figcaption>${alt}</figcaption></figure>`)
    } else if (line === '') {
      flushParagraph()
    } else {
      paragraph.push(escapeHtml(line))
    }
  }
  flushParagraph()
  return html.join('')
}

function escapeHtml(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function escapeAttr(text: string) {
  return text.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const profileSaving = ref(false)
const avatarUploading = ref(false)
const profileForm = reactive({
  name: '',
  avatar: '',
  title: '',
  specialty: '',
  bio: '',
})

const ongoingConsultations = computed(() =>
  consultations.value.filter(c => c.status === '进行中')
)
const endedConsultations = computed(() =>
  consultations.value.filter(c => c.status === '已结束')
)

// 农事作业按种植批次分组
const groupedWorks = computed(() => {
  const map = new Map<number, {
    batchId: number
    batchNo: string
    cropName: string
    cropVariety: string
    cropStatus: string
    landName: string
    farmerName: string
    plantDate: string
    works: any[]
  }>()

  for (const w of works.value) {
    const bid = w.batch_id
    if (!map.has(bid)) {
      map.set(bid, {
        batchId: bid,
        batchNo: w.batch_no || '',
        cropName: w.crop_name || '未知作物',
        cropVariety: w.crop_variety || '',
        cropStatus: w.crop_status || '',
        landName: w.land_name || '',
        farmerName: w.farmer_name || '农户',
        plantDate: w.plant_date || '',
        works: [],
      })
    }
    map.get(bid)!.works.push(w)
  }

  // 批次内作业按日期升序（从播种→采收的自然叙事）
  for (const g of map.values()) {
    g.works.sort((a, b) =>
      (a.work_date || '').localeCompare(b.work_date || '')
    )
  }

  // 批次之间按种植日期降序（最新种植的排前面）
  return Array.from(map.values()).sort((a, b) =>
    (b.plantDate || '').localeCompare(a.plantDate || '')
  )
})

const CROP_EMOJI_MAP: Record<string, string> = {
  '生菜': '🥬', '白菜': '🥬', '菠菜': '🥬', '芹菜': '🥬', '韭菜': '🥬',
  '番茄': '🍅', '西红柿': '🍅',
  '黄瓜': '🥒', '茄子': '🍆', '辣椒': '🌶️', '玉米': '🌽',
  '萝卜': '🥕', '胡萝卜': '🥕', '土豆': '🥔', '洋葱': '🧅', '大蒜': '🧄',
  '西瓜': '🍉', '草莓': '🍓', '苹果': '🍎', '葡萄': '🍇',
  '水稻': '🌾', '小麦': '🌾',
}

function cropEmoji(name: string): string {
  return CROP_EMOJI_MAP[name] || '🌱'
}
const filteredConsultations = computed(() => {
  if (sessionFilter.value === '全部') return consultations.value
  return consultations.value.filter(c => c.status === sessionFilter.value)
})

// 按农户分组（同一农户的多次咨询聚合）
const groupedConsultations = computed(() => {
  const list = filteredConsultations.value
  const map = new Map<number, {
    farmerId: number
    farmerName: string
    avatar: string | null
    sessions: any[]
  }>()

  for (const c of list) {
    const fid = c.farmer_id || 0
    if (!map.has(fid)) {
      map.set(fid, {
        farmerId: fid,
        farmerName: c.farmer_name || '农户',
        avatar: c.farmer_avatar || null,
        sessions: [],
      })
    }
    map.get(fid)!.sessions.push(c)
  }

  // 每个农户的会话按时间降序
  for (const g of map.values()) {
    g.sessions.sort((a, b) =>
      (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || '')
    )
  }

  // 农户之间按最近会话时间降序
  return Array.from(map.values()).sort((a, b) => {
    const aLatest = a.sessions[0]?.updated_at || a.sessions[0]?.created_at || ''
    const bLatest = b.sessions[0]?.updated_at || b.sessions[0]?.created_at || ''
    return bLatest.localeCompare(aLatest)
  })
})

function toggleFarmer(farmerId: number) {
  expandedFarmer.value = expandedFarmer.value === farmerId ? null : farmerId
}
const myArticles = computed(() => {
  const userId = auth.user?.id
  return userId ? articles.value.filter(article => article.author_id === userId) : articles.value
})

// 专家好评率：4-5星占比（按已结束且已评价会话）
const myPositiveRate = computed(() => {
  const rated = endedConsultations.value.filter(c => c.rating != null)
  if (!rated.length) return null
  const positive = rated.filter(c => c.rating >= 4).length
  return Math.round((positive * 100) / rated.length)
})

const statCards = computed(() => [
  { value: ongoingConsultations.value.length, label: '进行中咨询', icon: ChatDotRound, tone: 'amber' },
  { value: endedConsultations.value.length, label: '已结束咨询', icon: CircleCheck, tone: 'green' },
  { value: myArticles.value.length, label: '已发文章', icon: Notebook, tone: 'cyan' },
  { value: myPositiveRate.value == null ? '—' : `${myPositiveRate.value}%`, label: '农户好评率', icon: Star, tone: 'gold' },
])

async function fetchWorks() {
  try {
    works.value = await api.getExpertWorks()
  } catch {
    works.value = []
  }
}

async function fetchConsultations() {
  try {
    consultations.value = await api.getExpertQuestions()
  } catch {
    consultations.value = []
  }
}

async function fetchArticles() {
  try {
    articles.value = await api.getMyArticles()
  } catch {
    articles.value = []
  }
}

function syncProfileForm() {
  profileForm.name = auth.user?.name || ''
  profileForm.avatar = auth.user?.avatar || ''
  profileForm.title = auth.user?.title || ''
  profileForm.specialty = auth.user?.specialty || ''
  profileForm.bio = auth.user?.bio || ''
}

async function handleAvatarChange(file: UploadFile) {
  if (!file.raw) return
  avatarUploading.value = true
  try {
    const res = await api.uploadAvatar(file.raw)
    profileForm.avatar = res.url
    await api.updateProfile({ avatar: res.url })
    await auth.fetchUser()
    syncProfileForm()
    ElMessage.success('头像已更新')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
  } finally {
    avatarUploading.value = false
  }
}

async function saveProfile() {
  if (!profileForm.name.trim()) {
    ElMessage.warning('请输入专家姓名')
    return
  }

  profileSaving.value = true
  try {
    // 专家不能修改职称和专业领域（由管理员维护），仅提交允许的字段
    await api.updateProfile({
      name: profileForm.name.trim(),
      avatar: profileForm.avatar || null,
      bio: profileForm.bio.trim() || null,
    })
    await auth.fetchUser()
    syncProfileForm()
    ElMessage.success('个人资料已保存')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '资料保存失败')
  } finally {
    profileSaving.value = false
  }
}

function articleStatusText(status = 'published') {
  const map: Record<string, string> = {
    pending: '待审核',
    published: '已发布',
    rejected: '已拒绝',
  }
  return map[status] || '待审核'
}

function articleStatusClass(status = 'published') {
  const map: Record<string, string> = {
    pending: 'pending',
    published: 'answered',
    rejected: 'rejected',
  }
  return map[status] || 'pending'
}

// ========== 会话 IM ==========
function formatMsgTime(ts: string) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formatSessionTime(ts: string) {
  if (!ts) return ''
  const d = new Date(ts)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

function scrollToBottom() {
  if (chatMessagesRef.value) chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
}

async function loadMessages(consultationId: number) {
  try {
    consultationMessages.value = await api.listMessages(consultationId, 0)
    await nextTick()
    scrollToBottom()
  } catch {
    consultationMessages.value = []
  }
}

function startPolling(consultationId: number) {
  stopPolling()
  pollingTimer.value = window.setInterval(async () => {
    if (!selectedConsultation.value || selectedConsultation.value.id !== consultationId) {
      stopPolling()
      return
    }
    try {
      const lastId = consultationMessages.value.length
        ? Math.max(...consultationMessages.value.map(m => m.id))
        : 0
      const newMsgs = await api.listMessages(consultationId, lastId)
      if (newMsgs.length) {
        consultationMessages.value.push(...newMsgs)
        await nextTick()
        scrollToBottom()
      }
      // 同步会话状态：农户可能已结束/评价
      const fresh: any[] = await api.getExpertQuestions()
      consultations.value = fresh
      const cur = fresh.find(c => c.id === consultationId)
      if (cur && cur.status === '已结束' && selectedConsultation.value?.status !== '已结束') {
        selectedConsultation.value = cur
        stopPolling()
        if (cur.ended_by === 'farmer') ElMessage.info('农户已结束本次会话')
      } else if (cur) {
        selectedConsultation.value = cur
      }
    } catch {}
  }, 3000)
}

async function openConsultation(c: any) {
  active.value = 'questions'
  stopPolling()
  selectedConsultation.value = c
  consultationInput.value = ''
  pendingImages.value = []
  await loadMessages(c.id)
  if (c.status === '进行中') startPolling(c.id)
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

function clearPendingImages() {
  pendingImages.value = []
}

async function sendMessage() {
  if (!selectedConsultation.value) return
  const content = consultationInput.value.trim()
  const images = pendingImages.value.length ? pendingImages.value.join(',') : null
  if (!content && !images) return
  sending.value = true
  try {
    const msg = await api.sendMessage(selectedConsultation.value.id, { content, images })
    consultationMessages.value.push(msg)
    consultationInput.value = ''
    pendingImages.value = []
    await nextTick()
    scrollToBottom()
    // 刷新会话列表的预览/时间
    const fresh: any[] = await api.getExpertQuestions()
    consultations.value = fresh
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

const endConfirmVisible = ref(false)

function confirmEndConsultation() {
  if (!selectedConsultation.value) return
  endConfirmVisible.value = true
}

async function executeEndConsultation() {
  if (!selectedConsultation.value) return
  endConfirmVisible.value = false
  try {
    const res = await api.endConsultation(selectedConsultation.value.id)
    // 后端返回 system_message（结束语消息对象），直接 push 到本地消息列表，
    // 不依赖下一次 loadMessages 拉取，避免 race condition 导致专家看不到结束语
    const sysMsg = res?.system_message
    if (sysMsg && !consultationMessages.value.some(m => m.id === sysMsg.id)) {
      consultationMessages.value.push(sysMsg)
      await nextTick()
      scrollToBottom()
    }
    const fresh: any[] = await api.getExpertQuestions()
    consultations.value = fresh
    const cur = fresh.find(c => c.id === selectedConsultation.value!.id)
    if (cur) selectedConsultation.value = cur
    stopPolling()
    ElMessage.success('会话已结束')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '结束失败')
  }
}

async function submitAdvice(workId: number) {
  if (!adviceContents[workId]?.trim()) {
    ElMessage.warning('请输入指导建议')
    return
  }

  advising.value = workId
  try {
    await api.createExpertAdvice(workId, adviceContents[workId].trim())
    ElMessage.success('指导建议已提交')
    delete adviceContents[workId]
    await fetchWorks()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '提交失败')
  } finally {
    advising.value = null
  }
}

function openArticle(article?: any) {
  editingArticleId.value = article?.id || null
  articleForm.title = article?.title || ''
  articleForm.category = article?.category || ''
  articleForm.source = article?.source || ''
  articleForm.original_author = article?.original_author || ''
  articleForm.summary = article?.summary || ''
  articleForm.content = article?.content || ''
  articleForm.cover = article?.cover || ''
  articleEditorVisible.value = true
}

function closeArticleEditor() {
  articleEditorVisible.value = false
}

async function handleArticleCoverChange(file: UploadFile) {
  if (!file.raw) return
  articleCoverUploading.value = true
  try {
    const res = await api.uploadArticleCover(file.raw)
    articleForm.cover = res.url
    ElMessage.success('封面已上传')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '封面上传失败')
  } finally {
    articleCoverUploading.value = false
  }
}

// 触发图片选择
function triggerArticleImage() {
  articleImageInputRef.value?.click()
}

// 获取正文 textarea 原生元素（兼容 Element Plus 组件实例暴露方式）
function getArticleTextarea(): HTMLTextAreaElement | null {
  const inst: any = articleContentRef.value
  if (!inst) return null
  if (inst.textarea instanceof HTMLTextAreaElement) return inst.textarea
  const root: any = inst.$el ?? inst.ref
  if (root?.querySelector) {
    return root.querySelector('textarea')
  }
  return null
}

// 选择图片后上传并插入到正文光标位置
async function onPickArticleImage(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  articleImageUploading.value = true
  try {
    const res = await api.uploadArticleImage(file)
    // Markdown 图片语法
    const imgMarkdown = `\n\n![图片](${res.url})\n\n`

    // 在光标位置插入（元素未选中或未聚焦时 selectionStart 仍保留上次位置）
    const textarea = getArticleTextarea()
    if (textarea) {
      const start = textarea.selectionStart ?? articleForm.content.length
      const end = textarea.selectionEnd ?? start
      articleForm.content = articleForm.content.substring(0, start) + imgMarkdown + articleForm.content.substring(end)
      // 光标移到插入内容之后
      await nextTick()
      const newPos = start + imgMarkdown.length
      textarea.focus()
      textarea.setSelectionRange(newPos, newPos)
    } else {
      articleForm.content += imgMarkdown
    }
    ElMessage.success('图片已插入')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '图片上传失败')
  } finally {
    articleImageUploading.value = false
    target.value = ''  // 允许重复选择同一文件
  }
}

async function saveArticle() {
  if (!articleForm.title.trim() || !articleForm.category || !articleForm.content.trim()) {
    ElMessage.warning('请填写标题、分类和正文')
    return
  }

  articleSaving.value = true
  try {
    const payload = {
      title: articleForm.title.trim(),
      category: articleForm.category,
      source: articleForm.source.trim() || null,
      original_author: articleForm.original_author.trim() || null,
      summary: articleForm.summary.trim() || null,
      content: articleForm.content.trim(),
      cover: articleForm.cover || null,
    }

    if (editingArticleId.value) {
      await api.updateArticle(editingArticleId.value, payload)
      // 根据原状态判断提示
      const original = myArticles.value.find(a => a.id === editingArticleId.value)
      if (original?.review_status === 'rejected') {
        ElMessage.success('文章已修改并重新提交审核')
      } else {
        ElMessage.success('文章已更新')
      }
    } else {
      await api.createArticle(payload)
      ElMessage.success('文章已提交审核')
    }

    articleEditorVisible.value = false
    await fetchArticles()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    articleSaving.value = false
  }
}

function removeArticle(article: any) {
  deletingArticle.value = article
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  if (!deletingArticle.value) return
  deleteSaving.value = true
  try {
    await api.deleteArticle(deletingArticle.value.id)
    ElMessage.success('文章已删除')
    deleteDialogVisible.value = false
    deletingArticle.value = null
    await fetchArticles()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  } finally {
    deleteSaving.value = false
  }
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  if (auth.token && !auth.user) await auth.fetchUser()
  syncProfileForm()
  await Promise.all([fetchWorks(), fetchConsultations(), fetchArticles()])
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.expert-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #f3faf5;
  color: #142117;
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
}

.expert-sidebar {
  display: flex;
  flex: 0 0 340px;
  flex-direction: column;
  height: 100%;
  background: #f8fff9;
  border-right: 1px solid #dbe9df;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 92px;
  padding: 0 28px;
  border-bottom: 1px solid #dbe9df;
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 15px;
  background: #178844;
  color: #fff;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.brand-copy strong {
  color: #102016;
  font-size: 20px;
  line-height: 1.1;
  font-weight: 900;
}

.brand-copy span {
  color: #7c8d82;
  font-size: 14px;
}

.side-nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
}

.side-nav-item {
  display: flex;
  align-items: center;
  gap: 16px;
  border: 0;
  background: transparent;
  color: #52635a;
  font-family: inherit;
  font-size: 20px;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.sidebar-logout {
  display: flex;
  align-items: center;
  gap: 16px;
  border: 0;
  background: transparent;
  color: #52635a;
  font-family: inherit;
  font-size: 20px;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.side-nav-item {
  min-height: 56px;
  padding: 0 20px;
  border-radius: 12px;
  transition: background .2s, color .2s;
}

.side-nav-item:hover {
  background: #edf8ef;
  color: #178844;
}

.side-nav-item.active {
  background: #ddf2e3;
  color: #178844;
}

.sidebar-logout {
  flex-shrink: 0;
  min-height: 84px;
  padding: 0 28px;
  border-top: 1px solid #dbe9df;
  color: #66766d;
}

.sidebar-logout:hover {
  color: #178844;
}

.expert-workspace {
  display: flex;
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
}

.expert-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 92px;
  padding: 0 42px;
  background: #fff;
  border-bottom: 1px solid #dbe9df;
}

.topbar-spacer {
  flex: 1;
}

.topbar-title {
  color: #7b8b82;
  font-size: 19px;
}

.topbar-user {
  display: flex;
  align-items: center;
  gap: 14px;
}

.topbar-user-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-end;
}

.topbar-user-copy strong {
  color: #152117;
  font-size: 18px;
}

.topbar-user-copy span {
  color: #7b8b82;
  font-size: 14px;
}

.topbar-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  overflow: hidden;
  border-radius: 50%;
  background: #edf4e8;
  color: #52665a;
  font-size: 22px;
  font-weight: 900;
}

.topbar-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.expert-content {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 32px 42px 56px;
  background: #f3faf5;
}

.page-heading {
  margin-bottom: 28px;
}

.page-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.page-heading h1 {
  margin: 0;
  color: #102016;
  font-size: 32px;
  line-height: 1.2;
  font-weight: 900;
}

.page-heading p {
  margin: 12px 0 0;
  color: #718178;
  font-size: 19px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 24px;
  margin-bottom: 30px;
}

.stat-card {
  display: flex;
  min-height: 210px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 28px 30px;
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  margin-bottom: 18px;
  border-radius: 50%;
}

.stat-icon.amber {
  background: #fff0ce;
  color: #9e6d12;
}

.stat-icon.green {
  background: #e3f2e8;
  color: #23904e;
}

.stat-icon.cyan {
  background: #d9f3f7;
  color: #0e9db7;
}

.stat-icon.gold {
  background: #f9efd7;
  color: #c59614;
}

.stat-value {
  color: #08170c;
  font-size: 46px;
  line-height: 1;
  font-weight: 900;
}

.stat-label {
  margin-top: 8px;
  color: #5f7066;
  font-size: 19px;
}

.panel {
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.overview-panel {
  padding: 32px 30px 24px;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-heading h2 {
  margin: 0;
  color: #102016;
  font-size: 25px;
  font-weight: 900;
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 0;
  background: transparent;
  color: #178844;
  font: inherit;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}

.overview-question-list {
  display: flex;
  flex-direction: column;
}

.overview-question {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  width: 100%;
  min-height: 86px;
  padding: 18px 0;
  border: 0;
  border-bottom: 1px solid #e4ece6;
  background: transparent;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.overview-question:last-child {
  border-bottom: 0;
}

.overview-question:hover strong {
  color: #178844;
}

.overview-question div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
}

.overview-question strong {
  overflow: hidden;
  color: #162419;
  font-size: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-question span:not(.status-chip) {
  color: #718178;
  font-size: 16px;
}

.status-chip {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  min-height: 30px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 800;
}

.status-chip.pending {
  background: #ffe3a8;
  color: #815a10;
}

.status-chip.answered {
  background: #e0f3e7;
  color: #168148;
}

.status-chip.rejected {
  background: #ffe4e4;
  color: #d94747;
}

.status-stack {
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  gap: 7px;
}

.status-stack small {
  max-width: 260px;
  color: #d94747;
  font-size: 13px;
  line-height: 1.45;
}

.batch-group-list {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.batch-group {
  overflow: hidden;
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.batch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px;
  background: linear-gradient(135deg, #f0f9f2 0%, #e8f6ec 100%);
  border-bottom: 1px solid #dcebdd;
}

.batch-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.batch-crop-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  border-radius: 16px;
  background: #fff;
  font-size: 30px;
  box-shadow: 0 2px 6px rgba(23, 136, 68, .12);
}

.batch-title {
  min-width: 0;
}

.batch-title h2 {
  margin: 0;
  color: #102016;
  font-size: 24px;
  font-weight: 900;
  line-height: 1.3;
}

.batch-variety {
  color: #6b7c70;
  font-size: 18px;
  font-weight: 600;
}

.batch-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  color: #718178;
  font-size: 15px;
}

.batch-farmer-name {
  color: #178844;
  font-weight: 800;
}

.batch-sep {
  color: #c4d2c8;
}

.batch-no-tag {
  font-family: "SF Mono", "Consolas", monospace;
  font-size: 14px;
  color: #5f7066;
}

.batch-land {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.batch-harvested-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  margin-left: 4px;
  border-radius: 8px;
  background: #e6eae6;
  color: #7c8b82;
  font-size: 12px;
  font-weight: 800;
}

.batch-header-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

.batch-stage-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 16px;
  border-radius: 8px;
  background: #178844;
  color: #fff;
  font-size: 16px;
  font-weight: 800;
  white-space: nowrap;
}

.batch-works {
  padding: 20px 28px 24px;
}

.work-timeline-item {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  position: relative;
}

.work-timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 36px;
  bottom: -16px;
  width: 2px;
  background: #e1ece3;
}

.work-timeline-dot {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 6px;
  border-radius: 50%;
  background: #178844;
  border: 3px solid #ddf2e3;
  z-index: 1;
}

.work-timeline-dot.打药 {
  background: #e67e22;
  border-color: #fcecd8;
}

.work-timeline-dot.施肥 {
  background: #8e44ad;
  border-color: #f0e0f5;
}

.work-timeline-dot.采收 {
  background: #e74c3c;
  border-color: #fce0dc;
}

.work-timeline-dot.灌溉 {
  background: #3498db;
  border-color: #d6eaf8;
}

.work-timeline-dot.整地 {
  background: #7f8c8d;
  border-color: #ececec;
}

.work-timeline-content {
  flex: 1;
  min-width: 0;
}

.work-timeline-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.work-type-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 8px;
  background: #178844;
  color: #fff;
  font-size: 15px;
  font-weight: 800;
}

.work-timeline-top time {
  color: #93a399;
  font-size: 15px;
}

.photo-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 8px;
  background: #f1f5f2;
  color: #63736a;
  font-size: 14px;
  font-weight: 800;
}

.work-description {
  margin: 10px 0 0;
  color: #142117;
  font-size: 18px;
  line-height: 1.5;
}

.work-photos {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.work-photo {
  width: 100px;
  height: 100px;
  border-radius: 10px;
  object-fit: cover;
  cursor: zoom-in;
}

.advice-box {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  padding: 16px 18px;
  border-radius: 16px;
  background: #edf7f0;
  color: #263c2d;
  font-size: 17px;
  line-height: 1.55;
}

.advice-box strong {
  flex-shrink: 0;
  color: #178844;
}

.advice-editor {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.advice-editor .el-input {
  min-width: 0;
}

.advice-editor :deep(.el-input__wrapper) {
  min-height: 54px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
}

.green-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  padding: 0 20px;
  border: 0;
  border-radius: 12px;
  background: #178844;
  color: #fff;
  font-family: inherit;
  font-size: 18px;
  font-weight: 800;
  cursor: pointer;
}

.green-action:hover {
  background: #116d36;
}

.green-action:disabled {
  opacity: .62;
  cursor: wait;
}

.green-action.compact {
  min-width: 102px;
  min-height: 54px;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.question-card {
  display: flex;
  min-height: 365px;
  flex-direction: column;
  padding: 28px 30px;
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.question-card-top,
.farmer-identity {
  display: flex;
  align-items: center;
}

.question-card-top {
  justify-content: space-between;
  gap: 16px;
}

.farmer-identity {
  min-width: 0;
  gap: 14px;
}

.farmer-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #eef5e8;
  color: #49624e;
  font-size: 22px;
  font-weight: 900;
}

.farmer-identity div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.farmer-identity strong {
  color: #132017;
  font-size: 20px;
}

.farmer-identity div span {
  color: #718178;
  font-size: 16px;
}

.question-card h2 {
  margin: 24px 0 12px;
  color: #102016;
  font-size: 23px;
  line-height: 1.4;
}

.question-description {
  margin: 0;
  color: #718178;
  font-size: 17px;
  line-height: 1.6;
}

.question-image {
  display: flex;
  flex: 1;
  min-height: 136px;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
  border-radius: 16px;
  background: #eef5ef;
  color: #6f7f75;
  font-size: 18px;
}

.question-action {
  width: 100%;
  min-height: 50px;
  margin-top: 18px;
  border: 0;
  border-radius: 12px;
  font-family: inherit;
  font-size: 19px;
  font-weight: 800;
  cursor: pointer;
}

.question-action.primary {
  background: #178844;
  color: #fff;
}

.question-action.primary:hover {
  background: #116d36;
}

.question-action.secondary {
  border: 1px solid #d6e5da;
  background: #f8fcf8;
  color: #203126;
}

/* ========== 会话 IM ========== */
.consult-workspace {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  height: min(calc(100dvh - 280px), 760px);
  min-height: 540px;
  overflow: hidden;
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.consult-sessions {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid #e1ece3;
  background: #f7fbf7;
}

.sessions-header {
  padding: 22px 20px 16px;
  border-bottom: 1px solid #e1ece3;
}

.sessions-header h2 {
  margin: 0 0 14px;
  color: #102016;
  font-size: 21px;
  font-weight: 900;
  text-align: center;
}

.session-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 4px;
  border-radius: 14px;
  background: #e9f1e5;
}

.session-tab {
  border: 0;
  border-radius: 10px;
  padding: 6px 28px;
  background: transparent;
  color: #5a6b5f;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all .15s;
}

.session-tab:hover {
  color: #178844;
}

.session-tab.active {
  background: #fff;
  color: #152117;
  box-shadow: 0 2px 6px rgba(18, 46, 31, .12);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
}

/* 农户分组 */
.farmer-group {
  margin-bottom: 4px;
}

.farmer-group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 0;
  border-radius: 12px;
  background: #f0f7f2;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background .2s;
}

.farmer-group-header:hover {
  background: #e4f0e8;
}

.farmer-group-header.expanded {
  border-radius: 12px 12px 0 0;
  background: #e4f0e8;
}

.farmer-avatar-img {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
}

.farmer-avatar-text {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #eef5e8;
  color: #49624e;
  font-size: 15px;
  font-weight: 900;
}

.farmer-group-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.farmer-group-info strong {
  font-size: 15px;
  font-weight: 700;
  color: #152117;
}

.farmer-group-info small {
  font-size: 12px;
  color: #7d8f83;
}

.farmer-chevron {
  flex-shrink: 0;
  color: #93a399;
  transition: transform .2s;
}

.farmer-chevron.rotated {
  transform: rotate(180deg);
}

.farmer-sessions {
  background: #f8fcf9;
  border-radius: 0 0 12px 12px;
  padding: 4px 6px 8px;
}

.farmer-sessions .session-item {
  padding: 10px 10px;
  margin: 2px 0;
}

.session-title {
  overflow: hidden;
  color: #152117;
  font-size: 15px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 12px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background .2s;
}

.session-item:hover {
  background: #edf7ef;
}

.session-item.active {
  background: #ddf2e3;
}

.session-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #eef5e8;
  color: #49624e;
  font-size: 17px;
  font-weight: 900;
}

.session-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}

.session-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.session-top strong {
  overflow: hidden;
  color: #152117;
  font-size: 17px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-top small {
  flex-shrink: 0;
  color: #93a399;
  font-size: 13px;
}

.session-preview {
  overflow: hidden;
  color: #6b7c70;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-status {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 9px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 800;
}

.session-status.ongoing {
  background: #ffe3a8;
  color: #815a10;
}

.session-status.ended {
  background: #e6eae6;
  color: #7c8b82;
}

.session-rated {
  color: #ca8a04;
  font-size: 12px;
  font-weight: 800;
}

/* 软提示：农户已 N 分钟未回复（不弹窗、不打断，只是会话栏一行灰色小字） */
.session-idle-hint {
  display: inline-block;
  margin-top: 4px;
  font-size: 12px;
  color: #b45309;
  background: rgba(245, 158, 11, .12);
  padding: 2px 8px;
  border-radius: 6px;
}

.session-empty {
  padding: 50px 16px;
  color: #9ca3a0;
  font-size: 15px;
  text-align: center;
}

.consult-chat {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 26px;
  border-bottom: 1px solid #eef0ee;
  background: #fbfdfb;
}

.chat-farmer {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.chat-farmer .farmer-avatar {
  width: 44px;
  height: 44px;
  font-size: 18px;
}

.chat-farmer h2 {
  margin: 0;
  color: #102016;
  font-size: 19px;
  font-weight: 900;
}

.chat-farmer p {
  margin: 3px 0 0;
  color: #6b7c70;
  font-size: 14px;
}

.chat-actions {
  flex-shrink: 0;
}

.end-btn {
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid #f0c4c4;
  border-radius: 12px;
  background: #fff5f5;
  color: #d94747;
  font-family: inherit;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: background .2s, color .2s;
}

.end-btn:hover {
  background: #d94747;
  color: #fff;
}

.ended-tag {
  color: #909399;
  font-size: 14px;
  font-weight: 700;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 26px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #f6faf6;
}

.messages-empty {
  margin: auto;
  color: #9ca3a0;
  font-size: 15px;
}

.msg-bubble {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.msg-bubble.mine {
  align-self: flex-end;
  align-items: flex-end;
}

.msg-bubble.theirs {
  align-self: flex-start;
  align-items: flex-start;
}

.msg-content {
  padding: 11px 14px;
  border-radius: 14px;
  font-size: 16px;
  line-height: 1.5;
  word-break: break-word;
}

.msg-bubble.mine .msg-content {
  background: #178844;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-bubble.theirs .msg-content {
  background: #fff;
  color: #152117;
  border: 1px solid #eef0ee;
  border-bottom-left-radius: 4px;
}

.msg-text {
  margin: 0;
  white-space: pre-wrap;
}

.msg-images {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.msg-bubble.mine .msg-images {
  margin-top: 0;
}

.msg-image {
  width: 130px;
  height: 130px;
  border-radius: 10px;
  object-fit: cover;
  cursor: zoom-in;
}

.msg-time {
  margin-top: 4px;
  padding: 0 4px;
  color: #9ca3a0;
  font-size: 11px;
}

.chat-input-box {
  position: relative;
  z-index: 1;
  display: block;
  width: auto;
  min-height: 120px;
  margin: 14px 26px 18px;
  padding: 8px 14px 14px;
  box-sizing: border-box;
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

.textarea-wrap {
  position: relative;
  flex: 1;
}

.textarea-wrap :deep(.el-textarea__inner) {
  min-height: 64px !important;
  padding: 10px 52px 30px 14px;
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

.chat-readonly {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 90px;
  color: #909399;
  font-size: 15px;
}

.chat-placeholder {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #b6c2b9;
}

.chat-placeholder p {
  margin: 0;
  font-size: 16px;
}

.article-panel {
  overflow: hidden;
}

.article-table-wrap {
  overflow-x: auto;
}

.article-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  font-size: 18px;
}

.article-table th,
.article-table td {
  padding: 22px 28px;
  border-bottom: 1px solid #e1ebe3;
  text-align: left;
  vertical-align: middle;
}

.article-table th {
  color: #718178;
  font-weight: 700;
}

.article-table tr:last-child td {
  border-bottom: 0;
}

.article-title-cell {
  color: #152117;
  font-weight: 800;
}

.article-date-cell {
  color: #718178;
}

.cover-preview {
  position: relative;
  width: 160px;
  height: 96px;
  overflow: hidden;
  border: 1px solid #d8e7dc;
  border-radius: 12px;
  background: #edf4e8;
}

.cover-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  cursor: pointer;
}

.cover-remove:hover {
  background: rgba(0, 0, 0, .8);
}

.cover-hint {
  color: #718178;
  font-size: 14px;
}

.category-chip {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 14px;
  border-radius: 8px;
  background: #eaf4e7;
  color: #49634d;
  font-size: 15px;
  font-weight: 800;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.table-action {
  border: 0;
  background: transparent;
  color: #152117;
  font-family: inherit;
  font-size: 17px;
  font-weight: 800;
  cursor: pointer;
}

.table-action:hover {
  color: #178844;
}

.table-action.danger {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 12px;
  background: #ffe6e6;
  color: #e34c4c;
}

.table-action.danger:hover {
  background: #ffd4d4;
  color: #c63333;
}

.empty-state {
  padding: 56px 24px;
  color: #7b8b82;
  font-size: 18px;
  text-align: center;
}

.profile-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, .85fr);
  gap: 24px;
  align-items: start;
}

.profile-workbench--single {
  grid-template-columns: minmax(0, 1fr);
  max-width: 680px;
  margin: 0 auto;
}

.profile-save-row {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.profile-card,
.password-card {
  padding: 30px;
}

.profile-avatar-row {
  display: flex;
  align-items: center;
  gap: 22px;
  margin-bottom: 28px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e1ece4;
}

.profile-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 92px;
  height: 92px;
  overflow: hidden;
  border: 1px solid #d8e7dc;
  border-radius: 50%;
  background: #edf4e8;
  color: #52665a;
  font-size: 34px;
  font-weight: 900;
}

.profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-avatar-row h2,
.password-card h2 {
  margin: 0;
  color: #102016;
  font-size: 25px;
  font-weight: 900;
}

.profile-avatar-row p {
  margin: 8px 0 14px;
  color: #708178;
  font-size: 17px;
}

.outline-action {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid #bad9c2;
  border-radius: 12px;
  background: #f7fcf8;
  color: #178844;
  font-family: inherit;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
}

.outline-action:hover {
  background: #edf8f0;
}

.profile-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.profile-form :deep(.el-form-item__label) {
  margin-bottom: 9px;
  color: #263c2d;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.3;
}

.profile-form :deep(.el-input__wrapper),
.profile-form :deep(.el-textarea__inner) {
  min-height: 54px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 18px;
}

.profile-form :deep(.el-input__wrapper:hover),
.profile-form :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #9bc8a8 inset;
}

.profile-form :deep(.el-input__wrapper.is-focus),
.profile-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(23, 136, 68, .22) inset;
}

/* 不可编辑字段：灰色背景+灰色文字，一眼区分 */
.profile-form :deep(.el-input__wrapper:has(input[readonly])),
.profile-form :deep(.el-input.is-disabled .el-input__wrapper) {
  background: #f5f5f5 !important;
  box-shadow: 0 0 0 1px #e0e0e0 inset !important;
  cursor: not-allowed;
}

.profile-form :deep(.el-input__inner[readonly]),
.profile-form :deep(.el-input.is-disabled .el-input__inner) {
  color: #999 !important;
  cursor: not-allowed;
}

/* 可编辑字段：白色背景+深色文字 */
.profile-form :deep(.el-input__wrapper:not(:has(input[readonly])):not(.is-disabled)) {
  background: #fff;
}

.profile-form :deep(.el-input__inner:not([readonly]):not(.is-disabled)) {
  color: #333;
}

.profile-form :deep(.el-input__inner) {
  font-size: 18px;
}

.profile-form :deep(.el-textarea__inner) {
  padding: 15px 17px;
  line-height: 1.6;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.question-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-question-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dialog-question-meta strong {
  color: #142117;
  font-size: 20px;
  line-height: 1.45;
}

.dialog-question-meta span,
.dialog-description {
  color: #718178;
  font-size: 16px;
  line-height: 1.6;
}

.dialog-description {
  margin: 0;
}

.answered-copy {
  min-height: 120px;
  padding: 18px;
  border-radius: 16px;
  background: #f1f8f2;
  color: #37513e;
  font-size: 17px;
  line-height: 1.7;
}

.question-dialog {
  gap: 20px;
}

.dialog-question-meta {
  padding: 18px 20px;
  border: 1px solid #dcebdd;
  border-radius: 16px;
  background: #f4fbf5;
}

.dialog-question-meta strong {
  font-size: 22px;
}

.dialog-question-meta span,
.dialog-description {
  font-size: 18px;
}

.question-dialog :deep(.el-textarea__inner),
.article-form :deep(.el-textarea__inner) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  color: #142117;
  font-size: 18px;
  line-height: 1.65;
}

/* 文章正文编辑器工具栏 */
.article-editor-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.article-editor-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border: 1px solid #d8e7dc;
  border-radius: 12px;
  background: #f6fbf7;
}

.editor-tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 16px;
  border: 0;
  border-radius: 10px;
  background: #178844;
  color: #fff;
  font-family: inherit;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: background .2s;
}

.editor-tool-btn:hover:not(:disabled) {
  background: #116d36;
}

.editor-tool-btn:disabled {
  opacity: .6;
  cursor: wait;
}

.editor-tool-hint {
  color: #8a9a90;
  font-size: 14px;
}

/* 编辑/预览切换标签 */
.editor-tabs {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.editor-tab {
  height: 30px;
  padding: 0 14px;
  border: 1px solid #d8e7dc;
  border-radius: 8px;
  background: #fff;
  color: #5a6b5f;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all .15s;
}

.editor-tab.active {
  background: #178844;
  border-color: #178844;
  color: #fff;
}

/* 正文编辑区（单栏） */
.article-editor-wrap :deep(.el-textarea__inner) {
  min-height: 420px;
  resize: vertical;
}

/* 正文预览区 */
.article-preview-body {
  min-height: 420px;
  padding: 18px 22px;
  border: 1px solid #d8e7dc;
  border-radius: 12px;
  background: #fff;
  overflow-y: auto;
  font-size: 16px;
  line-height: 1.8;
  color: #1a2a1f;
}

.article-preview-body :deep(p) {
  margin: 0 0 1em;
}

.article-preview-body :deep(.article-img) {
  margin: 1.2em 0;
  text-align: center;
}

.article-preview-body :deep(.article-img img) {
  max-width: 100%;
  border-radius: 10px;
  border: 1px solid #edf2ee;
}

.article-preview-body :deep(.article-img figcaption) {
  margin-top: 6px;
  color: #8a9388;
  font-size: 13px;
}

.article-preview-body :deep(.article-img figcaption:empty) {
  display: none;
}

.article-preview-body :deep(.preview-empty) {
  color: #a8b5ac;
  font-size: 14px;
  text-align: center;
  padding: 60px 20px;
}

.question-dialog :deep(.el-textarea__inner) {
  min-height: 210px;
  padding: 16px 18px;
}

.question-dialog :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #9bc8a8 inset;
}

.question-dialog :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(23, 136, 68, .22) inset;
}

.cover-upload-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d8e7dc;
  border-radius: 12px;
  background: #f6fbf6;
}

:global(.expert-category-popper) {
  overflow: hidden;
  border-radius: 14px !important;
}

.expert-shell :deep(.el-button--success) {
  --el-button-bg-color: #178844;
  --el-button-border-color: #178844;
  --el-button-hover-bg-color: #116d36;
  --el-button-hover-border-color: #116d36;
}

@media (max-width: 1200px) {
  .expert-sidebar {
    flex-basis: 270px;
  }

  .expert-content {
    padding-right: 26px;
    padding-left: 26px;
  }

  .stats-grid {
    gap: 16px;
  }

  .stat-card {
    padding: 24px;
  }

  .stat-value {
    font-size: 40px;
  }
}

@media (max-width: 920px) {
  .stats-grid,
  .question-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-workbench {
    grid-template-columns: 1fr;
  }

  .expert-topbar {
    padding: 0 26px;
  }

  .expert-content {
    padding: 26px 22px 44px;
  }

  .consult-workspace {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
    height: min(calc(100dvh - 260px), 720px);
  }

  .consult-sessions {
    max-height: 240px;
    border-right: 0;
    border-bottom: 1px solid #e1ece3;
  }
}

@media (max-width: 680px) {
  .expert-shell {
    display: block;
  }

  .expert-sidebar {
    min-height: auto;
  }

  .brand {
    height: 76px;
    padding: 0 18px;
  }

  .side-nav {
    flex-direction: row;
    overflow-x: auto;
    padding: 12px 14px;
  }

  .side-nav-item {
    flex: 0 0 auto;
    min-height: 48px;
    padding: 0 15px;
    font-size: 16px;
  }

  .sidebar-logout {
    min-height: 58px;
    padding: 0 18px;
    border-top: 1px solid #dbe9df;
    border-bottom: 1px solid #dbe9df;
    font-size: 16px;
  }

  .expert-topbar {
    min-height: 72px;
    padding: 0 18px;
  }

  .topbar-title {
    font-size: 16px;
  }

  .topbar-user-copy strong {
    font-size: 15px;
  }

  .topbar-user-copy span {
    font-size: 12px;
  }

  .topbar-avatar {
    width: 42px;
    height: 42px;
    font-size: 18px;
  }

  .expert-content {
    padding: 22px 16px 38px;
  }

  .page-heading {
    margin-bottom: 20px;
  }

  .page-heading-row {
    align-items: stretch;
    flex-direction: column;
  }

  .page-heading h1 {
    font-size: 27px;
  }

  .page-heading p {
    font-size: 16px;
  }

  .stats-grid,
  .question-grid {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .profile-card,
  .password-card {
    padding: 22px 18px;
  }

  .profile-avatar-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .stat-card {
    min-height: 170px;
  }

  .overview-panel,
  .question-card {
    padding: 22px 18px;
    border-radius: 16px;
  }

  .batch-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 18px 20px;
  }

  .batch-crop-icon {
    width: 44px;
    height: 44px;
    font-size: 26px;
  }

  .batch-title h2 {
    font-size: 20px;
  }

  .batch-meta {
    font-size: 13px;
  }

  .batch-header-right {
    width: 100%;
    justify-content: space-between;
  }

  .batch-works {
    padding: 14px 20px 18px;
  }

  .panel-heading h2 {
    font-size: 21px;
  }

  .overview-question strong {
    font-size: 17px;
  }

  .overview-question span:not(.status-chip) {
    font-size: 14px;
  }

  .work-description {
    font-size: 16px;
  }

  .advice-box,
  .advice-editor {
    align-items: stretch;
    flex-direction: column;
    font-size: 16px;
  }

  .green-action.compact {
    width: 100%;
  }

  .question-card h2 {
    font-size: 20px;
  }

  .question-action {
    font-size: 17px;
  }

  .article-table {
    min-width: 680px;
    font-size: 16px;
  }

  .article-table th,
  .article-table td {
    padding: 16px 18px;
  }
}
</style>

<!-- 非 scoped：文章编辑覆盖层 + Element Plus 表单样式穿透 -->
<style>
/* ===== 全屏写文章覆盖层 ===== */
.article-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  background: #f3faf5;
}

.article-overlay-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  height: 72px;
  padding: 0 32px;
  background: #fff;
  border-bottom: 1px solid #dbe9df;
  box-shadow: 0 2px 8px rgba(43, 80, 53, .08);
}

.article-overlay-bar strong {
  color: #102016;
  font-size: 22px;
  font-weight: 900;
}

.article-overlay-back {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  color: #52635a;
  font-family: inherit;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
  transition: color .2s;
}

.article-overlay-back:hover {
  color: #178844;
}

.article-overlay-actions {
  display: flex;
  gap: 12px;
}

.article-overlay-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112px;
  height: 46px;
  padding: 0 22px;
  border: 1px solid #d9e6dc;
  border-radius: 12px;
  background: #f8fcf8;
  color: #203126;
  font-family: inherit;
  font-size: 17px;
  font-weight: 800;
  cursor: pointer;
  transition: all .2s;
}

.article-overlay-btn.cancel:hover {
  border-color: #c0c0c0;
  background: #f0f0f0;
}

.article-overlay-btn.submit {
  border-color: #178844;
  background: #178844;
  color: #fff;
}

.article-overlay-btn.submit:hover:not(:disabled) {
  background: #116d36;
}

.article-overlay-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.article-overlay-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 36px 0;
}

.article-overlay-body .article-form {
  max-width: 860px;
  margin: 0 auto;
  padding: 0 32px;
}

/* ===== 文章表单样式 ===== */
.article-form .el-form-item {
  margin-bottom: 24px;
}

.article-form .el-form-item__label {
  margin-bottom: 9px;
  color: #263c2d;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.3;
}

.article-form .el-input__wrapper,
.article-form .el-select__wrapper {
  min-height: 54px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 18px;
}

.article-form .el-input__wrapper:hover,
.article-form .el-select__wrapper:hover,
.article-form .el-textarea__inner:hover {
  box-shadow: 0 0 0 1px #9bc8a8 inset;
}

.article-form .el-input__wrapper.is-focus,
.article-form .el-select__wrapper.is-focused,
.article-form .el-textarea__inner:focus {
  box-shadow: 0 0 0 2px rgba(23, 136, 68, .22) inset;
}

.article-form .el-input__inner,
.article-form .el-select__placeholder,
.article-form .el-select__selected-item {
  font-size: 18px;
}

.article-form .el-textarea__inner {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 17px;
  line-height: 1.7;
  padding: 15px 17px;
}
</style>
