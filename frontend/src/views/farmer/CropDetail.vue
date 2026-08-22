<template>
  <div class="crop-detail-page">
    <div class="back-bar">
      <button class="back-btn" type="button" @click="router.push('/crops')">
        <el-icon :size="20"><ArrowLeft /></el-icon>
        返回作物列表
      </button>
    </div>

    <div v-if="crop" class="batch-header-card">
      <div class="batch-header-top">
        <div class="batch-crop-identity">
          <span class="batch-emoji">{{ cropEmoji(crop.name) }}</span>
          <div>
            <h1 class="batch-title">{{ crop.name }}</h1>
            <p class="batch-variety">{{ crop.variety || '未标注品种' }}</p>
          </div>
        </div>
        <div class="batch-actions">
          <el-button v-if="crop.status === '种植中'" class="harvest-btn" :icon="Scissor" size="large" @click="handleHarvest">采收</el-button>
          <el-button v-if="crop.status === '已采收'" class="restore-btn" :icon="RefreshLeft" size="large" @click="handleRestore">恢复种植中</el-button>
          <el-button class="record-btn" :icon="Plus" size="large" @click="openAddDialog">记录作业</el-button>
        </div>
      </div>

      <div class="batch-info-row">
        <div class="batch-info-item">
          <span class="batch-info-label">生产批次</span>
          <strong>{{ crop.batch_no }}</strong>
        </div>
        <div class="batch-info-item">
          <span class="batch-info-label">关联地块</span>
          <strong>{{ crop.land_name }}</strong>
        </div>
        <div class="batch-info-item">
          <span class="batch-info-label">种植日期</span>
          <strong>{{ crop.plant_date || '-' }}</strong>
        </div>
        <div v-if="crop.status === '已采收'" class="batch-info-item">
          <span class="batch-info-label">采收日期</span>
          <strong>{{ crop.harvest_date || '-' }}</strong>
        </div>
        <div class="batch-info-item">
          <span class="batch-info-label">{{ crop.status === '已采收' ? '种植周期' : '已种植' }}</span>
          <strong>{{ plantedDays(crop) }} 天</strong>
        </div>
        <div class="batch-info-item">
          <span class="batch-info-label">上次作业</span>
          <strong>{{ crop.last_work || '暂无记录' }}</strong>
        </div>
      </div>
    </div>

    <!-- 农事记录 -->
    <div v-if="crop" class="records-section">
      <div class="records-title">
        <h2>农事记录</h2>
        <span v-if="works.length" class="records-count">共 {{ works.length }} 条</span>
      </div>

      <div class="filter-bar">
        <button
          v-for="t in workTypes"
          :key="t"
          :class="['filter-pill', { active: filter === t }]"
          type="button"
          @click="filter = t"
        >
          {{ t }}
        </button>
      </div>

      <div v-if="sortedWorks.length" class="timeline">
        <div v-for="w in sortedWorks" :key="w.id" :class="['tl-item', { 'has-advice': w.advices && w.advices.length > 0 }]" :data-work-id="w.id">
          <span :class="['tl-icon', typeColor(w.work_type)]">
            <el-icon :size="20"><component :is="typeIcon(w.work_type)" /></el-icon>
          </span>
          <el-card class="tl-card">
            <div class="tl-header">
              <div class="tl-type-row">
                <span class="tl-type">{{ w.work_type }}</span>
              </div>
              <div class="tl-header-right">
                <span class="tl-date">
                  <el-icon :size="18"><Calendar /></el-icon>
                  {{ w.work_date }}
                </span>
                <div class="tl-actions">
                  <button class="tl-act-btn edit" type="button" title="编辑" @click="openEditDialog(w)">
                    <el-icon :size="16"><Edit /></el-icon>
                  </button>
                  <button class="tl-act-btn del" type="button" title="删除" @click="handleDelete(w)">
                    <el-icon :size="16"><Delete /></el-icon>
                  </button>
                </div>
              </div>
            </div>
            <p class="tl-desc">{{ w.description }}</p>
            <div v-if="parsePhotos(w.photos).length" class="tl-photos">
              <el-image
                v-for="(url, idx) in parsePhotos(w.photos)"
                :key="url"
                :src="url"
                :preview-src-list="parsePhotos(w.photos)"
                :initial-index="idx"
                fit="cover"
                class="tl-photo"
                preview-teleported
              />
            </div>
            <div v-if="w.advices && w.advices.length" class="tl-advice-list">
              <div v-for="a in w.advices" :key="a.expert_id" class="tl-advice" :class="{ 'is-unread': !a.is_read }">
                <el-icon :size="16" color="#16a34a"><ChatLineSquare /></el-icon>
                <div>
                  <span class="advice-label">{{ a.expert_name || '专家' }} 的建议：</span>
                  {{ a.content }}
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>
      <div v-else class="empty-text">
        该批次暂无农事作业记录<br>点击右上角「记录作业」开始记录
      </div>
    </div>

    <div v-if="loading" class="empty-text">加载中...</div>
    <div v-else-if="!crop" class="empty-text">批次不存在或已删除</div>

    <el-dialog v-model="addDialogVisible" :title="dialogTitle" width="600px" class="form-dialog" :close-on-click-modal="false">

      <el-form
        ref="addFormRef"
        :model="addForm"
        :rules="addRules"
        label-position="top"
      >
        <el-form-item label="作业类型" prop="work_type">
          <el-select v-model="addForm.work_type" placeholder="请选择" style="width: 100%">
            <el-option v-for="t in workTypeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="addForm.work_type === '其他'" label="具体类型" prop="custom_type">
          <el-input
            v-model="addForm.custom_type"
            placeholder="如：除草、修剪、中耕"
            maxlength="20"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="作业日期" prop="work_date">
          <el-date-picker
            v-model="addForm.work_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择作业日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="作业描述" prop="description">
          <el-input
            v-model="addForm.description"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="本次作业的详细情况，如：施用复合肥 15kg，使用小型旋耕机"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="作业照片">
          <div class="upload-area">
            <div v-for="(url, idx) in photoUrls" :key="url" class="upload-thumb">
              <el-image :src="url" :preview-src-list="photoUrls" :initial-index="idx" fit="cover" class="thumb-img" />
              <button class="thumb-remove" type="button" @click="photoUrls.splice(idx, 1)">
                <el-icon :size="14"><Close /></el-icon>
              </button>
            </div>
            <label v-if="photoUrls.length < 6" class="upload-btn" :class="{ uploading: uploadingPhoto }">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                class="upload-input"
                @change="handlePhotoUpload($event)"
              />
              <el-icon :size="28" v-if="!uploadingPhoto"><Plus /></el-icon>
              <span v-if="!uploadingPhoto">添加照片</span>
            </label>
          </div>
          <div class="upload-hint">最多上传 6 张，支持 jpg/png/webp，单张不超过 10MB</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="addSubmitting" @click="submitAdd">{{ editingWork ? '更新' : '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- 采收确认弹窗（统一圆角风格） -->
    <el-dialog v-model="harvestConfirmVisible" title="采收确认" width="460px" class="form-dialog confirm-dialog" :close-on-click-modal="false">
      <div class="confirm-dialog__body">{{ harvestConfirmText }}</div>
      <template #footer>
        <el-button @click="harvestConfirmVisible = false">取消</el-button>
        <el-button type="success" :loading="actionLoading" @click="confirmHarvest">确认采收</el-button>
      </template>
    </el-dialog>

    <!-- 恢复种植中确认弹窗 -->
    <el-dialog v-model="restoreConfirmVisible" title="恢复确认" width="460px" class="form-dialog confirm-dialog" :close-on-click-modal="false">
      <div class="confirm-dialog__body">{{ restoreConfirmText }}</div>
      <template #footer>
        <el-button @click="restoreConfirmVisible = false">取消</el-button>
        <el-button type="success" :loading="actionLoading" @click="confirmRestore">确认恢复</el-button>
      </template>
    </el-dialog>

    <!-- 删除作业确认弹窗 -->
    <el-dialog v-model="deleteConfirmVisible" title="删除确认" width="460px" class="form-dialog confirm-dialog danger" :close-on-click-modal="false">
      <div class="confirm-dialog__body" v-html="deleteConfirmText"></div>
      <template #footer>
        <el-button @click="deleteConfirmVisible = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="confirmDelete">确定删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import {
  Plus, Calendar, ChatLineSquare, Edit, Delete, ArrowLeft,
  Tools, Sunny, Box, Aim, Drizzling, Scissor, Ticket, Close, RefreshLeft,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const crop = ref<any>(null)
const works = ref<any[]>([])
const loading = ref(true)

const workTypes = ['全部', '整地', '播种', '施肥', '打药', '灌溉', '其他']
const workTypeOptions = workTypes.filter(t => t !== '全部')
const presetWorkTypes = ['整地', '播种', '施肥', '打药', '灌溉', '采收']
const filter = ref('全部')

const typeIcons: Record<string, string> = {
  整地: 'Tools', 播种: 'Sunny', 施肥: 'Box', 打药: 'Aim', 灌溉: 'Drizzling', 采收: 'Scissor', 其他: 'Ticket',
}
function typeIcon(t: string) { return typeIcons[t] || 'Ticket' }

const typeColors: Record<string, string> = {
  整地: 'yellow', 播种: 'green', 施肥: 'yellow', 打药: 'red', 灌溉: 'cyan', 采收: 'teal', 其他: 'gray',
}
function typeColor(t: string) { return typeColors[t] || 'gray' }

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

function parsePhotos(photos: string | null | undefined): string[] {
  if (!photos) return []
  return photos.split(',').map(u => u.trim()).filter(Boolean)
}

function plantedDays(c: any): number {
  if (!c.plant_date) return 0
  const plant = new Date(c.plant_date.replace(/-/g, '/'))
  // 已采收：用采收日期 - 种植日期（固定周期，不再随今天变化）
  // 种植中：用今天 - 种植日期
  const end = (c.status === '已采收' && c.harvest_date)
    ? new Date(c.harvest_date.replace(/-/g, '/'))
    : new Date()
  const diff = Math.floor((end.getTime() - plant.getTime()) / 86400000)
  return Math.max(0, diff)
}

// 农事记录筛选
const sortedWorks = computed(() => {
  const list = filter.value === '全部'
    ? [...works.value]
    : filter.value === '其他'
      ? works.value.filter(w => !presetWorkTypes.includes(w.work_type))
      : works.value.filter(w => w.work_type === filter.value)
  return list.sort((a, b) => (a.work_date || '').localeCompare(b.work_date || ''))
})

async function loadData() {
  const batchId = Number(route.params.id)
  if (!batchId) return
  loading.value = true
  try {
    // 进入作物详情时，先标记专家建议为已读，再加载详情数据
    // 注意：必须 await 标记完成，否则返回列表时列表接口可能读到的还是未读状态
    try {
      await api.markCropAdviceRead(batchId)
    } catch (e: any) {
      console.error('标记建议已读失败:', e?.response?.status, e?.response?.data)
    }
    const [allCrops, batchWorks] = await Promise.all([
      api.getCrops(),
      api.getFarmWorksByBatch(batchId),
    ])
    crop.value = allCrops.find((c: any) => c.id === batchId) || null
    works.value = batchWorks
    // 如果带 ?advice=1 参数，滚动到第一条有专家建议的记录
    if (route.query.advice) {
      await nextTick()
      const firstAdviceEl = document.querySelector('.tl-item.has-advice')
      if (firstAdviceEl) {
        firstAdviceEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(() => route.params.id, loadData)

// ========== 记录/编辑作业 ==========
const addDialogVisible = ref(false)
const addSubmitting = ref(false)
const addFormRef = ref()
const editingWork = ref<any>(null)
const dialogTitle = computed(() => editingWork.value ? '编辑作业' : '记录作业')

const addForm = reactive({
  work_type: '' as string,
  custom_type: '' as string,
  work_date: '' as string,
  description: '',
})
const photoUrls = ref<string[]>([])
const uploadingPhoto = ref(false)
const addRules = {
  work_type: [{ required: true, message: '请选择作业类型', trigger: 'change' }],
  work_date: [{ required: true, message: '请选择作业日期', trigger: 'change' }],
  description: [{ required: true, message: '请输入作业描述', trigger: 'blur' }],
}

function resetAddForm() {
  addForm.work_type = ''
  addForm.custom_type = ''
  addForm.work_date = new Date().toISOString().slice(0, 10)
  addForm.description = ''
  photoUrls.value = []
  addFormRef.value?.clearValidate()
}

function openAddDialog() {
  editingWork.value = null
  resetAddForm()
  addDialogVisible.value = true
}

function openEditDialog(work: any) {
  editingWork.value = work
  // 若原作业类型不在预设列表中，视为自定义类型，下拉显示"其他"并预填自定义值
  if (presetWorkTypes.includes(work.work_type) || work.work_type === '其他') {
    addForm.work_type = work.work_type
    addForm.custom_type = ''
  } else {
    addForm.work_type = '其他'
    addForm.custom_type = work.work_type
  }
  addForm.work_date = work.work_date
  addForm.description = work.description || ''
  photoUrls.value = work.photos ? work.photos.split(',').filter((u: string) => u.trim()) : []
  addFormRef.value?.clearValidate()
  addDialogVisible.value = true
}

async function handlePhotoUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || !input.files.length) return
  const file = input.files[0]
  // 前端校验
  const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  if (!allowed.includes(file.type)) {
    ElMessage.warning('仅支持 jpg/png/webp 格式')
    input.value = ''
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('单张图片不能超过 10MB')
    input.value = ''
    return
  }
  uploadingPhoto.value = true
  try {
    const res = await api.uploadWorkPhoto(file)
    photoUrls.value.push(res.url)
  } catch {
    ElMessage.error('图片上传失败，请重试')
  } finally {
    uploadingPhoto.value = false
    input.value = ''
  }
}

async function submitAdd() {
  try {
    await addFormRef.value?.validate()
  } catch {
    return
  }
  // 选了"其他"且填写了自定义类型时，用自定义值作为最终作业类型
  const finalWorkType = addForm.work_type === '其他' && addForm.custom_type.trim()
    ? addForm.custom_type.trim()
    : addForm.work_type
  addSubmitting.value = true
  try {
    if (editingWork.value) {
      await api.updateFarmWork(editingWork.value.id, {
        work_type: finalWorkType,
        work_date: addForm.work_date,
        description: addForm.description.trim(),
        photos: photoUrls.value.length ? photoUrls.value.join(',') : null,
      })
      ElMessage.success('作业已更新')
    } else {
      await api.createFarmWork({
        work_type: finalWorkType,
        work_date: addForm.work_date,
        land_id: crop.value.land_id,
        batch_id: crop.value.id,
        description: addForm.description.trim(),
        photos: photoUrls.value.length ? photoUrls.value.join(',') : null,
      })
      ElMessage.success('作业记录已保存')
    }
    addDialogVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败，请重试')
  } finally {
    addSubmitting.value = false
  }
}

// ========== 确认弹窗（统一风格） ==========
const harvestConfirmVisible = ref(false)
const harvestConfirmText = ref('')
const restoreConfirmVisible = ref(false)
const restoreConfirmText = ref('')
const deleteConfirmVisible = ref(false)
const deleteConfirmText = ref('')
const pendingDeleteWork = ref<any>(null)
const actionLoading = ref(false)

async function handleDelete(work: any) {
  pendingDeleteWork.value = work
  deleteConfirmText.value = work.advice
    ? `此条作业包含专家指导建议，删除后建议将一并消失，<span class="danger-text">无法恢复</span>。\n\n确定删除这条【${work.work_type}】作业吗？`
    : `确定删除这条【<span class="danger-text">${work.work_type}</span>】作业吗？删除后无法恢复。`
  deleteConfirmVisible.value = true
}

async function confirmDelete() {
  if (!pendingDeleteWork.value) return
  actionLoading.value = true
  try {
    await api.deleteFarmWork(pendingDeleteWork.value.id)
    ElMessage.success('已删除')
    deleteConfirmVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败，请重试')
  } finally {
    actionLoading.value = false
  }
}

async function handleHarvest() {
  harvestConfirmText.value = `确认采收「${crop.value.name}」吗？\n\n采收后该作物的农事记录将不再更新，关联地块若无其他种植中作物将自动释放为空闲。`
  harvestConfirmVisible.value = true
}

async function confirmHarvest() {
  actionLoading.value = true
  try {
    await api.harvestCrop(crop.value.id)
    ElMessage.success('采收成功')
    harvestConfirmVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '采收失败，请重试')
  } finally {
    actionLoading.value = false
  }
}

async function handleRestore() {
  restoreConfirmText.value = `确认将「${crop.value.name}」恢复为种植中吗？\n\n地块状态将恢复为种植中，您可以重新记录农事或再次采收。`
  restoreConfirmVisible.value = true
}

async function confirmRestore() {
  actionLoading.value = true
  try {
    await api.restoreCrop(crop.value.id)
    ElMessage.success('已恢复种植中')
    restoreConfirmVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '恢复失败，请重试')
  } finally {
    actionLoading.value = false
  }
}
</script>

<style scoped>
.crop-detail-page {
  color: #07170e;
}

.back-bar {
  margin-bottom: 20px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 10px;
  background: #edf4e8;
  color: #178844;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.back-btn:hover {
  background: #e1eedf;
}

.batch-header-card {
  padding: 32px 34px;
  border-radius: 22px;
  background: linear-gradient(135deg, #e8f5e9 0%, #f0f9f0 100%);
  border: 1px solid rgba(34, 94, 56, .14);
  box-shadow: 0 5px 14px rgba(28, 62, 39, .1);
  margin-bottom: 24px;
}

.batch-header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 28px;
}

.batch-crop-identity {
  display: flex;
  align-items: center;
  gap: 18px;
}

.batch-emoji {
  font-size: 48px;
  line-height: 1;
}

.batch-title {
  font-size: 32px;
  font-weight: 900;
  margin: 0;
  color: #06150d;
  line-height: 1.1;
}

.batch-variety {
  font-size: 20px;
  color: #4e5e55;
  margin: 8px 0 0;
  font-weight: 500;
}

.record-btn {
  height: 50px;
  padding: 0 24px;
  border: none;
  border-radius: 12px;
  background: #178844;
  color: #fff;
  font-size: 19px;
  font-weight: 900;
  box-shadow: none;
}

.record-btn:hover,
.record-btn:focus {
  background: #0f783a;
  color: #fff;
}

.batch-actions {
  display: flex;
  gap: 12px;
}

.harvest-btn {
  height: 50px;
  padding: 0 24px;
  border: none;
  border-radius: 12px;
  background: #f97316;
  color: #fff;
  font-size: 19px;
  font-weight: 900;
  box-shadow: none;
}

.harvest-btn:hover,
.harvest-btn:focus {
  background: #ea6a0b;
  color: #fff;
}

.restore-btn {
  height: 50px;
  padding: 0 24px;
  border: none;
  border-radius: 12px;
  background: #6b7280;
  color: #fff;
  font-size: 19px;
  font-weight: 900;
  box-shadow: none;
}

.restore-btn:hover,
.restore-btn:focus {
  background: #4b5563;
  color: #fff;
}

.batch-info-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 24px;
}

.batch-info-item {
  min-width: 0;
}

.batch-info-label {
  display: block;
  margin-bottom: 8px;
  font-size: 15px;
  color: #53635b;
  font-weight: 500;
}

.batch-info-item strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 20px;
  color: #06150d;
  font-weight: 800;
}

