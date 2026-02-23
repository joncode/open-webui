<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { nextStep, getAllSteps } from '$lib/apis/chats';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let chatId: string = '';
	export let currentStep: number = 1;
	export let totalSteps: number = 0;
	export let planSummary: string = '';

	const dispatch = createEventDispatcher();

	let loading = false;

	async function handleNext() {
		if (loading || !chatId) return;
		loading = true;
		try {
			const res = await nextStep(localStorage.token, chatId);
			dispatch('nextStep', res);
		} catch (err) {
			console.error('nextStep failed:', err);
		} finally {
			loading = false;
		}
	}

	async function handleShowAll() {
		if (!chatId) return;
		try {
			const res = await getAllSteps(localStorage.token, chatId);
			dispatch('showAllSteps', res);
		} catch (err) {
			console.error('getAllSteps failed:', err);
		}
	}

	$: progress = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;
</script>

{#if totalSteps > 0}
	<div class="mt-3">
		<!-- Sunflower progress bar -->
		<div
			class="w-full h-1.5 bg-jaco-dusty/20 rounded-full overflow-hidden mb-2"
			role="progressbar"
			aria-valuenow={currentStep}
			aria-valuemin={1}
			aria-valuemax={totalSteps}
			aria-label="Step {currentStep} of {totalSteps}"
		>
			<div
				class="h-full bg-jaco-sunflower rounded-full transition-all duration-300 ease-out"
				style="width: {progress}%"></div>
		</div>

		<div class="flex items-center gap-3 text-sm">
			<span class="text-jaco-dusty">
				Step {currentStep} of ~{totalSteps}
			</span>

			<button
				on:click={handleNext}
				disabled={loading}
				class="px-4 py-1.5 bg-jaco-red text-jaco-cream rounded-full text-sm font-medium
					   hover:bg-jaco-red/90 transition-colors disabled:opacity-50 flex items-center gap-1.5"
			>
				{#if loading}
					<Spinner className="size-3" />
					Working…
				{:else}
					Next →
				{/if}
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
	</div>
{/if}
