<template>
  <div class="filter-bar">
    <div class="search-wrapper">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
      </svg>
      <input
        v-model="searchText"
        class="filter-bar__search"
        type="text"
        placeholder="搜索..."
        @input="emitChange"
      />
    </div>
    <template v-if="showSelects">
      <select v-model="selectedCategory" class="filter-bar__select" @change="emitChange">
        <option value="">全部分类</option>
        <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="selectedEffectiveness" class="filter-bar__select" @change="emitChange">
        <option value="">全部时效</option>
        <option v-for="e in effectivenessOptions" :key="e" :value="e">{{ e }}</option>
      </select>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  categories: { type: Array, default: () => [] },
  effectivenessOptions: { type: Array, default: () => [] },
  showSelects: { type: Boolean, default: true },
})

const emit = defineEmits(['filter-change'])

const searchText = ref('')
const selectedCategory = ref('')
const selectedEffectiveness = ref('')

function emitChange() {
  emit('filter-change', {
    searchText: searchText.value,
    category: selectedCategory.value,
    effectiveness: selectedEffectiveness.value,
  })
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.search-wrapper {
  min-width: 180px;
  position: relative;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
  pointer-events: none;
}
.filter-bar__search {
  width: 100%;
  padding: 6px 10px 6px 30px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  outline: none;
  background: var(--bg);
  color: var(--text);
  transition: border-color var(--transition-fast);
}
.filter-bar__search::placeholder {
  color: var(--text-tertiary);
}
.filter-bar__search:focus {
  border-color: var(--text-tertiary);
}
.filter-bar__select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  background: var(--bg);
  color: var(--text-secondary);
  cursor: pointer;
  outline: none;
  transition: border-color var(--transition-fast);
}
.filter-bar__select:focus {
  border-color: var(--text-tertiary);
}
</style>
