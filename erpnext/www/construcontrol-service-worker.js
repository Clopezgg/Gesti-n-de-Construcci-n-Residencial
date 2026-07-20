/* ConstruControl PWA service worker. Public assets only; business and private data are never cached. */
const VERSION = "2026.07.20-b12";
const CACHE_PREFIX = "construcontrol-shell-";
const CACHE_NAME = `${CACHE_PREFIX}${VERSION}`;
const SHELL_ASSETS = [
	"/assets/erpnext/construcontrol/manifest.webmanifest",
	"/assets/erpnext/construcontrol/deploy-version.json",
	"/assets/erpnext/construcontrol/icon-192.png",
	"/assets/erpnext/construcontrol/icon-512.png",
	"/assets/erpnext/construcontrol/apple-touch-icon-180.png",
	"/assets/erpnext/construcontrol/favicon-32.png",
	"/assets/erpnext/js/construcontrol_mobile.js",
	"/assets/erpnext/js/construcontrol_ux.js",
	"/assets/erpnext/js/construcontrol_pwa.js",
	"/assets/erpnext/css/construcontrol_canonical.css",
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

function isSensitive(requestUrl) {
	return (
		requestUrl.pathname.startsWith("/api/") ||
		requestUrl.pathname.startsWith("/private/") ||
		requestUrl.pathname.startsWith("/files/") ||
		requestUrl.pathname.startsWith("/app/")
	);
}

function isShellAsset(requestUrl) {
	return (
		requestUrl.origin === self.location.origin &&
		(requestUrl.pathname.startsWith("/assets/erpnext/") ||
			requestUrl.pathname.startsWith("/assets/frappe/"))
	);
}

self.addEventListener("fetch", (event) => {
	const request = event.request;
	if (request.method !== "GET") return;
	const url = new URL(request.url);
	if (url.origin !== self.location.origin || isSensitive(url)) return;
	if (!isShellAsset(url)) return;

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
	if (event.data?.type === "GET_VERSION") {
		event.source?.postMessage({
			type: "CONSTRUCONTROL_VERSION",
			version: VERSION,
		});
	}
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
