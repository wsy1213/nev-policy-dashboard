<script setup>
import { ref, computed, onMounted } from 'vue'
import PolicyCard from './components/PolicyCard.vue'
import IndustryCard from './components/IndustryCard.vue'
import IntlCard from './components/IntlCard.vue'
import MediaCard from './components/MediaCard.vue'

// ─── 周工具函数 ───
function getMonday(d) {
  const date = new Date(d)
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

function getSunday(monday) {
  const d = new Date(monday)
  d.setDate(d.getDate() + 6)
  return d
}

function formatDate(d) {
  const m = d.getMonth() + 1
  const day = d.getDate()
  return `${m}月${day}日`
}

function formatDateFull(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getISOWeekNumber(d) {
  const date = new Date(d)
  date.setHours(0, 0, 0, 0)
  date.setDate(date.getDate() + 3 - ((date.getDay() + 6) % 7))
  const week1 = new Date(date.getFullYear(), 0, 4)
  return 1 + Math.round(((date - week1) / 86400000 - 3 + ((week1.getDay() + 6) % 7)) / 7)
}

function getWeekKey(dateStr) {
  if (!dateStr) return null
  const monday = getMonday(dateStr)
  return formatDateFull(monday)
}

// ─── 数据 ───
const allPolicies = ref([])
const allIndustry = ref([])
const allIntl = ref([])
const allMedia = ref([])
const briefData = ref(null)
const loading = ref(true)

// 当前选中的周（用周一日期作为 key）
const selectedWeekKey = ref('')

// 搜索
const searchText = ref('')

// ─── 去重（含模糊标题匹配） ───
function titleSimilar(a, b) {
  if (!a || !b) return false
  // 提取标题中的数字（年月期数等），数字不同则视为不同条目
  const nums = s => (s.match(/\d+/g) || []).join(',')
  if (nums(a) !== nums(b)) return false
  const clean = s => s.replace(/[\s，。、；：！？""''\-—·()（）《》【】\[\]|｜/\\,.;:!?'"+丨]/g, '')
  const ca = clean(a), cb = clean(b)
  if (ca === cb) return true
  const shorter = ca.length <= cb.length ? ca : cb
  const longer = ca.length <= cb.length ? cb : ca
  // 短标题被长标题包含
  if (shorter.length >= 8 && longer.includes(shorter)) return true
  // 检查最长公共子串占短标题比例
  let maxCommon = 0
  for (let i = 0; i < shorter.length; i++) {
    for (let j = i + 1; j <= shorter.length; j++) {
      const sub = shorter.slice(i, j)
      if (longer.includes(sub)) { maxCommon = Math.max(maxCommon, sub.length) }
      else break
    }
  }
  if (maxCommon >= 10 && maxCommon / shorter.length >= 0.5) return true
  // 字符重叠比例
  let common = 0
  for (let i = 0; i < shorter.length; i++) {
    if (longer.includes(shorter[i])) common++
  }
  return common / shorter.length > 0.85
}

function dedup(items) {
  const seenUrl = new Set()
  const titles = []
  return items.filter(it => {
    const url = it.url || ''
    const title = it.title || ''
    if (url && seenUrl.has(url)) return false
    if (title && titles.some(t => titleSimilar(t, title))) return false
    if (url) seenUrl.add(url)
    if (title) titles.push(title)
    return true
  })
}

// ─── 数据加载 ───
async function loadData() {
  loading.value = true
  try {
    const manifestRes = await fetch('./data/manifest.json')
    const manifest = await manifestRes.json()
    const policyData = []
    for (const file of manifest.files) {
      const res = await fetch(`./data/${file}`)
      policyData.push(...await res.json())
    }
    allPolicies.value = dedup(policyData)

    try {
      const indManifestRes = await fetch('./data/industry/manifest.json')
      const indManifest = await indManifestRes.json()
      const indData = []
      for (const file of indManifest.files) {
        const res = await fetch(`./data/industry/${file}`)
        indData.push(...await res.json())
      }
      allIndustry.value = dedup(indData)
    } catch { allIndustry.value = [] }

    try {
      const intlManifestRes = await fetch('./data/international/manifest.json')
      const intlManifest = await intlManifestRes.json()
      const intlData = []
      for (const file of intlManifest.files) {
        const res = await fetch(`./data/international/${file}`)
        intlData.push(...await res.json())
      }
      allIntl.value = dedup(intlData)
    } catch { allIntl.value = [] }

    try {
      const mediaManifestRes = await fetch('./data/media/manifest.json')
      const mediaManifest = await mediaManifestRes.json()
      const mediaData = []
      for (const file of mediaManifest.files) {
        const res = await fetch(`./data/media/${file}`)
        mediaData.push(...await res.json())
      }
      allMedia.value = dedup(mediaData)
    } catch { allMedia.value = [] }
    // 加载周报简报
    try {
      const briefRes = await fetch('./data/brief.json')
      briefData.value = await briefRes.json()
    } catch { briefData.value = null }
  } catch (e) {
    console.error('加载数据失败:', e)
  }
  loading.value = false

  // 默认选中最新的周
  if (availableWeeks.value.length > 0) {
    selectedWeekKey.value = availableWeeks.value[0].key
  }
}

// ─── 所有可用的周（从数据中提取，按时间倒序） ───
const availableWeeks = computed(() => {
  const weekMap = new Map()
  const allData = [...allPolicies.value, ...allIndustry.value, ...allIntl.value, ...allMedia.value]

  for (const item of allData) {
    const key = getWeekKey(item.pub_date)
    if (!key) continue
    if (!weekMap.has(key)) {
      const monday = new Date(key)
      const sunday = getSunday(monday)
      weekMap.set(key, {
        key,
        monday,
        sunday,
        label: `${formatDate(monday)} - ${formatDate(sunday)}`,
        year: monday.getFullYear(),
        weekNum: getISOWeekNumber(monday),
        count: 0,
      })
    }
    weekMap.get(key).count++
  }

  return [...weekMap.values()].sort((a, b) => b.monday - a.monday)
})

// ─── 当前周信息 ───
const currentWeek = computed(() => {
  return availableWeeks.value.find(w => w.key === selectedWeekKey.value) || null
})

const currentWeekIndex = computed(() => {
  return availableWeeks.value.findIndex(w => w.key === selectedWeekKey.value)
})

const hasPrev = computed(() => currentWeekIndex.value < availableWeeks.value.length - 1)
const hasNext = computed(() => currentWeekIndex.value > 0)

function goToPrevWeek() {
  if (hasPrev.value) {
    selectedWeekKey.value = availableWeeks.value[currentWeekIndex.value + 1].key
  }
}
function goToNextWeek() {
  if (hasNext.value) {
    selectedWeekKey.value = availableWeeks.value[currentWeekIndex.value - 1].key
  }
}

// ─── 按周筛选数据 ───
function filterByWeek(items) {
  if (!selectedWeekKey.value) return []
  const monday = new Date(selectedWeekKey.value)
  const sunday = getSunday(monday)
  const monStr = formatDateFull(monday)
  const sunStr = formatDateFull(sunday)
  return items.filter(i => i.pub_date >= monStr && i.pub_date <= sunStr)
}

function filterBySearch(items) {
  if (!searchText.value) return items
  const q = searchText.value.toLowerCase()
  return items.filter(i =>
    (i.title || '').toLowerCase().includes(q) ||
    (i.source || '').toLowerCase().includes(q) ||
    (i.title_en || '').toLowerCase().includes(q) ||
    (i.issuing_body || '').toLowerCase().includes(q)
  )
}

const weekPolicies = computed(() => filterBySearch(filterByWeek(allPolicies.value)))
const weekIndustry = computed(() => filterBySearch(filterByWeek(allIndustry.value)))
const weekIntl = computed(() => filterBySearch(filterByWeek(allIntl.value)))
const weekMedia = computed(() => filterBySearch(filterByWeek(allMedia.value)))

const weekTotal = computed(() =>
  weekPolicies.value.length + weekIndustry.value.length +
  weekIntl.value.length + weekMedia.value.length
)

// 周选择下拉
const showWeekPicker = ref(false)

function selectWeek(key) {
  selectedWeekKey.value = key
  showWeekPicker.value = false
}

// 解析周报内容为分块
function parseBrief(content) {
  if (!content) return []
  const blocks = []
  const lines = content.split('\n')
  let currentTitle = ''
  let currentText = ''

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    // 匹配 **📊 产业数据** 或 **总结** 格式
    const match = trimmed.match(/^\*\*(.+?)\*\*$/)
    if (match) {
      if (currentTitle && currentText) {
        blocks.push({ title: currentTitle, text: currentText.trim() })
      }
      currentTitle = match[1]
      currentText = ''
    } else {
      currentText += (currentText ? ' ' : '') + trimmed
    }
  }
  if (currentTitle && currentText) {
    blocks.push({ title: currentTitle, text: currentText.trim() })
  }
  return blocks
}

onMounted(() => {
  loadData()
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.week-picker')) {
      showWeekPicker.value = false
    }
  })
})
</script>

