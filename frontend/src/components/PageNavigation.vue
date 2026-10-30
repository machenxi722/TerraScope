<script setup lang="ts">
defineProps<{ modelValue: number; count: number; size: number }>();
const emit = defineEmits<{ "update:modelValue": [number] }>();
</script>
<template>
  <div class="row" style="margin-top: 18px">
    <el-button
      :disabled="modelValue <= 1"
      @click="emit('update:modelValue', modelValue - 1)"
      >上一页</el-button
    >
    <span class="muted">第 {{ modelValue }} 页 · 本页 {{ count }} 条</span>
    <el-button
      :disabled="count < size"
      @click="emit('update:modelValue', modelValue + 1)"
      >下一页</el-button
    >
  </div>
</template>
