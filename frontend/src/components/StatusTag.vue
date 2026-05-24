<template>
  <span class="tag" :class="tagClass">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
})

const tagClass = computed(() => {
  const t = props.label
  if (t.includes('有效') || t.includes('现行')) return 'tag--green'
  if (t.includes('失效') || t.includes('废止')) return 'tag--red'
  if (t.includes('修改') || t.includes('修订')) return 'tag--yellow'
  return 'tag--blue'
})
</script>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
  border: 1px solid;
}
.tag--green { color: var(--tag-green); border-color: rgba(10, 124, 66, 0.15); background: var(--tag-green-bg); }
.tag--red   { color: var(--tag-red);   border-color: rgba(193, 28, 28, 0.15);  background: var(--tag-red-bg);   }
.tag--yellow{ color: var(--tag-yellow); border-color: rgba(154, 103, 0, 0.15); background: var(--tag-yellow-bg);}
.tag--blue  { color: var(--tag-blue);  border-color: rgba(0, 96, 208, 0.15);  background: var(--tag-blue-bg);  }
</style>
