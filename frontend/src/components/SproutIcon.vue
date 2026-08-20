<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    class="sprout-icon"
  >
    <!-- 底部土壤弧线 + 浅椭圆，形成"地气" -->
    <path
      v-if="withSoil"
      d="M 9 41 C 16 39.5, 32 39.5, 39 41"
      :stroke="iconColor"
      stroke-width="2"
      stroke-linecap="round"
      opacity="0.35"
    />
    <ellipse
      v-if="withSoil"
      cx="24"
      cy="41"
      rx="12"
      ry="1.5"
      :fill="iconColor"
      opacity="0.15"
    />

    <!-- 主茎：优雅 S 形弯曲，自下而上贯穿，更有生长感 -->
    <path
      d="M 24 41 C 22 33 26 26 24 15"
      :stroke="iconColor"
      stroke-width="2.4"
      stroke-linecap="round"
      fill="none"
    />

    <!-- 左叶（饱满叶形，位置偏低，向左下方舒展） -->
    <path
      d="M 24 29 C 20 24 12 25 8 32 C 13 35 20 34 24 29 Z"
      :fill="iconColor"
    />

    <!-- 右叶（饱满叶形，位置偏高，向右上方舒展，辅色形成层次） -->
    <path
      d="M 24 21 C 28 16 35 15 39 16 C 35 20 29 22 24 21 Z"
      :fill="accentColor"
    />

    <!-- 顶嫩芽：圆润水滴形，象征"生长 · 清新" -->
    <path
      d="M 24 5 C 19 9 19 14 24 16 C 29 14 29 9 24 5 Z"
      :fill="iconColor"
    />

    <!-- 叶脉：左（沿叶轴的柔和曲线） -->
    <path
      d="M 23 29 C 19 28 14 30 9 31"
      stroke="rgba(255,255,255,.6)"
      stroke-width="0.9"
      stroke-linecap="round"
      fill="none"
    />

    <!-- 叶脉：右 -->
    <path
      d="M 25 21 C 29 20 34 18 38 16"
      stroke="rgba(255,255,255,.75)"
      stroke-width="0.9"
      stroke-linecap="round"
      fill="none"
    />

    <!-- 露珠高光：顶芽上的微光，提示"清新 · 饱满" -->
    <circle cx="22" cy="9" r="0.9" fill="#ffffff" opacity="0.85" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: number | string
  variant?: 'light' | 'dark' | 'white' | 'auto'
  withSoil?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 32,
  variant: 'auto',
  withSoil: false,
})

/** 主色：茎、左叶、顶嫩芽、土堆 */
const iconColor = computed(() => {
  if (props.variant === 'white') return '#FFFFFF'
  if (props.variant === 'light') return '#B9F0C9'
  return '#168744' // dark / auto：品牌绿
})

/** 辅色：右叶（亮一档，与主色形成层次感） */
const accentColor = computed(() => {
  if (props.variant === 'white') return 'rgba(255,255,255,.75)'
  if (props.variant === 'light') return '#E1FAD8'
  return '#34C25C' // dark / auto：亮一档的品牌绿
})

/** 兼容旧 prop：soilColor 现在没在模板直接用到，保留 export 不报错 */
const soilColor = computed(() => iconColor.value)
</script>

<style scoped>
.sprout-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
