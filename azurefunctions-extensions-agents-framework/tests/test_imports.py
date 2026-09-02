import subprocess
import sys


def test_framework_import_does_not_import_durable():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import azurefunctions.extensions.agents.framework; "
                "assert 'azure.durable_functions' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
