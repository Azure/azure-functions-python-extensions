#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from setuptools import setup, find_packages

# TODO: pin to ext base version after published

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
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Environment :: Web Environment',
        'Development Status :: 5 - Production/Stable',
    ],
    license='MIT',
    python_requires='>=3.8',
    install_requires=[
        'azure-functions-extension-base',
        'fastapi==0.110.0',
        'uvicorn==0.28.0'
    ],
    extras_require=EXTRA_REQUIRES
)
