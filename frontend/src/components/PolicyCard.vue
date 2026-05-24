<template>
  <a class="item" :href="policy.url" target="_blank" rel="noopener">
    <div class="item__meta">
      <span class="item__source src--gov">{{ policy.issuing_body || '政策文件' }}</span>
      <span v-if="policy.pub_date" class="item__date">{{ policy.pub_date }}</span>
    </div>
    <div class="item__header">
      <h3 class="item__title">{{ policy.title }}</h3>
      <StatusTag v-if="policy.effectiveness" :label="policy.effectiveness" />
    </div>
    <div v-if="policy.doc_number || policy.category" class="item__tags">
      <span v-if="policy.doc_number" class="item__tag">{{ policy.doc_number }}</span>
      <span v-if="policy.category" class="item__tag">{{ policy.category }}</span>
    </div>
    <p v-if="policy.summary" class="item__summary">{{ policy.summary }}</p>
  </a>
</template>

<script setup>
import StatusTag from './StatusTag.vue'

defineProps({
  policy: { type: Object, required: true },
})
</script>

<style scoped>
.item {
  display: block;
  padding: 16px 20px;
  text-decoration: none;
  color: inherit;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition-fast);
}
.item:last-child { border-bottom: none; }
.item:hover { background: var(--bg-hover); }

.item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.item__source {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
  letter-spacing: 0.03em;
}
.src--gov { color: var(--src-gov); background: var(--src-gov-bg); }

.item__date {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.item__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.item__title {
  font-size: 17px;
  font-weight: 600;
  line-height: 1.5;
  flex: 1;
  color: var(--text);
  margin: 0;
}
.item__tags {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.item__tag {
  font-size: 11px;
  color: var(--text-muted);
  padding: 1px 6px;
  border: 1px solid var(--border);
  border-radius: 3px;
}
.item__summary {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-tertiary);
  margin-top: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
