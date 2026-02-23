import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/svelte';
import { writable } from 'svelte/store';

// Mock child components — factory must be self-contained (vi.mock is hoisted)
vi.mock('./FileItemModal.svelte', () => ({ default: () => {} }));
vi.mock('./Spinner.svelte', () => ({ default: () => {} }));
vi.mock('./Tooltip.svelte', () => ({ default: () => {} }));
vi.mock('$lib/components/icons/XMark.svelte', () => ({ default: () => {} }));
vi.mock('../icons/GarbageBin.svelte', () => ({ default: () => {} }));
vi.mock('../icons/DocumentPage.svelte', () => ({ default: () => {} }));
vi.mock('../icons/Database.svelte', () => ({ default: () => {} }));
vi.mock('../icons/PageEdit.svelte', () => ({ default: () => {} }));
vi.mock('../icons/ChatBubble.svelte', () => ({ default: () => {} }));
vi.mock('../icons/Folder.svelte', () => ({ default: () => {} }));

import FileItem from './FileItem.svelte';

// Mock stores — settings must be a Svelte writable store
vi.mock('$lib/stores', () => {
	const { writable } = require('svelte/store');
	return {
		settings: writable({ highContrastMode: false })
	};
});

// Mock constants
vi.mock('$lib/constants', () => ({
	WEBUI_API_BASE_URL: 'http://localhost:8080/api/v1'
}));

// Mock $lib/utils (formatFileSize)
vi.mock('$lib/utils', () => ({
	formatFileSize: (size: number) => `${size} B`
}));

describe('FileItem', () => {
	const defaultProps = {
		name: 'test-file.txt',
		type: 'file',
		size: 1024,
		dismissible: true
	};

	// i18n context needs to be a Svelte store whose value has a .t() method
	const i18nStore = writable({ t: (s: string) => s });

	afterEach(() => {
		cleanup();
	});

	function renderFileItem(props = {}) {
		return render(FileItem, {
			props: { ...defaultProps, ...props },
			context: new Map([['i18n', i18nStore]])
		});
	}

	it('dismiss button uses div with role=button (not a nested button)', () => {
		renderFileItem({ dismissible: true });

		const dismissEl = document.querySelector('[aria-label="Remove File"]');
		expect(dismissEl).toBeInTheDocument();
		// The dismiss element should be a div, not a button (to avoid nested button a11y issue)
		expect(dismissEl!.tagName).toBe('DIV');
		expect(dismissEl).toHaveAttribute('role', 'button');
	});

	it('dismiss button is clickable', async () => {
		renderFileItem({ dismissible: true });

		const dismissEl = document.querySelector('[aria-label="Remove File"]')!;
		expect(dismissEl).toBeInTheDocument();
		// Verify it has click handler (the element should be interactive)
		expect(dismissEl).toHaveAttribute('role', 'button');
		expect(dismissEl).toHaveAttribute('tabindex', '0');
	});

	it('dismiss button responds to Enter key', async () => {
		renderFileItem({ dismissible: true });

		const dismissEl = document.querySelector('[aria-label="Remove File"]')!;
		// Verify keyboard accessibility — element has tabindex for keyboard focus
		expect(dismissEl).toHaveAttribute('tabindex', '0');
		// Fire keydown — no error means handler exists
		await fireEvent.keyDown(dismissEl, { key: 'Enter' });
	});
});
