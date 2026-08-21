<template>
  <div class="crops-page">
    <div v-if="filterLandName" class="filter-banner">
      <span>按地块筛选：<strong>{{ filterLandName }}</strong></span>
      <router-link to="/crops" class="clear-filter">清除筛选 ✕</router-link>
    </div>

    <div class="status-bar">
      <div class="status-tabs">
        <button
          v-for="t in statusTabs"
          :key="t.value"
          :class="['status-bar-item', { active: statusFilter === t.value }]"
          type="button"
          @click="statusFilter = t.value"
        >
          {{ t.label }}
        </button>
      </div>
      <el-button v-if="statusFilter === '种植中'" class="add-btn" :icon="Plus" size="large" @click="openAddDialog">新增作物</el-button>
    </div>

    <div class="crop-list">
      <el-card v-for="c in filteredCrops" :key="c.id" class="crop-card" shadow="never">
        <div class="crop-card-inner">
          <div class="crop-identity">
            <span class="crop-icon">
              <SproutIcon :size="32" variant="dark" />
            </span>
            <div>
              <p class="crop-name">{{ c.name }}</p>
              <p class="crop-variety">{{ c.variety || '-' }}</p>
              <router-link
                v-if="c.advice_count"
                :to="`/crops/${c.id}?advice=1`"
                class="advice-badge"
              >
                <span class="advice-dot"></span>
                专家建议 {{ c.advice_count }} 条
              </router-link>
            </div>
          </div>

          <div class="crop-info-grid">
            <div class="info-item">
              <span class="info-label"># 生产批次</span>
              <strong>{{ c.batch_no }}</strong>
            </div>
            <div class="info-item">
              <span class="info-label">
                <el-icon :size="17"><Location /></el-icon>
                关联地块
              </span>
              <strong>{{ c.land_name }}</strong>
            </div>
            <div class="info-item">
              <span class="info-label">
                <el-icon :size="17"><Calendar /></el-icon>
                种植日期
              </span>
              <strong>{{ c.plant_date || '-' }}</strong>
            </div>
            <div v-if="c.status === '已采收'" class="info-item">
              <span class="info-label">
                <el-icon :size="17"><Select /></el-icon>
                采收日期
              </span>
              <strong>{{ c.harvest_date || '-' }}</strong>
            </div>
          </div>

          <div class="crop-summary">
            <router-link :to="`/crops/${c.id}`" class="record-btn">
              查看农事记录
            </router-link>
          </div>
        </div>
      </el-card>
    </div>
    <div v-if="filteredCrops.length === 0" class="empty-text">暂无作物</div>

    <!-- 新增作物弹窗 -->
    <el-dialog v-model="addDialogVisible" title="新增作物" width="560px" class="form-dialog" :close-on-click-modal="false">
      <el-alert
        v-if="!lands.length"
        type="warning"
        :closable="false"
        title="请先添加地块，再建立作物档案"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-form
        v-else
        ref="addFormRef"
        :model="addForm"
        :rules="addRules"
        label-position="top"
      >
        <el-form-item label="作物名称" prop="name">
          <el-input v-model="addForm.name" placeholder="如：水稻、番茄" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="品种">
          <el-input v-model="addForm.variety" placeholder="如：湘早籼 45 号（选填）" maxlength="50" />
        </el-form-item>
        <el-form-item label="关联地块" prop="land_id">
          <el-select v-model="addForm.land_id" placeholder="请选择地块" filterable style="width: 100%">
            <el-option v-for="l in lands" :key="l.id" :label="`${l.name}（${l.region} · ${l.area}亩）`" :value="l.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="种植时间" prop="plant_date">
          <el-date-picker
            v-model="addForm.plant_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择种植日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <template v-if="!lands.length">
          <el-button type="success" @click="goAddLand">确定</el-button>
        </template>
        <template v-else>
          <el-button @click="addDialogVisible = false">取消</el-button>
          <el-button type="success" :loading="addSubmitting" @click="submitAdd">保存</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { Plus, Location, Calendar, Select } from '@element-plus/icons-vue'
