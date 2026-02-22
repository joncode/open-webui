import { WEBUI_API_BASE_URL } from '$lib/constants';

export const createSideChat = async (
	token: string,
	body: { chat_id: string; step_number: number; original_step_content: string }
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/side-chats/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSideChatsByChatId = async (token: string, chatId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/side-chats/by-chat/${chatId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addSideChatMessage = async (
	token: string,
	sideChatId: string,
	body: { role: string; content: string }
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/side-chats/${sideChatId}/messages`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const combineSideChat = async (token: string, sideChatId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/side-chats/${sideChatId}/combine`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSideChat = async (token: string, sideChatId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/side-chats/${sideChatId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
