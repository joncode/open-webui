<script lang="ts">
	import { createEventDispatcher, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let stepNumber: number = 1;
	export let stepContent: string = '';
	export let messages: Array<{ role: string; content: string }> = [];
	export let isOpen: boolean = false;

	const dispatch = createEventDispatcher();

	let inputText = '';
	let isStreaming = false;
	let combineLoading = false;
	let discardLoading = false;
	let messagesEndElement: HTMLDivElement;

	function handleSend() {
		if (!inputText.trim() || isStreaming) return;

		dispatch('sendMessage', { content: inputText.trim() });
		inputText = '';
		scrollToBottom();
	}

	async function handleCombine() {
		combineLoading = true;
		dispatch('combine');
	}

	async function handleDiscard() {
		discardLoading = true;
		dispatch('discard');
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	}

	function handleClose() {
		dispatch('close');
	}

	async function scrollToBottom() {
		await tick();
		if (messagesEndElement) {
			messagesEndElement.scrollIntoView({ behavior: 'smooth' });
		}
	}

	$: if (messages.length) {
		scrollToBottom();
	}
</script>

{#if isOpen}
	<div
		transition:fly={{ x: 320, duration: 250 }}
		class="w-80 shrink-0 border-l-2 border-jaco-sunflower bg-jaco-cream/50
			   dark:bg-jaco-vinyl/80 dark:border-jaco-sunflower/40
			   flex flex-col h-full overflow-hidden"
	>
		<!-- Header -->
		<div class="px-4 py-3 border-b border-jaco-leather/15 dark:border-jaco-dusty/20">
			<div class="flex items-center justify-between">
				<div class="font-heading font-semibold text-sm text-jaco-leather dark:text-jaco-sunflower">
					Side Chat: Step {stepNumber}
				</div>
				<button
					on:click={handleClose}
					class="p-1 text-jaco-dusty hover:text-jaco-charcoal dark:hover:text-jaco-cream transition-colors rounded"
					aria-label="Close side chat"
				>
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-4">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			<div class="flex gap-2 mt-2">
				<button
					on:click={handleCombine}
					disabled={combineLoading || discardLoading}
					class="px-3 py-1 bg-jaco-red text-jaco-cream rounded-full text-xs font-semibold
						   hover:bg-jaco-red/90 transition-colors disabled:opacity-50 flex items-center gap-1"
				>
					{#if combineLoading}
						<Spinner className="size-3" />
					{/if}
					Combine ↩
				</button>
				<button
					on:click={handleDiscard}
					disabled={combineLoading || discardLoading}
					class="px-3 py-1 text-jaco-dusty hover:text-jaco-charcoal
						   dark:hover:text-jaco-cream text-xs transition-colors disabled:opacity-50 flex items-center gap-1"
				>
					{#if discardLoading}
						<Spinner className="size-3" />
					{/if}
					Discard
				</button>
			</div>
		</div>

		<!-- Step context -->
		{#if stepContent}
			<div class="px-4 py-2 bg-jaco-sunflower/5 dark:bg-jaco-sunflower/10 border-b border-jaco-leather/10 dark:border-jaco-dusty/15">
				<div class="text-xs text-jaco-dusty leading-relaxed line-clamp-3" title={stepContent}>
					{stepContent}
				</div>
			</div>
		{/if}

		<!-- Messages -->
		<div class="flex-1 overflow-y-auto px-4 py-3 space-y-3">
			{#each messages as msg}
				<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div
						class="max-w-full px-3 py-2 rounded-lg text-sm leading-relaxed
							   {msg.role === 'user'
								? 'bg-jaco-denim text-white rounded-br-sm'
								: 'bg-jaco-warm-white dark:bg-jaco-charcoal border border-jaco-leather/10 dark:border-jaco-dusty/20 rounded-bl-sm'}"
					>
						{msg.content}
					</div>
				</div>
			{/each}
			<div bind:this={messagesEndElement} />
		</div>

		<!-- Input -->
		<div class="px-4 py-3 border-t border-jaco-leather/15 dark:border-jaco-dusty/20">
			<div class="flex gap-2">
				<textarea
					bind:value={inputText}
					on:keydown={handleKeydown}
					placeholder="Ask about this step..."
					rows="2"
					class="flex-1 px-3 py-2 text-sm rounded-lg border border-jaco-leather/20
						   dark:border-jaco-dusty/30 bg-white dark:bg-jaco-vinyl
						   focus:outline-none focus:border-jaco-denim resize-none
						   placeholder:text-jaco-dusty"
				/>
				<button
					on:click={handleSend}
					disabled={!inputText.trim() || isStreaming}
					class="self-end px-3 py-2 bg-jaco-denim text-white rounded-lg text-sm
						   hover:bg-jaco-denim/90 disabled:opacity-40 transition-colors"
				>
					↑
				</button>
			</div>
		</div>
	</div>
{/if}