<template>
  <div class="page">
    <!-- ═══ 顶栏 ═══ -->
    <header class="topbar">
      <div class="topbar__inner">
        <img src="/fudan-logo.png" alt="复旦大学" class="topbar__logo" />
        <h1 class="topbar__brand">新能源汽车产业周报</h1>
        <span class="topbar__divider"></span>
        <span class="topbar__org">复旦大学经济科学智能研究中心</span>
        <div class="topbar__spacer"></div>
        <div class="search-bar">
          <svg class="search-bar__icon" width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <input v-model="searchText" class="search-bar__input" type="text" placeholder="搜索标题、来源..." />
        </div>
      </div>
    </header>

    <!-- ═══ 周报头 ═══ -->
    <section class="hero" v-if="!loading && currentWeek">
      <div class="hero__inner">
        <div class="hero__top">
          <div class="hero__divider"></div>
          <p class="hero__subtitle">WEEKLY BRIEFING</p>
        </div>
        <div class="week-nav">
          <button class="week-nav__btn" :disabled="!hasPrev" @click="goToPrevWeek">
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <div class="week-picker">
            <button class="week-nav__current" @click.stop="showWeekPicker = !showWeekPicker">
              <span class="week-nav__range">{{ currentWeek.label }}  · 第{{ currentWeek.weekNum }}周</span>
              <svg class="week-nav__chevron" :class="{ open: showWeekPicker }" width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4.5 6.5l3.5 3.5 3.5-3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <Transition name="dropdown">
              <div v-if="showWeekPicker" class="week-dropdown">
                <button v-for="w in availableWeeks" :key="w.key" class="week-dropdown__item" :class="{ active: w.key === selectedWeekKey }" @click="selectWeek(w.key)">
                  <span>{{ w.label }}</span>
                  <span class="week-dropdown__meta">第{{ w.weekNum }}周 · {{ w.count }}条</span>
                </button>
              </div>
            </Transition>
          </div>
          <button class="week-nav__btn" :disabled="!hasNext" @click="goToNextWeek">
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none"><path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>

        <div class="hero__stats">
          <span class="hero__stat">政策法规 <b>{{ weekPolicies.length }}</b></span>
          <span class="hero__stat">行业新闻 <b>{{ weekIndustry.length }}</b></span>
          <span class="hero__stat">媒体报道 <b>{{ weekMedia.length }}</b></span>
          <span class="hero__stat">国际动态 <b>{{ weekIntl.length }}</b></span>
        </div>
      </div>
    </section>

    <!-- ═══ 加载中 ═══ -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载数据中...</p>
    </div>

    <!-- ═══ 周报总结 ═══ -->
    <section class="brief" v-if="!loading && briefData && briefData.content">
      <div class="brief__inner">
        <div class="brief__head">
          <span class="brief__icon">📋</span>
          <h2 class="brief__title">本周总结</h2>
        </div>
        <div class="brief__body">
          <div v-for="(block, idx) in parseBrief(briefData.content)" :key="idx" class="brief__block">
            <h3 class="brief__block-title">{{ block.title }}</h3>
            <p class="brief__block-text">{{ block.text }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 内容区 ═══ -->
    <main class="content" v-if="!loading && currentWeek">
      <div class="content__inner">

        <div v-if="weekTotal === 0" class="empty">
          <p class="empty__text">本周暂无数据</p>
        </div>

        <!-- 政策法规 -->
        <section class="section" v-if="weekPolicies.length > 0">
          <div class="section__head">
            <span class="section__label section__label--gov">政策法规</span>
            <span class="section__line"></span>
          </div>
          <div class="article-list">
            <PolicyCard v-for="item in weekPolicies" :key="item.id" :policy="item" />
          </div>
        </section>

        <!-- 行业新闻 -->
        <section class="section" v-if="weekIndustry.length > 0">
          <div class="section__head">
            <span class="section__label section__label--data">行业新闻</span>
            <span class="section__line"></span>
          </div>
          <div class="article-list">
            <IndustryCard v-for="item in weekIndustry" :key="item.id" :item="item" />
          </div>
        </section>

        <!-- 媒体报道 -->
        <section class="section" v-if="weekMedia.length > 0">
          <div class="section__head">
            <span class="section__label section__label--media">媒体报道</span>
            <span class="section__line"></span>
          </div>
          <div class="article-list">
            <MediaCard v-for="item in weekMedia" :key="item.id" :item="item" />
          </div>
        </section>

        <!-- 国际动态 -->
        <section class="section" v-if="weekIntl.length > 0">
          <div class="section__head">
            <span class="section__label section__label--intl">国际动态</span>
            <span class="section__line"></span>
          </div>
          <div class="article-list">
            <IntlCard v-for="item in weekIntl" :key="item.id" :item="item" />
          </div>
        </section>

      </div>
    </main>

    <!-- ═══ 无数据 ═══ -->
    <div v-if="!loading && availableWeeks.length === 0" class="empty" style="padding: 120px 20px;">
      <p class="empty__text">暂无数据</p>
    </div>

    <!-- ═══ Footer ═══ -->
    <footer class="footer">
      <div class="footer__inner">
        <img src="/fudan-logo.png" alt="复旦大学" class="footer__logo" />
        <div class="footer__text">
          <span>复旦大学经济科学智能研究中心</span>
          <span class="footer__sep">·</span>
          <span>新能源汽车产业周报</span>
          <span class="footer__sep">·</span>
          <span>&copy; 2026</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ═══════════ 页面 ═══════════ */
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

/* ═══════════ 顶栏 ═══════════ */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 1px 8px rgba(0,0,0,0.04);
}

