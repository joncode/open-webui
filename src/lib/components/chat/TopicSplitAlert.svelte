<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';

	export let oldTopic: string = '';
	export let newTopic: string = '';
	export let timeoutMs: number = 5000;

	const dispatch = createEventDispatcher();

	let progress = 100;
	let intervalId: ReturnType<typeof setInterval>;
	let visible = true;

	onMount(() => {
		const tickMs = 50;
		const decrement = (tickMs / timeoutMs) * 100;

		intervalId = setInterval(() => {
			progress -= decrement;
			if (progress <= 0) {
				progress = 0;
				clearInterval(intervalId);
				confirmSplit();
			}
		}, tickMs);
	});

	onDestroy(() => {
		if (intervalId) clearInterval(intervalId);
	});

	function cancelSplit() {
		clearInterval(intervalId);
		visible = false;
		dispatch('cancelSplit');
	}

	function confirmSplit() {
		visible = false;
		dispatch('confirmSplit');
	}
</script>

{#if visible}
	<div
		class="relative overflow-hidden rounded-xl border border-jaco-sunflower/40
			   bg-gradient-to-r from-jaco-sunflower/10 to-jaco-cream
			   dark:from-jaco-sunflower/5 dark:to-jaco-vinyl/50
			   dark:border-jaco-sunflower/20 px-5 py-3.5 mb-4"
	>
		<!-- Progress bar countdown -->
		<div
			class="absolute bottom-0 left-0 h-1 bg-jaco-sunflower/60 transition-all duration-50 ease-linear"
			style="width: {progress}%"
		/>

		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-2 text-sm">
				<span>🎸</span>
				<span class="text-jaco-charcoal dark:text-jaco-cream">
					Jaco's about to split
					<strong class="text-jaco-red">{newTopic}</strong>
					out of
					<strong>{oldTopic}</strong>
				</span>
			</div>

			<button
				on:click={cancelSplit}
				class="text-jaco-red font-semibold text-sm whitespace-nowrap
					   hover:underline underline-offset-2 transition-colors"
			>
				Don't do it, Jaco →
			</button>
		</div>
	</div>
{/if}
