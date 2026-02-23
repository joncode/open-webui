import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
	plugins: [svelte({ hot: !process.env.VITEST })],
	resolve: {
		alias: {
			$lib: path.resolve('./src/lib')
		},
		conditions: ['browser']
	},
	test: {
		globals: true,
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
		setupFiles: ['src/test/setup.ts']
	}
});
