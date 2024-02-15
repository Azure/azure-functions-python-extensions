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
        'coverage'
    ]
}

setup(
    name='azure-functions-extension-blob',
    version='0.0.3',
    author='Azure Functions team at Microsoft Corp.',
    author_email='azurefunctions@microsoft.com',
    description='Blob Python worker extension for Azure Functions.',
    packages=find_packages(exclude=[
        'azure.functions.extension', 'azure.functions', 'azure', 'tests'
    ]),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    install_requires=[
        'azure-functions-extension-base',
        'azure-storage-blob'
    ],
    extras_require=EXTRA_REQUIRES,
)