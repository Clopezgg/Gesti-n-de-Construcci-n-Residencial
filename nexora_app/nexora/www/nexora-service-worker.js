/* NEXORA PWA: only public shell assets are cached. Business and private data remain online-only. */
const VERSION = "2026.07.26-dashboard";
const CACHE_PREFIX = "nexora-shell-";
const CACHE_NAME = `${CACHE_PREFIX}${VERSION}`;
const SHELL_ASSETS = [
	"/assets/nexora/manifest.json",
	"/assets/nexora/images/nexora.svg",
	"/assets/nexora/images/nexora-192.png",
	"/assets/nexora/images/nexora-512.png",
	"/assets/nexora/js/nexora.js",
	"/assets/nexora/css/nexora.css",
];

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches
			.open(CACHE_NAME)
			.then((cache) =>
				Promise.allSettled(
					SHELL_ASSETS.map((url) => cache.add(new Request(url, { cache: "reload" })))
				)
			)
			.then(() => self.skipWaiting())
	);
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) =>
				Promise.all(
					keys
						.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
						.map((key) => caches.delete(key))
				)
			)
			.then(() => self.clients.claim())
	);
});

function isSensitive(url) {
	return (
		url.pathname.startsWith("/api/") ||
		url.pathname.startsWith("/private/") ||
		url.pathname.startsWith("/files/") ||
		url.pathname.startsWith("/app/")
	);
}

function isNexoraShell(url) {
	return url.origin === self.location.origin && url.pathname.startsWith("/assets/nexora/");
}

self.addEventListener("fetch", (event) => {
	const request = event.request;
	if (request.method !== "GET") return;
	const url = new URL(request.url);
	if (url.origin !== self.location.origin || isSensitive(url) || !isNexoraShell(url)) return;

	event.respondWith(
		fetch(new Request(request, { cache: "no-cache" }))
			.then((response) => {
				if (response.ok && response.type === "basic") {
					const copy = response.clone();
					event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)));
				}
				return response;
			})
			.catch(() => caches.match(request).then((cached) => cached || Response.error()))
	);
});

self.addEventListener("message", (event) => {
	if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
	if (event.data?.type === "CLEAR_OLD_CACHES") {
		event.waitUntil(
			caches
				.keys()
				.then((keys) =>
					Promise.all(
						keys
							.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
							.map((key) => caches.delete(key))
					)
				)
		);
	}
});
