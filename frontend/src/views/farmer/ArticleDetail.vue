<template>
  <div class="article-detail-page">
    <div class="article-content-wrapper">
      <button class="back-btn" type="button" @click="goBack">
        <el-icon :size="18"><Back /></el-icon>
        返回
      </button>

      <div v-if="loading" class="loading-text">加载中...</div>

      <article v-else-if="article" class="article-body" :style="{ fontSize: fontSize + 'px' }">
        <h1 class="article-title">{{ article.title }}</h1>

        <div class="article-meta">
          <div class="meta-top">
            <span class="meta-tag">{{ article.category }}</span>
            <div class="font-size-switcher">
              <span class="font-label">字号</span>
              <button
                v-for="opt in fontOptions"
                :key="opt.value"
                :class="['font-btn', { active: fontSize === opt.value }]"
                type="button"
                @click="setFontSize(opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>
          <div class="meta-info">
            <span v-if="article.source" class="meta-source">来源：{{ article.source }}</span>
            <span v-if="article.original_author" class="meta-author">{{ article.source ? ' · ' : '' }}作者：{{ article.original_author }}</span>
            <span class="meta-date">{{ formatDate(article.date) }}</span>
          </div>
        </div>

        <div class="article-content" v-html="formattedContent"></div>
      </article>

      <div v-else class="empty-text">文章不存在或已下架</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back } from '@element-plus/icons-vue'
import { api } from '@/api/client'

const route = useRoute()
const router = useRouter()
const article = ref<any>(null)
const loading = ref(true)

const fontOptions = [
  { label: '小', value: 14 },
  { label: '中', value: 16 },
  { label: '大', value: 18 },
]
const fontSize = ref(16)

const formattedContent = computed(() => {
  if (!article.value?.content) return ''
  const content = article.value.content
  // 按行处理：识别 Markdown 图片行 ![alt](url)，其余按段落渲染
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

  // 图片语法：![alt](url)
  const imgRegex = /^!\[([^\]]*)\]\(([^)]+)\)\s*$/

  for (const rawLine of lines) {
    const line = rawLine.trim()
    const imgMatch = line.match(imgRegex)
    if (imgMatch) {
      flushParagraph()
      const alt = escapeHtml(imgMatch[1])
      const url = escapeAttr(imgMatch[2])
      html.push(`<figure class="article-img"><img src="${url}" alt="${alt}" loading="lazy" /><figcaption>${alt}</figcaption></figure>`)
    } else if (line === '') {
      flushParagraph()
    } else {
      paragraph.push(escapeHtml(line))
    }
  }
  flushParagraph()
  return html.join('')
})

function escapeAttr(text: string) {
  return text.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeHtml(text: string) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function formatDate(date?: string) {
  return date?.slice(0, 10) || '-'
}

function setFontSize(size: number) {
  fontSize.value = size
  localStorage.setItem('article-font-size', String(size))
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/news')
  }
}

async function fetchArticle() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    article.value = await api.getArticle(id)
    // 记录浏览历史（失败不影响阅读）
    api.recordArticleView(id)
  } catch {
    article.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const saved = localStorage.getItem('article-font-size')
  if (saved) fontSize.value = Number(saved)
})

watch(() => route.params.id, fetchArticle, { immediate: true })
</script>

<style scoped>
.article-detail-page {
  color: #07170e;
}

.back-btn {
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
  margin-bottom: 16px;
}

.back-btn:hover {
  border-color: #178844;
  color: #178844;
}

.article-content-wrapper {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 20px 0;
}

.article-body {
  padding: 10px 0 40px;
}

.article-title {
  font-size: 30px;
  font-weight: 900;
  line-height: 1.3;
  margin: 0 0 24px;
  color: #06150d;
  text-align: center;
}

.article-meta {
  padding-bottom: 22px;
  margin-bottom: 28px;
  border-bottom: 1px solid #edf2ee;
}

.meta-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.meta-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 14px;
  color: #7d887f;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border-radius: 8px;
  background: #e1f2e6;
  color: #178844;
  font-size: 14px;
  font-weight: 700;
}

.meta-source {
  color: #178844;
  font-weight: 500;
}

.meta-author {
  color: #178844;
  font-weight: 500;
}

.meta-date {
  color: #98a39a;
}

.font-size-switcher {
  display: flex;
  align-items: center;
  gap: 6px;
}

.font-label {
  font-size: 14px;
  color: #8a9388;
  font-weight: 500;
}

.font-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #d4e3d8;
  border-radius: 8px;
  background: #fff;
  color: #52635a;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all .15s;
}

.font-btn:hover {
  border-color: #178844;
  color: #178844;
}

.font-btn.active {
  background: #178844;
  border-color: #178844;
  color: #fff;
}

.article-content :deep(p) {
  margin: 0 0 1.2em;
  line-height: 1.85;
  color: #1a2a1f;
  text-align: justify;
}

.article-content :deep(p:last-child) {
  margin-bottom: 0;
}

.article-content :deep(.article-img) {
  margin: 1.4em 0;
  text-align: center;
}

.article-content :deep(.article-img img) {
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid #edf2ee;
  cursor: zoom-in;
  transition: transform .2s;
}

.article-content :deep(.article-img img:hover) {
  transform: scale(1.01);
}

.article-content :deep(.article-img figcaption) {
  margin-top: 8px;
  color: #8a9388;
  font-size: 14px;
}

.article-content :deep(.article-img figcaption:empty) {
  display: none;
}

.loading-text,
.empty-text {
  padding: 80px 0;
  text-align: center;
  font-size: 16px;
  color: #7d887f;
}

@media (max-width: 768px) {
  .article-body {
    padding: 28px 20px;
  }

  .article-title {
    font-size: 24px;
  }

  .meta-top {
    flex-wrap: wrap;
    gap: 10px;
  }

  .meta-info {
    font-size: 13px;
  }
}
</style>
