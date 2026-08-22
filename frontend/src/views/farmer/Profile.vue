<template>
  <div class="profile-page">
    <div class="profile-layout">
      <el-card class="profile-hero" shadow="never">
        <div class="profile-cover"></div>
        <div class="profile-main">
          <div class="avatar">
            <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="用户头像" />
            <span v-else>{{ auth.user?.name?.charAt(0) || '陈' }}</span>
          </div>
          <h1>{{ auth.user?.name || '陈志强' }}</h1>

          <div class="profile-info-grid">
            <div class="profile-info">
              <span class="info-label"><el-icon :size="19"><Phone /></el-icon>手机号</span>
              <strong>{{ maskedPhone }}</strong>
            </div>
            <div class="profile-info">
              <span class="info-label"><el-icon :size="19"><Location /></el-icon>所在地区</span>
              <strong>{{ auth.user?.region || '未设置' }}</strong>
            </div>
          </div>
        </div>

      </el-card>

      <div class="profile-actions">
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#178844" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div class="stat-card-number">{{ stats.landCount }}</div>
            <div class="stat-card-label">我的地块</div>
            <div class="stat-card-sub" v-if="stats.landArea">{{ stats.landArea }} 亩</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#178844" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c4-4 8-7.5 8-12a8 8 0 1 0-16 0c0 4.5 4 8 8 12z"/><circle cx="12" cy="10" r="3"/></svg>
            </div>
            <div class="stat-card-number">{{ stats.growingCrops }}</div>
            <div class="stat-card-label">我的作物</div>
            <div class="stat-card-sub" v-if="stats.harvestedCrops">{{ stats.harvestedCrops }} 已采收</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#178844" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </div>
            <div class="stat-card-number">{{ stats.aiCount + stats.expertCount }}</div>
            <div class="stat-card-label">我的问答</div>
            <div class="stat-card-sub">AI {{ stats.aiCount }} · 专家 {{ stats.expertCount }}</div>
          </div>
        </div>

        <!-- 菜单列表 -->
        <el-card class="menu-card" shadow="never">
          <button type="button" class="menu-item" @click="router.push('/history')">
            <span>浏览历史</span>
            <el-icon :size="24"><ArrowRight /></el-icon>
          </button>
          <button type="button" class="menu-item" @click="openPwdDialog">
            <span>修改密码</span>
            <el-icon :size="24"><ArrowRight /></el-icon>
          </button>
          <button type="button" class="menu-item" @click="openEdit">
            <span>账号设置</span>
            <el-icon :size="24"><ArrowRight /></el-icon>
          </button>
        </el-card>

      </div>
    </div>

    <el-dialog v-model="showEdit" title="账号设置" width="620px" class="edit-dialog form-dialog" :close-on-click-modal="false">
      <div class="edit-avatar-row">
        <div class="edit-avatar">
          <img v-if="form.avatar" :src="form.avatar" alt="用户头像" />
          <span v-else>{{ form.name?.charAt(0) || '农' }}</span>
        </div>
        <div class="avatar-actions">
          <strong>头像</strong>
          <p>支持 jpg、png、webp，图片不超过 3MB</p>
          <el-upload
            accept="image/*"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleAvatarChange"
          >
            <button class="avatar-upload-btn" type="button" :disabled="avatarUploading">
              <el-icon :size="17"><Camera /></el-icon>
              {{ avatarUploading ? '上传中' : '更换头像' }}
            </button>
          </el-upload>
        </div>
      </div>

      <el-form label-position="top" class="edit-form">
        <el-form-item label="用户名">
          <el-input v-model="form.name" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input :model-value="maskedPhone" disabled />
        </el-form-item>
        <el-form-item label="所在地区">
          <div class="region-picker-row">
            <el-cascader
              ref="regionCascaderRef"
              v-model="form.regionPath"
              :class="{ 'region-cascader--filled': form.region && !form.regionPath.length }"
              :props="regionCascaderProps"
              :placeholder="regionCascaderPlaceholder"
              clearable
              filterable
              @change="handleRegionCascaderChange"
            />
            <button class="locate-region-btn" type="button" :disabled="locatingRegion" @click="handleLocateRegion">
              <el-icon :size="17"><Aim /></el-icon>
              {{ locatingRegion ? '定位中' : '定位' }}
            </button>
          </div>
          <p class="region-current">当前所在地：{{ form.region || '未设置' }}</p>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button type="success" :loading="saving" @click="handleSave">保存修改</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPwdDialog" title="修改密码" width="460px" class="edit-dialog form-dialog" :close-on-click-modal="false">
      <el-form class="pwd-form" autocomplete="off">
        <el-form-item>
          <el-input v-model="pwdForm.oldPassword" type="password" show-password placeholder="请输入旧密码" autocomplete="current-password" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="新密码（6-20位，含字母和数字）" autocomplete="new-password" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPwdDialog = false">取消</el-button>
        <el-button type="primary" :loading="changingPwd" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { Aim, ArrowRight, Camera, Location, Phone } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const auth = useAuthStore()
