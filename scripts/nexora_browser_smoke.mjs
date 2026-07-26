import { chromium, webkit } from "playwright";

const browserTypes = [chromium, webkit];

for (const browserType of browserTypes) {
  const launch = browserType.launch.bind(browserType);
  browserType.launch = async (...launchArgs) => {
    const browser = await launch(...launchArgs);
    const newContext = browser.newContext.bind(browser);
    browser.newContext = async (...contextArgs) => {
      const context = await newContext(...contextArgs);
      const post = context.request.post.bind(context.request);
      context.request.post = async (url, options) => {
        const response = await post(url, options);
        if (String(url).endsWith("/api/method/login") && response.ok()) {
          const headers = await response.allHeaders();
          const setCookie = headers["set-cookie"] || "";
          const sid = setCookie.match(/(?:^|,\s*)sid=([^;]+)/)?.[1];
          if (sid) {
            const origin = new URL(String(url)).origin;
            await context.addCookies([
              {
                name: "sid",
                value: decodeURIComponent(sid),
                url: `${origin}/`,
                httpOnly: true,
                sameSite: "Lax",
              },
            ]);
          }
        }
        return response;
      };
      return context;
    };
    return browser;
  };
}

await import("./nexora_browser_smoke_original.mjs");