/* ========== 农事记录 ========== */
.records-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.records-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.records-title h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 900;
  color: #06150d;
}

.records-count {
  font-size: 15px;
  color: #888780;
  font-weight: 500;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}

.filter-pill {
  height: 44px;
  padding: 0 20px;
  border: none;
  border-radius: 22px;
  background: #edf4e8;
  color: #06150d;
  font-size: 17px;
  font-weight: 900;
  line-height: 44px;
  cursor: pointer;
  transition: all .18s ease;
}

.filter-pill:hover {
  background: #e1eedf;
  color: #178844;
}

.filter-pill.active {
  background: #178844;
  color: #fff;
}

.timeline {
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 34px;
  top: 34px;
  bottom: 28px;
  width: 2px;
  background: #d8e5dc;
}

.tl-item {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.tl-icon {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tl-icon.green { background: #ddf2e4; color: #178844; }
.tl-icon.teal { background: #dff3ec; color: #147d66; }
.tl-icon.red { background: #f9dddd; color: #f04444; }
.tl-icon.orange { background: #faead9; color: #f97316; }
.tl-icon.yellow { background: #f8efd4; color: #d59a00; }
.tl-icon.cyan { background: #d9f3f5; color: #07aeca; }
.tl-icon.gray { background: #edf1ed; color: #7d887f; }

.tl-card {
  flex: 1;
  border-radius: 18px;
  border: 1px solid rgba(34, 94, 56, .16);
  box-shadow: 0 5px 12px rgba(28, 62, 39, .12);
}

/* 有专家建议的记录高亮 */
.tl-item.has-advice .tl-card {
  border: 2px solid #178844;
  box-shadow: 0 4px 16px rgba(23, 136, 68, .2);
}

.tl-card :deep(.el-card__body) {
  padding: 30px 26px 24px;
}

.tl-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}

.tl-type-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tl-type {
  font-size: 24px;
  line-height: 1;
  font-weight: 900;
  color: #06150d;
}

.tl-date {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  color: #45534c;
  font-weight: 500;
}

.tl-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tl-actions {
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity .2s ease;
}

.tl-item:hover .tl-actions {
  opacity: 1;
}

.tl-act-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 10px;
  background: #edf4e8;
  color: #178844;
  cursor: pointer;
  transition: all .18s ease;
}

.tl-act-btn:hover {
  transform: translateY(-1px);
}

.tl-act-btn.edit:hover {
  background: #178844;
  color: #fff;
}

.tl-act-btn.del {
  background: #fce8e8;
  color: #e04444;
}

.tl-act-btn.del:hover {
  background: #e04444;
  color: #fff;
}

.tl-desc {
  margin: 24px 0 0;
  font-size: 21px;
  line-height: 1.6;
  color: #07170e;
  font-weight: 500;
}

/* 时间线照片 */
.tl-photos {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.tl-photo {
  width: 96px;
  height: 96px;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid rgba(34, 94, 56, .12);
}

.tl-photo :deep(.el-image__inner) {
  width: 100%;
  height: 100%;
  transition: transform .25s ease;
}

.tl-photo:hover :deep(.el-image__inner) {
  transform: scale(1.08);
}

.tl-advice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 24px;
}
.tl-advice {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 20px;
  border-radius: 14px;
  background: #edf8f0;
  font-size: 19px;
  line-height: 1.45;
  color: #142118;
}
/* 未读建议：轻量高亮，提示农户查看 */
.tl-advice.is-unread {
  background: #fff7e0;
  box-shadow: inset 0 0 0 1px #f5d785;
}

.advice-label {
  font-weight: 900;
  color: #178844;
}

.empty-text {
  padding: 64px 0;
  text-align: center;
  font-size: 16px;
  color: #7d887f;
  line-height: 1.8;
}

/* ========== 对话框图片上传 ========== */
.upload-area {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.upload-thumb {
  position: relative;
  width: 88px;
  height: 88px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(34, 94, 56, .12);
}

.thumb-img {
  width: 100%;
  height: 100%;
}

.thumb-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  cursor: pointer;
  transition: background .18s ease;
}

.thumb-remove:hover {
  background: rgba(240, 68, 68, .85);
}

.upload-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 88px;
  height: 88px;
  border-radius: 10px;
  border: 2px dashed #c3d5c9;
  background: #f7faf7;
  color: #7d887f;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all .18s ease;
}

.upload-btn:hover {
  border-color: #178844;
  color: #178844;
  background: #edf8f0;
}

.upload-btn.uploading {
  opacity: .5;
  pointer-events: none;
}

.upload-input {
  display: none;
}

.upload-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #9aa8a0;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .batch-header-card {
    padding: 24px 20px;
  }

  .batch-emoji {
    font-size: 38px;
  }

  .batch-title {
    font-size: 26px;
  }

  .batch-variety {
    font-size: 17px;
  }

  .batch-info-row {
    grid-template-columns: 1fr 1fr;
    gap: 18px;
  }

  .batch-info-item strong {
    font-size: 17px;
  }

  .records-title h2 {
    font-size: 20px;
  }

  .filter-pill {
    height: 40px;
    padding: 0 18px;
    font-size: 16px;
    line-height: 40px;
  }

  .timeline::before {
    left: 25px;
  }

  .tl-item {
    gap: 14px;
  }

  .tl-icon {
    width: 52px;
    height: 52px;
  }

  .tl-card :deep(.el-card__body) {
    padding: 22px 18px;
  }

  .tl-actions {
    opacity: 1;
  }

  .tl-act-btn {
    width: 30px;
    height: 30px;
  }

  .tl-type {
    font-size: 21px;
  }

  .tl-date,
  .tl-desc {
    font-size: 16px;
  }

  .tl-advice {
    font-size: 14px;
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
