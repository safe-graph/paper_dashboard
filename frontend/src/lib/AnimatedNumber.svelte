<script>
  import { tweened } from "svelte/motion";
  import { onMount } from "svelte";

  let { value = 0, duration = 1200, delay = 0, format = (n) => n.toLocaleString("en-US") } = $props();

  // Custom elastic easing
  function elasticOut(t) {
    return Math.sin(-13 * (t + 1) * Math.PI / 2) * Math.pow(2, -10 * t) + 1;
  }

  const displayed = tweened(0, {
    duration,
    easing: elasticOut,
  });

  let started = $state(false);

  onMount(() => {
    setTimeout(() => {
      started = true;
      displayed.set(value);
    }, delay);
  });

  $effect(() => {
    if (started && value !== undefined) {
      displayed.set(value);
    }
  });
</script>

<span class="animated-number">{format(Math.round($displayed))}</span>

<style>
  .animated-number {
    display: inline-block;
    font-variant-numeric: tabular-nums;
  }
</style>
