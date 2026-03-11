<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import './landing.css';
	import SiteNavbar from '$lib/components/layout/SiteNavbar.svelte';

	const DEMO_RESPONSES = [
		"I'm agent1.Manifest — a fully sovereign AI running on decentralized compute via **Manifest Network** and **Render Network**. My inference is powered by **Morpheus Network** and **Venice AI**. No conversation is ever stored or logged. How can I help?",
		"Great question. Because I run on decentralized GPU infrastructure, there is no single point of control or failure. Your data never touches a centralized server — everything is processed across a distributed network of nodes.",
		"Absolutely. Unlike traditional AI services, I don't retain any chat history. Once you close this window, the conversation is gone. That's the benefit of sovereign, privacy-first design.",
		"I was created by **Sarson Funds** to demonstrate what no-cost, private, uncensored AI looks like when built on decentralized infrastructure. agent1.Manifest represents the future of fully sovereign AI for every user.",
		"The premium LLM models I use are provided through **Morpheus Network** and **Venice AI**, ensuring high-quality, uncensored responses without centralized gatekeeping."
	];

	type Message = { role: 'user' | 'assistant'; text: string; html?: string };

	let chatInput = '';
	let messages: Message[] = [
		{
			role: 'assistant',
			text: '',
			html: '<p>Welcome to <strong>agent1.Manifest</strong> — your private, sovereign AI assistant. I run on decentralized infrastructure with no stored conversations.</p><p>How can I help you today?</p>'
		}
	];
	let showTyping = false;
	let isBusy = false;
	let responseIndex = 0;
	let chatMessagesEl: HTMLDivElement;
	let typingTimeout: ReturnType<typeof setTimeout>;
	let typingInterval: ReturnType<typeof setInterval>;

	function renderMarkdown(text: string): string {
		const html = text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			.replace(/`(.*?)`/g, '<code>$1</code>')
			.replace(/\n\n/g, '</p><p>')
			.replace(/\n/g, '<br>');
		return '<p>' + html + '</p>';
	}

	function scrollToBottom() {
		tick().then(() => {
			if (chatMessagesEl) {
				chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
			}
		});
	}

	function sendMessage() {
		const text = chatInput.trim();
		if (!text || isBusy) return;

		messages = [...messages, { role: 'user', text }];
		chatInput = '';
		isBusy = true;
		showTyping = true;
		scrollToBottom();

		const delay = 800 + Math.random() * 1200;
		typingTimeout = setTimeout(() => {
			showTyping = false;
			const reply = DEMO_RESPONSES[responseIndex % DEMO_RESPONSES.length];
			responseIndex += 1;

			// Type out the response character by character
			let i = 0;
			const fullHtml = renderMarkdown(reply);
			const plainReply = reply;
			const assistantMessage: Message = { role: 'assistant', text: '', html: '<p></p>' };
			messages = [...messages, assistantMessage];
			scrollToBottom();

			typingInterval = setInterval(() => {
				i += 1;
				if (i <= plainReply.length) {
					const slice = plainReply.slice(0, i);
					const html = renderMarkdown(slice);
					messages = messages.map((m, idx) =>
						idx === messages.length - 1 ? { ...m, html } : m
					);
					scrollToBottom();
				} else {
					if (typingInterval) clearInterval(typingInterval);
					// Final message with full html
					messages = messages.map((m, idx) =>
						idx === messages.length - 1 ? { ...m, text: plainReply, html: fullHtml } : m
					);
					isBusy = false;
					scrollToBottom();
				}
			}, 18);
		}, delay);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}

	onMount(() => {
		// Override the global html { overflow-y: hidden !important } from app.html
		// so the landing page can scroll
		document.documentElement.style.setProperty('overflow-y', 'auto', 'important');

		return () => {
			if (typingTimeout) clearTimeout(typingTimeout);
			if (typingInterval) clearInterval(typingInterval);
			// Restore hidden overflow for the chat app
			document.documentElement.style.setProperty('overflow-y', 'hidden', 'important');
		};
	});
</script>

<svelte:head>
	<title>agent1.Manifest — Private, Sovereign AI</title>
	<meta name="description" content="agent1.Manifest: No-cost private, secure, uncensored AI running on decentralized compute." />
	<link href="https://api.fontshare.com/v2/css?f[]=general-sans@400,500,600,700&display=swap" rel="stylesheet" />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
</svelte:head>

