<template>
  <a class="item" :href="item.url" target="_blank" rel="noopener">
    <div class="item__meta">
      <span class="item__source src--media">{{ item.source }}</span>
      <span v-if="item.pub_date" class="item__date">{{ item.pub_date }}</span>
    </div>
    <h3 class="item__title">{{ item.title }}</h3>
    <p v-if="item.summary" class="item__summary">{{ item.summary }}</p>
  </a>
</template>

<script setup>
defineProps({
  item: { type: Object, required: true },
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
.src--media { color: var(--src-media); background: var(--src-media-bg); }

.item__date {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.item__title {
  font-size: 17px;
  font-weight: 600;
  line-height: 1.5;
  color: var(--text);
  margin: 0;
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