import SproutIcon from '@/components/SproutIcon.vue'

const route = useRoute()
const router = useRouter()
const crops = ref<any[]>([])
const lands = ref<any[]>([])

const filterLandId = computed(() => {
  const v = route.query.land_id
  return v ? Number(v) : null
})

const filterLandName = computed(() => {
  if (!filterLandId.value) return ''
  const land = lands.value.find((l) => l.id === filterLandId.value)
  return land ? land.name : ''
})

const filteredCrops = computed(() => {
  let list = crops.value
  if (filterLandId.value) {
    list = list.filter((c) => c.land_id === filterLandId.value)
  }
  return list.filter((c) => c.status === statusFilter.value)
})

const statusFilter = ref<'种植中' | '已采收'>('种植中')
const statusTabs = [
  { label: '种植中', value: '种植中' as const },
  { label: '已采收', value: '已采收' as const },
]

async function loadCrops() {
  try { crops.value = await api.getCrops() } catch {}
}
async function loadLands() {
  try { lands.value = await api.getLands() } catch {}
}

onMounted(async () => {
  await Promise.all([loadCrops(), loadLands()])
})

function plantedDays(c: any): number {
  if (!c.plant_date) return 0
  const plant = new Date(c.plant_date.replace(/-/g, '/'))
  const now = new Date()
  const diff = Math.floor((now.getTime() - plant.getTime()) / 86400000)
  return Math.max(0, diff)
}

// ========== 新增作物 ==========
const addDialogVisible = ref(false)
const addSubmitting = ref(false)
const addFormRef = ref()
const addForm = reactive({
  name: '',
  variety: '',
  land_id: null as number | null,
  plant_date: '' as string,
})
const addRules = {
  name: [{ required: true, message: '请输入作物名称', trigger: 'blur' }],
  land_id: [{ required: true, message: '请选择关联地块', trigger: 'change' }],
  plant_date: [{ required: true, message: '请选择种植时间', trigger: 'change' }],
}

function resetAddForm() {
  addForm.name = ''
  addForm.variety = ''
  addForm.land_id = null
  addForm.plant_date = ''
  addFormRef.value?.clearValidate()
}

function openAddDialog() {
  if (!lands.value.length) {
    loadLands()
  }
  resetAddForm()
  addDialogVisible.value = true
}

function goAddLand() {
  addDialogVisible.value = false
  router.push('/lands')
}

async function submitAdd() {
  try {
    await addFormRef.value?.validate()
  } catch {
    return
  }
  addSubmitting.value = true
  try {
    const payload: any = {
      name: addForm.name.trim(),
      land_id: addForm.land_id,
      plant_date: addForm.plant_date,
    }
    if (addForm.variety?.trim()) payload.variety = addForm.variety.trim()
    await api.createCrop(payload)
    ElMessage.success('作物已添加')
    addDialogVisible.value = false
    await loadCrops()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败，请重试')
  } finally {
    addSubmitting.value = false
  }
}
</script>

<style scoped>
.crops-page {
  color: #07170e;
}

.add-btn {
  grid-column: 3;
  justify-self: end;
  height: 50px;
  padding: 0 24px;
  border: none;
  border-radius: 12px;
  background: #178844;
  color: #fff;
  font-size: 19px;
  font-weight: 900;
  box-shadow: none;
  flex-shrink: 0;
}

.add-btn:hover,
.add-btn:focus {
  background: #0f783a;
  color: #fff;
}

.crop-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.status-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
}

.status-tabs {
  grid-column: 2;
  justify-self: center;
  display: flex;
  gap: 16px;
}

.status-bar-item {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  min-width: 200px;
  padding: 0 48px;
  border-radius: 18px;
  border: 1px solid #dde6df;
  background: #fff;
  color: #8a978f;
  font-size: 22px;
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.status-bar-item:hover {
  border-color: #b8c9bd;
  color: #4e5e55;
}

.status-bar-item.active {
  background: #eaf6ee;
  border-color: #178844;
  color: #178844;
  font-weight: 900;
  box-shadow: 0 4px 10px rgba(23, 136, 68, .12);
}

.filter-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  margin-bottom: 20px;
  border-radius: 14px;
  background: #e8f5ed;
  border: 1px solid rgba(23, 136, 68, .2);
  font-size: 16px;
  color: #06150d;
  font-weight: 600;
}

