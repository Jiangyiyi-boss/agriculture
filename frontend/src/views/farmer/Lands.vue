<template>
  <div class="lands-page">
    <div class="summary-grid">
      <el-card v-for="s in summaryCards" :key="s.label" class="summary-card" shadow="never">
        <span :class="['summary-icon', s.tone]">
          <el-icon :size="28"><component :is="s.icon" /></el-icon>
        </span>
        <div>
          <p class="summary-label">{{ s.label }}</p>
          <p class="summary-value">{{ s.value }}</p>
        </div>
      </el-card>
    </div>

    <div class="soil-strip" :class="{ expanded: soilExpanded }" @click="soilExpanded = !soilExpanded">
      <div class="soil-strip-header">
        <span class="soil-strip-title">
          <el-icon :size="16"><InfoFilled /></el-icon>
          如何判断土壤类型？
        </span>
        <span class="soil-strip-hint">手感判断法 · 沙土 / 沙壤土 / 壤土 / 粘壤土 / 粘土</span>
        <span class="soil-strip-arrow">{{ soilExpanded ? '收起 ▴' : '展开 ▾' }}</span>
      </div>
      <transition name="soil-expand">
        <div v-show="soilExpanded" class="soil-strip-body">
          <div class="soil-guide-list">
            <div v-for="item in soilGuide" :key="item.name" class="soil-guide-item">
              <span>{{ item.name }}</span>
              <p>{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <div class="land-action-bar">
      <el-button class="add-btn" :icon="Plus" size="large" @click="openAddDialog">新增地块</el-button>
    </div>

    <div class="land-grid">
      <el-card v-for="l in lands" :key="l.id" class="land-card" shadow="never">
        <div class="land-top">
          <div class="land-title-row">
            <span class="land-icon">
              <el-icon :size="30"><MapLocation /></el-icon>
            </span>
            <div>
              <p class="land-name">{{ l.name }}</p>
              <p class="land-region">{{ l.region }}</p>
            </div>
          </div>
          <span :class="['status-pill', { idle: l.status !== '种植中' }]">{{ l.status }}</span>
        </div>

        <div class="land-chips">
          <div class="land-chip">
            <span class="chip-label">面积</span>
            <strong class="chip-value">{{ l.area }} 亩</strong>
          </div>
          <div class="land-chip">
            <span class="chip-label">土壤类型</span>
            <strong class="chip-value">{{ l.soil_type || '未设置' }}</strong>
          </div>
          <div class="land-chip">
            <span class="chip-label">在种批次</span>
            <strong class="chip-value">{{ l.crops }} 个</strong>
          </div>
        </div>

        <div class="land-info-rows">
          <div class="land-info-row">
            <span class="info-label">当前种植</span>
            <div v-if="l.current_crops && l.current_crops.length" class="crop-tags">
              <span v-for="c in l.current_crops" :key="c" class="crop-tag">{{ c }}</span>
            </div>
            <span v-else class="info-empty">暂无种植</span>
          </div>
          <div class="land-info-row">
            <span class="info-label">最近农事</span>
            <span v-if="l.last_work" class="info-value">{{ l.last_work }}</span>
            <span v-else class="info-empty">暂无记录</span>
          </div>
        </div>

        <div class="land-actions">
          <el-button class="edit-btn" @click="openEditDialog(l)">编辑</el-button>
          <el-button class="view-btn" @click="openCropsDialog(l)">查看作物</el-button>
          <el-button class="delete-btn" @click="confirmDelete(l)">删除</el-button>
        </div>
      </el-card>
    </div>
    <div v-if="lands.length === 0" class="empty-text">暂无地块，请先添加地块</div>

    <!-- 新增/编辑地块弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑地块' : '新增地块'" width="520px" class="form-dialog" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="地块名称" prop="name">
          <el-input v-model="form.name" placeholder="如：北坡 1 号地" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="所在地" prop="region">
          <el-input v-model="form.region" placeholder="如：岳麓区雨敞坪镇" maxlength="100" />
        </el-form-item>
        <el-form-item label="面积(亩)" prop="area">
          <el-input-number v-model="form.area" :min="0.1" :max="10000" :step="0.1" :precision="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="土壤类型">
          <el-select v-model="form.soil_type" placeholder="请选择（可选）" clearable style="width: 100%">
            <el-option v-for="t in soilTypeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="success" :loading="submitting" @click="submit">{{ editingId ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>

    <!-- 查看作物弹窗 -->
    <el-dialog v-model="cropsDialogVisible" :title="`${currentLandName} 的作物`" width="640px" class="form-dialog" :close-on-click-modal="false">
      <div v-if="cropsLoading" class="crops-empty">加载中...</div>
      <div v-else-if="landCrops.length" class="land-crop-list">
        <div
          v-for="c in landCrops"
          :key="c.id"
          class="land-crop-item"
          @click="goCropDetail(c.id)"
        >
          <div class="land-crop-identity">
            <span class="land-crop-emoji">{{ cropEmoji(c.name) }}</span>
            <div class="land-crop-info">
              <p class="land-crop-name">{{ c.name }}</p>
              <p class="land-crop-variety">{{ c.variety || '未标注品种' }}</p>
            </div>
          </div>
          <div class="land-crop-meta">
            <span :class="['land-crop-status', c.status === '已采收' ? 'harvested' : 'growing']">{{ c.status }}</span>
            <span class="land-crop-date">{{ c.plant_date || '-' }}</span>
          </div>
        </div>
      </div>
      <div v-else class="crops-empty">该地块暂无作物记录</div>
    </el-dialog>

    <!-- 删除地块确认弹窗 -->
    <el-dialog v-model="deleteConfirmVisible" title="删除地块" width="460px" class="form-dialog confirm-dialog danger" :close-on-click-modal="false">
      <div class="confirm-dialog__body">确定删除地块 <strong>{{ pendingDeleteLand?.name }}</strong> 吗？<br>删除后该地块下的作物和农事记录将无法恢复。</div>
      <template #footer>
        <el-button @click="deleteConfirmVisible = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="executeDelete">确定删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { Plus, MapLocation, Files, ScaleToOriginal, Crop, InfoFilled, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

const lands = ref<any[]>([])
const soilExpanded = ref(false)

const soilGuide = [
  { name: '沙土', desc: '手握不成团，干松' },
  { name: '沙壤土', desc: '手捏勉强成团，一碰就散' },
  { name: '壤土', desc: '手捏成团，不粘手' },
  { name: '粘壤土', desc: '手捏成团，略粘手' },
  { name: '粘土', desc: '手捏成团，很粘手，干了硬邦邦' },
]

const soilTypeOptions = soilGuide.map(s => s.name)

const totalArea = computed(() => {
  const sum = lands.value.reduce((total, land) => total + Number(land.area || 0), 0)
  return Number.isInteger(sum) ? String(sum) : sum.toFixed(1)
})

const totalCropBatches = computed(() =>
  lands.value.reduce((total, land) => total + Number(land.crops || 0), 0)
)

const idleLandCount = computed(() =>
  lands.value.filter(land => land.status !== '种植中').length
)

const summaryCards = computed(() => [
  { label: '地块总数', value: `${lands.value.length} 块`, icon: 'Files', tone: 'green' },
  { label: '总面积', value: `${totalArea.value} 亩`, icon: 'ScaleToOriginal', tone: 'green' },
  { label: '在种作物批次', value: `${totalCropBatches.value} 个`, icon: 'Crop', tone: 'green' },
  { label: '空闲地块', value: `${idleLandCount.value} 块`, icon: 'Files', tone: 'gray' },
])

onMounted(async () => {
  await loadLands()
})

async function loadLands() {
  try { lands.value = await api.getLands() } catch {}
}

// ========== 查看作物弹窗 ==========
const cropsDialogVisible = ref(false)
const cropsLoading = ref(false)
const currentLandName = ref('')
const landCrops = ref<any[]>([])

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

async function openCropsDialog(land: any) {
  currentLandName.value = land.name
  cropsDialogVisible.value = true
  cropsLoading.value = true
  landCrops.value = []
  try {
    const allCrops = await api.getCrops()
    landCrops.value = allCrops.filter((c: any) => c.land_id === land.id)
  } catch {
    ElMessage.error('加载作物失败')
  } finally {
    cropsLoading.value = false
  }
}

function goCropDetail(cropId: number) {
  cropsDialogVisible.value = false
  router.push(`/crops/${cropId}`)
}

// ========== 新增/编辑地块 ==========
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  region: '',
  area: 1.0,
  soil_type: '' as string,
})
const rules = {
  name: [{ required: true, message: '请输入地块名称', trigger: 'blur' }],
  region: [{ required: true, message: '请输入所在地', trigger: 'blur' }],
  area: [{ required: true, message: '请输入面积', trigger: 'blur' }],
}

