<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-mark"><SproutIcon :size="24" variant="white" /></span>
        <div class="brand-copy">
          <strong>慧农宝</strong>
          <span>系统管理后台</span>
        </div>
      </div>

      <nav class="side-nav" aria-label="系统管理导航">
        <div v-for="section in sections" :key="section.key" class="side-nav-group">
          <button
            type="button"
            :class="['side-nav-item', { active: active === section.key }]"
            @click="activateSection(section.key)"
          >
            <el-icon :size="22"><component :is="section.icon" /></el-icon>
            <span>{{ section.label }}</span>
          </button>

          <div v-if="section.key === 'articles' && active === 'articles'" class="sub-nav">
            <button
              v-for="item in articleSections"
              :key="item.key"
              type="button"
              :class="['sub-nav-item', { active: articleView === item.key }]"
              @click="articleView = item.key"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
      </nav>

      <button class="sidebar-logout" type="button" @click="handleLogout">
        <el-icon :size="22"><SwitchButton /></el-icon>
        <span>退出登录</span>
      </button>
    </aside>

    <section class="admin-workspace">
      <header class="admin-topbar">
        <span class="topbar-spacer"></span>
        <div class="topbar-user">
          <span class="topbar-user-copy">
            <strong>{{ auth.user?.name || '管理员' }}</strong>
          </span>
          <span class="topbar-avatar">{{ (auth.user?.name || '管').charAt(0) }}</span>
        </div>
      </header>

      <main class="admin-content">
        <template v-if="active === 'overview'">
          <div class="stats-grid">
            <article v-for="card in statCards" :key="card.label" class="stat-card">
              <span :class="['stat-icon', card.tone]">
                <el-icon :size="31"><component :is="card.icon" /></el-icon>
              </span>
              <div class="stat-copy">
                <strong>{{ formatNumber(card.value) }}</strong>
                <span>{{ card.label }}</span>
              </div>
            </article>
          </div>

          <section class="panel growth-panel">
            <h2>近 6 个月农户新增</h2>
            <div v-if="monthlyData.length" class="growth-chart">
              <div v-for="item in monthlyData" :key="item.month" class="growth-column">
                <span class="growth-value">{{ item.users }}</span>
                <div class="growth-bar" :style="{ height: `${growthHeight(item.users)}px` }"></div>
                <span class="growth-label">{{ item.month }}</span>
              </div>
            </div>
            <div v-else class="empty-state">暂无农户新增数据</div>
          </section>
        </template>

        <template v-else-if="active === 'users'">
          <section class="panel table-panel">
            <div v-if="users.length" class="table-scroll">
              <table class="admin-table user-table">
                <thead>
                  <tr>
                    <th>用户 ID</th>
                    <th>姓名</th>
                    <th>手机号</th>
                    <th>地区</th>
                    <th>角色</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="user in users" :key="user.id">
                    <td class="id-cell">{{ userCode(user.id) }}</td>
                    <td class="strong-cell">{{ user.name }}</td>
                    <td class="muted-cell">{{ maskPhone(user.phone) }}</td>
                    <td class="muted-cell">{{ user.region || '—' }}</td>
                    <td><span class="role-chip farmer">农户</span></td>
                    <td>
                      <span :class="['status-chip', user.status === 1 ? 'normal' : 'disabled']">
                        {{ user.status === 1 ? '正常' : '已禁用' }}
                      </span>
                    </td>
                    <td>
                      <button
                        :class="['table-action', user.status === 1 ? 'danger' : 'enable']"
                        type="button"
                        @click="toggleUserStatus(user)"
                      >
                        <el-icon :size="17"><component :is="user.status === 1 ? CircleClose : CircleCheck" /></el-icon>
                        {{ user.status === 1 ? '禁用' : '启用' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state">暂无农户用户</div>
          </section>
        </template>

        <template v-else-if="active === 'experts'">
          <div class="page-heading page-heading-row" style="justify-content: flex-end;">
            <button class="green-action" type="button" @click="openExpert()">
              <el-icon :size="20"><Plus /></el-icon>
              创建专家账号
            </button>
          </div>

          <div v-if="experts.length" class="expert-grid">
            <article v-for="expert in experts" :key="expert.id" class="expert-card">
              <div class="expert-identity">
                <span class="expert-avatar">
                  <img v-if="expert.avatar" :src="expert.avatar" :alt="expert.name" />
                  <span v-else>{{ (expert.name || '专').charAt(0) }}</span>
                </span>
                <div>
                  <strong>{{ expert.name }}</strong>
                  <span>{{ expert.title || '农业专家' }}</span>
                </div>
              </div>
              <p><b>擅长：</b>{{ expert.specialty || '农业种植与病虫害防治' }}</p>
              <p><b>账号：</b>{{ maskPhone(expert.phone) }}</p>
              <div class="expert-actions">
                <button type="button" class="table-action edit" @click="openExpert(expert)">编辑</button>
                <button type="button" class="table-action danger-block" @click="openDeleteExpert(expert)">删除</button>
              </div>
            </article>
          </div>
          <div v-else class="panel empty-state">暂无专家账号</div>
        </template>

        <template v-else>
          <div class="page-heading page-heading-row" style="justify-content: flex-end;">
            <button v-if="articleView === 'mine'" class="green-action" type="button" @click="openArticle()">
              <el-icon :size="20"><Plus /></el-icon>
              发布文章
            </button>
          </div>

          <section v-if="articleView === 'review'" class="panel article-section">
              <div v-if="reviewArticles.length" class="article-table-wrap">
                <table class="article-table">
                  <thead>
                    <tr>
                      <th>标题</th>
                      <th>分类</th>
                      <th>投稿人</th>
                      <th>日期</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="article in reviewArticles" :key="article.id">
                      <td class="article-title-cell">{{ article.title }}</td>
                      <td><span class="category-chip">{{ article.category }}</span></td>
                      <td>{{ article.author_name || '专家' }}</td>
                      <td class="article-date-cell">{{ article.date }}</td>
                      <td>
                        <span :class="['status-chip', articleStatusClass(article.review_status)]">
                          {{ articleStatusText(article.review_status) }}
                        </span>
                      </td>
                      <td>
                        <div class="table-actions">
                          <button type="button" class="table-action" @click="openArticleDetail(article)">查看详情</button>
                          <template v-if="canReviewArticle(article)">
                            <button type="button" class="table-action approve" @click="reviewArticle(article, 'approve')">通过</button>
                            <button type="button" class="table-action danger" @click="reviewArticle(article, 'reject')">拒绝</button>
                          </template>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="empty-state compact">暂无专家投稿</div>
          </section>

          <section v-if="articleView === 'mine'" class="panel article-section">
              <div v-if="myAdminArticles.length" class="article-table-wrap">
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
                    <tr v-for="article in myAdminArticles" :key="article.id">
                      <td class="article-title-cell">{{ article.title }}</td>
                      <td><span class="category-chip">{{ article.category }}</span></td>
                      <td>
                        <span :class="['status-chip', articleStatusClass(article.review_status)]">
                          {{ articleStatusText(article.review_status) }}
                        </span>
                      </td>
                      <td class="article-date-cell">{{ article.date }}</td>
                      <td>
                        <div class="table-actions">
                          <button type="button" class="table-action" @click="openArticle(article)">编辑</button>
                          <button type="button" class="table-action danger" @click="removeArticle(article)">删除</button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="empty-state compact">暂无自己发布的文章</div>
          </section>
        </template>
      </main>
    </section>

    <el-dialog
      v-model="expertDialogVisible"
      :title="editingExpertId ? '编辑专家资料' : '创建专家账号'"
      width="680px"
      class="admin-form-dialog"
    >
      <el-form label-position="top" class="dialog-form expert-account-form">
        <el-form-item label="姓名">
          <el-input v-model="expertForm.name" placeholder="请输入专家姓名" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="expertForm.phone" placeholder="请输入手机号" :disabled="!!editingExpertId" />
        </el-form-item>
        <el-form-item v-if="!editingExpertId" label="登录密码">
          <el-input v-model="expertForm.password" type="password" show-password placeholder="6-20 位密码" />
        </el-form-item>
        <el-form-item label="职称">
          <el-input v-model="expertForm.title" placeholder="例如：高级农艺师" />
        </el-form-item>
        <el-form-item label="专业领域">
          <el-input v-model="expertForm.specialty" placeholder="例如：水稻、病虫害防治" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="expertDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="expertSaving" @click="saveExpert">
          {{ editingExpertId ? '保存修改' : '创建账号' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 全屏写文章覆盖层 -->
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
            {{ articleSaving ? '发布中' : (editingArticleId ? '保存修改' : '发布文章') }}
          </button>
        </div>
      </div>
      <div class="article-overlay-body">
        <el-form label-position="top" class="article-form">
          <el-form-item label="文章标题">
            <el-input v-model="articleForm.title" placeholder="请输入文章标题" maxlength="50" show-word-limit />
          </el-form-item>
          <el-form-item label="文章分类">
            <el-select v-model="articleForm.category" style="width: 100%" placeholder="请选择文章分类">
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
              />
              <div v-show="editorMode === 'preview'" class="article-editor-preview-body" v-html="articlePreviewHtml"></div>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 文章详情弹窗 -->
    <el-dialog v-model="articleDetailVisible" title="文章详情" width="720px" class="form-dialog">
      <div v-if="articleDetail" class="article-detail-content">
        <h2 class="article-detail-title">{{ articleDetail.title }}</h2>
        <div class="article-detail-meta">
          <span class="meta-item"><strong>分类：</strong>{{ articleDetail.category }}</span>
          <span class="meta-item"><strong>作者：</strong>{{ articleDetail.author_name || '专家' }}</span>
          <span class="meta-item"><strong>提交时间：</strong>{{ articleDetail.date }}</span>
          <span class="meta-item">
            <strong>状态：</strong>
            <span :class="['status-chip', articleStatusClass(articleDetail.review_status)]">
              {{ articleStatusText(articleDetail.review_status) }}
            </span>
          </span>
        </div>
        <div v-if="articleDetail.review_status === 'rejected' && articleDetail.review_reason" class="article-detail-reject">
          <strong>拒绝原因：</strong>{{ articleDetail.review_reason }}
        </div>
        <div class="article-detail-body" v-html="articleDetailHtml"></div>
      </div>
    </el-dialog>

    <!-- 审核通过确认弹窗 -->
    <el-dialog v-model="approveDialogVisible" title="审核通过" width="460px" class="form-dialog confirm-dialog" :close-on-click-modal="false">
      <div class="confirm-dialog__body">确认通过《{{ approvingArticle?.title }}》并发布吗？</div>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="approveSaving" @click="confirmApprove">通过并发布</el-button>
      </template>
    </el-dialog>

    <!-- 拒绝文章弹窗 -->
    <el-dialog v-model="rejectDialogVisible" title="拒绝文章" width="520px" class="form-dialog confirm-dialog danger" :close-on-click-modal="false">
      <div class="reject-dialog-body">
        <p class="reject-dialog-tip">请输入拒绝原因，专家会看到该审核意见</p>
        <el-input
          v-model="rejectReason"
          type="textarea"
          :rows="4"
          placeholder="例如：内容表述不完整，请补充防治措施"
          maxlength="200"
          show-word-limit
        />
      </div>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejectSaving" @click="confirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>

    <!-- 删除文章确认弹窗 -->
    <el-dialog v-model="deleteDialogVisible" title="删除文章" width="460px" class="form-dialog confirm-dialog danger" :close-on-click-modal="false">
      <div class="confirm-dialog__body">确定删除《{{ deletingArticle?.title }}》吗？</div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleteSaving" @click="confirmDelete">确定删除</el-button>
      </template>
    </el-dialog>

    <!-- 删除专家确认弹窗 -->
    <el-dialog v-model="deleteExpertDialogVisible" title="删除专家" width="460px" class="form-dialog confirm-dialog danger" :close-on-click-modal="false">
      <div class="confirm-dialog__body">确定要删除专家<strong>{{ deletingExpert?.name }}</strong>的账号吗？</div>
      <template #footer>
        <el-button @click="deleteExpertDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleteExpertSaving" @click="confirmDeleteExpert">确定删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  SwitchButton,
  ChatDotRound,
  CircleCheck,
  CircleClose,
  CloseBold,
  DataAnalysis,
  Document,
  Location,
  Plus,
  Picture,
  User,
  UserFilled,
  Notebook,
  Back,
} from '@element-plus/icons-vue'
import SproutIcon from '@/components/SproutIcon.vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

type SectionKey = 'overview' | 'users' | 'experts' | 'articles'
type ArticleViewKey = 'review' | 'mine'

const router = useRouter()
const auth = useAuthStore()
const active = ref<SectionKey>('overview')
const articleView = ref<ArticleViewKey>('review')

const sections = [
  { key: 'overview' as SectionKey, label: '数据看板', icon: DataAnalysis },
  { key: 'users' as SectionKey, label: '农户管理', icon: User },
  { key: 'experts' as SectionKey, label: '专家管理', icon: UserFilled },
  { key: 'articles' as SectionKey, label: '三农资讯', icon: Document },
]

const articleSections = [
  { key: 'review' as ArticleViewKey, label: '专家文章审核' },
  { key: 'mine' as ArticleViewKey, label: '我的文章管理' },
]

const currentSection = computed(() => sections.find(section => section.key === active.value) || sections[0])
const currentArticleSection = computed(() => articleSections.find(section => section.key === articleView.value) || articleSections[0])
const currentTitle = computed(() => active.value === 'articles' ? currentArticleSection.value.label : currentSection.value.label)
const stats = ref<Record<string, number>>({})
const monthlyData = ref<any[]>([])
const users = ref<any[]>([])
const experts = ref<any[]>([])
const articles = ref<any[]>([])

const expertDialogVisible = ref(false)
const expertSaving = ref(false)
const editingExpertId = ref<number | null>(null)
const expertForm = reactive({
  name: '',
  phone: '',
  password: '',
  title: '',
  specialty: '',
})

const articleEditorVisible = ref(false)
const editorMode = ref<'edit' | 'preview'>('edit')
const articleSaving = ref(false)
const articleCoverUploading = ref(false)
const articleImageUploading = ref(false)
const articleImageInputRef = ref<HTMLInputElement | null>(null)
const articleContentRef = ref<any>(null)
const editingArticleId = ref<number | null>(null)
const articleDetailVisible = ref(false)
const articleDetail = ref<any>(null)
const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejectingArticle = ref<any>(null)
const rejectSaving = ref(false)
const approveDialogVisible = ref(false)
const approvingArticle = ref<any>(null)
const approveSaving = ref(false)
const deleteDialogVisible = ref(false)
const deletingArticle = ref<any>(null)
const deleteSaving = ref(false)

// 删除专家弹窗
const deleteExpertDialogVisible = ref(false)
const deletingExpert = ref<any>(null)
const deleteExpertSaving = ref(false)
const articleCategories = ['农业要闻', '政策解读', '种植技术', '病虫害防治', '市场行情']
const articleForm = reactive({
  title: '',
  category: '',
  summary: '',
  content: '',
  cover: '',
  source: '',
  original_author: '',
})

// 文章正文预览
const articlePreviewHtml = computed(() => renderArticlePreview(articleForm.content))

function renderArticlePreview(content: string): string {
  if (!content) return '<div class="preview-empty">暂无内容，开始写文章后会在这里实时预览效果</div>'
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

// 文章详情正文渲染
const articleDetailHtml = computed(() => {
  if (!articleDetail.value?.content) return '<div class="preview-empty">暂无正文</div>'
  return renderArticlePreview(articleDetail.value.content)
})

// 打开文章详情
async function openArticleDetail(article: any) {
  try {
    const res = await api.getArticle(article.id)
    articleDetail.value = res
    articleDetailVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取详情失败')
  }
}

const statCards = computed(() => [
  { value: stats.value.users || 0, label: '注册农户', hint: '', icon: User, tone: 'green' },
  { value: stats.value.experts || 0, label: '农业专家', hint: '', icon: UserFilled, tone: 'cyan' },
  { value: stats.value.articles || 0, label: '已发布资讯', hint: '', icon: Notebook, tone: 'coral' },
  { value: stats.value.pending_articles || 0, label: '待审核文章', hint: '', icon: Document, tone: 'amber' },
  { value: stats.value.total_consultations || 0, label: '累计咨询数', hint: '', icon: DataAnalysis, tone: 'teal' },
  { value: stats.value.land_plots || 0, label: '录入地块', hint: '', icon: Location, tone: 'sage' },
])

const reviewArticles = computed(() => {
  const order: Record<string, number> = { pending: 0, rejected: 1, published: 2 }
  return articles.value
    .filter(article => article.author_role === 2)
    .slice()
    .sort((a, b) => (order[a.review_status] ?? 3) - (order[b.review_status] ?? 3))
})

const myAdminArticles = computed(() => {
  const userId = auth.user?.id
  return userId ? articles.value.filter(article => article.author_id === userId) : []
})

function activateSection(section: SectionKey) {
  active.value = section
  if (section === 'articles' && !articleView.value) articleView.value = 'review'
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value || 0)
}

function growthHeight(value: number) {
  const values = monthlyData.value.map(item => Number(item.users) || 0)
  const max = Math.max(...values, 1)
  return Math.max(28, Math.round((value / max) * 248))
}

function maskPhone(phone = '') {
  return phone.replace(/^(\d{3})\d{4}(\d{4})$/, '$1****$2')
}

function userCode(id: number) {
  return `U${String(id).padStart(5, '0')}`
}

async function fetchStats() {
  try { stats.value = await api.getAdminStats() } catch { stats.value = {} }
}

async function fetchMonthly() {
  try { monthlyData.value = await api.getMonthlyData() } catch { monthlyData.value = [] }
}

async function fetchUsers() {
  try {
    const data = await api.getAdminUsers()
    users.value = data.filter((user: any) => user.role === 1)
  } catch {
    users.value = []
  }
}

async function fetchExperts() {
  try { experts.value = await api.getAdminExperts() } catch { experts.value = [] }
}

async function fetchArticles() {
  try { articles.value = await api.getAdminArticles() } catch { articles.value = [] }
}

function articleStatusText(status = 'published') {
  const map: Record<string, string> = {
    pending: '待审核',
    published: '已发布',
    rejected: '已拒绝',
  }
  return map[status] || '已发布'
}

function articleStatusClass(status = 'published') {
  const map: Record<string, string> = {
    pending: 'pending',
    published: 'normal',
    rejected: 'rejected',
  }
  return map[status] || 'normal'
}

function canEditArticle(article: any) {
  return article.author_id === auth.user?.id
}

function canReviewArticle(article: any) {
  return article.author_role === 2 && article.review_status === 'pending'
}

async function toggleUserStatus(user: any) {
  try {
    const nextStatus = user.status === 1 ? 0 : 1
    await api.updateAdminUser(user.id, { status: nextStatus })
    user.status = nextStatus
    ElMessage.success(nextStatus === 1 ? '用户已启用' : '用户已禁用')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '状态更新失败')
  }
}

function openExpert(expert?: any) {
  editingExpertId.value = expert?.id || null
  expertForm.name = expert?.name || ''
  expertForm.phone = expert?.phone || ''
  expertForm.password = ''
  expertForm.title = expert?.title || ''
  expertForm.specialty = expert?.specialty || ''
  expertDialogVisible.value = true
}

async function saveExpert() {
  if (!expertForm.name.trim() || !expertForm.phone.trim()) {
    ElMessage.warning('请填写姓名和手机号')
    return
  }
  if (!editingExpertId.value && !expertForm.password.trim()) {
    ElMessage.warning('请设置登录密码')
    return
  }

  expertSaving.value = true
  try {
    if (editingExpertId.value) {
      await api.updateAdminExpert(editingExpertId.value, {
        name: expertForm.name.trim(),
        title: expertForm.title.trim() || null,
        specialty: expertForm.specialty.trim() || null,
      })
      ElMessage.success('专家资料已更新')
    } else {
      await api.createExpert({
        phone: expertForm.phone.trim(),
        name: expertForm.name.trim(),
        password: expertForm.password,
        title: expertForm.title.trim() || null,
        specialty: expertForm.specialty.trim() || null,
      })
      ElMessage.success('专家账号已创建')
    }
    expertDialogVisible.value = false
    await fetchExperts()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    expertSaving.value = false
  }
}

function openDeleteExpert(expert: any) {
  deletingExpert.value = expert
  deleteExpertDialogVisible.value = true
}

async function confirmDeleteExpert() {
  if (!deletingExpert.value) return
  deleteExpertSaving.value = true
  try {
    await api.deleteExpert(deletingExpert.value.id)
    ElMessage.success('专家账号已删除')
    deleteExpertDialogVisible.value = false
    deletingExpert.value = null
    await fetchExperts()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  } finally {
    deleteExpertSaving.value = false
  }
}

function openArticle(article?: any) {
  editingArticleId.value = article?.id || null
  articleForm.title = article?.title || ''
  articleForm.category = article?.category || ''
  articleForm.summary = article?.summary || ''
  articleForm.content = article?.content || ''
  articleForm.cover = article?.cover || ''
  articleForm.source = article?.source || ''
  articleForm.original_author = article?.original_author || ''
  editorMode.value = 'edit'
  articleEditorVisible.value = true
}

function closeArticleEditor() {
  articleEditorVisible.value = false
  editingArticleId.value = null
  editorMode.value = 'edit'
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

// 选择图片后上传并插入到正文光标位置
async function onPickArticleImage(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  articleImageUploading.value = true
  try {
    const res = await api.uploadArticleImage(file)
    const imgMarkdown = `\n\n![图片](${res.url})\n\n`

    const textarea = articleContentRef.value?.ref?.querySelector('textarea') as HTMLTextAreaElement | null
    if (textarea) {
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      articleForm.content = articleForm.content.substring(0, start) + imgMarkdown + articleForm.content.substring(end)
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
    target.value = ''
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
      summary: articleForm.summary.trim() || null,
      content: articleForm.content.trim(),
      cover: articleForm.cover || null,
      source: articleForm.source.trim() || null,
      original_author: articleForm.original_author.trim() || null,
    }
    if (editingArticleId.value) {
      await api.updateArticle(editingArticleId.value, payload)
      ElMessage.success('文章已更新')
    } else {
      await api.createArticle(payload)
      ElMessage.success('文章已发布')
    }
    articleEditorVisible.value = false
    editingArticleId.value = null
    editorMode.value = 'edit'
    await fetchArticles()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '文章保存失败')
  } finally {
    articleSaving.value = false
  }
}

async function reviewArticle(article: any, action: 'approve' | 'reject') {
  if (action === 'reject') {
    // 拒绝走自定义圆角弹窗收集原因
    rejectingArticle.value = article
    rejectReason.value = ''
    rejectDialogVisible.value = true
    return
  }
  // 通过走自定义圆角弹窗
  approvingArticle.value = article
  approveSaving.value = false
  approveDialogVisible.value = true
}

async function confirmApprove() {
  if (!approvingArticle.value) return
  approveSaving.value = true
  try {
    await api.reviewArticle(approvingArticle.value.id, 'approve', '')
    ElMessage.success('文章已发布')
    approveDialogVisible.value = false
    await Promise.all([fetchArticles(), fetchStats()])
  } catch {
    ElMessage.error('操作失败，请重试')
  } finally {
    approveSaving.value = false
  }
}

async function confirmReject() {
  if (!rejectingArticle.value) return
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }
  rejectSaving.value = true
  try {
    await api.reviewArticle(rejectingArticle.value.id, 'reject', rejectReason.value.trim())
    ElMessage.success('文章已拒绝')
    rejectDialogVisible.value = false
    await Promise.all([fetchArticles(), fetchStats()])
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    rejectSaving.value = false
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
  await Promise.all([fetchStats(), fetchMonthly(), fetchUsers(), fetchExperts(), fetchArticles()])
})
</script>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background: #f3faf5;
  color: #142117;
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
}

