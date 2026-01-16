<script>
  import { onMount } from "svelte";

  let { direction = "up", delay = 0, threshold = 0.1, once = true, children } = $props();

  let el = $state(null);
  let visible = $state(true); // Start visible for fallback

  const directionClass = {
    up: "",
    down: "from-down",
    left: "from-left",
    right: "from-right",
    scale: "from-scale",
  };

  onMount(() => {
    if (typeof IntersectionObserver === "undefined" || !el) {
      visible = true;
      return;
    }

    // Start hidden for animation effect
    visible = false;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setTimeout(() => {
              visible = true;
            }, delay);
            if (once) {
              observer.unobserve(el);
            }
          } else if (!once) {
            visible = false;
          }
        });
      },
      { threshold, rootMargin: "50px" }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  });
</script>

<div
  bind:this={el}
  class="reveal {directionClass[direction] || ''}"
  class:visible
  style={delay ? `transition-delay: ${delay}ms;` : ""}
>
  {@render children()}
</div>
