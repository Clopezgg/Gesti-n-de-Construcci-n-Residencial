#!/bin/bash

set -e

cd ~ || exit

export DEBIAN_FRONTEND=noninteractive
# `apt update` colgó 24 minutos sin ninguna salida contra un mirror real
# (evidencia: PR #218, job mariadb, 2026-08-18 — el registro se detiene a
# mitad de "noble-security InRelease" y no vuelve a escribir nada hasta que
# el timeout externo del paso lo mata). apt no tiene temporizador propio por
# fuente; sin `Acquire::*::Timeout` una conexión que no responde (no que la
# rechaza) se queda esperando indefinidamente en vez de reintentar o fallar.
APT_OPTS=(-o Acquire::Retries=3 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20)
sudo apt update "${APT_OPTS[@]}"
sudo apt remove -y "${APT_OPTS[@]}" mysql-server mysql-client
sudo apt install -y "${APT_OPTS[@]}" libcups2-dev redis-server mariadb-client

pip install frappe-bench

githubbranch=${GITHUB_BASE_REF:-${GITHUB_REF##*/}}
frappeuser=${FRAPPE_USER:-"frappe"}
source "${GITHUB_WORKSPACE}/.github/helper/resolve-ci-refs.sh"
frappebranch=$(resolve_frappe_ref "$githubbranch")
paymentsbranch=$(resolve_payments_ref)

echo "Installing Frappe ref: ${frappebranch}"
echo "Installing Payments ref: ${paymentsbranch}"
git clone "https://github.com/${frappeuser}/frappe" --branch "${frappebranch}" --depth 1
bench init --skip-assets --frappe-path ~/frappe --python "$(which python)" frappe-bench

mkdir ~/frappe-bench/sites/test_site

if [ "$DB" == "mariadb" ];then
    cp -r "${GITHUB_WORKSPACE}/.github/helper/site_config_mariadb.json" ~/frappe-bench/sites/test_site/site_config.json
else
    cp -r "${GITHUB_WORKSPACE}/.github/helper/site_config_postgres.json" ~/frappe-bench/sites/test_site/site_config.json
fi


if [ "$DB" == "mariadb" ];then
    mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
    mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

    mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE USER 'test_frappe'@'localhost' IDENTIFIED BY 'test_frappe'"
    mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE DATABASE test_frappe"
    mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "GRANT ALL PRIVILEGES ON \`test_frappe\`.* TO 'test_frappe'@'localhost'"

    mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "FLUSH PRIVILEGES"
fi

if [ "$DB" == "postgres" ];then
    echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE DATABASE test_frappe" -U postgres;
    echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE USER test_frappe WITH PASSWORD 'test_frappe'" -U postgres;
fi


install_whktml() {
    wget --timeout=60 --tries=3 -O /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
    sudo apt install -y "${APT_OPTS[@]}" /tmp/wkhtmltox.deb

}
# Redirigido a su propio archivo, no heredado del script principal: un hijo en
# segundo plano que conserva el mismo stdout que `install.sh | tee ...` deja el
# pipe abierto aunque `timeout` mate al proceso padre — el paso del workflow
# queda esperando ese descriptor de archivo, no la señal, y no hay temporizador
# que lo acote desde aquí.
install_whktml > /tmp/install-whktml.log 2>&1 &
wkpid=$!


cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

bench get-app payments --branch "$paymentsbranch"
bench get-app erpnext "${GITHUB_WORKSPACE}"

if [ "$TYPE" == "server" ]; then bench setup requirements --dev; fi

wait $wkpid

bench start &>> ~/frappe-bench/bench_start.log &
# Igual que `install_whktml`: sin redirigir, este hijo en segundo plano hereda
# el stdout del script y mantiene el pipe de `install.sh | tee ...` abierto
# hasta que termine por su cuenta, sin que el temporizador del paso lo sepa.
CI=Yes bench build --app frappe >> ~/frappe-bench/bench_build.log 2>&1 &
bench --site test_site reinstall --yes