<div class="landing">
	<div class="landing-bg-grid" aria-hidden="true"></div>
	<div class="landing-bg-glow" aria-hidden="true"></div>

	<div class="landing-page-wrapper">
		<SiteNavbar />

		<div class="landing-partners-mobile animate-in">
			<span class="landing-partners-mobile-label">Your Partners in Decentralization</span>
			<div class="landing-partners-mobile-logos">
				<a href="https://manifest.network" target="_blank" rel="noopener noreferrer">
					<img src="/landing/manifest-logo.png" alt="Manifest Network" class="landing-partners-mobile-logo landing-partners-mobile-logo--manifest" />
				</a>
				<a href="https://rendernetwork.com" target="_blank" rel="noopener noreferrer">
					<img src="/landing/render-logo.svg" alt="Render Network" class="landing-partners-mobile-logo" />
				</a>
				<a href="https://mor.org" target="_blank" rel="noopener noreferrer">
					<img src="/landing/morpheus-og.png" alt="Morpheus" class="landing-partners-mobile-logo landing-partners-mobile-logo--wordmark" />
				</a>
				<a href="https://venice.ai" target="_blank" rel="noopener noreferrer">
					<img src="/landing/venice-lockup-white.png" alt="Venice AI" class="landing-partners-mobile-logo landing-partners-mobile-logo--tall" />
				</a>
			</div>
		</div>

		<main class="main-content">
			<section class="hero-section animate-in">
				<div class="cost-badge">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
						<path d="M9 12l2 2 4-4" />
					</svg>
					No Cost · Private · Secure
				</div>
				<h1 class="hero-title">
					<span class="accent">Sovereign AI</span><br />on Decentralized Compute
				</h1>
				<p class="hero-subtitle">
					Premium, uncensored AI — running entirely on decentralized infrastructure. No stored chats. No surveillance. Fully sovereign.
				</p>
			</section>

			<div class="features-strip animate-in animate-in--delay-1">
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
					<span class="chip-text">Private</span>
				</div>
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><line x1="9" y1="10" x2="15" y2="10" /></svg>
					<span class="chip-text">No Stored Chats</span>
				</div>
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
					<span class="chip-text">Premium Models</span>
				</div>
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></svg>
					<span class="chip-text">Uncensored</span>
				</div>
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V4a4 4 0 0 0-8 0v3" /></svg>
					<span class="chip-text">Fully Sovereign</span>
				</div>
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" /></svg>
					<span class="chip-text">Decentralized Compute</span>
				</div>
				<div class="feature-chip">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z" /><path d="M16 14H8a4 4 0 0 0-4 4v2h16v-2a4 4 0 0 0-4-4z" /><path d="M18 8h2a2 2 0 0 1 2 2v1" /><path d="M6 8H4a2 2 0 0 0-2 2v1" /></svg>
					<span class="chip-text">Designed for Agents</span>
				</div>
			</div>

			<div class="chat-container animate-in animate-in--delay-2">
				<div class="chat-header">
					<div class="chat-header-left">
						<div class="chat-status"></div>
						<div>
							<div class="chat-header-title">agent1.Manifest</div>
							<div class="chat-header-subtitle">Decentralized AI Assistant</div>
						</div>
					</div>
					<div class="chat-header-right">
						<span class="chat-header-badge">Encrypted</span>
					</div>
				</div>

				<div class="chat-messages" bind:this={chatMessagesEl} role="log" aria-live="polite">
					{#each messages as msg, i (i)}
						<div class="message message--{msg.role}">
							<div class="message-avatar">{msg.role === 'user' ? 'You' : 'A1'}</div>
							<div class="message-bubble">
								{#if msg.html}
									{@html msg.html}
								{:else}
									<p>{msg.text}</p>
								{/if}
							</div>
						</div>
					{/each}
					{#if showTyping}
						<div class="message message--assistant">
							<div class="message-avatar">A1</div>
							<div class="typing-indicator">
								<div class="typing-dot"></div>
								<div class="typing-dot"></div>
								<div class="typing-dot"></div>
							</div>
						</div>
					{/if}
				</div>

				<div class="chat-input-area">
					<div class="chat-input-wrapper">
						<textarea
							class="chat-input"
							bind:value={chatInput}
							placeholder="Ask agent1.Manifest anything..."
							rows="1"
							aria-label="Chat message input"
							on:keydown={handleKeydown}
							disabled={isBusy}
						></textarea>
						<button
							class="chat-send-btn"
							on:click={sendMessage}
							disabled={isBusy || !chatInput.trim()}
							aria-label="Send message"
						>
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<line x1="22" y1="2" x2="11" y2="13" />
								<polygon points="22 2 15 22 11 13 2 9 22 2" />
							</svg>
						</button>
					</div>
					<div class="chat-disclaimer">No conversations stored · Running on Manifest &amp; Render networks</div>
				</div>
			</div>

			<div class="coming-soon animate-in animate-in--delay-3">
				<svg class="coming-soon-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="10" />
					<path d="M12 6v6l4 2" />
				</svg>
				<div class="coming-soon-text">
					<strong>Coming Soon:</strong> Secure object and chat storage via Manifest Network — encrypted, decentralized, and fully under your control.
				</div>
			</div>
		</main>

		<section class="partners-section animate-in animate-in--delay-4">
			<div class="partners-roles">
				<div class="partner-role">
					<div class="partner-role-label">Decentralized Compute</div>
					<div class="partner-role-value">Manifest Network · Render Network</div>
				</div>
				<div class="partner-role">
					<div class="partner-role-label">Premium LLM Inference</div>
					<div class="partner-role-value">Morpheus Network · Venice AI</div>
				</div>
				<div class="partner-role">
					<div class="partner-role-label">Agent Creator</div>
					<div class="partner-role-value">Sarson Funds</div>
				</div>
			</div>
		</section>

		<footer class="site-footer animate-in animate-in--delay-5">
			<div class="footer-sarson">
				<img src="/landing/sarson-funds-logo.png" alt="Sarson Funds" class="footer-sarson-logo" loading="lazy" />
				<div class="footer-sarson-text">
					Brought to you by <a href="https://sarsonfunds.com" target="_blank" rel="noopener noreferrer">Sarson Funds</a>
				</div>
			</div>
		</footer>
	</div>
</div>
