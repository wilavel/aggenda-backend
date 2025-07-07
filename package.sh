#!/bin/bash

# Crear carpeta dist si no existe
mkdir -p dist

# Empaquetar users_lambda.zip
rm -f dist/users_lambda.zip && rm -rf temp_package
mkdir -p temp_package
cp src/users_function.py temp_package/
if [ -d libs ]; then mkdir -p temp_package/libs && cp -r libs/* temp_package/libs/; fi
cd temp_package && zip -r ../dist/users_lambda.zip . && cd ..
rm -rf temp_package

echo "dist/users_lambda.zip empaquetado correctamente."

# Empaquetar clinics_lambda.zip
rm -f dist/clinics_lambda.zip && rm -rf temp_package
mkdir -p temp_package
cp src/clinics_function.py temp_package/
if [ -d libs ]; then mkdir -p temp_package/libs && cp -r libs/* temp_package/libs/; fi
cd temp_package && zip -r ../dist/clinics_lambda.zip . && cd ..
rm -rf temp_package

echo "dist/clinics_lambda.zip empaquetado correctamente." 