.admin-sidebar {
  display: flex;
  flex: 0 0 340px;
  min-height: 100vh;
  flex-direction: column;
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

.side-nav-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.side-nav-item,
.sub-nav-item {
  display: flex;
  align-items: center;
  border: 0;
  background: transparent;
  color: #52635a;
  font-family: inherit;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.sidebar-logout {
  display: flex;
  align-items: center;
  border: 0;
  background: transparent;
  color: #52635a;
  font-family: inherit;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.side-nav-item,
.sidebar-logout {
  gap: 16px;
  font-size: 20px;
}

.side-nav-item {
  min-height: 56px;
  padding: 0 20px;
  border-radius: 12px;
  transition: background .2s, color .2s;
}

.side-nav-item:hover,
.side-nav-item.active {
  background: #ddf2e3;
  color: #178844;
}

.sub-nav {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 0 0 6px 48px;
}

.sub-nav-item {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 10px;
  color: #6b7c72;
  font-size: 17px;
  transition: background .2s, color .2s;
}

.sub-nav-item:hover,
.sub-nav-item.active {
  background: #edf8ef;
  color: #178844;
}

.sub-nav-item.active {
  font-weight: 900;
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

.admin-workspace {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}

.admin-topbar {
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
  color: #718178;
  font-size: 19px;
}

.topbar-user {
  display: flex;
  align-items: center;
  gap: 14px;
}

.topbar-user-copy {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 2px;
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
  border-radius: 50%;
  background: #edf4e8;
  color: #52665a;
  font-size: 22px;
  font-weight: 900;
}

.admin-content {
  flex: 1;
  min-width: 0;
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
  margin-bottom: 30px;
}

.stat-card {
  display: flex;
  align-items: center;
  min-height: 144px;
  gap: 22px;
  padding: 24px 28px;
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
  border-radius: 14px;
}

.stat-icon.green { background: #e5f3e9; color: #208b4a; }
.stat-icon.cyan { background: #dff4f8; color: #0a9bb7; }
.stat-icon.coral { background: #fdeae3; color: #e77850; }
.stat-icon.amber { background: #fff2d9; color: #cc9515; }
.stat-icon.teal { background: #e0f1ee; color: #13927e; }
.stat-icon.sage { background: #edf4e8; color: #55745a; }

.stat-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.stat-copy strong {
  color: #0b1a0f;
  font-size: 36px;
  line-height: 1;
  font-weight: 900;
}

.stat-copy span {
  color: #718178;
  font-size: 19px;
}

.panel {
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.growth-panel {
  min-height: 420px;
  padding: 32px 30px 22px;
}

.growth-panel h2 {
  margin: 0;
  color: #102016;
  font-size: 25px;
  font-weight: 900;
}

.growth-chart {
  display: flex;
  height: 326px;
  align-items: flex-end;
  justify-content: space-around;
  gap: 28px;
  padding: 30px 0 0;
}

.growth-column {
  display: flex;
  flex: 1;
  min-width: 60px;
  height: 100%;
  align-items: center;
  flex-direction: column;
  justify-content: flex-end;
  gap: 8px;
}

.growth-value {
  color: #5d6d63;
  font-size: 17px;
}

.growth-bar {
  width: min(100%, 250px);
  min-height: 28px;
  border-radius: 18px 18px 0 0;
  background: #208b43;
}

.growth-label {
  color: #718178;
  font-size: 17px;
}

.table-panel {
  overflow: hidden;
}

.table-scroll {
  overflow-x: auto;
}

.admin-table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
  font-size: 18px;
}

.admin-table th,
.admin-table td {
  padding: 23px 28px;
  border-bottom: 1px solid #e0e9e2;
  text-align: left;
  vertical-align: middle;
}

.admin-table th {
  color: #718178;
  font-weight: 700;
}

.admin-table tbody tr:last-child td {
  border-bottom: 0;
}

.id-cell {
  color: #21342a;
  font-size: 16px;
}

.strong-cell {
  color: #162419;
  font-weight: 800;
}

.role-chip,
.status-chip,
.category-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 800;
  white-space: nowrap;
}

.role-chip.farmer,
.category-chip {
  background: #eaf4e7;
  color: #49634d;
}

.status-chip.normal {
  background: #e1f3e7;
  color: #168148;
}

.status-chip.disabled {
  background: #edf2ee;
  color: #78857d;
}

.status-chip.pending {
  background: #fff1d6;
  color: #9b6a12;
}

.status-chip.rejected {
  background: #ffe4e4;
  color: #d94747;
}

.article-cover-thumb,
.cover-preview {
  overflow: hidden;
  border-radius: 10px;
  background: #edf4e8;
}

.article-cover-thumb {
  width: 84px;
  height: 56px;
}

.article-cover-thumb img,
.cover-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-empty {
  color: #a3afa8;
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

.cover-preview {
  position: relative;
  width: 160px;
  height: 96px;
  overflow: hidden;
  border: 1px solid #d8e7dc;
  border-radius: 12px;
  background: #edf4e8;
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

.article-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, .92fr);
  gap: 24px;
  align-items: start;
}

.article-section {
  overflow: hidden;
}

.article-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 92px;
  padding: 22px 26px;
  border-bottom: 1px solid #e1ebe3;
}

.article-section-head h2 {
  margin: 0;
  color: #102016;
  font-size: 24px;
  font-weight: 900;
}

.section-count {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 8px;
  background: #fff1d6;
  color: #9b6a12;
  font-size: 15px;
  font-weight: 900;
  white-space: nowrap;
}

.article-review-list,
.my-article-list {
  display: flex;
  flex-direction: column;
}

.article-review-item,
.my-article-item {
  display: grid;
  align-items: center;
  gap: 16px;
  padding: 16px 26px;
  border-bottom: 1px solid #e1ebe3;
}

.article-review-item {
  grid-template-columns: minmax(0, 1fr) auto;
}

.my-article-item {
  grid-template-columns: 84px minmax(0, 1fr) auto;
}

.article-review-item:last-child,
.my-article-item:last-child {
  border-bottom: 0;
}

.article-review-main,
.my-article-main {
  min-width: 0;
}

.article-review-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.article-review-title strong,
.my-article-main strong {
  display: block;
  overflow: hidden;
  color: #152117;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-review-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 8px;
  color: #718178;
  font-size: 15px;
}

.article-review-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.article-review-actions .status-chip {
  margin-left: auto;
}

.cover-empty-block {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a3afa8;
}

.table-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid #d9e6dc;
  border-radius: 12px;
  background: #f8fcf8;
  color: #203126;
  font-family: inherit;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
}

.table-action:hover {
  border-color: #178844;
  color: #178844;
}

.table-action.danger {
  border-color: #ffe0e0;
  background: #ffe7e7;
  color: #e34c4c;
}

.table-action.enable {
  background: #f8fcf8;
  color: #2e4a37;
}

.table-action.edit {
  flex: 1;
}

.table-action.danger-block {
  flex: 1;
  border-color: #ffe0e0;
  background: #ffe5e5;
  color: #e34c4c;
}

/* ===== 文章表格样式 ===== */
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
  background: #f6fbf7;
  color: #52635a;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
}

.article-title-cell {
  color: #152117;
  font-weight: 800;
}

.article-date-cell {
  color: #718178;
}

.status-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.article-table .status-chip {
  display: inline-flex !important;
  min-height: 28px !important;
  padding: 0 12px !important;
  font-size: 14px !important;
  width: fit-content;
}

.reject-reason {
  color: #e34c4c;
  font-size: 13px;
}

.reject-reason-label {
  font-weight: 700;
}

.table-actions {
  display: flex;
  gap: 10px;
}

.table-actions .table-action {
  min-height: auto;
  padding: 0;
  border: none;
  background: transparent;
  font-size: 15px;
  font-weight: 700;
  color: #178844;
}

.table-actions .table-action:hover {
  text-decoration: underline;
  border-color: transparent;
}

.table-actions .table-action.danger {
  color: #e34c4c;
  background: transparent;
}

.table-action.approve {
  border-color: #cfe8d6;
  background: #e8f6ec;
  color: #168148;
}

.table-action.reject {
  border-color: #ffe0e0;
  background: #ffe7e7;
  color: #e34c4c;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.expert-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}

.expert-card {
  display: flex;
  min-height: 250px;
  flex-direction: column;
  padding: 28px 30px;
  border: 1px solid #d8e7dc;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 3px 7px rgba(43, 80, 53, .14);
}

.expert-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.expert-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62px;
  height: 62px;
  overflow: hidden;
  flex-shrink: 0;
  border-radius: 50%;
  background: #edf4e8;
  color: #17301d;
  font-size: 25px;
  font-weight: 900;
}

.expert-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.expert-identity div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.expert-identity strong {
  color: #152117;
  font-size: 23px;
}

.expert-identity span {
  color: #718178;
  font-size: 17px;
}

.expert-card p {
  margin: 0 0 10px;
  color: #718178;
  font-size: 18px;
  line-height: 1.45;
}

.expert-card p b {
  color: #4d6053;
}

.expert-actions {
  display: flex;
  gap: 12px;
  margin-top: auto;
  padding-top: 14px;
}

.article-title {
  min-width: 350px;
}

.dialog-form :deep(.el-form-item__label) {
  color: #304036;
  font-weight: 700;
}

.dialog-form :deep(.el-input__wrapper),
.dialog-form :deep(.el-textarea__inner) {
  border-radius: 10px;
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
  height: 36px;
  padding: 0 16px;
  border: 0;
  border-radius: 10px;
  background: #178844;
  color: #fff;
  font-family: inherit;
  font-size: 14px;
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
  font-size: 13px;
}

/* 左右分栏预览 */
.article-editor-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  width: 100%;
}

.article-editor-input :deep(.el-textarea__inner) {
  min-height: 360px;
  resize: vertical;
}

.article-editor-preview {
  border: 1px solid #d8e7dc;
  border-radius: 12px;
  background: #fbfdfb;
  display: flex;
  flex-direction: column;
  min-height: 360px;
  overflow: hidden;
}

.article-editor-preview-label {
  padding: 10px 16px;
  border-bottom: 1px solid #ecf3ee;
  color: #5a6b5f;
  font-size: 14px;
  font-weight: 700;
  background: #f6fbf7;
}

.article-editor-preview-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  font-size: 15px;
  line-height: 1.8;
  color: #1a2a1f;
}

.article-editor-preview-body :deep(p) {
  margin: 0 0 1em;
}

.article-editor-preview-body :deep(.article-img) {
  margin: 1.2em 0;
  text-align: center;
}

.article-editor-preview-body :deep(.article-img img) {
  max-width: 100%;
  border-radius: 10px;
  border: 1px solid #edf2ee;
}

.article-editor-preview-body :deep(.article-img figcaption) {
  margin-top: 6px;
  color: #8a9388;
  font-size: 13px;
}

.article-editor-preview-body :deep(.article-img figcaption:empty) {
  display: none;
}

.article-editor-preview-body :deep(.preview-empty) {
  color: #a8b5ac;
  font-size: 14px;
  text-align: center;
  padding: 60px 20px;
}

@media (max-width: 1100px) {
  .article-editor-split {
    grid-template-columns: 1fr;
  }
}

/* ===== 全屏文章编辑器覆盖层 ===== */
.article-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: #f3faf5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.article-overlay-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  border-bottom: 1px solid #e1ebe3;
  background: #fff;
  flex-shrink: 0;
}

.article-overlay-bar strong {
  font-size: 20px;
  font-weight: 800;
  color: #142117;
}

.article-overlay-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #d4e3d8;
  border-radius: 12px;
  background: #f8fcf8;
  padding: 8px 16px;
  color: #52635a;
  font-family: inherit;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all .2s;
}

.article-overlay-back:hover {
  border-color: #178844;
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
  min-height: 40px;
  padding: 0 24px;
  border-radius: 12px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  transition: all .2s;
}

.article-overlay-btn.cancel {
  border: 1px solid #d9e6dc;
  background: #f8fcf8;
  color: #52635a;
}

.article-overlay-btn.cancel:hover {
  border-color: #178844;
  color: #178844;
}

.article-overlay-btn.submit {
  border: 0;
  background: #178844;
  color: #fff;
}

.article-overlay-btn.submit:hover:not(:disabled) {
  background: #116d36;
}

.article-overlay-btn.submit:disabled {
  opacity: .6;
  cursor: wait;
}

.article-overlay-body {
  flex: 1;
  overflow-y: auto;
  padding: 28px 40px 40px;
}

.article-overlay-body .article-form {
  max-width: 860px;
  margin: 0 auto;
  padding: 0 32px;
}

.article-overlay-body .article-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.article-overlay-body .article-form :deep(.el-form-item__label) {
  margin-bottom: 9px;
  color: #263c2d;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.3;
}

.article-overlay-body .article-form :deep(.el-input__wrapper),
.article-overlay-body .article-form :deep(.el-select__wrapper) {
  min-height: 54px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 18px;
}

.article-overlay-body .article-form :deep(.el-input__wrapper:hover),
.article-overlay-body .article-form :deep(.el-select__wrapper:hover),
.article-overlay-body .article-form :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #9bc8a8 inset;
}

.article-overlay-body .article-form :deep(.el-input__wrapper.is-focus),
.article-overlay-body .article-form :deep(.el-select__wrapper.is-focused),
.article-overlay-body .article-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(23, 136, 68, .22) inset;
}

