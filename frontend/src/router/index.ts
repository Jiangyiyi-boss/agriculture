import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/FarmerLayout.vue'),
      meta: { requiresAuth: true, role: 1 },
      children: [
        { path: '', name: 'home', component: () => import('@/views/farmer/Home.vue') },
        // 旧路径 /farm-work 已合并到 /crops（方案 A：作物管理为唯一主入口）
        { path: 'farm-work', redirect: '/crops' },
        { path: 'crops', name: 'crops', component: () => import('@/views/farmer/Crops.vue') },
        { path: 'crops/:id', name: 'cropDetail', component: () => import('@/views/farmer/CropDetail.vue') },
        { path: 'lands', name: 'lands', component: () => import('@/views/farmer/Lands.vue') },
        { path: 'news', name: 'news', component: () => import('@/views/farmer/News.vue') },
        { path: 'news/:id', name: 'articleDetail', component: () => import('@/views/farmer/ArticleDetail.vue') },
        { path: 'history', name: 'browseHistory', component: () => import('@/views/farmer/BrowseHistory.vue') },
        { path: 'qa', name: 'qa', component: () => import('@/views/farmer/QA.vue') },
        { path: 'profile', name: 'profile', component: () => import('@/views/farmer/Profile.vue') },
      ],
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/admin/Dashboard.vue'),
      meta: { requiresAuth: true, role: 3 },
    },
    {
      path: '/expert',
      name: 'expert',
      component: () => import('@/views/expert/Dashboard.vue'),
      meta: { requiresAuth: true, role: 2 },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.token) {
    return next('/login')
  }
  // 带 token 但 user 还没加载（页面刷新场景）：先拉用户信息再判断角色
  if (auth.token && !auth.user && !to.meta.guest) {
    await auth.fetchUser()
  }
  if (to.meta.role && auth.user) {
    const role = to.meta.role
    const userRole = auth.user.role
    // 角色不匹配时，按用户角色重定向到对应主页（避免循环跳转到 / ）
    const roleMismatchRedirect: Record<number, string> = {
      1: '/',
      2: '/expert',
      3: '/admin',
    }
    const allowed = Array.isArray(role) ? role.includes(userRole) : userRole === role
    if (!allowed) {
      // 避免重定向到当前已所在的路径导致死循环
      const target = roleMismatchRedirect[userRole] || '/'
      return next(target === to.path ? false : target)
    }
  }
  if (to.meta.guest && auth.token) {
    // 已登录用户访问登录页：按角色跳转
    const roleRedirect: Record<number, string> = {
      1: '/',
      2: '/expert',
      3: '/admin',
    }
    const target = auth.user ? (roleRedirect[auth.user.role] || '/') : '/'
    return next(target)
  }
  next()
})

export default router