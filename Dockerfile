FROM frappe/erpnext:v15.117.0

USER root
COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/erpnext
RUN chmod 0755 /home/frappe/frappe-bench/apps/erpnext/deploy/render/*.sh

USER frappe
WORKDIR /home/frappe/frappe-bench