.article-overlay-body .article-form :deep(.el-input__inner),
.article-overlay-body .article-form :deep(.el-select__placeholder),
.article-overlay-body .article-form :deep(.el-select__selected-item) {
  font-size: 18px;
}

.article-overlay-body .article-form :deep(.el-textarea__inner) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 17px;
  line-height: 1.7;
  padding: 15px 17px;
  min-height: 360px;
  resize: vertical;
}

/* 编辑/预览切换标签 */
.editor-tabs {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.editor-tab {
  border: 1px solid #d8e7dc;
  border-radius: 8px;
  background: #fff;
  padding: 4px 14px;
  color: #5a6b5f;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all .2s;
}

.editor-tab.active {
  background: #178844;
  border-color: #178844;
  color: #fff;
}

.editor-tab:hover:not(.active) {
  border-color: #178844;
  color: #178844;
}

/* 文章详情弹窗内部样式（dialog 外壳样式见全局 style 块） */
.article-detail-content {
  padding: 24px 28px;
  max-height: 60vh;
  overflow-y: auto;
}

.article-detail-title {
  margin: 0 0 16px;
  font-size: 22px;
  font-weight: 800;
  color: #142117;
  line-height: 1.4;
}

.article-detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
  padding: 14px 16px;
  background: #f6fbf7;
  border-radius: 10px;
  margin-bottom: 18px;
  font-size: 14px;
  color: #5a6b5f;
}

