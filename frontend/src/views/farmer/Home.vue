<template>
  <div class="home-page">
    <!-- 欢迎 + 农事计划 + 天气 -->
    <el-row :gutter="16" class="top-row">
      <el-col :lg="8" :span="24">
        <el-card class="welcome-card">
          <div class="welcome-inner">
            <!-- 顶部：欢迎标签 -->
            <div class="welcome-top">
              <span class="welcome-pill">
                <span class="welcome-pill-dot"></span>
                欢迎回来
              </span>
            </div>

            <!-- 主标题 -->
            <div class="welcome-title">
              <h1 class="welcome-name">{{ greetingPrefix }}，{{ auth.user?.name || '农户' }}</h1>
            </div>

            <!-- 位置徽章 -->
            <div class="welcome-loc">
              <el-icon :size="14" color="#178844"><Location /></el-icon>
              <span>{{ displayRegion }}</span>
            </div>

            <!-- 统计卡（横向布局 + 彩色图标） -->
            <div class="welcome-stats">
              <div class="welcome-stat">
                <div class="welcome-stat-icon icon-land">
                  <el-icon :size="18" color="#fff"><MapLocation /></el-icon>
                </div>
                <div class="welcome-stat-info">
                  <strong>{{ stats.lands }}</strong>
                  <span>地块数量</span>
                </div>
              </div>
              <div class="welcome-stat">
                <div class="welcome-stat-icon icon-crop">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                    <path d="M12 21 V12" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
                    <path d="M12 14 C7 14 4 11 4 7 C8 7 11 9 12 14 Z" fill="#fff" opacity="0.95"/>
                    <path d="M12 11 C17 11 20 8 20 4 C16 4 13 6 12 11 Z" fill="#fff" opacity="0.75"/>
                  </svg>
                </div>
                <div class="welcome-stat-info">
                  <strong>{{ stats.crops }}</strong>
                  <span>种植批次</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 农事计划 -->
      <el-col :lg="8" :span="24">
        <el-card class="plan-card">
          <div class="plan-inner">
            <div class="plan-header">
              <div class="plan-title">
                <h3>农事计划</h3>
              </div>
              <div class="plan-actions">
                <button class="plan-add-btn" @click="showAddInput = true">＋ 添加</button>
                <a class="plan-more" @click="planDialogVisible = true">全部 ›</a>
              </div>
            </div>

            <!-- 添加输入行 -->
            <div v-if="showAddInput" class="plan-add-row">
              <input
                v-model="newPlanContent"
                placeholder="如：给番茄追肥、检查病虫害"
                maxlength="200"
                @keyup.enter="addPlan"
              />
              <button class="plan-add-confirm" @click="addPlan">添加</button>
            </div>

            <!-- 空状态 -->
            <div v-if="undonePlans.length === 0 && !showAddInput" class="plan-empty">
              <SproutIcon :size="44" variant="light" />
              <p>还没有农事安排</p>
              <a class="plan-empty-btn" @click="showAddInput = true">添加计划</a>
            </div>

            <!-- 计划列表 -->
            <div v-else class="plan-list">
              <div v-for="p in undonePlans.slice(0, 4)" :key="p.id" class="plan-item">
                <button class="plan-check" title="点击标记完成" @click="togglePlan(p)"></button>
                <span class="plan-content">{{ p.content }}</span>
              </div>
              <div v-if="undonePlans.length > 4" class="plan-more-row" @click="planDialogVisible = true">
                还有 {{ undonePlans.length - 4 }} 项 · 查看全部
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :lg="8" :span="24">
        <el-card class="weather-card">
          <div class="weather-top">
            <div>
              <p class="weather-loc">
                {{ weatherStore.loading ? '正在定位当前位置' : `${weatherStore.shortRegion} · ${weatherStore.currentDateLabel}` }}
              </p>
              <p class="weather-temp">{{ weatherStore.currentTemperatureRange }}</p>
              <p class="weather-cond">{{ weatherStore.weather }}</p>
            </div>
            <el-icon :size="44" color="#fff"><component :is="weatherIconFor(weatherStore.currentIcon)" /></el-icon>
          </div>
          <div class="weather-info">
            <span><el-icon :size="13"><Drizzling /></el-icon> 湿度 {{ weatherStore.humidity }}%</span>
            <span><el-icon :size="13"><WindPower /></el-icon> {{ weatherStore.windText }}</span>
          </div>
          <p v-if="weatherStore.error" class="weather-error">{{ weatherStore.error }}</p>
          <div class="weather-forecast">
            <span v-for="f in weatherStore.forecast" :key="f.day" class="forecast-item">
              <span>{{ f.day }}</span>
              <span class="forecast-weather">
                <el-icon :size="14"><component :is="weatherIconFor(f.icon)" /></el-icon>
                {{ f.weather }}
              </span>
              <span class="forecast-temp">{{ f.low }}° / {{ f.high }}°</span>
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷入口 -->
    <h2 class="section-title">快捷入口</h2>
    <el-row :gutter="16" class="quick-row">
      <el-col v-for="e in quickEntries" :key="e.label" :xs="12" :lg="6" :span="12">
        <router-link :to="e.path" class="quick-card">
          <el-card shadow="hover">
            <span :class="['quick-icon', e.color]">
              <el-icon v-if="e.icon !== 'sprout'" :size="24"><component :is="e.icon" /></el-icon>
              <SproutIcon v-else :size="24" variant="dark" />
            </span>
            <p class="quick-label">{{ e.label }}</p>
          </el-card>
        </router-link>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 三农资讯 -->
      <el-col :lg="16" :span="24">
        <div class="section-header">
          <h2 class="section-title">三农资讯</h2>
          <router-link to="/news" class="more-link">更多 &gt;</router-link>
        </div>
        <div v-if="articles.length === 0" class="empty-text">暂无资讯</div>
        <div v-else class="article-card">
          <router-link
            v-for="a in articles.slice(0, 4)"
            :key="a.id"
            :to="`/news/${a.id}`"
            class="article-item"
          >
            <span class="article-title">{{ a.title }}</span>
            <span class="article-date">{{ a.date?.slice(5) }}</span>
          </router-link>
        </div>
      </el-col>

      <!-- 我的种植 -->
      <el-col :lg="8" :span="24">
        <div class="section-header">
          <h2 class="section-title">我的种植</h2>
          <router-link to="/crops" class="more-link">全部 &gt;</router-link>
        </div>
        <el-card class="planting-card">
          <div v-if="homeCrops.length === 0" class="empty-planting">
            <SproutIcon :size="48" variant="light" />
            <p class="empty-planting-text">还没有种植作物</p>
            <router-link to="/crops" class="empty-planting-btn">添加作物</router-link>
          </div>
          <div v-for="c in homeCrops.slice(0, 3)" :key="c.id" class="crop-item">
            <div class="crop-header">
              <span class="crop-name">
                <SproutIcon :size="14" variant="dark" />
                {{ c.name }} <small>{{ c.variety }}</small>
              </span>
              <router-link
                v-if="c.advice_count"
                :to="`/crops/${c.id}?advice=1`"
                class="advice-badge"
              >
                <span class="advice-dot"></span>
                专家建议 {{ c.advice_count }} 条
              </router-link>
            </div>
            <div class="crop-meta">
              <span>{{ c.land_name }}</span>
              <span>已种植 {{ plantedDays(c) }} 天</span>
              <span v-if="c.last_work">上次作业：{{ c.last_work }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 全部农事计划弹窗 -->
    <el-dialog v-model="planDialogVisible" title="全部农事计划" width="540px" class="form-dialog" :close-on-click-modal="false">
      <div v-if="plans.length === 0" class="dialog-empty">暂无农事计划</div>
      <template v-else>
        <div class="dialog-group-title">未完成（{{ undonePlans.length }}）</div>
        <div class="dialog-list">
          <div v-for="p in undonePlans" :key="p.id" class="dialog-plan-item">
            <button class="plan-check" title="点击标记完成" @click="togglePlan(p)"></button>
            <span class="plan-content">{{ p.content }}</span>
            <el-icon class="dialog-delete" title="删除" @click="removePlan(p)"><Delete /></el-icon>
          </div>
        </div>

        <div v-if="donePlans.length" class="dialog-group-title done-title">已完成（{{ donePlans.length }}）</div>
        <div v-if="donePlans.length" class="dialog-list">
          <div v-for="p in donePlans" :key="p.id" class="dialog-plan-item done">
            <button class="plan-check checked" title="点击恢复未完成" @click="togglePlan(p)">✓</button>
            <span class="plan-content">{{ p.content }}</span>
            <span class="dialog-plan-date">{{ p.plan_date }}</span>
            <el-icon class="dialog-delete" title="删除" @click="removePlan(p)"><Delete /></el-icon>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useWeatherStore } from '@/stores/weather'
