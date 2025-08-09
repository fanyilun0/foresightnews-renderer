<script setup lang="ts">
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { computed, ref } from 'vue'
import foresightData from '../data/foresight_data_20250809.json'
import defaultHiddenIds from '../data/hidenId.json'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const STORAGE_KEY = 'hiddenNewsIds'

// 从localStorage获取隐藏的新闻ID,并与默认隐藏ID合并
function getHiddenIds() {
  const localHidden = localStorage.getItem(STORAGE_KEY)
  const localIds = localHidden ? JSON.parse(localHidden) : []
  // 合并本地存储和默认隐藏ID,并去重
  return [...new Set([...localIds, ...defaultHiddenIds])]
}

// 隐藏的新闻ID
const hiddenNewsIds = ref(getHiddenIds())

// 搜索关键词
const searchKeyword = ref('')
const showImportantOnly = ref(false)

// 过滤后的新闻列表
const filteredNews = computed(() => {
  return foresightData
    .filter(item => !hiddenNewsIds.value.includes(item.id))
    .filter((item) => {
      if (showImportantOnly.value && !isImportant(item))
        return false
      if (!searchKeyword.value)
        return true
      const title = getTitle(item)?.toLowerCase() || ''
      return title.includes(searchKeyword.value.toLowerCase())
    })
})

// 隐藏新闻
function hideNews(id: number) {
  if (!hiddenNewsIds.value.includes(id)) {
    hiddenNewsIds.value.push(id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(hiddenNewsIds.value))
  }
}

// 显示新闻
function showNews(id: number) {
  hiddenNewsIds.value = hiddenNewsIds.value.filter(hid => hid !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(hiddenNewsIds.value))
}

// 复制隐藏ID到剪贴板
async function copyHiddenIds() {
  try {
    const idsString = JSON.stringify(hiddenNewsIds.value)
    await navigator.clipboard.writeText(idsString)
    alert('已复制到剪贴板')
  }
  catch (err) {
    console.error('复制失败:', err)
    alert('复制失败')
  }
}

// 导入隐藏ID
function importHiddenIds(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file)
    return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target?.result as string
      const ids = JSON.parse(content)
      if (Array.isArray(ids)) {
        // 合并导入的ID、默认ID和现有ID
        hiddenNewsIds.value = [...new Set([...hiddenNewsIds.value, ...ids, ...defaultHiddenIds])]
        localStorage.setItem(STORAGE_KEY, JSON.stringify(hiddenNewsIds.value))
        alert('导入成功')
      }
    }
    catch (err) {
      console.error('导入失败:', err)
      alert('导入失败')
    }
  }
  reader.readAsText(file)
}