.article-detail-meta .meta-item strong {
  color: #304036;
  font-weight: 700;
}

.article-detail-reject {
  padding: 12px 16px;
  background: #fef0f0;
  border: 1px solid #f5c2c2;
  border-radius: 10px;
  margin-bottom: 18px;
  font-size: 14px;
  color: #a8442b;
  line-height: 1.6;
}

.article-detail-reject strong {
  color: #842b1a;
}

/* 拒绝文章弹窗内部样式（dialog 外壳样式见全局 style 块） */
.reject-dialog-body {
  padding: 22px 24px;
}

.reject-dialog-tip {
  margin: 0 0 12px;
  font-size: 14px;
  color: #5a6b5f;
  line-height: 1.6;
}

.article-detail-body {
  font-size: 16px;
  line-height: 1.85;
  color: #1a2a1f;
}

.article-detail-body :deep(p) {
  margin: 0 0 1em;
}

.article-detail-body :deep(.article-img) {
  margin: 1.4em 0;
  text-align: center;
}

.article-detail-body :deep(.article-img img) {
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid #edf2ee;
}

.article-detail-body :deep(.article-img figcaption) {
  margin-top: 8px;
  color: #8a9388;
  font-size: 14px;
}

.article-detail-body :deep(.article-img figcaption:empty) {
  display: none;
}

