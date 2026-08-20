<template>
  <div class="login-container">
    <!-- 左侧：品牌展示区（纯渐变背景 + 装饰元素） -->
    <section class="brand-panel">
      <div class="brand-decoration brand-decoration--leaf-1"></div>
      <div class="brand-decoration brand-decoration--leaf-2"></div>
      <div class="brand-decoration brand-decoration--circle-1"></div>
      <div class="brand-decoration brand-decoration--circle-2"></div>
      <div class="brand-decoration brand-decoration--circle-3"></div>

      <header class="brand-header">
        <span class="brand-logo"><SproutIcon :size="28" variant="white" /></span>
        <span class="brand-name">慧农宝</span>
      </header>

      <div class="brand-center">
        <div class="brand-icon-wrap">
          <SproutIcon :size="120" variant="white" />
        </div>
        <h1 class="brand-slogan-title">让每一寸土地更聪明</h1>
        <p class="brand-slogan-desc">
          数据驱动的智慧农业种植管理，<br />助力科学决策、降本增效、稳产增收。
        </p>
      </div>

      <footer class="brand-footer">
        <span class="brand-dot"></span>
        <span class="brand-footer-text">智能农业种植顾问平台</span>
      </footer>
    </section>

    <!-- 右侧：表单区 -->
    <section class="form-panel">
      <div class="auth-card">
        <div class="mobile-brand">
          <span class="mobile-brand-logo"><SproutIcon :size="22" variant="white" /></span>
          <span class="mobile-brand-name">慧农宝</span>
        </div>

        <div class="form-heading">
          <h2>{{ headingTitle }}</h2>
          <p v-if="!showChangePassword" class="form-subtitle">
            {{
              mode === 'register'
                ? '注册即可开始体验智慧种植服务'
                : loginType === 'admin'
                ? '管理员专属入口'
                : '登录后即可继续您的种植之旅'
            }}
          </p>
        </div>

        <template v-if="mode === 'login' && !showChangePassword">
          <div v-if="loginType === 'user'" class="tab-switch">
            <button :class="['tab-item', { active: tab === 'password' }]" type="button" @click="tab = 'password'">
              密码登录
            </button>
            <button
              v-if="loginType === 'user'"
              :class="['tab-item', { active: tab === 'sms' }]"
              type="button"
              @click="tab = 'sms'"
            >
              短信登录
            </button>
          </div>

          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="error-alert" />

          <el-form @submit.prevent="handleSubmit" class="auth-form" autocomplete="off">
            <el-form-item>
              <el-input v-model="phone" :placeholder="phonePlaceholder" prefix-icon="Iphone" size="large" autocomplete="off" />
            </el-form-item>

            <el-form-item v-if="tab === 'password'">
              <el-input v-model="password" type="password" :placeholder="loginType === 'admin' ? '请输入密码' : '密码'" prefix-icon="Lock" size="large" show-password autocomplete="new-password" />
            </el-form-item>

            <el-form-item v-else>
              <div class="code-row">
                <el-input v-model="code" placeholder="验证码" prefix-icon="Lock" size="large" />
                <el-button :disabled="countdown > 0" class="code-btn" size="large" @click="sendCode">
                  {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
                </el-button>
              </div>
            </el-form-item>

            <div v-if="tab === 'password' && loginType === 'user'" class="login-options">
              <el-checkbox v-model="rememberPassword">记住登录</el-checkbox>
              <button type="button" class="text-link" @click="showReset = true">忘记密码</button>
            </div>

            <el-button type="primary" size="large" class="submit-btn" :loading="submitting" native-type="submit">
              登录
            </el-button>
          </el-form>

          <div v-if="loginType === 'user'" class="bottom-links">
            <button type="button" class="plain-link" @click="switchMode('register')">立即注册</button>
            <span class="divider">|</span>
            <button type="button" class="plain-link muted" @click="switchAdminLogin">
              管理员登录
            </button>
          </div>
          <div v-else class="admin-back">
            <button type="button" class="plain-link" @click="switchUserLogin">返回普通登录</button>
          </div>
        </template>

        <template v-else-if="mode === 'register'">
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="error-alert" />

          <el-form @submit.prevent="handleSubmit" class="auth-form register-form" autocomplete="off">
            <el-form-item>
              <el-input v-model="name" placeholder="请输入用户名" prefix-icon="User" size="large" autocomplete="off" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="phone" placeholder="请输入手机号" prefix-icon="Iphone" size="large" autocomplete="off" />
            </el-form-item>
            <el-form-item>
              <div class="code-row">
                <el-input v-model="code" placeholder="短信验证码" prefix-icon="Message" size="large" />
                <el-button :disabled="countdown > 0" class="code-btn" size="large" @click="sendCode">
                  {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item>
              <el-input v-model="password" type="password" placeholder="设置密码" prefix-icon="Lock" size="large" show-password autocomplete="new-password" />
              <p class="field-hint">密码 6-20 位，同时包含数字和字母</p>
            </el-form-item>
            <el-form-item>
              <el-input v-model="confirmPassword" type="password" placeholder="确认密码" prefix-icon="Lock" size="large" show-password autocomplete="new-password" />
            </el-form-item>

            <el-checkbox v-model="agreed" class="agree-check">
              我已阅读并同意<span>《用户服务协议》</span>和<span>《隐私政策》</span>
            </el-checkbox>

            <el-button type="primary" size="large" class="submit-btn" :loading="submitting" native-type="submit">
              注册
            </el-button>
          </el-form>

          <div class="bottom-links register-bottom">
            <span>已有账号？</span>
            <button type="button" class="plain-link" @click="switchMode('login')">立即登录</button>
          </div>
        </template>

        <!-- 专家首次登录强制改密 -->
        <template v-else>
          <div class="change-password-banner">
            <p>检测到您正在使用管理员下发的初始密码，</p>
            <p>为保障账号安全，请先修改密码后再登录。</p>
          </div>

          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="error-alert" />

          <el-form @submit.prevent="handleChangeInitialPassword" class="auth-form" autocomplete="off">
            <el-form-item>
              <el-input
                v-model="changePasswordForm.newPassword"
                type="password"
                placeholder="请输入新密码"
                prefix-icon="Lock"
                size="large"
                show-password
                autocomplete="new-password"
              />
              <p class="field-hint">密码 6-20 位，同时包含数字和字母</p>
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="changePasswordForm.confirmPassword"
                type="password"
                placeholder="请确认新密码"
                prefix-icon="Lock"
                size="large"
                show-password
                autocomplete="new-password"
              />
            </el-form-item>
            <el-button type="primary" size="large" class="submit-btn" :loading="changingPassword" native-type="submit">
              修改密码并继续
            </el-button>
          </el-form>

          <div class="admin-back">
            <button type="button" class="plain-link" @click="cancelChangePassword">返回登录</button>
          </div>
        </template>
      </div>
    </section>

    <el-dialog v-model="showReset" title="重置密码" width="540px" class="reset-dialog form-dialog" :close-on-click-modal="false">
      <el-form class="reset-form" autocomplete="off">
        <el-form-item>
          <el-input v-model="resetPhone" placeholder="请输入注册手机号" size="large" autocomplete="off" />
        </el-form-item>
        <el-form-item>
          <div class="code-row">
            <el-input v-model="resetCode" placeholder="验证码" size="large" />
            <el-button :disabled="resetCountdown > 0" class="code-btn" size="large" @click="sendResetCode">
              {{ resetCountdown > 0 ? `${resetCountdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-input v-model="resetNewPassword" type="password" placeholder="新密码（6-20位，含字母和数字）" size="large" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReset = false">取消</el-button>
        <el-button type="primary" :loading="resetSubmitting" @click="resetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'
import SproutIcon from '@/components/SproutIcon.vue'

const router = useRouter()
const auth = useAuthStore()

type Mode = 'login' | 'register'
type LoginTab = 'password' | 'sms'
type LoginType = 'user' | 'admin'

const mode = ref<Mode>('login')
const tab = ref<LoginTab>('password')
const loginType = ref<LoginType>('user')
const countdown = ref(0)
const resetCountdown = ref(0)
const submitting = ref(false)
const resetSubmitting = ref(false)
const error = ref('')

const phone = ref('')
const code = ref('')
const password = ref('')
const confirmPassword = ref('')
const name = ref('')
const agreed = ref(false)
const rememberPassword = ref(false)

const showReset = ref(false)
const resetPhone = ref('')
const resetCode = ref('')
const resetNewPassword = ref('')

// 专家首次登录强制改密相关状态
const showChangePassword = ref(false)
const changingPassword = ref(false)
// 用于 change-initial-password 接口：phone + old_password 都来自登录尝试
const pendingChangePhone = ref('')
const pendingChangeOldPassword = ref('')
const changePasswordForm = reactive({
  newPassword: '',
  confirmPassword: '',
})

const headingTitle = computed(() => {
  if (showChangePassword.value) return '修改初始密码'
  if (mode.value === 'register') return '注册新账号'
  if (loginType.value === 'admin') return '管理员登录'
  return '欢迎回来'
})

const phonePlaceholder = computed(() => {
  if (loginType.value === 'admin') return '管理员请输入手机号'
  return '请输入手机号'
})

function switchMode(nextMode: Mode) {
  mode.value = nextMode
  loginType.value = 'user'
  tab.value = 'password'
  error.value = ''
}

function switchAdminLogin() {
  loginType.value = 'admin'
  tab.value = 'password'
  rememberPassword.value = false
  error.value = ''
}

function switchUserLogin() {
  loginType.value = 'user'
  tab.value = 'password'
  error.value = ''
}

function validatePhone(value = phone.value) {
  return /^1[3-9]\d{9}$/.test(value)
}

function validatePasswordRule(value: string) {
  return /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d\S]{6,20}$/.test(value)
}

function startCountdown(target: typeof countdown = countdown) {
  target.value = 60
  const timer = setInterval(() => {
    target.value--
    if (target.value <= 0) clearInterval(timer)
  }, 1000)
}

async function sendCode() {
  if (!validatePhone()) {
    error.value = '请输入正确的手机号'
    return
  }
  error.value = ''
  try {
    const scene = mode.value === 'register' ? 'register' : 'login'
    await api.sendCode(phone.value, scene)
    ElMessage.success('验证码已发送')
    startCountdown()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '发送失败'
  }
}

async function sendResetCode() {
  if (!validatePhone(resetPhone.value)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  try {
    await api.sendCode(resetPhone.value, 'reset')
    ElMessage.success('验证码已发送')
    startCountdown(resetCountdown)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  }
}

async function handleSubmit() {
  error.value = ''
  submitting.value = true
  try {
    if (mode.value === 'register') {
      if (!name.value.trim()) { error.value = '请输入用户名'; return }
      if (!agreed.value) { error.value = '请先同意用户服务协议和隐私政策'; return }
      if (!validatePasswordRule(password.value)) { error.value = '密码需为6-20位，并同时包含字母与数字'; return }
      if (password.value !== confirmPassword.value) { error.value = '两次密码不一致'; return }
      await auth.register(phone.value, code.value, password.value, name.value)
      router.push('/')
      return
    }

    if (loginType.value === 'admin') {
      await auth.adminLogin(phone.value, password.value, false)
      router.push('/admin')
      return
    }

    if (tab.value === 'password') {
      const result = await auth.login(phone.value, password.value, rememberPassword.value)
      if (result?.mustChangePassword) {
        // 触发强制改密流程：暂存登录用的手机号和原密码，切换到改密表单
        pendingChangePhone.value = phone.value
        pendingChangeOldPassword.value = password.value
        showChangePassword.value = true
        error.value = ''
        changePasswordForm.newPassword = ''
        changePasswordForm.confirmPassword = ''
        return
      }
    } else {
      await auth.smsLogin(phone.value, code.value, rememberPassword.value)
    }

    const u = auth.user
    if (u?.role === 2) router.push('/expert')
    else if (u?.role === 3) router.push('/admin')
    else router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  } finally {
    submitting.value = false
  }
}

async function handleChangeInitialPassword() {
  error.value = ''
  if (!validatePasswordRule(changePasswordForm.newPassword)) {
    error.value = '密码需为6-20位，并同时包含字母与数字'
    return
  }
  if (changePasswordForm.newPassword !== changePasswordForm.confirmPassword) {
    error.value = '两次新密码不一致'
    return
  }
  if (changePasswordForm.newPassword === pendingChangeOldPassword.value) {
    error.value = '新密码不能与原密码相同'
    return
  }

  changingPassword.value = true
  try {
    await api.changeInitialPassword(
      pendingChangePhone.value,
      pendingChangeOldPassword.value,
      changePasswordForm.newPassword,
    )
    ElMessage.success('初始密码修改成功，请使用新密码登录')
    // 退出改密模式，预填手机号让用户用新密码重新登录
    showChangePassword.value = false
    password.value = ''
    changePasswordForm.newPassword = ''
    changePasswordForm.confirmPassword = ''
    pendingChangeOldPassword.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '密码修改失败'
  } finally {
    changingPassword.value = false
  }
}

function cancelChangePassword() {
  showChangePassword.value = false
  error.value = ''
  changePasswordForm.newPassword = ''
  changePasswordForm.confirmPassword = ''
  pendingChangePhone.value = ''
  pendingChangeOldPassword.value = ''
  password.value = ''
}

async function resetPassword() {
  if (!validatePhone(resetPhone.value)) { ElMessage.warning('请输入正确的手机号'); return }
  if (!resetCode.value.trim()) { ElMessage.warning('请输入验证码'); return }
  if (!resetNewPassword.value.trim()) { ElMessage.warning('请输入新密码'); return }
  if (!validatePasswordRule(resetNewPassword.value)) { ElMessage.warning('密码需为6-20位，并同时包含字母与数字'); return }
  resetSubmitting.value = true
  try {
    await api.resetPassword(resetPhone.value, resetCode.value, resetNewPassword.value)
    ElMessage.success('密码已重置，请重新登录')
    showReset.value = false
    phone.value = resetPhone.value
    password.value = ''
    resetCode.value = ''
    resetNewPassword.value = ''
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resetSubmitting.value = false
  }
}

onMounted(() => {
  localStorage.removeItem('remembered_login')
})
</script>

<style scoped>
/* ============ 容器布局 ============ */
.login-container {
  display: grid;
  min-height: 100vh;
  grid-template-columns: 1fr;
  overflow-y: auto;
}

@media (min-width: 1024px) {
  .login-container {
    grid-template-columns: 56% 44%;
  }
}

/* ============ 左侧：品牌展示区 ============ */
.brand-panel {
  position: relative;
  display: none;
  flex-direction: column;
  justify-content: space-between;
  padding: 56px 64px;
  overflow: hidden;
  background: linear-gradient(145deg, #178844 0%, #0a5c2e 100%);
  color: #fff;
}

@media (min-width: 1024px) {
  .brand-panel {
    display: flex;
  }
}

/* 装饰性背景：叶子 + 圆形，柔化纯渐变 */
.brand-decoration {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
}

.brand-decoration--circle-1 {
  top: -120px;
  right: -120px;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0) 70%);
}

.brand-decoration--circle-2 {
  bottom: -160px;
  left: -100px;
  width: 420px;
  height: 420px;
  background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0) 70%);
}

.brand-decoration--circle-3 {
  top: 38%;
  right: 8%;
  width: 140px;
  height: 140px;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
  background: transparent;
}

.brand-decoration--leaf-1,
.brand-decoration--leaf-2 {
  width: 220px;
  height: 220px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 0 100% 0 100%;
  transform: rotate(-30deg);
}

.brand-decoration--leaf-1 {
  top: 18%;
  left: -60px;
}

.brand-decoration--leaf-2 {
  bottom: 14%;
  right: -70px;
  transform: rotate(150deg);
  width: 280px;
  height: 280px;
  background: rgba(255, 255, 255, 0.05);
}

.brand-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(6px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
}

.brand-name {
  font-size: 30px;
  font-weight: 900;
  letter-spacing: 2px;
}

.brand-center {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin: 0 auto;
  padding: 24px 0;
}

.brand-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 220px;
  height: 220px;
  margin-bottom: 36px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 45%, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.04) 70%, rgba(255, 255, 255, 0) 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18), 0 20px 40px rgba(0, 40, 22, 0.25);
}

.brand-slogan-title {
  margin: 0 0 18px;
  font-size: 34px;
  font-weight: 900;
  line-height: 1.25;
  letter-spacing: 1px;
}

.brand-slogan-desc {
  margin: 0;
  max-width: 420px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 16px;
  line-height: 1.7;
}

.brand-footer {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  letter-spacing: 1px;
}

.brand-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9be7b8;
  box-shadow: 0 0 12px rgba(155, 231, 184, 0.8);
}

/* ============ 右侧：表单区 ============ */
.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 36px;
  background: #f8faf9;
}

.auth-card {
  width: 100%;
  max-width: 460px;
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
}

/* 移动端顶部品牌（桌面端隐藏） */
.mobile-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

@media (min-width: 1024px) {
  .mobile-brand {
    display: none;
  }
}

.mobile-brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(145deg, #178844 0%, #0a5c2e 100%);
  box-shadow: 0 4px 10px rgba(23, 136, 68, 0.25);
}

.mobile-brand-name {
  font-size: 22px;
  font-weight: 900;
  color: #0a5c2e;
  letter-spacing: 1px;
}

/* ============ 表单标题 ============ */
.form-heading {
  margin-bottom: 28px;
}

.form-heading h2 {
  margin: 0;
  color: #0a1f15;
  font-size: 32px;
  font-weight: 900;
  line-height: 1.2;
  letter-spacing: 0.5px;
}

.form-subtitle {
  margin: 10px 0 0;
  color: #6b7a72;
  font-size: 15px;
  line-height: 1.5;
}

/* ============ Tab 切换 ============ */
.tab-switch {
  display: flex;
  gap: 40px;
  margin-bottom: 24px;
  border-bottom: 1.5px solid #e1e8e3;
}

.tab-item {
  height: 42px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #98a3a0;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.tab-item.active {
  color: #178844;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -2px;
  height: 2.5px;
  border-radius: 2px;
  background: #178844;
}

/* ============ 错误提示 ============ */
.error-alert {
  margin-bottom: 16px;
}

/* ============ 表单元素 ============ */
.auth-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.auth-form :deep(.el-input__wrapper),
.reset-form :deep(.el-input__wrapper) {
  min-height: 56px;
  height: 56px;
  border-radius: 12px;
  padding: 0 18px;
  background: #ffffff;
  box-shadow: 0 0 0 1px #e1e8e3 inset;
  transition: box-shadow 0.2s;
}

.auth-form :deep(.el-input__wrapper:hover),
.reset-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c8d6cd inset;
}

.auth-form :deep(.el-input__wrapper.is-focus),
.auth-form :deep(.el-input__wrapper.is-focus:hover),
.reset-form :deep(.el-input__wrapper.is-focus),
.reset-form :deep(.el-input__wrapper.is-focus:hover) {
  box-shadow: 0 0 0 1.5px #178844 inset;
}

.auth-form :deep(.el-input__inner),
.reset-form :deep(.el-input__inner) {
  height: 56px;
  font-size: 15px;
  color: #0a1f15;
}

.auth-form :deep(.el-input__inner::placeholder),
.reset-form :deep(.el-input__inner::placeholder) {
  color: #a4b0ab;
}

.auth-form :deep(.el-input__prefix),
.auth-form :deep(.el-input__prefix-inner),
.reset-form :deep(.el-input__prefix),
.reset-form :deep(.el-input__prefix-inner) {
  color: #178844;
}

/* ============ 验证码一行 ============ */
.code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px;
  gap: 12px;
  width: 100%;
}

.code-btn {
  height: 56px;
  min-height: 56px;
  border-radius: 12px;
  border: 1.5px solid #178844;
  background: #ffffff;
  color: #178844;
  font-size: 14px;
  font-weight: 700;
}

.code-btn:hover,
.code-btn:focus {
  background: #f0f8f2;
  border-color: #178844;
  color: #0a5c2e;
}

.code-btn.is-disabled,
.code-btn.is-disabled:hover {
  background: #eef3ef;
  border-color: #d6ded8;
  color: #98a3a0;
  cursor: not-allowed;
}

/* ============ 登录选项 / 协议 ============ */
.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -6px 0 24px;
}

.login-options :deep(.el-checkbox__label),
.agree-check :deep(.el-checkbox__label) {
  color: #4a5853;
  font-size: 14px;
}

.login-options :deep(.el-checkbox__input.is-checked .el-checkbox__inner),
.agree-check :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: #178844;
  border-color: #178844;
}

.text-link,
.plain-link {
  border: 0;
  background: transparent;
  color: #178844;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
}

.text-link:hover,
.plain-link:hover {
  color: #0a5c2e;
}

.plain-link.muted {
  color: #98a3a0;
  font-weight: 500;
}

.plain-link.muted:hover {
  color: #178844;
}

/* ============ 提交按钮 ============ */
.submit-btn {
  --el-button-bg-color: #178844;
  --el-button-border-color: #178844;
  --el-button-hover-bg-color: #147a3b;
  --el-button-hover-border-color: #147a3b;
  --el-button-active-bg-color: #0e6a31;
  --el-button-active-border-color: #0e6a31;
  --el-button-disabled-bg-color: #178844;
  --el-button-disabled-border-color: #178844;
  --el-button-disabled-text-color: #ffffff;
  width: 100%;
  height: 56px;
  border-radius: 12px;
  background: #178844 !important;
  border-color: #178844 !important;
  color: #ffffff !important;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  box-shadow: 0 10px 22px rgba(23, 136, 68, 0.28);
  transition: background 0.2s, box-shadow 0.2s, transform 0.05s;
}

.submit-btn:hover,
.submit-btn:focus {
  background: #147a3b !important;
  border-color: #147a3b !important;
  color: #ffffff !important;
  box-shadow: 0 12px 26px rgba(23, 136, 68, 0.34);
}

.submit-btn:active {
  background: #0e6a31 !important;
  border-color: #0e6a31 !important;
  transform: translateY(1px);
}

.submit-btn.is-disabled,
.submit-btn.is-loading,
.submit-btn.is-disabled:hover,
.submit-btn.is-loading:hover {
  background: #178844 !important;
  border-color: #178844 !important;
  color: #ffffff !important;
  opacity: 0.85;
  box-shadow: none;
}

/* ============ 底部链接 ============ */
.bottom-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 28px;
  color: #98a3a0;
  font-size: 14px;
}

.admin-back {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.divider {
  color: #d6ded8;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.field-hint {
  width: 100%;
  margin: 8px 0 0 2px;
  color: #98a3a0;
  font-size: 13px;
  line-height: 1.4;
}

.agree-check {
  margin: 4px 0 24px;
}

.agree-check span {
  color: #178844;
}

.register-bottom {
  margin-top: 24px;
}

/* ============ 改密提示条 ============ */
.change-password-banner {
  margin-bottom: 20px;
  padding: 16px 20px;
  border-radius: 12px;
  background: #fff8e6;
  border-left: 4px solid #f0a020;
  color: #7a5a10;
  font-size: 14px;
  line-height: 1.6;
}

.change-password-banner p {
  margin: 0;
}

/* ============ 重置密码对话框（复用 form-dialog 统一样式，仅保留验证码行特殊样式） ============ */
.reset-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

/* 验证码行：输入框 + 按钮并排 */
.code-row {
  display: flex;
  gap: 12px;
}
.code-row .el-input {
  flex: 1;
}
.code-btn {
  flex-shrink: 0;
  min-width: 120px;
}

/* ============ 移动端（< 1024px）：隐藏品牌区，表单全屏 ============ */
@media (max-width: 1023px) {
  .form-panel {
    min-height: 100vh;
    padding: 32px 22px;
  }

  .auth-card {
    max-width: 100%;
  }

  .form-heading h2 {
    font-size: 28px;
  }

  .code-row {
    grid-template-columns: 1fr;
  }
}
</style>
