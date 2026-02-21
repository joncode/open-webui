<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let currentStep: number = 1;
	export let totalSteps: number = 0;
	export let planSummary: string = '';

	const dispatch = createEventDispatcher();

	function handleNext() {
		dispatch('nextStep');
	}

	function handleShowAll() {
		dispatch('showAllSteps');
	}
</script>

{#if totalSteps > 0}
	<div class="flex items-center gap-3 mt-3 text-sm">
		<span class="text-jaco-dusty">
			Step {currentStep} of ~{totalSteps}
		</span>

		<button
			on:click={handleNext}
			class="px-4 py-1.5 bg-jaco-red text-jaco-cream rounded-full text-sm font-medium
				   hover:bg-jaco-red/90 transition-colors"
		>
			Next →
		</button>

		<button
			on:click={handleShowAll}
			class="text-jaco-dusty hover:text-jaco-charcoal dark:hover:text-jaco-cream
				   transition-colors underline-offset-2 hover:underline"
		>
			Show all steps
		</button>

		{#if planSummary}
			<span class="text-jaco-dusty text-xs truncate max-w-48" title={planSummary}>
				{planSummary}
			</span>
		{/if}
	</div>
{/if}