function resetForm() {
  form.name = ''
  form.region = ''
  form.area = 1.0
  form.soil_type = ''
  editingId.value = null
  formRef.value?.clearValidate()
}

function openAddDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(land: any) {
  resetForm()
  editingId.value = land.id
  form.name = land.name
  form.region = land.region
  form.area = Number(land.area)
  form.soil_type = land.soil_type || ''
  dialogVisible.value = true
}

async function submit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const payload: any = {
      name: form.name.trim(),
      region: form.region.trim(),
      area: Number(form.area),
    }
    if (form.soil_type) payload.soil_type = form.soil_type
    if (editingId.value) {
      await api.updateLand(editingId.value, payload)
      ElMessage.success('地块已更新')
    } else {
      await api.createLand(payload)
      ElMessage.success('地块已添加')
    }
    dialogVisible.value = false
    await loadLands()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败，请重试')
  } finally {
    submitting.value = false
  }
}

// ========== 删除地块 ==========
const deleteConfirmVisible = ref(false)
const pendingDeleteLand = ref<any>(null)
const actionLoading = ref(false)

function confirmDelete(land: any) {
  pendingDeleteLand.value = land
  deleteConfirmVisible.value = true
}

async function executeDelete() {
  if (!pendingDeleteLand.value) return
  actionLoading.value = true
  try {
    await api.deleteLand(pendingDeleteLand.value.id)
    ElMessage.success('地块已删除')
    await loadLands()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败，请重试')
  } finally {
    actionLoading.value = false
    deleteConfirmVisible.value = false
    pendingDeleteLand.value = null
  }
}
</script>

