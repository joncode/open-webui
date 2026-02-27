<script>
	import { marked } from 'marked';
	import { onDestroy } from 'svelte';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';

	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { disableSingleTilde } from '$lib/utils/marked/strikethrough-extension';
	import { mentionExtension } from '$lib/utils/marked/mention-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';
	import footnoteExtension from '$lib/utils/marked/footnote-extension';
	import citationExtension from '$lib/utils/marked/citation-extension';

	export let id = '';
	export let content;
	export let done = true;
	export let model = null;
	export let save = false;
	export let preview = false;

	export let paragraphTag = 'p';
	export let editCodeBlock = true;
	export let topPadding = false;

	export let sourceIds = [];

	export let onSave = () => {};
	export let onUpdate = () => {};

	export let onPreview = () => {};

	export let onSourceClick = () => {};
	export let onTaskClick = () => {};

	let tokens = [];

	const options = {
		throwOnError: false,
		breaks: true
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));
	marked.use(citationExtension(options));
	marked.use(footnoteExtension(options));
	marked.use(disableSingleTilde);
	marked.use({
		extensions: [
			mentionExtension({ triggerChar: '@' }),
			mentionExtension({ triggerChar: '#' }),
			mentionExtension({ triggerChar: '$' })
		]
	});

	const DEBOUNCE_MS = 100;
	let _debounceTimer = null;
	let _pendingContent = null;

	function lexContent(text) {
		tokens = marked.lexer(
			replaceTokens(processResponseContent(text), model?.name, $user?.name)
		);
	}

	$: if (content) {
		if (done) {
			// When streaming is done, lex immediately and cancel any pending debounce
			if (_debounceTimer) {
				clearTimeout(_debounceTimer);
				_debounceTimer = null;
			}
			lexContent(content);
		} else {
			// During streaming, debounce lexing to at most once per DEBOUNCE_MS
			_pendingContent = content;
			if (!_debounceTimer) {
				// Lex immediately on the first token, then debounce subsequent ones
				lexContent(content);
				_debounceTimer = setTimeout(() => {
					_debounceTimer = null;
					if (_pendingContent) {
						lexContent(_pendingContent);
						_pendingContent = null;
					}
				}, DEBOUNCE_MS);
			}
		}
	}

	onDestroy(() => {
		if (_debounceTimer) {
			clearTimeout(_debounceTimer);
		}
	});
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{done}
		{save}
		{preview}
		{paragraphTag}
		{editCodeBlock}
		{sourceIds}
		{topPadding}
		{onTaskClick}
		{onSourceClick}
		{onSave}
		{onUpdate}
		{onPreview}
	/>
{/key}