.topbar__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 22px 32px;
  display: flex;
  align-items: center;
  gap: 0;
}

.topbar__logo {
  width: 56px;
  height: 56px;
  margin-right: 14px;
  flex-shrink: 0;
}

.topbar__brand {
  font-family: "PingFang SC", "SF Pro Display", "Helvetica Neue", "Microsoft YaHei", sans-serif;
  font-size: 26px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: 0.08em;
  margin: 0;
  white-space: nowrap;
}

.topbar__divider {
  width: 1px;
  height: 28px;
  background: var(--border-dark);
  margin: 0 20px;
  flex-shrink: 0;
  opacity: 0.4;
}

.topbar__org {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 400;
  letter-spacing: 0.02em;
  white-space: nowrap;
  flex-shrink: 0;
}

.topbar__spacer {
  flex: 1;
}

/* ─── 搜索 ─── */
.search-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--bg-secondary);
  transition: all var(--transition-fast);
}

.search-bar:focus-within {
  border-color: var(--border-dark);
  background: var(--bg);
}

.search-bar__icon { color: var(--text-muted); flex-shrink: 0; }

.search-bar__input {
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: var(--text);
  width: 160px;
}

.search-bar__input::placeholder { color: var(--text-muted); }

/* ═══════════ Hero 区 ═══════════ */
.hero {
  background: var(--bg);
  border-bottom: 3px solid var(--accent);
}

