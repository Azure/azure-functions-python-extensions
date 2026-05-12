#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import os
import subprocess
import sys
import unittest


class TestCodeQuality(unittest.TestCase):
    def test_flake8(self):
        """Run flake8 on the package"""
        package_dir = os.path.join(
            os.path.dirname(__file__),
            '..',
            'azurefunctions'
        )
        result = subprocess.run(
            [sys.executable, '-m', 'flake8', package_dir],
            capture_output=True
        )
        if result.returncode != 0:
            self.fail(f"flake8 found issues:\n{result.stdout.decode()}")

    def test_mypy(self):
        """Run mypy on the package"""
        package_dir = os.path.join(
            os.path.dirname(__file__),
            '..',
            'azurefunctions'
        )
        result = subprocess.run(
            [sys.executable, '-m', 'mypy', package_dir, '--ignore-missing-imports'],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"mypy output:\n{result.stdout.decode()}")


if __name__ == "__main__":
    unittest.main()
