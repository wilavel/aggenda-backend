#!/bin/bash
set -e

mkdir -p dist

# Helper: copia el módulo shared en el directorio temporal
copy_shared() {
  mkdir -p "$1/shared"
  cp src/shared/__init__.py "$1/shared/"
  cp src/shared/utils.py "$1/shared/"
}

# Helper: copia libs si existen
copy_libs() {
  if [ -d libs ]; then
    mkdir -p "$1/libs"
    cp -r libs/* "$1/libs/"
  fi
}

# ── users_lambda.zip ─────────────────────────────────────────────────────────
rm -f dist/users_lambda.zip && rm -rf temp_package && mkdir -p temp_package
cp src/users_function.py temp_package/
copy_shared temp_package
copy_libs temp_package
cd temp_package && zip -r ../dist/users_lambda.zip . && cd ..
rm -rf temp_package
echo "dist/users_lambda.zip empaquetado correctamente."

# ── clinics_lambda.zip ───────────────────────────────────────────────────────
rm -f dist/clinics_lambda.zip && rm -rf temp_package && mkdir -p temp_package
cp src/clinics_function.py temp_package/
copy_shared temp_package
copy_libs temp_package
cd temp_package && zip -r ../dist/clinics_lambda.zip . && cd ..
rm -rf temp_package
echo "dist/clinics_lambda.zip empaquetado correctamente."

# ── email_lambda.zip ─────────────────────────────────────────────────────────
rm -f dist/email_lambda.zip && rm -rf temp_package && mkdir -p temp_package
cp src/email_function.py temp_package/
copy_shared temp_package
copy_libs temp_package
cd temp_package && zip -r ../dist/email_lambda.zip . && cd ..
rm -rf temp_package
echo "dist/email_lambda.zip empaquetado correctamente."

# ── get_ws_message_lambda.zip ────────────────────────────────────────────────
rm -f dist/get_ws_message_lambda.zip && rm -rf temp_package && mkdir -p temp_package
cp src/get_ws_message.py temp_package/
copy_libs temp_package
cd temp_package && zip -r ../dist/get_ws_message_lambda.zip . && cd ..
rm -rf temp_package
echo "dist/get_ws_message_lambda.zip empaquetado correctamente."