.hero__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 40px 24px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.hero__top {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.hero__divider {
  width: 40px;
  height: 3px;
  background: var(--accent);
  border-radius: 2px;
}

.hero__subtitle {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--accent);
  text-transform: uppercase;
}

/* ─── 周切换器 ─── */
.week-nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.week-nav__btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.week-nav__btn:hover:not(:disabled) {
  background: var(--bg-hover);
}

.week-nav__btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.week-picker { position: relative; }

.week-nav__current {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.week-nav__current:hover { opacity: 0.7; }

.week-nav__range {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}

.week-nav__chevron {
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
  margin-top: 2px;
}

.week-nav__chevron.open { transform: rotate(180deg); }

/* ─── 周下拉 ─── */
.week-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  z-index: 200;
  min-width: 280px;
  max-height: 360px;
  overflow-y: auto;
  padding: 6px;
}

.week-dropdown__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: var(--text);
  transition: all var(--transition-fast);
  text-align: left;
}

.week-dropdown__item:hover { background: var(--bg-hover); }

.week-dropdown__item.active {
  background: var(--accent);
  color: #fff;
}

.week-dropdown__meta {
  font-size: 12px;
  color: var(--text-tertiary);
}

.week-dropdown__item.active .week-dropdown__meta {
  color: rgba(255, 255, 255, 0.7);
}

