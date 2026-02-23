import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import ConfirmDialog from './ConfirmDialog.svelte';

// Mock focus-trap
vi.mock('focus-trap', () => ({
	createFocusTrap: () => ({
		activate: vi.fn(),
		deactivate: vi.fn()
	})
}));

// Mock transitions
vi.mock('svelte/transition', () => ({
	fade: () => ({ duration: 0 })
}));

vi.mock('$lib/utils/transitions', () => ({
	flyAndScale: () => ({ duration: 0 })
}));

// Mock dompurify
vi.mock('dompurify', () => ({
	default: {
		sanitize: (html: string) => html
	}
}));

// Mock marked
vi.mock('marked', () => ({
	marked: {
		parse: (text: string) => text
	}
}));

// Mock SensitiveInput — Svelte 5 components must be functions
vi.mock('./SensitiveInput.svelte', () => ({ default: () => {} }));

describe('ConfirmDialog', () => {
	// i18n context needs to be a Svelte store whose value has a .t() method
	const i18nStore = writable({ t: (s: string) => s });

	afterEach(() => {
		cleanup();
		document.body.querySelectorAll('.fixed').forEach((el) => el.remove());
		document.body.style.overflow = '';
	});

	function renderDialog(props = {}) {
		return render(ConfirmDialog, {
			props: { show: true, ...props },
			context: new Map([['i18n', i18nStore]])
		});
	}

	it('renders confirm and cancel buttons', () => {
		renderDialog();

		const buttons = document.body.querySelectorAll('button');
		const buttonTexts = Array.from(buttons).map((b) => b.textContent?.trim());

		expect(buttonTexts).toContain('Cancel');
		expect(buttonTexts).toContain('Confirm');
	});

	it('calls onConfirm callback when confirm button is clicked', async () => {
		const onConfirm = vi.fn();
		renderDialog({ onConfirm });

		const buttons = document.body.querySelectorAll('button');
		const confirmBtn = Array.from(buttons).find((b) => b.textContent?.trim() === 'Confirm');
		expect(confirmBtn).toBeDefined();

		await fireEvent.click(confirmBtn!);

		expect(onConfirm).toHaveBeenCalledTimes(1);
	});

	it('has a cancel button that can be clicked', async () => {
		renderDialog();

		const buttons = document.body.querySelectorAll('button');
		const cancelBtn = Array.from(buttons).find((b) => b.textContent?.trim() === 'Cancel');
		expect(cancelBtn).toBeDefined();

		// Click should not throw — handler is wired up
		await fireEvent.click(cancelBtn!);
	});

	it('closes dialog when cancel button is clicked', async () => {
		renderDialog();

		// Verify dialog is present
		const buttons = document.body.querySelectorAll('button');
		expect(buttons.length).toBeGreaterThan(0);

		const cancelBtn = Array.from(buttons).find((b) => b.textContent?.trim() === 'Cancel');
		await fireEvent.click(cancelBtn!);

		// After cancel, the dialog should be removed from the DOM
		const remainingButtons = document.body.querySelectorAll('button');
		const confirmBtnAfter = Array.from(remainingButtons).find(
			(b) => b.textContent?.trim() === 'Confirm'
		);
		expect(confirmBtnAfter).toBeUndefined();
	});
});