import { api } from '@/api/client'
import {
  Location, Sunny, Drizzling, WindPower, Cloudy, MostlyCloudy,
  PartlyCloudy, Pouring, Lightning, Umbrella, MapLocation, Notebook, ChatDotRound, Delete
} from '@element-plus/icons-vue'
import SproutIcon from '@/components/SproutIcon.vue'

const auth = useAuthStore()
const weatherStore = useWeatherStore()
const articles = ref<any[]>([])
const crops = ref<any[]>([])
const stats = reactive({ lands: 0, crops: 0 })

// ============================================================
// 农事计划
// ============================================================
const plans = ref<any[]>([])
const planDialogVisible = ref(false)
const showAddInput = ref(false)
const newPlanContent = ref('')

// 未完成计划（首页卡片展示，后端已按日期升序排好）
const undonePlans = computed(() => plans.value.filter(p => !p.is_done))
const donePlans = computed(() => plans.value.filter(p => p.is_done))

async function loadPlans() {
  try { plans.value = await api.getFarmPlans() } catch {}
}

async function addPlan() {
  const content = newPlanContent.value.trim()
  if (!content) return
  try {
    await api.createFarmPlan(content)
    newPlanContent.value = ''
    showAddInput.value = false
    await loadPlans()
  } catch {
    ElMessage.error('添加失败，请重试')
  }
}

