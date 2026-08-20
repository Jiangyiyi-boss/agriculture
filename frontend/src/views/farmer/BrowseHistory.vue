<template>
  <div class="history-page">
    <h1 class="page-title">浏览历史</h1>

    <div v-if="loading" class="loading-text">加载中...</div>
    <div v-else-if="!history.length" class="empty-text">还没有浏览过三农资讯文章</div>

    <!-- 文章卡片网格 -->
    <div v-else class="card-grid">
      <div
        v-for="item in history"
        :key="item.article_id"
        class="article-card"
        @click="goToArticle(item.article_id)"
      >
        <div class="card-cover">
          <img v-if="item.cover" :src="item.cover" :alt="item.title" loading="lazy" />
          <div v-else class="cover-placeholder">
            <SproutIcon :size="34" variant="dark" />
          </div>
          <span class="card-category">{{ item.category }}</span>
        </div>
        <div class="card-body">
          <h3 class="card-title" :title="item.title">{{ item.title }}</h3>
          <div class="card-meta">
            <span class="card-date">浏览于 {{ item.viewed_at }}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import SproutIcon from '@/components/SproutIcon.vue'

const router = useRouter()
const history = ref<any[]>([])
const loading = ref(true)

function goToArticle(id: number) {
  router.push(`/news/${id}`)
}

onMounted(async () => {
  try {
    history.value = await api.getArticleViews()
  } catch {
    history.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.history-page {
  color: #07170e;
}

.page-title {
  margin: 0 0 28px;
  font-size: 28px;
  font-weight: 900;
  color: #0e1a12;
}

/* ---- 卡片网格 ---- */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 26px;
}

.article-card {
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(34, 94, 56, .08);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow .2s, transform .2s;
  display: flex;
  flex-direction: column;
}

.article-card:hover {
  box-shadow: 0 8px 24px rgba(34, 94, 56, .12);
  transform: translateY(-3px);
}

/* 封面 */
.card-cover {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #f0f7f1;
  overflow: hidden;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform .25s;
}

.article-card:hover .card-cover img {
  transform: scale(1.04);
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f4ea, #d4ecd9);
}

.card-category {
  position: absolute;
  left: 12px;
  top: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(23, 136, 68, .92);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

/* 卡片信息 */
.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 18px 14px;
}

.card-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.5;
  color: #0e1a12;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 51px;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  color: #9aa59e;
}

.card-date {
  font-size: 13px;
  font-weight: 500;
}

.card-meta svg {
  color: #b8c8bd;
  transition: color .15s, transform .15s;
}

.article-card:hover .card-meta svg {
  color: #178844;
  transform: translateX(2px);
}

/* Loading / Empty */
.loading-text,
.empty-text {
  padding: 90px 0;
  text-align: center;
  font-size: 16px;
  color: #7d887f;
}

/* ---- Responsive ---- */
@media (max-width: 1100px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
}

@media (max-width: 640px) {
  .card-grid {
    grid-template-columns: 1fr;
  }

  .page-title {
    font-size: 24px;
  }
}
</style>
