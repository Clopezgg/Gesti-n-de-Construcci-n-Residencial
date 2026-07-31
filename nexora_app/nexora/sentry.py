import os

import sentry_sdk


def init_sentry():
	sentry_sdk.init(
		dsn=os.getenv(
			"SENTRY_DSN",
			"https://a0925cf9dcdc3feae0e225bb50d04fa1@o4511830522265600.ingest.us.sentry.io/4511830661529600",
		),
		send_default_pii=True,
		traces_sample_rate=1.0,
		environment="nexora",
	)
