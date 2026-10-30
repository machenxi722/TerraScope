<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import Map from "ol/Map.js";
import View from "ol/View.js";
import Projection from "ol/proj/Projection.js";
import ImageLayer from "ol/layer/Image.js";
import VectorLayer from "ol/layer/Vector.js";
import ImageStatic from "ol/source/ImageStatic.js";
import VectorSource from "ol/source/Vector.js";
import Draw from "ol/interaction/Draw.js";
import Feature from "ol/Feature.js";
import Polygon from "ol/geom/Polygon.js";
import { Fill, Stroke, Style } from "ol/style.js";
import { getRenderPixel } from "ol/render.js";
import {
  assetUrl,
  type ImageAsset,
  type Prediction,
  type Annotation,
} from "../api/client";
import { toMap, toPixel, pixelAt, clampPolygon } from "./coordinates";
const props = defineProps<{
  image: ImageAsset;
  prediction?: Prediction;
  comparePrediction?: Prediction;
  mode: string;
  layer: string;
  opacity: number;
  swipe: number;
  annotations: Annotation[];
}>();
const emit = defineEmits<{
  annotations: [Annotation[]];
  pixel: [[number, number]];
}>();
const first = ref<HTMLElement>(),
  second = ref<HTMLElement>(),
  drawing = ref(false);
let map: Map | undefined,
  map2: Map | undefined,
  view: View,
  projection: Projection,
  draw: Draw | undefined,
  observer: ResizeObserver | undefined;
let overlay: ImageLayer<ImageStatic>, overlay2: ImageLayer<ImageStatic>;
const vectorSource = new VectorSource(),
  vectorSource2 = new VectorSource();
