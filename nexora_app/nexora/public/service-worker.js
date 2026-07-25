/* eslint-env serviceworker */
const CACHE_NAME = "nexora-v1";

const STATIC_ASSETS = ["/app/nexora-dashboard"];

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => {
			return cache.addAll(STATIC_ASSETS);
		})
	);
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
	event.respondWith(
		fetch(event.request)
			.then((response) => {
				const cloned = response.clone();
				caches.open(CACHE_NAME).then((cache) => {
					cache.put(event.request, cloned);
				});
				return response;
			})
			.catch(() => {
				return caches.match(event.request).then((cached) => {
					return cached || new Response("Offline", { status: 503 });
				});
			})
	);
});
