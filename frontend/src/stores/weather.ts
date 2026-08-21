import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'

type WeatherPayload = {
  province: string
  region: string
  city: string
  district: string
  adcode: string
  live: {
    weather: string
    temperature: string
    humidity: string
    winddirection: string
    windpower: string
    reporttime: string
  }
  forecast: Array<{
    date: string
    dayweather: string
    nightweather: string
    daytemp: string
    nighttemp: string
    daywind: string
    daypower: string
  }>
}

const WEEK_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const CACHE_KEY = 'amap_weather_cache_v2'
const CACHE_MAX_AGE = 15 * 60 * 1000
const AMAP_SCRIPT_ID = 'amap-js-sdk'

declare global {
  interface Window {
    AMap?: any
    _AMapSecurityConfig?: { securityJsCode: string }
    __amapLoader?: Promise<any>
  }
}

function loadAmap() {
  if (window.AMap) return Promise.resolve(window.AMap)
  if (window.__amapLoader) return window.__amapLoader

  const key = import.meta.env.VITE_AMAP_WEB_KEY
  const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE
  if (!key || !securityCode) return Promise.reject(new Error('未配置高德地图 JS Key'))

  window._AMapSecurityConfig = { securityJsCode: securityCode }
  window.__amapLoader = new Promise((resolve, reject) => {
    const existing = document.getElementById(AMAP_SCRIPT_ID) as HTMLScriptElement | null
    if (existing) {
      existing.addEventListener('load', () => resolve(window.AMap))
      existing.addEventListener('error', () => reject(new Error('高德地图 JS SDK 加载失败')))
      return
    }

    const script = document.createElement('script')
    script.id = AMAP_SCRIPT_ID
    script.async = true
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}&plugin=AMap.Geolocation,AMap.Geocoder,AMap.Weather,AMap.CitySearch`
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

function lngLatFromPosition(position: any) {
  const lng = position?.lng ?? position?.getLng?.()
  const lat = position?.lat ?? position?.getLat?.()
  if (typeof lng !== 'number' || typeof lat !== 'number') {
    throw new Error('无法获取当前位置经纬度')
  }
  return { lng, lat }
}

function friendlyLocationError(message = '') {
  if (/denied|permission|拒绝/i.test(message)) {
    return '浏览器定位权限被拒绝，已尝试使用城市天气'
  }
  return message || '定位失败，已尝试使用城市天气'
}

function dateLabel(date = new Date()) {
  return `${date.getMonth() + 1}/${date.getDate()} ${WEEK_LABELS[date.getDay()]}`
}

function dayOffsetLabel(offset: number) {
  const date = new Date()
  date.setDate(date.getDate() + offset)
  return offset === 1 ? '明天' : WEEK_LABELS[date.getDay()]
}

function parseDate(value = '') {
  if (!value) return null
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

function weekdayLabel(value = '') {
  const date = parseDate(value)
  return date ? WEEK_LABELS[date.getDay()] : ''
}

function weatherIconKey(value = '') {
  if (/雷|电/.test(value)) return 'thunder'
  if (/暴雨|大雨|中雨|小雨|阵雨|雨/.test(value)) return 'rain'
  if (/雪|冰雹|冻雨/.test(value)) return 'snow'
  if (/雾|霾|沙|尘/.test(value)) return 'fog'
  if (/阴/.test(value)) return 'overcast'
  if (/云/.test(value)) return 'cloudy'
  if (/晴/.test(value)) return 'sunny'
  return 'cloudy'
}

export const useWeatherStore = defineStore('weather', () => {
  const loading = ref(false)
  const located = ref(false)
  const error = ref('')
  const data = ref<WeatherPayload | null>(null)

  const region = computed(() => data.value?.region || '定位未开启')
  const shortRegion = computed(() => {
    const payload = data.value
    if (!payload) return '定位未开启'
    return payload.district || payload.city || payload.region || '当前位置'
  })
  const currentDateLabel = computed(() => dateLabel())
  const temperature = computed(() => data.value?.live?.temperature || '--')
  const currentTemperatureRange = computed(() => {
    const today = data.value?.forecast?.[0]
    const low = today?.nighttemp || ''
    const high = today?.daytemp || ''
    if (low && high) return `${low}° / ${high}°`
    if (temperature.value !== '--') return `${temperature.value}°C`
    return '--'
  })
  const weather = computed(() => data.value?.live?.weather || '--')
  const currentIcon = computed(() => weatherIconKey(weather.value))
  const humidity = computed(() => data.value?.live?.humidity || '--')
  const windText = computed(() => {
    const live = data.value?.live
    if (!live?.winddirection && !live?.windpower) return '暂无风力数据'
    return `${live.winddirection || ''}风 ${live.windpower || ''}级`.trim()
  })
  const forecast = computed(() => {
    if (!data.value?.forecast?.length) {
      return [
        { day: '明天', high: '--', low: '--', weather: '--', icon: 'cloudy' },
        { day: dayOffsetLabel(2), high: '--', low: '--', weather: '--', icon: 'cloudy' },
        { day: dayOffsetLabel(3), high: '--', low: '--', weather: '--', icon: 'cloudy' },
      ]
    }
    const tomorrowOnward = data.value.forecast.slice(1, 4)
    const source = tomorrowOnward.length ? tomorrowOnward : data.value.forecast.slice(0, 3)
    return source.map((item, index) => {
      const weatherText = item.dayweather || item.nightweather || '--'
      return {
        day: index === 0 ? '明天' : weekdayLabel(item.date) || dayOffsetLabel(index + 1),
        high: item.daytemp || '--',
        low: item.nighttemp || '--',
        weather: weatherText,
        icon: weatherIconKey(weatherText),
      }
    })
  })

  function readCache() {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return
    try {
      const cached = JSON.parse(raw)
      if (Date.now() - cached.time > CACHE_MAX_AGE) return
      data.value = cached.data
      located.value = true
    } catch {
      localStorage.removeItem(CACHE_KEY)
    }
  }

  function writeCache(payload: WeatherPayload) {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ time: Date.now(), data: payload }))
  }

  function getBrowserPosition(): Promise<GeolocationPosition> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('当前浏览器不支持定位'))
        return
      }
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 10 * 60 * 1000,
      })
    })
  }

  async function getAmapPosition(AMap: any) {
    await amapPlugin(AMap, ['AMap.Geolocation'])
    return new Promise<{ lng: number; lat: number }>((resolve, reject) => {
      const geolocation = new AMap.Geolocation({
        enableHighAccuracy: true,
        timeout: 8000,
        zoomToAccuracy: false,
      })
      geolocation.getCurrentPosition((status: string, result: any) => {
        if (status === 'complete') {
          try {
            resolve(lngLatFromPosition(result.position))
          } catch (error) {
            reject(error)
          }
        } else {
          reject(new Error(result?.message || '定位失败'))
        }
      })
    })
  }

  async function getAmapAddress(AMap: any, lng: number, lat: number) {
    await amapPlugin(AMap, ['AMap.Geocoder'])
    return new Promise<any>((resolve, reject) => {
      const geocoder = new AMap.Geocoder()
      geocoder.getAddress([lng, lat], (status: string, result: any) => {
        if (status === 'complete' && result?.regeocode) {
          resolve(result.regeocode.addressComponent || {})
        } else {
          reject(new Error('当前位置解析失败'))
        }
      })
    })
  }

  async function getAmapLocalCity(AMap: any) {
    await amapPlugin(AMap, ['AMap.CitySearch'])
    return new Promise<any>((resolve, reject) => {
      const citySearch = new AMap.CitySearch()
      citySearch.getLocalCity((status: string, result: any) => {
        if (status === 'complete' && result?.info === 'OK') {
          resolve(result)
        } else {
          reject(new Error(result?.info || '当前城市识别失败'))
        }
      })
    })
  }

  async function getAmapWeather(AMap: any, city: string) {
    await amapPlugin(AMap, ['AMap.Weather'])
    return new Promise<{ live: any; forecast: any }>((resolve, reject) => {
      const weatherApi = new AMap.Weather()
      weatherApi.getLive(city, (liveError: any, live: any) => {
        if (liveError) {
          reject(new Error('实时天气获取失败'))
          return
        }
        weatherApi.getForecast(city, (forecastError: any, forecast: any) => {
          if (forecastError) {
            reject(new Error('天气预报获取失败'))
            return
          }
          resolve({ live, forecast })
        })
      })
    })
  }

  async function convertToAmapLngLat(AMap: any, lng: number, lat: number) {
    // 浏览器原生定位返回 WGS-84 坐标，高德使用 GCJ-02，需转换以免偏移
    if (typeof AMap?.convertFrom !== 'function') {
      return { lng, lat }
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
        // 转换失败时退回原始坐标（区县级精度通常不受影响）
        resolve({ lng, lat })
      })
    })
  }

  async function initWithAmap() {
    const AMap = await loadAmap()
    let address: any
    let approximate = false

    // 非安全源（HTTP + IP）下浏览器 Geolocation 被禁用，直接走 IP 城市定位
    if (!window.isSecureContext) {
      console.info('[定位] 非安全源（HTTP），跳过浏览器定位，直接使用 IP 城市定位')
      const localCity = await getAmapLocalCity(AMap)
      approximate = true
      address = {
        province: localCity.province || '',
        city: localCity.city || '',
        district: '',
        adcode: localCity.adcode || '',
      }
    } else {
      try {
        const position = await getAmapPosition(AMap)
        address = await getAmapAddress(AMap, position.lng, position.lat)
        console.info('[定位] 策略1（高德Geolocation）成功', address)
      } catch (amapError: any) {
        console.warn('[定位] 策略1失败，尝试策略2（浏览器原生定位）', amapError?.message)
        try {
          const coords = await getBrowserPosition()
          const converted = await convertToAmapLngLat(AMap, coords.coords.longitude, coords.coords.latitude)
          address = await getAmapAddress(AMap, converted.lng, converted.lat)
          console.info('[定位] 策略2（浏览器定位+逆地理编码）成功', address)
        } catch (browserError: any) {
          console.warn('[定位] 策略2失败，降级策略3（IP城市定位）', browserError?.message)
          error.value = friendlyLocationError(amapError?.message)
          const localCity = await getAmapLocalCity(AMap)
          approximate = true
          address = {
            province: localCity.province || '',
            city: localCity.city || '',
            district: '',
            adcode: localCity.adcode || '',
          }
        }
      }
    }

    const adcode = String(address.adcode || '')
    const city = Array.isArray(address.city) ? '' : (address.city || '')
    const district = Array.isArray(address.district) ? '' : (address.district || '')
    const region = [address.province, city, district].filter(Boolean).join(' ')
    const weatherPayload = await getAmapWeather(AMap, adcode || city || district)
    const live = weatherPayload.live || {}
    const forecastData = weatherPayload.forecast || {}

    return {
      province: address.province || '',
      city,
      district,
      adcode,
      region: approximate ? `${region || city || '当前城市'}（城市定位）` : (region || city || district || '当前位置'),
      formatted_address: region || city || district || '当前位置',
      live: {
        weather: live.weather || '',
        temperature: String(live.temperature ?? ''),
        humidity: String(live.humidity ?? ''),
        winddirection: live.windDirection || live.winddirection || '',
        windpower: live.windPower || live.windpower || '',
        reporttime: live.reportTime || live.reporttime || '',
      },
      forecast: (forecastData.forecasts || []).slice(0, 4).map((item: any) => ({
        date: item.date || '',
        week: item.week || '',
        dayweather: item.dayWeather || item.dayweather || '',
        nightweather: item.nightWeather || item.nightweather || '',
        daytemp: String(item.dayTemp ?? item.daytemp ?? ''),
        nighttemp: String(item.nightTemp ?? item.nighttemp ?? ''),
        daywind: item.dayWind || item.daywind || '',
        daypower: item.dayPower || item.daypower || '',
      })),
    } as WeatherPayload
  }

  async function initWithBackend() {
    const position = await getBrowserPosition()
    return await api.getLocationWeather(
      position.coords.longitude,
      position.coords.latitude,
    )
  }

  async function init(force = false, fallbackRegion = '') {
    if (loading.value) return
    if (!force && data.value) return
    if (!force) readCache()
    if (!force && data.value) return

    loading.value = true
    error.value = ''
    try {
      let payload: WeatherPayload
      // HTTP（非安全源）环境下浏览器精确定位不可用：
      // 优先用用户资料里的精确地区查天气（能到区县级），没有才走 IP 城市定位
      if (!window.isSecureContext && fallbackRegion) {
        console.info('[定位] 非安全源（HTTP），使用用户资料地区查天气:', fallbackRegion)
        try {
          payload = await api.getWeatherByRegion(fallbackRegion)
        } catch (regionError: any) {
          console.warn('[定位] 用户地区查天气失败，降级到 IP 城市定位', regionError?.message)
          payload = await initWithAmap()
        }
      } else {
        try {
          payload = await initWithAmap()
        } catch (caught) {
          console.warn('高德定位天气获取失败，尝试切换后端定位天气接口', caught)
          // 后端接口也需要浏览器定位，非安全源下跳过
          if (window.isSecureContext) {
            payload = await initWithBackend()
          } else {
            throw caught
          }
        }
      }
      data.value = payload
      located.value = true
      writeCache(payload)
    } catch (e: any) {
      error.value = e.response?.data?.detail || friendlyLocationError(e.message) || '定位天气获取失败'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    located,
    error,
    data,
    region,
    shortRegion,
    currentDateLabel,
    temperature,
    currentTemperatureRange,
    weather,
    currentIcon,
    humidity,
    windText,
    forecast,
    init,
  }
})
