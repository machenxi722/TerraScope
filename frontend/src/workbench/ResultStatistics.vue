<script setup lang="ts">
import { percent, decisionLabels, type Prediction } from "../api/client";
defineProps<{ prediction: Prediction }>();
defineEmits<{ review: [] }>();
</script>
<template>
  <div class="coverage-card">
    <span>影像内预测覆盖率</span>
    <div class="coverage-number" data-testid="coverage">
      {{ percent(prediction.metrics.coverage_percent) }}
    </div>
    <div class="coverage-track">
      <span
        :style="{
          width: Math.min(prediction.metrics.coverage_percent ?? 0, 100) + '%',
        }"
      />
    </div>
    <span class="coverage-foot"
      >{{ prediction.metrics.scene_screen_positive ? "达到" : "未达到" }} 1%
      场景筛查阈值</span
    >
  </div>
  <section class="inspector-section">
    <h3>像素统计 <span>整幅影像</span></h3>
    <dl class="metric-list">
      <dt>受淹道路像素</dt>
      <dd>
        {{ prediction.metrics.pred_pixels.toLocaleString() }}
      </dd>
      <dt>有效像素</dt>
      <dd>
        {{ prediction.metrics.valid_pixels.toLocaleString() }}
      </dd>
      <dt>分母依据</dt>
      <dd>
        {{
          prediction.metrics.validity_source === "label_non_255"
            ? "标签非 255 区域"
            : "整幅影像"
        }}
      </dd>
    </dl>
  </section>
  <section class="inspector-section">
    <h3>参考标签评估 <span>当前版本</span></h3>
    <template v-if="prediction.evaluation"
      ><div class="evaluation-grid">
        <div>
          <span>IoU</span
          ><strong>{{ percent(prediction.evaluation.iou, true) }}</strong>
        </div>
        <div>
          <span>精确率</span
          ><strong>{{ percent(prediction.evaluation.precision, true) }}</strong>
        </div>
        <div>
          <span>召回率</span
          ><strong>{{ percent(prediction.evaluation.recall, true) }}</strong>
        </div>
        <div>
          <span>覆盖率误差</span
          ><strong
            >{{ prediction.evaluation.coverage_error_pp.toFixed(4)
            }}<small> pp</small></strong
          >
        </div>
      </div>
    </template>
    <p v-else class="field-hint">未提供参考标签</p>
  </section>
  <section
    v-if="prediction.contract.source_mode === 'live_inference'"
    class="inspector-section"
  >
    <h3>
      推理记录
      <span>{{
        prediction.contract.strategy === "tta4" ? "四视图" : "单视图"
      }}</span>
    </h3>
    <dl class="metric-list">
      <dt>计算设备</dt>
      <dd>{{ prediction.contract.runtime.device }}</dd>
      <dt>推理耗时</dt>
      <dd>
        {{
          Number(prediction.contract.runtime.elapsed_seconds || 0).toFixed(2)
        }}
        秒
      </dd>
    </dl>
  </section>
  <section class="inspector-section">
    <h3>
      复核状态<el-tag size="small" type="info"
        >v{{ prediction.review_revision }}</el-tag
      >
    </h3>
    <p class="field-hint">
      {{
        prediction.reviews[0]
          ? decisionLabels[prediction.reviews[0].decision]
          : "尚未复核"
      }}
    </p>
    <el-button class="full-button" @click="$emit('review')"
      >打开人工复核</el-button
    >
  </section>
</template>

<style scoped>
.evaluation-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
.evaluation-grid > div { padding: 9px 7px; }
.evaluation-grid strong { font-size: 21px; }
.inspector-section { padding: 11px 16px; }
.metric-list { gap: 6px 12px; }
@media (max-width: 950px) { .evaluation-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