.filter-banner strong {
  color: #178844;
  font-weight: 900;
}

.clear-filter {
  font-size: 14px;
  color: #617069;
  text-decoration: none;
  font-weight: 700;
  transition: color .2s;
}

.clear-filter:hover {
  color: #178844;
}

.crop-card {
  border-radius: 22px;
  border: 1px solid rgba(34, 94, 56, .16);
  box-shadow: 0 5px 12px rgba(28, 62, 39, .12);
  overflow: hidden;
}

.crop-card :deep(.el-card__body) {
  padding: 36px 32px;
}

.crop-card-inner {
  display: grid;
  grid-template-columns: 280px minmax(420px, 1fr) 180px;
  align-items: center;
  gap: 32px;
}

.crop-identity {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
}

.crop-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: #e4f2e9;
  color: #178844;
  flex-shrink: 0;
}

.crop-name {
  font-size: 29px;
  line-height: 1.1;
  font-weight: 900;
  margin: 0;
  color: #06150d;
}

.crop-variety {
  font-size: 21px;
  line-height: 1.25;
  color: #4e5e55;
  margin: 9px 0 0;
  font-weight: 500;
}

.advice-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 5px 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, #e8f5ed, #d4f0e0);
  border: 1px solid #178844;
  color: #0f6e56;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all .2s ease;
  width: fit-content;
}

.advice-badge:hover {
  background: linear-gradient(135deg, #178844, #147d66);
  color: #fff;
  border-color: #147d66;
  box-shadow: 0 3px 10px rgba(23, 136, 68, .35);
}

.advice-badge:hover .advice-dot { background: #fff; }

.advice-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #178844;
  animation: advice-pulse 2s ease-in-out infinite;
}

@keyframes advice-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .5; transform: scale(1.3); }
}

.crop-info-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 28px;
}

.info-item {
  min-width: 0;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 12px;
  font-size: 17px;
  color: #53635b;
  font-weight: 500;
}

.info-item strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 22px;
  line-height: 1.25;
  color: #06150d;
  font-weight: 800;
}

.crop-summary {
  min-width: 0;
  padding-left: 16px;
  border-left: 1px solid #e8ede9;
  display: flex;
  align-items: center;
  justify-content: center;
}

.record-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 24px;
  border-radius: 12px;
  border: none;
  background: #eaf6ee;
  color: #0f6e56;
  font-size: 17px;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
  transition: all .18s ease;
}

.record-btn:hover,
.record-btn:focus {
  background: #ddf0e4;
  color: #0a5c48;
}

.empty-text {
  padding: 64px 0;
  text-align: center;
  font-size: 16px;
  color: #7d887f;
}

@media (max-width: 1200px) {
  .crop-card-inner {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 28px;
  }

  .crop-info-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }

  .crop-summary {
    border-left: none;
    padding-left: 0;
    padding-top: 16px;
    border-top: 1px solid #e8ede9;
  }
}

@media (max-width: 768px) {
  .page-title {
    font-size: 28px;
  }

  .crop-card :deep(.el-card__body) {
    padding: 24px 20px;
  }

  .crop-icon {
    width: 58px;
    height: 58px;
    border-radius: 16px;
  }

  .crop-name {
    font-size: 24px;
  }

  .crop-variety {
    font-size: 17px;
  }

  .crop-info-grid {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}

/* ========== 统一圆角规范 ========== */
:deep(.el-input__wrapper) {
  border-radius: 12px;
}

:deep(.el-textarea__inner) {
  border-radius: 12px;
}

:deep(.el-select__wrapper) {
  border-radius: 12px;
}

:deep(.el-button) {
  border-radius: 12px;
}
</style>