.dropdown-enter-active, .dropdown-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-4px);
}

/* ─── 统计 ─── */
.hero__stats {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  justify-content: center;
}

.hero__stat {
  font-size: 15px;
  color: var(--text-tertiary);
}

.hero__stat b {
  font-weight: 700;
  color: var(--text);
  margin-left: 4px;
  font-size: 16px;
}

/* ═══════════ 加载和空状态 ═══════════ */
.loading-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty {
  text-align: center;
  padding: 60px 20px;
}

.empty__text {
  color: var(--text-tertiary);
  font-size: 15px;
}

/* ═══════════ 周报总结 ═══════════ */
.brief {
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.brief__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 28px 24px 32px;
}
.brief__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}
.brief__icon { font-size: 18px; }
.brief__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.5px;
}
.brief__body {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.brief__block {
  background: var(--bg-secondary);
  border-radius: 10px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  transition: box-shadow 0.15s;
}
.brief__block:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.brief__block:last-child {
  grid-column: 1 / -1;
  background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
  border-color: #c3d7f7;
}
.brief__block-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 8px;
}
.brief__block:last-child .brief__block-title {
  color: #1a4cb0;
}
.brief__block-text {
  font-size: 13px;
  line-height: 1.75;
  color: var(--text-secondary);
}
.brief__block:last-child .brief__block-text {
  color: #2d4a7c;
  font-weight: 500;
}

/* ═══════════ 内容区 ═══════════ */
.content { flex: 1; }

.content__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 32px 24px 60px;
  display: flex;
  flex-direction: column;
  gap: 36px;
}

/* ─── 板块 ─── */
.section {
  background: var(--bg);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  overflow: hidden;
}

.section__head {
  padding: 16px 24px 14px;
  border-bottom: 1px solid var(--border);
}

.section__label {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.04em;
  padding-left: 14px;
  border-left: 4px solid currentColor;
  display: block;
}

.section__label--gov  { color: var(--src-gov); }
.section__label--data { color: var(--src-data); }
.section__label--intl { color: var(--src-intl); }
.section__label--media { color: var(--src-media); }

.section__line {
  display: none;
}

.article-list {
  display: flex;
  flex-direction: column;
}

/* ═══════════ Footer ═══════════ */
.footer {
  border-top: 1px solid var(--border);
  background: var(--bg);
  padding: 28px 24px;
}

.footer__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.footer__logo {
  width: 36px;
  height: 36px;
  opacity: 0.6;
}

.footer__text {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  gap: 4px;
  align-items: center;
}

.footer__sep {
  margin: 0 2px;
}
</style>
