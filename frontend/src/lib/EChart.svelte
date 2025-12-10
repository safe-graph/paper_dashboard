<script>
  import { onDestroy, onMount } from "svelte";
  import * as echarts from "echarts";

  export let option;
  export let height = "320px";

  let el;
  let chart;
  let resizeObserver;

  function render() {
    if (!el) return;
    try {
      if (!chart) {
        chart = echarts.init(el, null, { renderer: "canvas" });
      }
      if (option) {
        chart.setOption(option, true);
      }
    } catch (err) {
      console.error("EChart render error", err);
      el.innerHTML = `<div style="color:#94a3b8;padding:8px;">Chart failed: ${err?.message || err}</div>`;
    }
  }

  onMount(() => {
    render();
    resizeObserver = new ResizeObserver(() => {
      try {
        chart?.resize();
      } catch (err) {
        console.error("EChart resize error", err);
      }
    });
    resizeObserver.observe(el);
  });

  $: if (chart && option) {
    try {
      chart.setOption(option, true);
    } catch (err) {
      console.error("EChart update error", err);
    }
  }

  onDestroy(() => {
    resizeObserver?.disconnect();
    chart?.dispose();
  });
</script>

<div bind:this={el} style={`width:100%;height:${height};`}></div>
