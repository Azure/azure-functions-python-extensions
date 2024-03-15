# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from setuptools import setup, find_packages

setup(
    name='azure-functions-extension-base',
    version='1.0.0a1',
    author='Azure Functions team at Microsoft Corp.',
    author_email='azurefunctions@microsoft.com',
    description='Base Python worker extension for Azure Functions.',
    packages=find_packages(exclude=[
        'azure.functions.extension', 'azure.functions', 'azure', 'tests'
    ]),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9'
)
