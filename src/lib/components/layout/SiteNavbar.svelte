<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import {
		user,
		showControls,
		showArchivedChats,
		temporaryChatEnabled,
		settings,
		mobile
	} from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import ChatBubbleDotted from '$lib/components/icons/ChatBubbleDotted.svelte';
	import ChatBubbleDottedChecked from '$lib/components/icons/ChatBubbleDottedChecked.svelte';
	import Knobs from '$lib/components/icons/Knobs.svelte';

	const i18n = getContext('i18n');
</script>

<div class="site-navbar">
	<header class="site-navbar-header">
		<a href="/" class="site-navbar-brand">
			<img src="/landing/agent1-wordmark.png" alt="agent1.Manifest" class="site-navbar-logo" />
			<span class="site-navbar-tag">Private AI</span>
		</a>

		<!-- Partners -->
		<div class="site-navbar-partners">
			<span class="site-navbar-partners-label">Your Partners in Decentralization</span>
			<div class="site-navbar-partners-logos">
				<a href="https://manifest.network" target="_blank" rel="noopener noreferrer" class="site-navbar-partner-link">
					<img src="/landing/manifest-logo.png" alt="Manifest Network" class="site-navbar-partner-logo site-navbar-partner-logo--colored site-navbar-partner-logo--manifest" />
				</a>
				<a href="https://rendernetwork.com" target="_blank" rel="noopener noreferrer" class="site-navbar-partner-link">
					<img src="/landing/render-logo.svg" alt="Render Network" class="site-navbar-partner-logo" />
				</a>
				<a href="https://mor.org" target="_blank" rel="noopener noreferrer" class="site-navbar-partner-link">
					<img src="/landing/morpheus-og.png" alt="Morpheus" class="site-navbar-partner-logo site-navbar-partner-logo--colored site-navbar-partner-logo--wordmark" />
				</a>
				<a href="https://venice.ai" target="_blank" rel="noopener noreferrer" class="site-navbar-partner-link">
					<img src="/landing/venice-lockup-white.png" alt="Venice AI" class="site-navbar-partner-logo site-navbar-partner-logo--colored site-navbar-partner-logo--tall" />
				</a>
			</div>
		</div>

		<div class="site-navbar-actions">
			{#if $user}
				<!-- Temporary Chat toggle -->
				{#if $user?.role === 'user' ? ($user?.permissions?.chat?.temporary ?? true) && !($user?.permissions?.chat?.temporary_enforced ?? false) : true}
					<Tooltip content={$i18n.t('Temporary Chat')}>
						<button
							class="site-navbar-btn"
							id="site-temporary-chat-button"
							on:click={async () => {
								if (($settings?.temporaryChatByDefault ?? false) && $temporaryChatEnabled) {
									await temporaryChatEnabled.set(null);
								} else {
									await temporaryChatEnabled.set(!$temporaryChatEnabled);
								}

								if ($page.url.pathname !== '/') {
									await goto('/');
								}

								if ($temporaryChatEnabled) {
									window.history.replaceState(null, '', '?temporary-chat=true');
								} else {
									window.history.replaceState(null, '', location.pathname);
								}
							}}
						>
							{#if $temporaryChatEnabled}
								<ChatBubbleDottedChecked className="size-4.5" strokeWidth="1.5" />
							{:else}
								<ChatBubbleDotted className="size-4.5" strokeWidth="1.5" />
							{/if}
						</button>
					</Tooltip>
				{/if}

				<!-- Controls (admin only) -->
				{#if $user?.role === 'admin'}
					<Tooltip content={$i18n.t('Controls')}>
						<button
							class="site-navbar-btn"
							on:click={async () => {
								await showControls.set(!$showControls);
							}}
							aria-label="Controls"
						>
							<Knobs className="size-5" strokeWidth="1" />
						</button>
					</Tooltip>
				{/if}

				<!-- Account -->
				<UserMenu
					className="max-w-[240px]"
					role={$user?.role}
					help={true}
					on:show={(e) => {
						if (e.detail === 'archived-chat') {
							showArchivedChats.set(true);
						}
					}}
				>
					<div class="site-navbar-btn site-navbar-account">
						<span class="site-navbar-account-label">Account</span>
					</div>
				</UserMenu>
			{:else}
				<a href="/auth" class="site-navbar-cta">Sign in</a>
			{/if}
		</div>
	</header>


</div>

<style>
	/* ── Site Navbar ── */
	.site-navbar {
		width: 100%;
		flex-shrink: 0;
		z-index: 100;
	}

	/* Header */
	.site-navbar-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.5rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
		background: rgba(0, 0, 0, 0.94);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
	}

	.site-navbar-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-decoration: none;
	}

	.site-navbar-logo {
		height: 56px;
		width: auto;
		display: block;
		flex-shrink: 0;
	}

	.site-navbar-tag {
		font-size: 0.75rem;
		color: #00d4ff;
		background: rgba(0, 212, 255, 0.12);
		border: 1px solid rgba(0, 212, 255, 0.2);
		padding: 2px 10px;
		border-radius: 9999px;
		font-weight: 500;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.site-navbar-actions {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.site-navbar-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 0.75rem;
		color: #9ca3af;
		background: transparent;
		border: none;
		transition: background 0.15s, color 0.15s;
	}

	.site-navbar-btn:hover {
		background: rgba(255, 255, 255, 0.06);
		color: #d1d5db;
	}

	.site-navbar-account {
		padding: 0.375rem 0.5rem;
	}

	.site-navbar-account-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: #9ca3af;
	}

	.site-navbar-account:hover .site-navbar-account-label {
		color: #d1d5db;
	}

	.site-navbar-cta {
		font-size: 0.875rem;
		font-weight: 600;
		color: #00d4ff;
		text-decoration: none;
		padding: 0.5rem 1rem;
		border: 1px solid rgba(0, 212, 255, 0.3);
		border-radius: 9999px;
		transition: background 0.2s, border-color 0.2s;
	}

	.site-navbar-cta:hover {
		background: rgba(0, 212, 255, 0.12);
		border-color: #0099bb;
	}

	/* Partners (inline in header) */
	.site-navbar-partners {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.site-navbar-partners-label {
		font-size: 0.65rem;
		color: rgba(255, 255, 255, 0.3);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		font-weight: 600;
		white-space: nowrap;
	}

	.site-navbar-partners-logos {
		display: flex;
		align-items: center;
		gap: 1.25rem;
	}

	.site-navbar-partner-link {
		display: flex;
		align-items: center;
		text-decoration: none;
		opacity: 1;
		transition: opacity 0.2s, transform 0.2s;
	}

	.site-navbar-partner-link:hover {
		opacity: 0.8;
		transform: scale(1.03);
	}

	.site-navbar-partner-logo {
		height: 27.5px;
		width: auto;
		max-width: 175px;
		object-fit: contain;
		filter: brightness(0) invert(1);
	}

	.site-navbar-partner-logo--tall {
		height: 38.5px;
	}

	.site-navbar-partner-logo--colored {
		filter: none;
	}

	.site-navbar-partner-logo--manifest {
		height: 37.5px;
		max-width: 225px;
	}

	.site-navbar-partner-logo--wordmark {
		height: 26px;
		width: auto;
	}

	/* Responsive */
	@media (max-width: 1024px) {
		.site-navbar-partners-label {
			display: none;
		}
	}

	@media (max-width: 768px) {
		.site-navbar-logo {
			height: 46px;
		}

		.site-navbar-partners {
			display: none;
		}
	}

	@media (max-width: 480px) {
		.site-navbar-logo {
			height: 38px;
		}

		.site-navbar-header {
			padding: 0.75rem 1rem;
		}
	}
</style>