// 导出隐藏ID
function exportHiddenIds() {
  const idsString = JSON.stringify(hiddenNewsIds.value)
  const blob = new Blob([idsString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'hidden_news_ids.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 格式化时间
function formatTime(timestamp: number) {
  return dayjs(timestamp * 1000).locale('zh-cn').format('YYYY-MM-DD HH:mm:ss')
}

// 获取链接
function getLink(item: any) {
  return item.source_type === 'news' ? item.news.source_link : item.link
}

// 获取标题
function getTitle(item: any) {
  if (item.source_type === 'news') {
    const newsData = item.news
    // 优先使用news对象中的title
    if (newsData?.title) {
      return newsData.title
    }
    // 如果news.title为空,使用name + brief组合
    const name = newsData?.name || ''
    const brief = newsData?.brief || ''
    const briefPreview = brief.slice(0, 10) + (brief.length > 10 ? '...' : '')
    return name ? `${name} ${briefPreview}` : briefPreview
  }
  else {
    // 非news类型,使用外层的title/name/brief
    if (item.title) {
      return item.title
    }

    if (item.article.title) {
      return item.article.title
    }
  }
}

// 判断是否重要消息
function isImportant(item: any) {
  return item.source_type === 'news' && item.news.is_important
}
</script>

<template>
  <div class="mx-auto px-4 py-4 container">
    <div class="mb-6">
      <Author time="2025-08-09" />
      <div class="flex items-center justify-between space-x-4">
        <div class="flex items-center space-x-4">
          <h1 class="text-2xl font-bold">
            精选潜在空投汇总
          </h1>
        </div>

        <div class="max-w-2xl flex flex-1 items-center space-x-4">
          <div class="relative flex-1">
            <input
              v-model="searchKeyword"
              type="text"
              placeholder="搜索关键词..."
              class="w-full border border-gray-300 rounded-md px-4 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
            >
          </div>
          <div class="flex items-center space-x-2">
            <button
              class="whitespace-nowrap rounded px-4 py-2 text-sm font-medium"
              :class="showImportantOnly ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'"
              @click="showImportantOnly = !showImportantOnly"
            >
              {{ showImportantOnly ? '查看全部' : '只看重要' }}
            </button>
          </div>
          <button
            class="whitespace-nowrap rounded bg-blue-50 px-4 py-2 text-sm text-blue-600 font-medium hover:bg-blue-100"
            @click="copyHiddenIds"
          >
            复制隐藏ID列表
          </button>
          <input
            id="fileInput"
            type="file"
            accept=".json"
            class="hidden"
            @change="importHiddenIds"
          >
          <label
            for="fileInput"
            class="cursor-pointer whitespace-nowrap rounded bg-gray-50 px-4 py-2 text-sm text-gray-600 font-medium hover:bg-gray-100"
          >
            导入隐藏ID列表
          </label>
          <div class="whitespace-nowrap text-sm text-gray-500">
            已隐藏 {{ hiddenNewsIds.length }} 条新闻
          </div>
        </div>
      </div>
    </div>

    <div class="table-container">
      <table class="min-w-full bg-white">
        <thead class="bg-gray-50">
          <tr>
            <th class="sticky top-0 bg-gray-50 px-6 py-3 text-left text-xs text-gray-500 font-medium tracking-wider uppercase">
              标题
            </th>
            <th class="sticky top-0 w-32 bg-gray-50 px-6 py-3 text-center text-xs text-gray-500 font-medium tracking-wider uppercase">
              类型
            </th>
            <th class="sticky top-0 w-40 bg-gray-50 px-6 py-3 text-center text-xs text-gray-500 font-medium tracking-wider uppercase">
              发布时间
            </th>
            <th class="sticky top-0 w-40 bg-gray-50 px-6 py-3 text-center text-xs text-gray-500 font-medium tracking-wider uppercase">
              操作
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr
            v-for="item in filteredNews"
            :key="item.id"
            class="hover:bg-gray-50"
          >
            <td class="px-6 py-4">
              <div class="flex items-center space-x-2">
                <span
                  v-if="isImportant(item)"
                  class="inline-flex flex-shrink-0 rounded-full bg-red-100 px-2 text-xs text-red-800 font-semibold leading-5"
                >
                  重要
                </span>
                <div class="truncate text-sm text-gray-900 font-medium">
                  {{ getTitle(item) }}
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <span
                class="inline-flex rounded-full px-2 text-xs font-semibold leading-5"
                :class="item.source_type === 'news' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'"
              >
                {{ item.source_type }}
              </span>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">
              {{ formatTime(item.published_at) }}
            </td>
            <td class="px-6 py-4 text-sm">
              <div class="flex items-center space-x-4">
                <a
                  :href="getLink(item)"
                  target="_blank"
                  :disabled="!getLink(item)"
                  class="inline-flex items-center border border-blue-600 rounded-md px-3 py-1.5 text-blue-600 hover:bg-blue-50"
                >
                  查看原文
                </a>
                <button
                  class="inline-flex items-center border border-gray-300 rounded-md px-3 py-1.5 text-gray-700 hover:bg-gray-50"
                  @click="hideNews(item.id)"
                >
                  隐藏
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.container {
  max-width: 1200px;
}

.table-container {
  max-height: 70vh;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
}

/* 自定义滚动条样式 */
.table-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.table-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.table-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.table-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

th {
  white-space: nowrap;
  z-index: 1;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
}

/* 确保表头在滚动时保持可见 */
thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

/* 美化按钮过渡效果 */
button,
a {
  transition: all 0.2s ease;
}
</style>
