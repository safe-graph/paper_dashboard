<script>
  import { onDestroy, onMount } from "svelte";
  import * as echarts from "echarts";

  const mildTheme = {
    color: ["#94b0ff", "#7fc8c2", "#f2b6a0", "#c6b2ff", "#f7d19e", "#9dbad5"],
    backgroundColor: "transparent",
    textStyle: {
      color: "#e6edf3",
      fontFamily: "Manrope, system-ui, sans-serif",
    },
    title: {
      textStyle: {
        color: "#e6edf3",
        fontWeight: 600,
      },
    },
    axisLine: { lineStyle: { color: "#6b7a88" } },
    axisLabel: { color: "#b7c3cd" },
    splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
    tooltip: {
      backgroundColor: "rgba(21,27,36,0.92)",
      borderColor: "rgba(255,255,255,0.08)",
      textStyle: { color: "#e6edf3" },
    },
  };
  let themeRegistered = false;

  export let option;
  export let height = "320px";

  let el;
  let chart;
  let resizeObserver;

  function render() {
    if (!el) return;
    try {
      if (!themeRegistered) {
        echarts.registerTheme("mild", mildTheme);
        themeRegistered = true;
      }
      if (!chart) {
        chart = echarts.init(el, "mild", { renderer: "canvas" });
      }
      if (option) {
        chart.setOption(option, true);
      }
    } catch (err) {
      console.error("EChart render error", err);
      el.innerHTML = `<div style="color:#9aa8b5;padding:8px;">Chart failed: ${err?.message || err}</div>`;
    }
  }

  onMount(() => {
    render();
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        try {
          chart?.resize();
        } catch (err) {
          console.error("EChart resize error", err);
        }
      });
      resizeObserver.observe(el);
    } else {
      // Fallback for very old browsers: resize on window resize
      const handler = () => {
        try {
          chart?.resize();
        } catch (err) {
          console.error("EChart resize error", err);
        }
      };
      window.addEventListener("resize", handler);
      resizeObserver = {
        disconnect() {
          window.removeEventListener("resize", handler);
        },
      };
    }
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
