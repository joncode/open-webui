import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/svelte';
import Modal from './Modal.svelte';

// Mock focus-trap since jsdom doesn't support real focus management
vi.mock('focus-trap', () => ({
	createFocusTrap: () => ({
		activate: vi.fn(),
		deactivate: vi.fn()
	})
}));

// Mock svelte transitions (they don't run in jsdom)
vi.mock('svelte/transition', () => ({
	fade: () => ({ duration: 0 })
}));

vi.mock('$lib/utils/transitions', () => ({
	flyAndScale: () => ({ duration: 0 })
}));

describe('Modal', () => {
	afterEach(() => {
		cleanup();
		// Clean up any modals appended to body by previous tests
		document.body.querySelectorAll('.modal').forEach((el) => el.remove());
		document.body.style.overflow = '';
	});

	it('renders with dialog role and tabindex=-1', () => {
		render(Modal, { props: { show: true } });
		const dialog = document.body.querySelector('[role="dialog"]');
		expect(dialog).toBeInTheDocument();
		expect(dialog).toHaveAttribute('tabindex', '-1');
	});

	it('has aria-modal set to true', () => {
		render(Modal, { props: { show: true } });
		const dialog = document.body.querySelector('[role="dialog"]');
		expect(dialog).toHaveAttribute('aria-modal', 'true');
	});

	it('closes on escape key', async () => {
		render(Modal, { props: { show: true } });

		// Verify modal is present
		expect(document.body.querySelector('[role="dialog"]')).toBeInTheDocument();

		// The component adds a keydown listener on window
		await fireEvent.keyDown(window, { key: 'Escape' });

		// After escape, the modal should be removed from the DOM
		expect(document.body.querySelector('[role="dialog"]')).not.toBeInTheDocument();
	});

	it('closes on outside click (mousedown on backdrop)', async () => {
		render(Modal, { props: { show: true } });

		const backdrop = document.body.querySelector('.modal');
		expect(backdrop).toBeInTheDocument();

		await fireEvent.mouseDown(backdrop!);

		// After clicking backdrop, modal should be removed
		expect(document.body.querySelector('[role="dialog"]')).not.toBeInTheDocument();
	});

	it('does not close when clicking inside modal content', async () => {
		render(Modal, { props: { show: true } });

		// The inner div stops propagation on mousedown
		const innerDiv = document.body.querySelector('.modal > div');
		expect(innerDiv).toBeInTheDocument();

		await fireEvent.mouseDown(innerDiv!);

		// Modal should still be in the DOM
		expect(document.body.querySelector('[role="dialog"]')).toBeInTheDocument();
	});
});