async function togglePlan(p: any) {
  try {
    await api.toggleFarmPlan(p.id, !p.is_done)
    await loadPlans()
  } catch {
    ElMessage.error('操作失败，请重试')
  }
}

async function removePlan(p: any) {
  try {
    await api.deleteFarmPlan(p.id)
    await loadPlans()
  } catch {
    ElMessage.error('删除失败，请重试')
  }
}

const quickEntries = [
  { path: '/qa?mode=ai', label: 'AI 智能问答', icon: 'ChatDotRound', color: 'green' },
  { path: '/crops', label: '作物管理', icon: 'sprout', color: 'teal' },
  { path: '/lands', label: '地块管理', icon: 'MapLocation', color: 'pink' },
  { path: '/news', label: '三农资讯', icon: 'Notebook', color: 'yellow' },
]

const displayRegion = computed(() => auth.user?.region || weatherStore.region)

// 今日日期（用于欢迎卡片）
const today = computed(() => {
  const d = new Date()
  const weekMap = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getMonth() + 1}月${d.getDate()}日 · 周${weekMap[d.getDay()]}`
})

// ============================================================
// 欢迎语：时段问候 + 按日期轮播鼓励语（每次登录都有变化）
// ============================================================

function getTimeGreeting(): string {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 13) return '中午好'
  if (h < 18) return '下午好'
  if (h < 22) return '晚上好'
  return '夜深了'
}

const FARMER_QUOTES = [
  '今天也把地种好',
  '把握农时，丰收可期',
  '粒粒皆辛苦，年年有好收成',
  '一分耕耘，一分收获',
  '科学种田，丰收在望',
  '人勤地不懒，春耕正当时',
  '今日农事不可怠',
  '勤劳致富，科技兴农',
  '春种一粒粟，秋收万颗子',
  '土地是庄稼人的命根子',
  '田间管理做到位，作物长得旺',
  '勤观察、早预防，病虫害无处藏',
]

function getDailyQuote(): string {
  // 按日期稳定轮换：同一天看到同一句，第二天换新句
  const now = new Date()
  const dayOfYear = Math.floor(
    (now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86400000
  )
  return FARMER_QUOTES[dayOfYear % FARMER_QUOTES.length]
}

const greetingPrefix = computed(() => getTimeGreeting())
const dailyQuote = computed(() => getDailyQuote())

const homeCrops = computed(() => {
  const records = Array.isArray(crops.value) ? crops.value : []
  return records.filter((c: any) => c.status === '种植中')
})

function plantedDays(c: any): number {
  if (!c.plant_date) return 0
  const plant = new Date(c.plant_date.replace(/-/g, '/'))
  const now = new Date()
  const diff = Math.floor((now.getTime() - plant.getTime()) / 86400000)
  return Math.max(0, diff)
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

onMounted(async () => {
  weatherStore.init()
  loadPlans()
  try { articles.value = await api.getArticles() } catch {}
  try { crops.value = await api.getCrops() } catch {}
  try { const lands = await api.getLands(); stats.lands = lands.length } catch {}
  try { stats.crops = crops.value.length } catch {}
})
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 34px;
  color: #0f1f16;
}

.top-row {
  align-items: stretch;
}

.top-row :deep(.el-col) {
  display: flex;
}

.welcome-card,
.plan-card,
.weather-card {
  width: 100%;
  min-height: 276px;
  border: 1px solid rgba(34, 94, 56, .12);
  border-radius: 16px;
  box-shadow: 0 8px 22px rgba(26, 71, 43, .12);
  overflow: hidden;
}

.welcome-card {
  background: linear-gradient(135deg, #f0f8f1 0%, #e3f2e8 50%, #d8ead9 100%);
  color: #0b1710;
  position: relative;
  overflow: hidden;
}

.welcome-card :deep(.el-card__body) {
  height: 100%;
  padding: 24px 26px 20px;
}

.welcome-inner {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 232px;
  z-index: 1;
}

/* 顶部行：欢迎标签 + 日期 */
.welcome-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.welcome-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px 6px 12px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(23, 136, 68, 0.16);
  border-radius: 999px;
  font-size: 12px;
  color: #0f6e3c;
  font-weight: 700;
  letter-spacing: 0.4px;
  backdrop-filter: blur(10px) saturate(1.2);
  -webkit-backdrop-filter: blur(10px) saturate(1.2);
  box-shadow: 0 2px 8px rgba(23, 136, 68, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.welcome-pill-dot {
  width: 7px;
  height: 7px;
  background: #34C25C;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(52, 194, 92, 0.25);
  animation: pulse-dot 2.4s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px rgba(52, 194, 92, 0.25); }
  50%      { box-shadow: 0 0 0 8px rgba(52, 194, 92, 0); }
}

.welcome-date {
  font-size: 13px;
  color: #5f6b64;
  font-weight: 600;
}

/* 主标题 */
.welcome-title {
  margin-top: 4px;
}

.welcome-name {
  font-size: 24px;
  line-height: 1.25;
  font-weight: 900;
  margin: 0;
  letter-spacing: -0.3px;
  background: linear-gradient(135deg, #0b6b3a 0%, #178844 45%, #34C25C 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}

/* 位置徽章（玻璃 pill） */
.welcome-loc {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: #456a55;
  margin: 0;
  font-weight: 600;
  padding: 7px 14px 7px 12px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(34, 94, 56, 0.12);
  border-radius: 999px;
  width: fit-content;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 2px 8px rgba(26, 71, 43, 0.06);
}

.welcome-divider {
  opacity: 0.5;
  margin: 0 2px;
}

.welcome-area {
  color: #178844;
  font-weight: 700;
}

.welcome-arrow {
  margin-left: 4px;
  color: #178844;
  font-weight: 700;
  font-size: 16px;
  line-height: 1;
}

/* 统计卡（横向 2 列） */
.welcome-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: auto;
}

.welcome-stat {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 12px;
  backdrop-filter: blur(14px) saturate(1.3);
  -webkit-backdrop-filter: blur(14px) saturate(1.3);
  box-shadow: 0 4px 14px rgba(26, 71, 43, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.6);
  transition: transform .22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow .22s ease, background .22s ease;
}

.welcome-stat:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(26, 71, 43, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.65);
}

.welcome-stat-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-land {
  background: linear-gradient(135deg, #34C25C 0%, #168744 100%);
  box-shadow: 0 4px 10px rgba(22, 135, 68, 0.25);
}

.icon-crop {
  background: linear-gradient(135deg, #FFD166 0%, #F4A418 100%);
  box-shadow: 0 4px 10px rgba(244, 164, 24, 0.25);
}

.welcome-stat-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
}

.welcome-stat-info strong {
  font-size: 19px;
  font-weight: 900;
  line-height: 1.1;
  color: #0b1710;
}

.welcome-stat-info span {
  font-size: 12px;
  font-weight: 600;
  color: #7b827d;
  line-height: 1.2;
}

/* 用户偏好减少动画时，停止脉冲 */
@media (prefers-reduced-motion: reduce) {
  .welcome-pill-dot {
    animation: none;
  }
  .welcome-stat {
    transition: none;
  }
}

/* ============================================================
   农事计划卡片
   ============================================================ */
.plan-card :deep(.el-card__body) {
  height: 100%;
  padding: 20px 22px;
}

.plan-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 232px;
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.plan-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.plan-title h3 {
  margin: 0;
  font-size: 19px;
  font-weight: 900;
  color: #06150d;
}

.plan-count {
  flex-shrink: 0;
  padding: 3px 10px;
  background: #e8f5ed;
  color: #178844;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.plan-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.plan-add-btn {
  padding: 5px 14px;
  border: 1px solid rgba(23, 136, 68, 0.35);
  border-radius: 999px;
  background: #fff;
  color: #178844;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all .2s ease;
}

.plan-add-btn:hover {
  background: #178844;
  border-color: #178844;
  color: #fff;
}

.plan-more {
  font-size: 14px;
  color: #178844;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.plan-more:hover {
  opacity: .75;
}

/* 添加输入行 */
.plan-add-row {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.plan-add-row input {
  flex: 1;
  min-width: 0;
  padding: 9px 12px;
  border: 1px solid #d8e6dd;
  border-radius: 10px;
  font-size: 14px;
  color: #0e1a12;
  outline: none;
  transition: border-color .2s ease;
}

.plan-add-row input:focus {
  border-color: #178844;
}

.plan-add-row input::placeholder {
  color: #a6adA8;
}

.plan-add-confirm {
  padding: 0 18px;
  border: none;
  border-radius: 10px;
  background: #178844;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity .2s ease;
}

.plan-add-confirm:hover {
  opacity: .88;
}

/* 空状态 */
.plan-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 0;
}

.plan-empty p {
  margin: 0;
  font-size: 14px;
  color: #999;
}

.plan-empty-btn {
  display: inline-flex;
  align-items: center;
  padding: 7px 24px;
  background: var(--farm-green, #178844);
  color: #fff;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity .2s ease, transform .2s ease;
}

.plan-empty-btn:hover {
  opacity: .88;
  transform: translateY(-1px);
}

/* 计划列表 */
.plan-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 10px;
}

.plan-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  transition: background .2s ease;
}

.plan-item:hover {
  background: #f3f8f4;
}

/* 圆形勾选按钮 */
.plan-check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #b9d8c3;
  background: #fff;
  color: #fff;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  padding: 0;
  transition: all .2s ease;
}

.plan-check:hover {
  border-color: #178844;
}

.plan-check.checked {
  background: #178844;
  border-color: #178844;
}

.plan-content {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 600;
  color: #0e1a12;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-date-tag {
  flex-shrink: 0;
  padding: 2px 8px;
  background: #f0f4f2;
  color: #8a9388;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.plan-date-tag.today {
  background: #e8f5e9;
  color: #2e7d32;
}

.plan-more-row {
  margin-top: 4px;
  padding: 6px 0;
  text-align: center;
  font-size: 13px;
  color: #178844;
  font-weight: 700;
  cursor: pointer;
}

.plan-more-row:hover {
  opacity: .75;
}

/* 全部计划弹窗 */
.dialog-empty {
  padding: 40px 0;
  text-align: center;
  font-size: 14px;
  color: #999;
}

.dialog-group-title {
  font-size: 14px;
  font-weight: 800;
  color: #456a55;
  margin: 0 0 6px;
}

.dialog-group-title.done-title {
  margin-top: 18px;
  color: #999;
}

.dialog-plan-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
}

.dialog-plan-item:hover {
  background: #f6faf7;
}

.dialog-plan-item.done .plan-content {
  text-decoration: line-through;
  color: #a6adA8;
}

.dialog-plan-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #8a9388;
}

.dialog-delete {
  flex-shrink: 0;
  color: #c0c4cc;
  cursor: pointer;
  transition: color .2s ease;
}

.dialog-delete:hover {
  color: #f56c6c;
}

.weather-card {
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 255, 255, 0.20) 0%, transparent 40%),
    radial-gradient(circle at 0% 100%, rgba(255, 255, 255, 0.10) 0%, transparent 45%),
    radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(135deg, #178844 0%, #0d6b3a 100%);
  background-size: auto, auto, 16px 16px, auto;
  color: #fff;
  border: none;
}
.weather-card :deep(.el-card__body) { height: 100%; padding: 22px 24px 20px; }
.weather-top { display: flex; justify-content: space-between; align-items: flex-start; }
.weather-loc { font-size: 15px; opacity: .95; font-weight: 800; margin: 0 0 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.weather-temp { font-size: 34px; line-height: 1; font-weight: 900; margin: 0 0 6px; }
.weather-cond { font-size: 15px; opacity: .94; margin: 0; font-weight: 600; }
.weather-info { display: flex; gap: 18px; margin-top: 14px; font-size: 13px; opacity: .9; font-weight: 700; }
.weather-info span { display: flex; align-items: center; gap: 4px; }
.weather-error { margin: 12px 0 0; color: rgba(255,255,255,.72); font-size: 12px; font-weight: 700; }
.weather-forecast { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: auto; padding-top: 14px; border-top: 1px solid rgba(255,255,255,.22); }
.forecast-item { text-align: center; font-size: 13px; opacity: .92; font-weight: 700; }
.forecast-weather { display: flex; align-items: center; justify-content: center; gap: 4px; margin-top: 6px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.forecast-temp { display: block; margin-top: 6px; font-weight: 900; }

.section-title { font-size: 26px; line-height: 1.2; font-weight: 900; margin: 0; letter-spacing: 0; color: #06150d; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.more-link { font-size: 18px; color: #178844; text-decoration: none; font-weight: 800; }

.quick-row { margin-top: -4px; margin-bottom: 0; }
.quick-card { text-decoration: none; }
.quick-card :deep(.el-card) {
  border-radius: 16px;
  border-color: rgba(34, 94, 56, .12);
  box-shadow: 0 6px 16px rgba(26, 71, 43, .10);
  transition: transform .25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow .25s ease;
}
.quick-card :deep(.el-card:hover) {
  transform: translateY(-4px);
  box-shadow: 0 14px 28px rgba(26, 71, 43, .16);
}
.quick-card :deep(.el-card__body) { min-height: 134px; padding: 28px 30px; display: flex; flex-direction: column; gap: 8px; }
.quick-icon { display: flex; align-items: center; justify-content: center; width: 54px; height: 54px; border-radius: 14px; transition: transform .25s ease; }
.quick-card:hover .quick-icon { transform: scale(1.06); }
.quick-icon.green { background: rgba(22,163,74,.10); color: #16a34a; }
.quick-icon.yellow { background: rgba(234,179,8,.12); color: #ca8a04; }
.quick-icon.teal { background: rgba(20,184,166,.12); color: #0d9488; }
.quick-icon.pink { background: rgba(244,114,182,.12); color: #db2777; }
.quick-label { font-size: 22px; font-weight: 900; color: #08170f; margin: 12px 0 0; }

.article-card {
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(34, 94, 56, .1);
  overflow: hidden;
}
.article-item {
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f4f2;
  transition: background .28s ease;
}
.article-item:last-child {
  border-bottom: none;
}
.article-item:hover {
  background: #f3f8f4;
}
.article-title {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  color: #0e1a12;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.article-date {
  flex: 0 0 auto;
  font-size: 15px;
  color: #8a9388;
  font-weight: 500;
  margin-left: 16px;
}

.planting-card {
  border-radius: 16px;
  border-color: rgba(34, 94, 56, .12);
  box-shadow: 0 6px 16px rgba(26, 71, 43, .10);
}

.crop-item { padding: 14px 0; border-bottom: 1px solid #f0f0f0; }
.crop-item:last-child { border-bottom: none; }
.crop-header { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 8px; }
.crop-name { display: flex; align-items: center; gap: 6px; font-size: 15px; font-weight: 700; color: #06150d; }
.crop-name small { font-size: 13px; color: #888780; font-weight: 500; }
.advice-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 4px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #e8f5ed, #d4f0e0);
  border: 1px solid #178844;
  color: #0f6e56;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all .2s ease;
}
.advice-badge:hover {
  background: linear-gradient(135deg, #178844, #147d66);
  color: #fff;
  border-color: #147d66;
  box-shadow: 0 2px 8px rgba(23, 136, 68, .35);
}
.advice-badge:hover .advice-dot { background: #fff; }
.advice-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #178844;
  animation: advice-pulse 2s ease-in-out infinite;
}
@keyframes advice-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .5; transform: scale(1.3); }
}
.crop-meta { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 6px; font-size: 13px; color: #617069; }
.crop-meta span { display: inline-flex; align-items: center; }

.empty-text { padding: 32px 0; text-align: center; font-size: 14px; color: #999; }

.empty-planting {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 20px 32px;
}
.empty-planting-text {
  font-size: 15px;
  color: #999;
  margin: 0;
}
.empty-planting-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 28px;
  background: var(--farm-green, #178844);
  color: #fff;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
  transition: opacity .2s ease, transform .2s ease;
}
.empty-planting-btn:hover {
  opacity: .88;
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .welcome-card,
  .plan-card,
  .weather-card {
    min-height: auto;
    border-radius: 16px;
  }

  .welcome-card :deep(.el-card__body),
  .plan-card :deep(.el-card__body),
  .weather-card :deep(.el-card__body) {
    padding: 20px;
  }

  .welcome-inner {
    min-height: 0;
    gap: 12px;
  }

  .welcome-name {
    font-size: 22px;
  }

  .welcome-loc {
    font-size: 12px;
    padding: 6px 12px 6px 10px;
  }

  .weather-info,
  .forecast-item {
    font-size: 13px;
  }

  .welcome-stats {
    gap: 8px;
  }

  .plan-inner {
    min-height: 0;
  }

  .plan-list {
    margin-top: 6px;
  }

  .section-title {
    font-size: 22px;
  }
}
</style>
