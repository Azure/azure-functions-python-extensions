# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Bootstrap for '$ python setup.py test' command."""

import os.path
import sys
import unittest
import unittest.runner


def suite():
    test_loader = unittest.TestLoader()
    return test_loader.discover(os.path.dirname(__file__), pattern="test_*.py")


if __name__ == "__main__":
    runner = unittest.runner.TextTestRunner()
    result = runner.run(suite())
    sys.exit(not result.wasSuccessful())
