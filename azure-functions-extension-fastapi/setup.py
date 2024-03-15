#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from setuptools import setup, find_packages

EXTRA_REQUIRES = {
    'dev': [
        'flake8~=4.0.1',
        'flake8-logging-format',
        'mypy',
        'pytest',
        'pytest-cov',
        'requests==2.*',
        'coverage',
        'pytest-instafail'
    ]
}

setup(
    name='azure-functions-extension-fastapi',
    version='0.0.1',
    author='Azure Functions team at Microsoft Corp.',
    author_email='azurefunctions@microsoft.com',
    description='FastApi Python worker extension for Azure Functions.',
    packages=find_packages(exclude=[
        'azure.functions.extension', 'azure.functions',
        'azure', 'tests', 'samples'
    ]),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'azure-functions-extension-base',
        'fastapi',
        'uvicorn'
    ],
    extras_require=EXTRA_REQUIRES
)
