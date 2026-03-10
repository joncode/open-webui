<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Landing from '$lib/components/landing/Landing.svelte';
	import { page } from '$app/stores';
	import { user } from '$lib/stores';

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
	});
</script>

{#if $user}
	<Chat />
{:else}
	<Landing />
{/if}