.article-detail-body :deep(.preview-empty) {
  color: #a8b5ac;
  font-size: 14px;
  text-align: center;
  padding: 40px 20px;
}

.admin-form-dialog :deep(.el-dialog),
:deep(.admin-form-dialog.el-dialog),
:deep(.admin-form-dialog .el-dialog) {
  overflow: hidden;
  max-width: calc(100vw - 40px);
  border-radius: 20px;
  background: #fbfffb;
  box-shadow: 0 22px 54px rgba(29, 67, 39, .24);
}

.admin-form-dialog :deep(.el-dialog__header),
:deep(.admin-form-dialog .el-dialog__header) {
  margin: 0;
  padding: 28px 34px 20px;
  border-bottom: 1px solid #dcebdd;
  background: linear-gradient(180deg, #f1faf2 0%, #fbfffb 100%);
}

.admin-form-dialog :deep(.el-dialog__title),
:deep(.admin-form-dialog .el-dialog__title) {
  color: #102016;
  font-size: 26px;
  font-weight: 900;
  letter-spacing: 0;
}

.admin-form-dialog :deep(.el-dialog__headerbtn),
:deep(.admin-form-dialog .el-dialog__headerbtn) {
  top: 20px;
  right: 22px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
}

.admin-form-dialog :deep(.el-dialog__headerbtn:hover),
:deep(.admin-form-dialog .el-dialog__headerbtn:hover) {
  background: #e7f5ea;
}

.admin-form-dialog :deep(.el-dialog__body),
:deep(.admin-form-dialog .el-dialog__body) {
  padding: 28px 34px 8px;
}

.admin-form-dialog :deep(.el-dialog__footer),
:deep(.admin-form-dialog .el-dialog__footer) {
  padding: 8px 34px 30px;
}

.admin-form-dialog :deep(.el-dialog__footer .el-button),
:deep(.admin-form-dialog .el-dialog__footer .el-button) {
  min-width: 112px;
  height: 50px;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 900;
}

.admin-form-dialog :deep(.el-button--success),
:deep(.admin-form-dialog .el-button--success) {
  border-color: #178844;
  background: #178844;
}

.expert-account-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.expert-account-form :deep(.el-form-item__label) {
  margin-bottom: 9px;
  color: #263c2d;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.3;
}

.expert-account-form :deep(.el-input__wrapper),
.expert-account-form :deep(.el-textarea__inner) {
  min-height: 54px;
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 18px;
}

.expert-account-form :deep(.el-input__wrapper:hover),
.expert-account-form :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #9bc8a8 inset;
}

