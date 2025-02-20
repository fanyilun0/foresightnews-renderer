<script setup lang="ts">
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import foresightData from '../data/foresight_data_20250211.json'
import defaultHiddenIds from '../data/hidenId.json'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const STORAGE_KEY = 'hiddenNewsIds'

// 从localStorage获取隐藏的新闻ID,并与默认隐藏ID合并
const getHiddenIds = () => {
  const localHidden = localStorage.getItem(STORAGE_KEY)
  const localIds = localHidden ? JSON.parse(localHidden) : []
  // 合并本地存储和默认隐藏ID,并去重
  return [...new Set([...localIds, ...defaultHiddenIds])]
}

// 隐藏的新闻ID
const hiddenNewsIds = ref(getHiddenIds())

// 过滤后的新闻列表
const filteredNews = computed(() => {
  return foresightData.items.filter(item => !hiddenNewsIds.value.includes(item.id))
})

// 隐藏新闻
const hideNews = (id: number) => {
  if (!hiddenNewsIds.value.includes(id)) {
    hiddenNewsIds.value.push(id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(hiddenNewsIds.value))
  }
}

// 显示新闻
const showNews = (id: number) => {
  hiddenNewsIds.value = hiddenNewsIds.value.filter(hid => hid !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(hiddenNewsIds.value))
}

// 复制隐藏ID到剪贴板
const copyHiddenIds = async () => {
  try {
    const idsString = JSON.stringify(hiddenNewsIds.value)
    await navigator.clipboard.writeText(idsString)
    alert('已复制到剪贴板')
  } catch (err) {
    console.error('复制失败:', err)
    alert('复制失败')
  }
}

// 导入隐藏ID
const importHiddenIds = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

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
    } catch (err) {
      console.error('导入失败:', err)
      alert('导入失败')
    }
  }
  reader.readAsText(file)
}

// 导出隐藏ID
const exportHiddenIds = () => {
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
const formatTime = (timestamp: number) => {
  return dayjs(timestamp * 1000).fromNow()
}

// 获取链接
const getLink = (item: any) => {
  return item.source_type === 'news' ? item.news.source_link : item.link
}

// 获取标题
const getTitle = (item: any) => {
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
  } else {
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
const isImportant = (item: any) => {
  return item.source_type === 'news' && item.news.is_important
}
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">
        {{ foresightData.title }}
      </h1>
      <div class="flex items-center space-x-4">
        <button
          @click="copyHiddenIds"
          class="px-4 py-2 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 text-sm font-medium"
        >
          复制ID列表
        </button>
        <button
          @click="exportHiddenIds"
          class="px-4 py-2 bg-green-50 text-green-600 rounded hover:bg-green-100 text-sm font-medium"
        >
          导出JSON
        </button>
        <input
          type="file"
          accept=".json"
          @change="importHiddenIds"
          class="hidden"
          id="fileInput"
        >
        <label
          for="fileInput"
          class="px-4 py-2 bg-gray-50 text-gray-600 rounded hover:bg-gray-100 cursor-pointer text-sm font-medium"
        >
          导入JSON
        </label>
      </div>
    </div>

    <div class="mb-4 text-sm text-gray-500">
      已隐藏 {{ hiddenNewsIds.length }} 条新闻
    </div>

    <div class="table-container">
      <table class="min-w-full bg-white">
        <thead class="bg-gray-50">
          <tr>
            <th class="sticky top-0 px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">
              标题
            </th>
            <th class="sticky top-0 px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50 w-32">
              类型
            </th>
            <th class="sticky top-0 px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50 w-40">
              发布时间
            </th>
            <th class="sticky top-0 px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50 w-40">
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
                  class="flex-shrink-0 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800"
                >
                  重要
                </span>
                <div class="text-sm font-medium text-gray-900 truncate">
                  {{ getTitle(item) }}
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <span 
                class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
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
                  class="inline-flex items-center px-3 py-1.5 border border-blue-600 text-blue-600 rounded-md hover:bg-blue-50"
                >
                  查看原文
                </a>
                <button
                  @click="hideNews(item.id)"
                  class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
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
button, a {
  transition: all 0.2s ease;
}
</style>

