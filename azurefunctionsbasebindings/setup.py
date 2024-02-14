# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

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
    name='azfuncbindingbase',
    version='0.0.15',
    author='Your Name',
    author_email='your.email@example.com',
    description='A short description of your package',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    extras_require=EXTRA_REQUIRES,
)