<style scoped>
.lands-page {
  color: #07170e;
}

.land-action-bar {
  display: flex;
  justify-content: flex-end;
  margin: 20px 0 24px;
}

.add-btn {
  height: 50px;
  padding: 0 24px;
  border: none;
  border-radius: 12px;
  background: #178844;
  color: #fff;
  font-size: 19px;
  font-weight: 900;
}

.add-btn:hover,
.add-btn:focus {
  background: #0f783a;
  color: #fff;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 20px;
}

.summary-card {
  border-radius: 20px;
  border: 1px solid rgba(34, 94, 56, .16);
  box-shadow: 0 5px 12px rgba(28, 62, 39, .12);
}

.summary-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 28px 30px;
}

.summary-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  border-radius: 16px;
  background: #e8f2e3;
  color: #1a6d3c;
  flex-shrink: 0;
}

.summary-icon.gray {
  background: #edf2ee;
  color: #617069;
}

.summary-label {
  margin: 0 0 4px;
  font-size: 18px;
  color: #617069;
  font-weight: 700;
}

.summary-value {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 900;
  color: #06150d;
}

/* 折叠式土壤参考 */
.soil-strip {
  margin-bottom: 20px;
  border-radius: 14px;
  background: #f8fbf7;
  border: 1px dashed rgba(34, 94, 56, .2);
  cursor: pointer;
  overflow: hidden;
  transition: background .2s, border-color .2s;
}

.soil-strip:hover {
  background: #f0f7ee;
}

.soil-strip.expanded {
  border-style: solid;
  border-color: rgba(34, 94, 56, .25);
}

.soil-strip-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 24px;
}

.soil-strip-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 900;
  color: #1a6d3c;
  white-space: nowrap;
}

.soil-strip-hint {
  flex: 1;
  font-size: 14px;
  color: #617069;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.soil-strip-arrow {
  font-size: 14px;
  color: #617069;
  font-weight: 700;
  white-space: nowrap;
}

.soil-strip-body {
  padding: 0 24px 18px;
}

.soil-guide-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid rgba(34, 94, 56, .1);
}

.soil-guide-item {
  min-width: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff;
}

.soil-guide-item span {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 13px;
  background: #e5f2e1;
  color: #183824;
  font-size: 15px;
  font-weight: 900;
}

.soil-guide-item p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #617069;
  font-weight: 600;
  line-height: 1.4;
}

.soil-expand-enter-active,
.soil-expand-leave-active {
  transition: opacity .25s ease;
}

.soil-expand-enter-from,
.soil-expand-leave-to {
  opacity: 0;
}

/* 地块卡片 */
.land-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}

.land-card {
  border-radius: 22px;
  border: 1px solid rgba(34, 94, 56, .16);
  box-shadow: 0 5px 12px rgba(28, 62, 39, .12);
  overflow: hidden;
}

.land-card :deep(.el-card__body) {
  padding: 26px 24px 22px;
}

.land-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.land-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.land-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: #e2f1e7;
  color: #178844;
  flex-shrink: 0;
}

.land-name {
  margin: 0;
  font-size: 22px;
  line-height: 1.15;
  font-weight: 900;
  color: #06150d;
}

