<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number }>(), { size: 20 });
const paths: Record<string, string> = {
  pin: "M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  globe:
    "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c4 5 4 13 0 18-4-5-4-13 0-18Z",
  projects: "M3 6h7l2 2h9v12H3ZM3 6V4h7l2 2h9v2",
  images: "M3 4h18v16H3ZM3 16l5-5 5 5 3-3 5 5M15 8h.01",
  tasks: "M8 6h13M8 12h13M8 18h13M3 5l1 1 2-2M3 11l1 1 2-2M3 17l1 1 2-2",
  chart: "M4 3v17h17M8 16V9M13 16V5M18 16v-5",
  report: "M14 3H5v18h14V8ZM14 3v5h5M8 12h8M8 16h6",
  settings:
    "M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  layers: "m3 8 9-5 9 5-9 5ZM3 12l9 5 9-5M3 16l9 5 9-5",
  calendar: "M4 5h16v16H4ZM4 10h16M8 3v4M16 3v4M8 14h2M14 14h2M8 17h2",
  compare: "M12 3v18M8 6H3v12h5M16 6h5v12h-5M7 9l3 3-3 3M17 9l-3 3 3 3",
  region:
    "M5 4 19 6 21 17 10 21 3 13ZM5 4h.01M19 6h.01M21 17h.01M10 21h.01M3 13h.01",
  review: "M9 5H5v16h14V5h-4M9 3h6v4H9ZM8 13l3 3 5-6",
  info: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 11v6M12 7h.01",
  fit: "M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5M8 8h8v8H8Z",
  expand:
    "M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5M3 3l6 6M21 3l-6 6M3 21l6-6M21 21l-6-6",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  close: "m6 6 12 12M18 6 6 18",
  left: "m14 5-7 7 7 7",
  right: "m10 5 7 7-7 7",
  chevron: "m6 9 6 6 6-6",
  download: "M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6",
  play: "m8 4 13 8-13 8Z",
  user: "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-3a8 8 0 0 1 16 0v3",
  search: "M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Zm-2 5 6 6",
  undo: "M9 5 4 10l5 5M4 10h10a6 6 0 0 1 0 12",
};
</script>
<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="app-icon"
  >
    <path :d="paths[name] || paths.layers" />
  </svg>
</template>
