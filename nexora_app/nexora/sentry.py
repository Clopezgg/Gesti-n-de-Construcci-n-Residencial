import os
import sentry_sdk


def init_sentry():

    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        return


    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=True,
        traces_sample_rate=1.0,
    )
