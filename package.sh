#!/bin/bash

# Clean up any existing package
rm -f lambda_function.zip
rm -rf temp_package

# Create a temporary directory for packaging
mkdir -p temp_package

# Copy the source code to the temporary directory
cp -v src/users_function.py temp_package/

# Make sure the file has the correct permissions
chmod 644 temp_package/users_function.py

# Create the zip file
cd temp_package
zip -r ../lambda_function.zip .
cd ..

# Clean up
rm -rf temp_package

echo "Lambda function packaged successfully!" 