const router = useRouter()
const saving = ref(false)
const showEdit = ref(false)
const avatarUploading = ref(false)
const locatingRegion = ref(false)
const regionCascaderRef = ref<any>()

const form = reactive({
  name: auth.user?.name || '',
  avatar: auth.user?.avatar || '',
  region: auth.user?.region || '',
  regionPath: [] as string[],
})

const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const showPwdDialog = ref(false)
const changingPwd = ref(false)

// 种植数据统计
const stats = reactive({
  landCount: 0,
  landArea: '' as string | number,
  growingCrops: 0,
  harvestedCrops: 0,
  aiCount: 0,
  expertCount: 0,
})

onMounted(async () => {
  const [landsRes, cropsRes, aiRes, consultRes] = await Promise.allSettled([
    api.getLands(),
    api.getCrops(),
    api.getAIConversations(),
    api.getMyConsultations(),
  ])

  if (landsRes.status === 'fulfilled') {
    const lands = landsRes.value || []
    stats.landCount = lands.length
    const sum = lands.reduce((total: number, land: any) => total + Number(land.area || 0), 0)
    stats.landArea = sum ? Math.round(sum * 10) / 10 : ''
  }
  if (cropsRes.status === 'fulfilled') {
    const crops = cropsRes.value || []
    stats.growingCrops = crops.filter((c: any) => c.status === '种植中').length
    stats.harvestedCrops = crops.filter((c: any) => c.status === '已采收').length
  }
  if (aiRes.status === 'fulfilled') {
    stats.aiCount = (aiRes.value || []).length
  }
  if (consultRes.status === 'fulfilled') {
    stats.expertCount = (consultRes.value || []).length
  }
})

const regionCascaderPlaceholder = computed(() => form.region || '请选择省 / 市 / 区县')

const regionCascaderProps = {
  lazy: true,
  emitPath: true,
  checkStrictly: false,
  value: 'value',
  label: 'label',
  lazyLoad: loadRegionOptions,
}

const provinceOrder = [
  '北京市', '天津市', '河北省', '山西省', '内蒙古自治区',
  '辽宁省', '吉林省', '黑龙江省', '上海市', '江苏省',
  '浙江省', '安徽省', '福建省', '江西省', '山东省',
  '河南省', '湖北省', '湖南省', '广东省', '广西壮族自治区',
  '海南省', '重庆市', '四川省', '贵州省', '云南省',
  '西藏自治区', '陕西省', '甘肃省', '青海省', '宁夏回族自治区',
  '新疆维吾尔自治区',
]

const excludedProvinceNames = new Set(['香港特别行政区', '澳门特别行政区', '台湾省'])
const pinyinCollator = new Intl.Collator('zh-Hans-CN-u-co-pinyin', {
  numeric: true,
  sensitivity: 'base',
})

const maskedPhone = computed(() => {
  const phone = auth.user?.phone || ''
  if (!phone) return '未设置'
  return phone.replace(/^(\d{3})\d{4}(\d{4})$/, '$1****$2')
})