.expert-account-form :deep(.el-input__wrapper.is-focus),
.expert-account-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(23, 136, 68, .22) inset;
}

.expert-account-form :deep(.el-input__inner) {
  font-size: 18px;
}

.expert-account-form :deep(.el-textarea__inner) {
  padding: 15px 17px;
  line-height: 1.6;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.green-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 50px;
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

.empty-state {
  padding: 58px 24px;
  color: #7b8b82;
  font-size: 18px;
  text-align: center;
}

.empty-state.compact {
  padding: 42px 18px;
  font-size: 16px;
}

.admin-shell :deep(.el-button--success) {
  --el-button-bg-color: #178844;
  --el-button-border-color: #178844;
  --el-button-hover-bg-color: #116d36;
  --el-button-hover-border-color: #116d36;
}

@media (max-width: 1200px) {
  .admin-sidebar { flex-basis: 270px; }
  .admin-content { padding-right: 26px; padding-left: 26px; }
  .stats-grid, .expert-grid { gap: 16px; }
  .stat-card { padding: 22px; }
  .stat-copy strong { font-size: 31px; }
  .article-workbench { grid-template-columns: 1fr; }
}

@media (max-width: 920px) {
  .stats-grid, .expert-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .admin-topbar { padding: 0 26px; }
  .admin-content { padding: 26px 22px 44px; }
}

@media (max-width: 680px) {
  .admin-shell { display: block; }
  .admin-sidebar { min-height: auto; }
  .brand { height: 76px; padding: 0 18px; }
  .side-nav { flex-direction: row; overflow-x: auto; padding: 12px 14px; }
  .side-nav-group { flex: 0 0 auto; }
  .side-nav-item { flex: 0 0 auto; min-height: 48px; padding: 0 15px; font-size: 16px; }
  .sub-nav { padding: 4px 0 0; }
  .sub-nav-item { min-height: 36px; padding: 0 12px; font-size: 14px; white-space: nowrap; }
  .sidebar-logout { min-height: 58px; padding: 0 18px; border-top: 1px solid #dbe9df; border-bottom: 1px solid #dbe9df; font-size: 16px; }
  .admin-topbar { min-height: 72px; padding: 0 18px; }
  .topbar-title { font-size: 16px; }
  .topbar-user-copy strong { font-size: 15px; }
  .topbar-user-copy span { font-size: 12px; }
  .topbar-avatar { width: 42px; height: 42px; font-size: 18px; }
  .admin-content { padding: 22px 16px 38px; }
  .page-heading { margin-bottom: 20px; }
  .page-heading-row { align-items: stretch; flex-direction: column; }
  .page-heading h1 { font-size: 27px; }
  .stats-grid, .expert-grid { grid-template-columns: 1fr; }
  .form-grid { grid-template-columns: 1fr; }
  .article-section-head { align-items: flex-start; flex-direction: column; padding: 20px 18px; }
  .article-review-item,
  .my-article-item { grid-template-columns: 1fr; padding: 18px; }
  .article-review-title { align-items: flex-start; flex-direction: column; }
  .article-review-actions,
  .my-article-item .table-actions { width: 100%; }
  .article-review-actions .table-action,
  .my-article-item .table-action { flex: 1; }
  .growth-panel { min-height: 330px; padding: 22px 18px 18px; }
  .growth-chart { height: 240px; gap: 8px; }
  .growth-bar { width: 100%; }
  .stat-card, .expert-card { border-radius: 16px; }
  .article-table { min-width: 980px; }
}
</style>

<!-- 全局样式：el-dialog 会被 teleport 到 body，scoped 的 :deep() 无法匹配，需用全局样式 -->
<style>
</style>
