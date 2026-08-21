import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

export const api = {
  // ========== Auth ==========
  sendCode: (phone: string, scene: 'login' | 'register' | 'reset' = 'login') =>
    http.post('/auth/send-code', { phone, scene }).then(r => r.data),
  register: (phone: string, code: string, password: string, name: string) =>
    http.post('/auth/register', { phone, code, password, name }).then(r => r.data),
  login: (phone: string, password: string, remember = false) =>
    http.post('/auth/login', { phone, password, remember }).then(r => r.data),
  adminLogin: (phone: string, password: string, remember = false) =>
    http.post('/auth/admin-login', { phone, password, remember }).then(r => r.data),
  smsLogin: (phone: string, code: string, remember = false) =>
    http.post('/auth/sms-login', { phone, code, remember }).then(r => r.data),
  resetPassword: (phone: string, code: string, password: string) =>
    http.post('/auth/reset-password', { phone, code, password }).then(r => r.data),
  changeInitialPassword: (phone: string, oldPassword: string, newPassword: string) =>
    http.post('/auth/change-initial-password', { phone, old_password: oldPassword, new_password: newPassword }).then(r => r.data),
  getMe: () => http.get('/auth/me').then(r => r.data),
  updateProfile: (data: any) => http.put('/users/me', data).then(r => r.data),
  changePassword: (oldPassword: string, newPassword: string) =>
    http.put('/users/me/password', { old_password: oldPassword, new_password: newPassword }).then(r => r.data),
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/users/avatar', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  getLocationWeather: (longitude: number, latitude: number) =>
    http.get('/location/weather', { params: { longitude, latitude } }).then(r => r.data),
  getWeatherByRegion: (region: string) =>
    http.get('/location/weather/by-region', { params: { region } }).then(r => r.data),

  // ========== Lands ==========
  getLands: () => http.get('/lands').then(r => r.data),
  createLand: (data: any) => http.post('/lands', data).then(r => r.data),
  updateLand: (id: number, data: any) => http.put(`/lands/${id}`, data).then(r => r.data),
  deleteLand: (id: number) => http.delete(`/lands/${id}`).then(r => r.data),

  // ========== Crops ==========
  getCrops: () => http.get('/crops').then(r => r.data),
  createCrop: (data: any) => http.post('/crops', data).then(r => r.data),
  markCropAdviceRead: (id: number) => http.post(`/crops/${id}/mark-advice-read`).then(r => r.data),
  harvestCrop: (id: number) => http.post(`/crops/${id}/harvest`).then(r => r.data),
  restoreCrop: (id: number) => http.post(`/crops/${id}/restore`).then(r => r.data),

  // ========== Farm Works ==========
  getFarmWorks: (workType?: string) => {
    const params = workType && workType !== '全部' ? `?work_type=${workType}` : ''
    return http.get(`/farm-works${params}`).then(r => r.data)
  },
  getFarmWorksByBatch: (batchId: number) =>
    http.get(`/farm-works?batch_id=${batchId}`).then(r => r.data),
  createFarmWork: (data: any) => http.post('/farm-works', data).then(r => r.data),
  updateFarmWork: (id: number, data: any) => http.put(`/farm-works/${id}`, data).then(r => r.data),
  deleteFarmWork: (id: number) => http.delete(`/farm-works/${id}`).then(r => r.data),
  uploadWorkPhoto: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/farm-works/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  // ========== Articles ==========
  getArticles: (category?: string) => {
    const params = category && category !== '全部' ? `?category=${category}` : ''
    return http.get(`/articles${params}`).then(r => r.data)
  },
  getArticle: (id: number) => http.get(`/articles/${id}`).then(r => r.data),
  recordArticleView: (id: number) => http.post(`/articles/${id}/view`).then(r => r.data).catch(() => null),
  getArticleViews: () => http.get('/articles/my-views').then(r => r.data),
  createArticle: (data: any) => http.post('/articles', data).then(r => r.data),
  updateArticle: (id: number, data: any) => http.put(`/articles/${id}`, data).then(r => r.data),
  deleteArticle: (id: number) => http.delete(`/articles/${id}`).then(r => r.data),
  getMyArticles: () => http.get('/articles/mine').then(r => r.data),
  uploadArticleCover: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/articles/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  uploadArticleImage: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/articles/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  // ========== Expert ==========
  getExpertWorks: (farmerId?: number) => {
    const params = farmerId ? `?farmer_id=${farmerId}` : ''
    return http.get(`/expert/works${params}`).then(r => r.data)
  },
  createExpertAdvice: (workId: number, content: string) =>
    http.post('/expert/advice', { work_id: workId, content }).then(r => r.data),
  getExpertQuestions: (status?: string) => {
    const params = status ? `?status=${status}` : ''
    return http.get(`/expert/questions${params}`).then(r => r.data)
  },
  getExperts: () => http.get('/expert/experts').then(r => r.data),
  // 专家咨询 IM
  startConsultation: (data: { expert_id: number; content: string; images?: string | null }) =>
    http.post('/expert/questions', data).then(r => r.data),
  sendMessage: (questionId: number, data: { content: string; images?: string | null }) =>
    http.post(`/expert/questions/${questionId}/messages`, data).then(r => r.data),
  listMessages: (questionId: number, afterId = 0) =>
    http.get(`/expert/questions/${questionId}/messages`, { params: { after_id: afterId } }).then(r => r.data),
  endConsultation: (questionId: number) =>
    http.post(`/expert/questions/${questionId}/end`).then(r => r.data),
  rateConsultation: (questionId: number, rating: number) =>
    http.post(`/expert/questions/${questionId}/rate`, { rating }).then(r => r.data),
  skipConsultationRating: (questionId: number) =>
    http.post(`/expert/questions/${questionId}/skip-rating`).then(r => r.data),
  getMyConsultations: () => http.get('/expert/my-consultations').then(r => r.data),
  // 农户：按专家聚合的咨询列表（去重）
  getMyExperts: () => http.get('/expert/my-experts').then(r => r.data),
  // 农户：与某专家的所有历史消息（跨会话合并）
  listMessagesWithExpert: (expertId: number, afterId = 0) =>
    http.get(`/expert/experts/${expertId}/messages`, { params: { after_id: afterId } }).then(r => r.data),
  // 农户：获取与某专家的会话（有进行中就返回，没有返回占位）
  getOrCreateConsultation: (expertId: number) =>
    http.get(`/expert/experts/${expertId}/consultation`).then(r => r.data),
  // 农户：标记与某专家的所有会话（含旧会话）的未读通知为已读
  markExpertRead: (expertId: number) =>
    http.post(`/expert/experts/${expertId}/read-all`).then(r => r.data),
  getNotificationUnreadCount: () => http.get('/expert/notifications/unread-count').then(r => r.data),
  markNotificationsRead: () => http.post('/expert/notifications/read-all').then(r => r.data),
  markConsultationRead: (questionId: number) => http.post(`/expert/notifications/read/${questionId}`).then(r => r.data),
  uploadConsultationImage: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/expert/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  // ========== Push ==========
  updateLocation: (adcode: string, city: string) =>
    http.post('/users/update-location', { adcode, city }).then(r => r.data),
  getLatestPush: () => http.get('/push/latest').then(r => r.data),
  markPushShown: (id: number) => http.post(`/push/mark-shown/${id}`).then(r => r.data),

  // ========== 农事计划 ==========
  getFarmPlans: () => http.get('/plans').then(r => r.data),
  createFarmPlan: (content: string, planDate?: string) =>
    http.post('/plans', { content, plan_date: planDate }).then(r => r.data),
  toggleFarmPlan: (id: number, isDone: boolean) =>
    http.patch(`/plans/${id}`, { is_done: isDone }).then(r => r.data),
  deleteFarmPlan: (id: number) => http.delete(`/plans/${id}`).then(r => r.data),

  // ========== AI Knowledge Q&A ==========
  getAIConversations: () => http.get('/ai/conversations').then(r => r.data),
  getAIMessages: (conversationId: number | string) =>
    http.get(`/ai/conversations/${conversationId}/messages`).then(r => r.data),
  deleteAIConversation: (conversationId: number | string) =>
    http.delete(`/ai/conversations/${conversationId}`).then(r => r.data),
  streamAIChat: (data: {
    message: string
    conversationId?: number | string | null
    images?: File[]
    signal?: AbortSignal
  }) => {
    const form = new FormData()
    form.append('message', data.message)
    if (data.conversationId) form.append('conversation_id', String(data.conversationId))
    data.images?.forEach(image => form.append('images', image))
    const token = localStorage.getItem('access_token')
    return fetch('/api/ai/chat/stream', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
      signal: data.signal,
    })
  },

  // ========== Admin ==========
  getAdminStats: () => http.get('/admin/stats').then(r => r.data),
  getAdminUsers: () => http.get('/admin/users').then(r => r.data),
  updateAdminUser: (id: number, data: any) => http.put(`/admin/users/${id}`, data).then(r => r.data),
  getAdminExperts: () => http.get('/admin/experts').then(r => r.data),
  createExpert: (data: any) => http.post('/admin/experts', data).then(r => r.data),
  updateAdminExpert: (id: number, data: any) => http.put(`/admin/experts/${id}`, data).then(r => r.data),
  deleteExpert: (id: number) => http.delete(`/admin/experts/${id}`).then(r => r.data),
  getMonthlyData: () => http.get('/admin/monthly-data').then(r => r.data),
  getAdminArticles: () => http.get('/admin/articles').then(r => r.data),
  reviewArticle: (id: number, action: 'approve' | 'reject', reason?: string) =>
    http.post(`/admin/articles/${id}/review`, { action, reason }).then(r => r.data),
}