const regionStyle = new Style({
  stroke: new Stroke({ color: "#f0c942", width: 2 }),
  fill: new Fill({ color: "rgba(240,201,66,0.13)" }),
});
function layerId(pred?: Prediction) {
  return props.layer === "original"
    ? undefined
    : props.layer === "difference"
      ? pred?.difference_asset_id
      : props.layer === "reference"
        ? pred?.gt_layer_asset_id
        : pred?.layer_asset_id;
}
function staticSource(id: string) {
  return new ImageStatic({
    url: assetUrl(id),
    projection,
    imageExtent: [0, -props.image.height, props.image.width, 0],
    interpolate: false,
  });
}
function updateLayers() {
  if (!overlay) return;
  const id = layerId(props.prediction);
  overlay.setSource(id ? staticSource(id) : null);
  overlay.setOpacity(props.opacity / 100);
  const id2 = props.comparePrediction
    ? layerId(props.comparePrediction)
    : undefined;
  overlay2?.setSource(id2 ? staticSource(id2) : null);
  overlay2?.setOpacity(props.opacity / 100);
  map?.render();
}
function renderAnnotations() {
  for (const source of [vectorSource, vectorSource2]) {
    source.clear();
    source.addFeatures(
      props.annotations.map(
        (a) => new Feature(new Polygon([a.coordinates.map((p) => toMap(p))])),
      ),
    );
  }
}
function fit() {
  if (map)
    view.fit([0, -props.image.height, props.image.width, 0], {
      size: map.getSize(),
      padding: [48, 68, 48, 24],
    });
}
function fillView() {
  const size = map?.getSize();
  if (!size || !size[0] || !size[1]) return;
  view.setCenter([props.image.width / 2, -props.image.height / 2]);
  view.setResolution(
    Math.min(props.image.width / size[0], props.image.height / size[1]),
  );
}
function zoom(delta: number) {
  if (view)
    view.animate({ zoom: (view.getZoom() || 0) + delta, duration: 180 });
}
function stopDrawing() {
  if (draw) map?.removeInteraction(draw);
  draw = undefined;
  drawing.value = false;
}
function startDrawing() {
  stopDrawing();
  if (!map) return;
  drawing.value = true;
  draw = new Draw({ type: "Polygon", stopClick: true });
  draw.on("drawend", (event) => {
    const points = clampPolygon(
      (event.feature.getGeometry() as Polygon)
        .getCoordinates()[0]
        .map((p) => toPixel(p)),
      props.image.width,
      props.image.height,
    );
    emit("annotations", [
      ...props.annotations,
      { type: "Polygon", coordinates: points, note: "" },
    ]);
    stopDrawing();
  });
  map.addInteraction(draw);
}
function undo() {
  emit("annotations", props.annotations.slice(0, -1));
}
function keydown(event: KeyboardEvent) {
  const tag = (event.target as HTMLElement)?.tagName;
  if (
    ["INPUT", "TEXTAREA", "SELECT"].includes(tag) ||
    event.ctrlKey ||
    event.metaKey
  )
    return;
  if (event.key === "Escape") stopDrawing();
  if (event.key.toLowerCase() === "f") fit();
}
onMounted(() => {
  const extent = [0, -props.image.height, props.image.width, 0];
  projection = new Projection({
    code: `pixel-${props.image.id}`,
    units: "pixels",
    extent,
  });
  view = new View({
    projection,
    center: [props.image.width / 2, -props.image.height / 2],
    resolution: 2,
    minResolution: 0.05,
    maxResolution: 40,
    extent,
    constrainOnlyCenter: true,
  });
  overlay = new ImageLayer();
  overlay2 = new ImageLayer();
  map = new Map({
    target: first.value,
    controls: [],
    view,
    layers: [
      new ImageLayer({ source: staticSource(props.image.display_asset_id) }),
      overlay,
      new VectorLayer({ source: vectorSource, style: regionStyle }),
    ],
  });
  map2 = new Map({
    target: second.value,
    controls: [],
    view,
    layers: [
      new ImageLayer({ source: staticSource(props.image.display_asset_id) }),
      overlay2,
      new VectorLayer({ source: vectorSource2, style: regionStyle }),
    ],
  });
  overlay.on("prerender", (event) => {
    if (props.mode !== "swipe") return;
    const ctx = event.context as CanvasRenderingContext2D,
      size = map!.getSize()!;
    const topLeft = getRenderPixel(event, [0, 0]),
      topRight = getRenderPixel(event, [(size[0] * props.swipe) / 100, 0]),
      bottomRight = getRenderPixel(event, [
        (size[0] * props.swipe) / 100,
        size[1],
      ]),
      bottomLeft = getRenderPixel(event, [0, size[1]]);
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(...(topLeft as [number, number]));
    ctx.lineTo(...(topRight as [number, number]));
    ctx.lineTo(...(bottomRight as [number, number]));
    ctx.lineTo(...(bottomLeft as [number, number]));
    ctx.closePath();
    ctx.clip();
  });
  overlay.on("postrender", (event) => {
    if (props.mode === "swipe")
      (event.context as CanvasRenderingContext2D).restore();
  });
  map.on("singleclick", (event) => {
    if (drawing.value) return;
    const point = pixelAt(
      event.coordinate,
      props.image.width,
      props.image.height,
    );
    if (point) emit("pixel", point);
  });
  observer = new ResizeObserver(() => {
    map?.updateSize();
    map2?.updateSize();
  });
  observer.observe(first.value!);
  observer.observe(second.value!);
  updateLayers();
  renderAnnotations();
  fillView();
  window.addEventListener("keydown", keydown);
});
watch(
  () => [
    props.prediction?.id,
    props.comparePrediction?.id,
    props.layer,
    props.opacity,
  ],
  updateLayers,
);
watch(() => props.annotations, renderAnnotations, { deep: true });
watch(
  () => [props.mode, props.swipe],
  async () => {
    await nextTick();
    map?.updateSize();
    map2?.updateSize();
    map?.render();
  },
);
onBeforeUnmount(() => {
  stopDrawing();
  map?.setTarget(undefined);
  map2?.setTarget(undefined);
  observer?.disconnect();
  window.removeEventListener("keydown", keydown);
});
defineExpose({ fit, fillView, startDrawing, stopDrawing, undo, zoom });
</script>
<template>
  <div class="map-grid" :class="{ dual: mode === 'compare' }">
    <div class="map-wrap" :class="{ 'is-drawing': drawing }">
      <div
        ref="first"
        class="map-target"
        role="img"
        aria-label="影像判读视图"
      />
      <div class="map-label">
        {{
          drawing
            ? "圈选中：双击完成，Esc 取消"
            : prediction && layer !== "original"
              ? `${prediction.contract.strategy} · ${layer === "reference" ? "参考标签" : layer === "difference" ? "差异图" : "预测图层"}`
              : "原始影像"
        }}
      </div>
      <div
        v-if="mode === 'swipe'"
        class="swipe-divider"
        :style="{ left: swipe + '%' }"
        aria-hidden="true"
      >
        <span>‹ ›</span>
      </div>
    </div>
    <div v-show="mode === 'compare'" class="map-wrap">
      <div
        ref="second"
        class="map-target"
        role="img"
        aria-label="同步对比视图"
      />
      <div class="map-label">
        {{ comparePrediction?.contract.strategy || "原始影像" }} · 同步视图
      </div>
    </div>
  </div>
</template>