function openEdit() {
  resetForm()
  showEdit.value = true
}

function resetForm() {
  form.name = auth.user?.name || ''
  form.avatar = auth.user?.avatar || ''
  form.region = auth.user?.region || ''
  form.regionPath = []
}

function openPwdDialog() {
  pwdForm.oldPassword = ''
  pwdForm.newPassword = ''
  pwdForm.confirmPassword = ''
  showPwdDialog.value = true
}

async function handleChangePassword() {
  if (!pwdForm.oldPassword || !pwdForm.newPassword || !pwdForm.confirmPassword) {
    ElMessage.warning('请完整填写旧密码、新密码和确认密码')
    return
  }
  if (pwdForm.newPassword !== pwdForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changingPwd.value = true
  try {
    await api.changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    ElMessage.success('密码已修改')
    showPwdDialog.value = false
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  } finally {
    changingPwd.value = false
  }
}

function loadAmapDistrict() {
  if (window.AMap) return Promise.resolve(window.AMap)
  if (window.__amapLoader) return window.__amapLoader

  const key = import.meta.env.VITE_AMAP_WEB_KEY
  const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE
  if (!key || !securityCode) return Promise.reject(new Error('未配置高德地图 JS Key'))

  window._AMapSecurityConfig = { securityJsCode: securityCode }
  window.__amapLoader = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.async = true
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}&plugin=AMap.DistrictSearch,AMap.Geolocation,AMap.Geocoder`
    script.onload = () => resolve(window.AMap)
    script.onerror = () => reject(new Error('高德地图 JS SDK 加载失败'))
    document.head.appendChild(script)
  })
  return window.__amapLoader
}

function amapPlugin(AMap: any, names: string[]) {
  return new Promise<void>((resolve, reject) => {
    AMap.plugin(names, () => resolve())
    window.setTimeout(() => reject(new Error('高德地图插件加载超时')), 10000)
  })
}

function compareByPinyin(left: string, right: string) {
  return pinyinCollator.compare(left, right)
}

function getDistrictGroup(name: string) {
  if (name.includes('区')) return 0
  if (name.endsWith('市')) return 1
  if (name.includes('县') || name.includes('旗')) return 2
  return 3
}

function sortRegionChildren(children: any[], level: number) {
  const list = [...children]
  if (level === 0) {
    return list
      .filter((item: any) => !excludedProvinceNames.has(item.name))
      .sort((left: any, right: any) => {
        const leftIndex = provinceOrder.indexOf(left.name)
        const rightIndex = provinceOrder.indexOf(right.name)
        const safeLeftIndex = leftIndex === -1 ? provinceOrder.length : leftIndex
        const safeRightIndex = rightIndex === -1 ? provinceOrder.length : rightIndex
        return safeLeftIndex - safeRightIndex || compareByPinyin(left.name, right.name)
      })
  }

  if (level === 1) {
    return list.sort((left: any, right: any) => compareByPinyin(left.name, right.name))
  }

  return list.sort((left: any, right: any) => {
    const leftGroup = getDistrictGroup(left.name)
    const rightGroup = getDistrictGroup(right.name)
    return leftGroup - rightGroup || compareByPinyin(left.name, right.name)
  })
}

async function loadRegionOptions(node: any, resolve: (options: any[]) => void) {
  const level = node.level || 0
  if (level >= 3) {
    resolve([])
    return
  }

  try {
    const AMap = await loadAmapDistrict()
    await amapPlugin(AMap, ['AMap.DistrictSearch'])
    const districtSearch = new AMap.DistrictSearch({
      subdistrict: 1,
      extensions: 'base',
      level: level === 0 ? 'country' : level === 1 ? 'province' : 'city',
    })

    const keyword = level === 0 ? '中国' : node.value
    districtSearch.search(keyword, (status: string, result: any) => {
      const root = result?.districtList?.[0]
      const children = root?.districtList || []
      resolve(sortRegionChildren(children, level).map((item: any) => ({
        value: item.adcode || item.name,
        label: item.name,
        leaf: level >= 2,
      })))
    })
  } catch {
    ElMessage.error('省市区数据加载失败')
    resolve([])
  }
}

function handleRegionCascaderChange() {
  const node = regionCascaderRef.value?.getCheckedNodes?.()?.[0]
  const labels = node?.pathLabels || []
  if (labels.length) {
    form.region = labels.join(' ')
  }
}

function getCurrentAmapPosition(AMap: any) {
  return new Promise<{ lng: number; lat: number }>((resolve, reject) => {
    const geolocation = new AMap.Geolocation({
      enableHighAccuracy: true,
      timeout: 10000,
      zoomToAccuracy: false,
      showButton: false,
      showMarker: false,
      showCircle: false,
    })

    geolocation.getCurrentPosition((status: string, result: any) => {
      if (status !== 'complete') {
        reject(new Error(result?.message || '定位失败，请检查浏览器定位权限'))
        return
      }

      const lng = result?.position?.lng ?? result?.position?.getLng?.()
      const lat = result?.position?.lat ?? result?.position?.getLat?.()
      if (typeof lng !== 'number' || typeof lat !== 'number') {
        reject(new Error('无法获取当前位置经纬度'))
        return
      }

      resolve({ lng, lat })
    })
  })
}

function getCurrentAmapAddress(AMap: any, lng: number, lat: number) {
  return new Promise<{ province: string; city: string; district: string }>((resolve, reject) => {
    const geocoder = new AMap.Geocoder()
    geocoder.getAddress([lng, lat], (status: string, result: any) => {
      const address = result?.regeocode?.addressComponent
      if (status !== 'complete' || !address) {
        reject(new Error('当前位置解析失败'))
        return
      }

      resolve({
        province: address.province || '',
        city: Array.isArray(address.city) ? '' : (address.city || ''),
        district: Array.isArray(address.district) ? '' : (address.district || ''),
      })
    })
  })
}

function getCurrentAmapCity(AMap: any) {
  return new Promise<{ province: string; city: string; district: string }>((resolve, reject) => {
    const citySearch = new AMap.CitySearch()
    citySearch.getLocalCity((status: string, result: any) => {
      if (status !== 'complete' || result?.info !== 'OK') {
        reject(new Error(result?.info || '当前城市识别失败'))
        return
      }

      resolve({
        province: result.province || '',
        city: result.city || '',
        district: '',
      })
    })
  })
}

function getBrowserPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('当前浏览器不支持定位'))
      return
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 10 * 60 * 1000,
    })
  })
}

function convertToAmapLngLat(AMap: any, lng: number, lat: number) {
  // 浏览器原生定位返回 WGS-84 坐标，高德使用 GCJ-02，需转换以免偏移
  if (typeof AMap?.convertFrom !== 'function') {
    return Promise.resolve({ lng, lat })
  }
  return new Promise<{ lng: number; lat: number }>((resolve) => {
    AMap.convertFrom([lng, lat], 'gps', (status: string, result: any) => {
      if (status === 'complete' && result?.info === 'ok' && result.locations?.[0]) {
        const loc = result.locations[0]
        const convertedLng = loc.lng ?? loc.getLng?.()
        const convertedLat = loc.lat ?? loc.getLat?.()
        if (typeof convertedLng === 'number' && typeof convertedLat === 'number') {
          resolve({ lng: convertedLng, lat: convertedLat })
          return
        }
      }
      resolve({ lng, lat })
    })
  })
}

async function locateCurrentRegion() {
  const AMap = await loadAmapDistrict()
  await amapPlugin(AMap, ['AMap.Geolocation', 'AMap.Geocoder', 'AMap.CitySearch'])

  // 策略1：高德 Geolocation 定位 → 逆地理编码（精度最高）
  try {
    const position = await getCurrentAmapPosition(AMap)
    return {
      ...(await getCurrentAmapAddress(AMap, position.lng, position.lat)),
      approximate: false,
    }
  } catch {
    // 策略2：浏览器原生定位 → 高德逆地理编码（WiFi 下可获区县级精度）
    try {
      const coords = await getBrowserPosition()
      const converted = await convertToAmapLngLat(AMap, coords.coords.longitude, coords.coords.latitude)
      return {
        ...(await getCurrentAmapAddress(AMap, converted.lng, converted.lat)),
        approximate: false,
      }
    } catch {
      // 策略3：IP 城市级定位（无区县信息）
      return {
        ...(await getCurrentAmapCity(AMap)),
        approximate: true,
      }
    }
  }
}

async function handleLocateRegion() {
  locatingRegion.value = true
  try {
    const payload = await locateCurrentRegion()
    const region = [
      payload?.province,
      payload?.city,
      payload?.district,
    ].filter(Boolean).join(' ')

    if (!region) {
      ElMessage.warning('暂时无法解析当前位置，请手动选择所在地区')
      return
    }

    form.region = region
    form.regionPath = []
    ElMessage.success(payload.approximate ? '已定位到当前城市，可继续手动选择区县' : '已定位到当前位置')
  } catch (error: any) {
    ElMessage.error(error?.message || '定位失败，请手动选择所在地区')
  } finally {
    locatingRegion.value = false
  }
}

async function handleAvatarChange(file: UploadFile) {
  if (!file.raw) return
  avatarUploading.value = true
  try {
    const res = await api.uploadAvatar(file.raw)
    form.avatar = res.url
    ElMessage.success('头像已选择，保存资料后生效')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
  } finally {
    avatarUploading.value = false
  }
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }

  saving.value = true
  try {
    await api.updateProfile({
      name: form.name.trim(),
      avatar: form.avatar || null,
      region: form.region.trim() || null,
    })
    await auth.fetchUser()
    resetForm()
    ElMessage.success('资料已保存')
    showEdit.value = false
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

</script>

<style scoped>
.profile-page {
  color: #07170e;
}

.profile-layout {
  display: flex;
  flex-direction: column;
  width: min(100%, 960px);
  margin: 0 auto;
  gap: 24px;
  align-items: stretch;
}

.profile-hero {
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(34, 94, 56, .16);
  box-shadow: 0 6px 16px rgba(28, 62, 39, .12);
}

.profile-hero :deep(.el-card__body) {
  padding: 0;
}

.profile-cover {
  height: 156px;
  background: linear-gradient(135deg, #1a8b46 0%, #006d58 100%);
}

.profile-main {
  position: relative;
  padding: 0 32px 30px;
}

.avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 116px;
  height: 116px;
  margin-top: -30px;
  border: 8px solid #fff;
  border-radius: 30px;
  background: #e8f0e1;
  color: #17341f;
  font-size: 48px;
  font-weight: 900;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-main h1 {
  margin: 28px 0 8px;
  color: #06150d;
  font-size: 32px;
  line-height: 1.15;
  font-weight: 900;
}

.profile-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
}

.profile-info {
  min-width: 0;
  padding: 20px 18px;
  border-radius: 18px;
  background: #f4f8f4;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 9px;
  color: #617069;
  font-size: 17px;
  font-weight: 600;
}

.profile-info strong {
  display: block;
  overflow: hidden;
  color: #06150d;
  font-size: 21px;
  line-height: 1.25;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px 20px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid rgba(34, 94, 56, .1);
  box-shadow: 0 4px 12px rgba(28, 62, 39, .06);
}

.stat-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: #eaf6ee;
  margin-bottom: 14px;
}

.stat-card-number {
  font-size: 32px;
  font-weight: 900;
  color: #178844;
  line-height: 1.1;
}

.stat-card-label {
  margin-top: 6px;
  font-size: 15px;
  font-weight: 700;
  color: #3d4c44;
}

.stat-card-sub {
  margin-top: 3px;
  font-size: 13px;
  font-weight: 600;
  color: #8a968f;
}

.profile-actions {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.menu-card {
  border-radius: 22px;
  border: 1px solid rgba(34, 94, 56, .16);
  box-shadow: 0 6px 16px rgba(28, 62, 39, .12);
}

.menu-card :deep(.el-card__body) {
  padding: 12px 28px;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 78px;
  border: 0;
  border-bottom: 1px solid #edf1ed;
  background: transparent;
  color: #3d4c44;
  font-family: inherit;
  font-size: 19px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}

.menu-item .el-icon {
  color: #617069;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item:hover {
  color: #178844;
}

.menu-item:hover .el-icon {
  color: #178844;
}



/* 编辑资料弹窗内部元素样式（dialog 外壳样式由全局 farmer-dialog.css 提供） */
.edit-avatar-row {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #dceadf;
  border-radius: 22px;
  background: #f4faf5;
}

.edit-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  overflow: hidden;
  border: 1px solid #cfe3d3;
  border-radius: 24px;
  background: #e8f0e1;
  color: #17341f;
  font-size: 36px;
  font-weight: 900;
}

.edit-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-actions {
  min-width: 0;
}

.avatar-actions strong {
  display: block;
  color: #102016;
  font-size: 20px;
  font-weight: 900;
}

.avatar-actions p {
  margin: 7px 0 12px;
  color: #718278;
  font-size: 15px;
  line-height: 1.45;
}

.avatar-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid #b9d8c1;
  border-radius: 14px;
  background: #fff;
  color: #178844;
  font-family: inherit;
  font-size: 15px;
  font-weight: 900;
  cursor: pointer;
}

.avatar-upload-btn:hover {
  background: #edf8f0;
}

.avatar-upload-btn:disabled {
  cursor: not-allowed;
  opacity: .7;
}

.edit-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.edit-form :deep(.el-form-item__label) {
  margin-bottom: 9px;
  color: #263c2d;
  font-size: 17px;
  font-weight: 900;
  line-height: 1.3;
}

.edit-form :deep(.el-input__wrapper),
.edit-form :deep(.el-textarea__inner) {
  min-height: 52px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 17px;
}

.edit-form :deep(.el-input__wrapper:hover),
.edit-form :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #9bc8a8 inset;
}

.edit-form :deep(.el-input__wrapper.is-focus),
.edit-form :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px rgba(23, 136, 68, .22) inset;
}

.edit-form :deep(.el-input__inner) {
  color: #102016;
  font-size: 17px;
}

.region-picker-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  gap: 12px;
  width: 100%;
}

.region-cascader {
  width: 100%;
}

.region-cascader :deep(.el-input__wrapper) {
  min-height: 52px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 0 0 1px #d4e3d8 inset;
  font-size: 17px;
}

.region-cascader--filled :deep(.el-input__inner::placeholder) {
  color: #263c2e;
  opacity: 1;
  font-weight: 700;
}

.locate-region-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 52px;
  border: 1px solid #b9d8c1;
  border-radius: 16px;
  background: #f7fcf8;
  color: #178844;
  font-family: inherit;
  font-size: 16px;
  font-weight: 900;
  cursor: pointer;
}

.locate-region-btn:hover {
  background: #edf8f0;
  border-color: #8fc69c;
}

.locate-region-btn:disabled {
  cursor: not-allowed;
  opacity: .7;
}

.region-current {
  margin: 10px 0 0;
  color: #6f7e76;
  font-size: 14px;
  font-weight: 700;
}

.edit-form :deep(.el-textarea__inner) {
  padding: 14px 16px;
  line-height: 1.6;
}

/* 修改密码弹窗：与重置密码弹窗一致的无 label 输入框样式 */
.pwd-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .profile-main {
    padding: 0 20px 24px;
  }

  .profile-main h1 {
    font-size: 28px;
  }

  .profile-info-grid {
    grid-template-columns: 1fr;
  }

  .menu-card :deep(.el-card__body) {
    padding: 8px 20px;
  }

  .menu-item {
    min-height: 64px;
    font-size: 19px;
  }

  .stat-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .stat-value {
    font-size: 17px;
  }

  .edit-avatar-row {
    align-items: flex-start;
    padding: 16px;
  }

  .region-picker-row {
    grid-template-columns: 1fr;
  }
}
</style>