.land-region {
  margin: 4px 0 0;
  font-size: 14px;
  color: #617069;
  font-weight: 500;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 13px;
  border-radius: 14px;
  background: #e1f1e6;
  color: #178844;
  font-size: 14px;
  font-weight: 900;
  white-space: nowrap;
  flex-shrink: 0;
}

.status-pill.idle {
  background: #edf2ee;
  color: #617069;
}

/* 信息 chips 行 */
.land-chips {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eef2ee;
}

.land-chip {
  padding: 10px 8px;
  border-radius: 12px;
  background: #f8fbf7;
  text-align: center;
}

.chip-label {
  display: block;
  font-size: 13px;
  color: #617069;
  font-weight: 600;
  margin-bottom: 4px;
}

.chip-value {
  display: block;
  font-size: 16px;
  color: #06150d;
  font-weight: 900;
  line-height: 1.2;
}

/* 信息行 */
.land-info-rows {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.land-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-label {
  flex-shrink: 0;
  width: 64px;
  font-size: 14px;
  color: #617069;
  font-weight: 600;
}

.info-value {
  font-size: 14px;
  color: #06150d;
  font-weight: 700;
}

.info-empty {
  font-size: 14px;
  color: #9ca89f;
  font-weight: 500;
}

.crop-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.crop-tag {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 12px;
  background: #e5f2e1;
  color: #178844;
  font-size: 13px;
  font-weight: 700;
}

/* 底部操作 */
.land-actions {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  align-items: center;
  gap: 16px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #eef2ee;
}

.edit-btn {
  height: 40px;
  border-radius: 12px;
  border-color: rgba(34, 94, 56, .16);
  background: #f6fbf7;
  color: #06150d;
  font-size: 16px;
  font-weight: 900;
}

.edit-btn:hover,
.edit-btn:focus {
  border-color: #178844;
  color: #178844;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid #cfe3d3;
  background: #ffffff;
  color: #06150d;
  font-size: 16px;
  font-weight: 900;
  transition: all .18s ease;
}

.view-btn:hover,
.view-btn:focus {
  border-color: #178844;
  color: #178844;
  background: #f6fbf7;
}

.delete-btn {
  height: 40px;
  border-radius: 12px;
  border: 1px solid #fde0e0;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 16px;
  font-weight: 900;
  transition: all .18s ease;
}

.delete-btn:hover,
.delete-btn:focus {
  border-color: #e04444;
  color: #fff;
  background: #e04444;
}

/* 查看作物弹窗 */
.land-crop-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 480px;
  overflow-y: auto;
}

.land-crop-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid #e3ede5;
  background: #fbfdf9;
  cursor: pointer;
  transition: all .18s ease;
}

.land-crop-item:hover {
  border-color: #178844;
  background: #f6fbf7;
  transform: translateY(-1px);
}

.land-crop-identity {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.land-crop-emoji {
  font-size: 32px;
  line-height: 1;
  flex-shrink: 0;
}

.land-crop-info {
  min-width: 0;
}

.land-crop-name {
  margin: 0;
  font-size: 19px;
  font-weight: 900;
  color: #06150d;
  line-height: 1.2;
}

.land-crop-variety {
  margin: 4px 0 0;
  font-size: 14px;
  color: #617069;
  font-weight: 500;
}

.land-crop-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.land-crop-status {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 13px;
  font-size: 13px;
  font-weight: 800;
}

.land-crop-status.growing {
  background: #e1f1e6;
  color: #178844;
}

.land-crop-status.harvested {
  background: #edf2ee;
  color: #617069;
}

.land-crop-date {
  font-size: 13px;
  color: #9ca89f;
  font-weight: 600;
}

.crops-empty {
  padding: 48px 0;
  text-align: center;
  font-size: 16px;
  color: #7d887f;
}

.empty-text {
  padding: 64px 0;
  text-align: center;
  font-size: 16px;
  color: #7d887f;
}

@media (max-width: 1200px) {
  .summary-grid,
  .land-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .soil-guide-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .page-title {
    font-size: 28px;
  }

  .summary-grid,
  .land-grid,
  .soil-guide-list {
    grid-template-columns: 1fr;
  }

  .summary-card :deep(.el-card__body) {
    padding: 22px 22px;
  }

  .summary-icon {
    width: 50px;
    height: 50px;
  }

  .summary-value {
    font-size: 24px;
  }

  .soil-strip {
    flex-wrap: wrap;
  }

  .land-card :deep(.el-card__body) {
    padding: 22px 18px;
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
