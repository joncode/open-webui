<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		loaded = true;
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
	<link href="https://api.fontshare.com/v2/css?f[]=general-sans@400,500,600,700&display=swap" rel="stylesheet" />
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] text-white relative" id="auth-page">
	<!-- Landing-style background -->
	<div class="w-full h-full absolute top-0 left-0" style="background: #0a0f1a;"></div>
	<div class="auth-bg-grid" aria-hidden="true"></div>
	<div class="auth-bg-glow" aria-hidden="true"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>

	{#if loaded}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-white"
			id="auth-container"
			style="font-family: 'General Sans', system-ui, sans-serif;"
		>
			<div class="w-full px-10 min-h-screen flex flex-col text-center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full sm:max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium dark:text-gray-200"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<div class="my-auto flex flex-col justify-center items-center">
						<div class="w-full max-w-[480px] my-auto text-gray-100">
							<!-- Chat-style auth container -->
							<div class="auth-chat-container">
								<!-- Header -->
								<div class="auth-chat-header">
									<div class="flex items-center gap-3">
										<div class="auth-chat-status"></div>
										<div>
											<div class="text-sm font-semibold text-white">
												{#if $config?.onboarding ?? false}
													{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
												{:else if mode === 'ldap'}
													{$i18n.t(`Sign in with LDAP`)}
												{:else if mode === 'signin'}
													{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
												{:else}
													{$i18n.t(`Sign up for {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
												{/if}
											</div>
											<div class="text-xs text-gray-400">Private, Sovereign AI Assistant</div>
										</div>
									</div>
									<span class="auth-chat-badge">Encrypted</span>
								</div>

								<!-- Form body -->
								<form
									class="auth-chat-body"
									on:submit={(e) => {
										e.preventDefault();
										submitHandler();
									}}
								>
									{#if $config?.onboarding ?? false}
										<div class="text-xs text-gray-500 text-center mb-3">
											ⓘ {$WEBUI_NAME}
											{$i18n.t(
												'does not make any external connections, and your data stays securely on your locally hosted server.'
											)}
										</div>
									{/if}

									{#if !$config || $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<div class="flex flex-col gap-3">
											{#if mode === 'signup'}
												<div>
													<label for="name" class="auth-chat-label">{$i18n.t('Name')}</label>
													<input
														bind:value={name}
														type="text"
														id="name"
														class="auth-chat-input"
														autocomplete="name"
														placeholder={$i18n.t('Enter Your Full Name')}
														required
													/>
												</div>
											{/if}

											{#if mode === 'ldap'}
												<div>
													<label for="username" class="auth-chat-label">{$i18n.t('Username')}</label>
													<input
														bind:value={ldapUsername}
														type="text"
														class="auth-chat-input"
														autocomplete="username"
														name="username"
														id="username"
														placeholder={$i18n.t('Enter Your Username')}
														required
													/>
												</div>
											{:else}
												<div>
													<label for="email" class="auth-chat-label">{$i18n.t('Email')}</label>
													<input
														bind:value={email}
														type="email"
														id="email"
														class="auth-chat-input"
														autocomplete="email"
														name="email"
														placeholder={$i18n.t('Enter Your Email')}
														required
													/>
												</div>
											{/if}

											<div>
												<label for="password" class="auth-chat-label">{$i18n.t('Password')}</label>
												<SensitiveInput
													bind:value={password}
													type="password"
													id="password"
													outerClassName="auth-chat-input flex items-center"
													inputClassName="w-full bg-transparent text-sm outline-none text-white placeholder:text-[#4e5268]"
													showButtonClassName="pl-2 text-gray-500 hover:text-gray-300 transition"
													placeholder={$i18n.t('Enter Your Password')}
													autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
													name="password"
													screenReader={true}
													required
													aria-required="true"
												/>
											</div>

											{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
												<div>
													<label for="confirm-password" class="auth-chat-label">{$i18n.t('Confirm Password')}</label>
													<SensitiveInput
														bind:value={confirmPassword}
														type="password"
														id="confirm-password"
														outerClassName="auth-chat-input flex items-center"
														inputClassName="w-full bg-transparent text-sm outline-none text-white placeholder:text-[#4e5268]"
														showButtonClassName="pl-2 text-gray-500 hover:text-gray-300 transition"
														placeholder={$i18n.t('Confirm Your Password')}
														autocomplete="new-password"
														name="confirm-password"
														required
													/>
												</div>
											{/if}

											<!-- Submit button styled like chat send -->
											<div class="auth-chat-input-wrapper mt-1">
												<button
													class="auth-chat-submit"
													type="submit"
												>
													{#if mode === 'ldap'}
														{$i18n.t('Authenticate')}
													{:else}
														{mode === 'signin'
															? $i18n.t('Sign in')
															: ($config?.onboarding ?? false)
																? $i18n.t('Create Admin Account')
																: $i18n.t('Create Account')}
													{/if}
													<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
														<line x1="22" y1="2" x2="11" y2="13" />
														<polygon points="22 2 15 22 11 13 2 9 22 2" />
													</svg>
												</button>
											</div>
										</div>
									{/if}
								</form>

								<!-- Footer -->
								<div class="auth-chat-footer">
									{#if (!$config || $config?.features?.enable_signup) && !($config?.onboarding ?? false)}
										<span class="text-gray-500">
											{mode === 'signin'
												? $i18n.t("Don't have an account?")
												: $i18n.t('Already have an account?')}
										</span>
										<button
											class="text-cyan-400 hover:text-cyan-300 font-medium transition"
											type="button"
											on:click={() => {
												if (mode === 'signin') {
													mode = 'signup';
												} else {
													mode = 'signin';
												}
											}}
										>
											{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
										</button>
									{:else}
										<span class="text-gray-600">No conversations stored · Decentralized infrastructure</span>
									{/if}
								</div>
							</div>

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="inline-flex items-center justify-center w-full">
									<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<span
											class="px-3 text-sm font-medium text-gray-900 dark:text-white bg-transparent"
											>{$i18n.t('or')}</span
										>
									{/if}

									<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
								</div>
								<div class="flex flex-col space-y-2">
									{#if $config?.oauth?.providers?.google}
										<button
											class="flex justify-center items-center bg-white text-gray-900 hover:bg-gray-100 transition w-full rounded-xl font-semibold text-sm py-3 shadow-lg"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/><path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/><path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/><path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/><path fill="none" d="M0 0h48v48H0z" />
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.microsoft}
										<button
											class="flex justify-center items-center bg-white text-gray-900 hover:bg-gray-100 transition w-full rounded-xl font-semibold text-sm py-3 shadow-lg"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
													x="1"
													y="11"
													width="9"
													height="9"
													fill="#00a4ef"
												/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
													x="11"
													y="11"
													width="9"
													height="9"
													fill="#ffb900"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.github}
										<button
											class="flex justify-center items-center bg-white text-gray-900 hover:bg-gray-100 transition w-full rounded-xl font-semibold text-sm py-3 shadow-lg"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.oidc}
										<button
											class="flex justify-center items-center bg-white text-gray-900 hover:bg-gray-100 transition w-full rounded-xl font-semibold text-sm py-3 shadow-lg"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>

											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.feishu}
										<button
											class="flex justify-center items-center bg-white text-gray-900 hover:bg-gray-100 transition w-full rounded-xl font-semibold text-sm py-3 shadow-lg"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
										</button>
									{/if}
								</div>
							{/if}

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div class="mt-2">
									<button
										class="flex justify-center items-center text-xs w-full text-center underline"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										<span
											>{mode === 'ldap'
												? $i18n.t('Continue with Email')
												: $i18n.t('Continue with LDAP')}</span
										>
									</button>
								</div>
							{/if}
						</div>
						{#if $config?.metadata?.login_footer}
							<div class="max-w-3xl mx-auto">
								<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		{#if !$config?.metadata?.auth_logo_position}
			<div class="fixed m-10 z-50">
				<div class="auth-logo-container">
					<img
						src="/landing/agent1-wordmark.png"
						class="h-[3.75rem] w-auto max-w-[330px]"
						alt="{$WEBUI_NAME} logo"
					/>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.auth-bg-grid {
		position: absolute;
		inset: 0;
		background-image:
			linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
		background-size: 60px 60px;
		pointer-events: none;
	}

	.auth-bg-glow {
		position: absolute;
		top: -30%;
		left: 50%;
		transform: translateX(-50%);
		width: 800px;
		height: 800px;
		background: radial-gradient(circle, rgba(0,200,255,0.08) 0%, rgba(0,100,255,0.04) 40%, transparent 70%);
		pointer-events: none;
	}

	/* Chat-style auth container */
	:global(.auth-chat-container) {
		background: #111318;
		border: 1px solid #252a3a;
		border-radius: 1rem;
		overflow: hidden;
		box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 0 30px rgba(0,212,255,0.06);
	}

	:global(.auth-chat-header) {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.875rem 1.25rem;
		border-bottom: 1px solid #252a3a;
		background: rgba(255,255,255,0.02);
	}

	:global(.auth-chat-status) {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #34d399;
		box-shadow: 0 0 6px rgba(52,211,153,0.5);
	}

	:global(.auth-chat-badge) {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #34d399;
		border: 1px solid rgba(52,211,153,0.3);
		border-radius: 9999px;
		padding: 0.2rem 0.6rem;
	}

	:global(.auth-chat-body) {
		padding: 1.5rem 1.25rem;
	}

	:global(.auth-chat-label) {
		display: block;
		font-size: 0.8rem;
		font-weight: 500;
		color: rgba(255,255,255,0.6);
		margin-bottom: 0.35rem;
	}

	:global(.auth-chat-input) {
		width: 100%;
		font-size: 0.875rem;
		padding: 0.65rem 0.875rem;
		background: #0a0b0f;
		border: 1px solid #252a3a;
		border-radius: 1rem;
		color: #e8eaf0;
		outline: none;
		line-height: 1.5;
		font-family: 'General Sans', system-ui, sans-serif;
		transition: border-color 180ms cubic-bezier(0.16,1,0.3,1), box-shadow 180ms cubic-bezier(0.16,1,0.3,1);
	}

	:global(.auth-chat-input:focus) {
		border-color: #0099bb;
		box-shadow: 0 0 0 3px rgba(0,212,255,0.12);
	}

	:global(.auth-chat-input::placeholder) {
		color: #4e5268;
	}

	:global(.auth-chat-input-wrapper) {
		position: relative;
	}

	:global(.auth-chat-submit) {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.65rem 0.875rem;
		background: #0a0b0f;
		border: 1px solid #252a3a;
		border-radius: 1rem;
		color: #e8eaf0;
		font-size: 0.875rem;
		font-weight: 500;
		font-family: 'General Sans', system-ui, sans-serif;
		cursor: pointer;
		transition: border-color 180ms cubic-bezier(0.16,1,0.3,1), box-shadow 180ms cubic-bezier(0.16,1,0.3,1);
	}

	:global(.auth-chat-submit:hover) {
		border-color: #0099bb;
		box-shadow: 0 0 0 3px rgba(0,212,255,0.12);
	}

	:global(.auth-chat-footer) {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.75rem 1.25rem;
		border-top: 1px solid #252a3a;
		font-size: 0.75rem;
		background: rgba(255,255,255,0.01);
	}

	:global(.auth-logo-container) {
		border: 1px solid #252a3a;
		border-radius: 1rem;
		padding: 0.5rem 1rem;
		background: rgba(17,19,24,0.8);
		backdrop-filter: blur(8px);
	}

	:global(#auth-page input) {
		color: #e8eaf0 !important;
		background: transparent !important;
	}

	:global(#auth-page input:-webkit-autofill),
	:global(#auth-page input:-webkit-autofill:hover),
	:global(#auth-page input:-webkit-autofill:focus) {
		-webkit-text-fill-color: #e8eaf0 !important;
		-webkit-box-shadow: 0 0 0 1000px #0a0b0f inset !important;
		background-color: #0a0b0f !important;
		caret-color: #e8eaf0;
	}
</style>
