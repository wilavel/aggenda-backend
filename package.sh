#!/bin/bash

# Empaquetar users_lambda.zip
rm -f users_lambda.zip && rm -rf temp_package
mkdir -p temp_package
cp src/users_function.py temp_package/
if [ -d libs ]; then mkdir -p temp_package/libs && cp -r libs/* temp_package/libs/; fi
cd temp_package && zip -r ../users_lambda.zip . && cd ..
rm -rf temp_package

echo "users_lambda.zip empaquetado correctamente."

# Empaquetar clinics_lambda.zip
rm -f clinics_lambda.zip && rm -rf temp_package
mkdir -p temp_package
cp src/clinics_function.py temp_package/
if [ -d libs ]; then mkdir -p temp_package/libs && cp -r libs/* temp_package/libs/; fi
cd temp_package && zip -r ../clinics_lambda.zip . && cd ..
rm -rf temp_package

echo "clinics_lambda.zip empaquetado correctamente." 