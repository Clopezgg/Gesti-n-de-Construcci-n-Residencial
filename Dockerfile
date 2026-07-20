ARG ERPNEXT_VERSION=v15.117.0
FROM frappe/erpnext:${ERPNEXT_VERSION}

ARG TARGETARCH
USER root
RUN test "${TARGETARCH:-amd64}" = "amd64" \
    && apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*
COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/erpnext
COPY deploy/coolify/nginx-template.conf /templates/nginx/frappe.conf.template
RUN find /home/frappe/frappe-bench/apps/erpnext/deploy -type f -name '*.sh' -exec chmod 0755 {} + \
    && find /home/frappe/frappe-bench/apps/erpnext/scripts -maxdepth 1 -type f -name '*.py' -exec chmod 0755 {} +

USER frappe
WORKDIR /home/frappe/frappe-bench
