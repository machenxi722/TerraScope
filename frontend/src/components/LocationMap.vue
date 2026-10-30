<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import OSM from "ol/source/OSM";
import VectorSource from "ol/source/Vector";
import Cluster from "ol/source/Cluster";
import GeoJSON from "ol/format/GeoJSON";
import { Circle, Fill, Stroke, Style, Text } from "ol/style";
import { defaults as controls } from "ol/control";
import "ol/ol.css";
export interface Locations {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    id: string;
    geometry: { type: "Point"; coordinates: number[] };
    properties: Record<string, unknown>;
  }>;
}
const props = defineProps<{ locations: Locations }>();
const emit = defineEmits<{ select: [id: string] }>();
const target = ref<HTMLDivElement>(),
  selected = ref(""),
  tileFailed = ref(false);
let map: Map | undefined, resize: ResizeObserver | undefined;
const source = new VectorSource(),
  clustered = new Cluster({ distance: 32, source });
function fit() {
  source.clear();
  source.addFeatures(
    new GeoJSON().readFeatures(props.locations, {
      featureProjection: "EPSG:3857",
    }),
  );
  if (source.getFeatures().length)
    map
      ?.getView()
      .fit(source.getExtent()!, { padding: [48, 48, 48, 48], maxZoom: 16 });
}
watch(() => props.locations, fit);
onMounted(() => {
  const base = new OSM();
  base.on("tileloaderror", () => {
    tileFailed.value = true;
  });
  map = new Map({
    target: target.value,
    controls: controls({ attributionOptions: { collapsible: false } }),
    view: new View({ center: [0, 0], zoom: 2 }),
    layers: [
      new TileLayer({ source: base }),
      new VectorLayer({
        source: clustered,
        style: (feature) => {
          const count = feature.get("features").length;
          return new Style({
            image: new Circle({
              radius: count > 1 ? 17 : 9,
              fill: new Fill({ color: "#104a92" }),
              stroke: new Stroke({ color: "#fff", width: 2 }),
            }),
            text: new Text({
              text: count > 1 ? String(count) : "",
              fill: new Fill({ color: "#fff" }),
              font: "bold 13px sans-serif",
            }),
          });
        },
      }),
    ],
  });
  map.on("singleclick", (event) => {
    const cluster = map?.forEachFeatureAtPixel(
      event.pixel,
      (feature) => feature,
    );
    const points = cluster?.get("features");
    if (!points?.length) return;
    if (points.length > 1) {
      const group = new VectorSource({ features: points });
      map
        ?.getView()
        .fit(group.getExtent()!, {
          padding: [55, 55, 55, 55],
          maxZoom: 19,
          duration: 250,
        });
    } else {
      const p = points[0];
      selected.value = `样本 ${p.get("sample_id")} · ${p.get("latitude").toFixed(6)}°, ${p.get("longitude").toFixed(6)}°`;
      emit("select", String(p.getId()));
    }
  });
  resize = new ResizeObserver(() => map?.updateSize());
  if (target.value) resize.observe(target.value);
  fit();
});
onBeforeUnmount(() => {
  resize?.disconnect();
  map?.setTarget(undefined);
});
</script>
<template>
  <div class="location-map-wrap">
    <div ref="target" class="location-map" aria-label="GPS 拍摄点地图" />
    <div class="location-caption">
      {{ selected || `${locations.features.length} 个拍摄点 · WGS 84`
      }}<span v-if="tileFailed"> · 底图暂不可用</span>
    </div>
  </div>
</template>
<style scoped>
.location-map-wrap {
  position: relative;
  background: #e7edf2;
  border: 1px solid #c8d4df;
}
.location-map {
  height: var(--location-map-height, 420px);
  width: 100%;
}
.location-caption {
  position: absolute;
  bottom: 28px;
  left: 10px;
  right: 10px;
  pointer-events: none;
  width: fit-content;
  padding: 5px 9px;
  background: #fffef5f0;
  color: #173d69;
  font-size: 13px;
  box-shadow: 0 1px 5px #183e6422;
}
</style>
