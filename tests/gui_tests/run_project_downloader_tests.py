#!/usr/bin/env python3
"""Test runner for ProjectDownloader tests."""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run the ProjectDownloader tests."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    test_dir = Path(__file__).parent

    print("Running ProjectDownloader tests...")
    print(f"Project root: {project_root}")
    print(f"Test directory: {test_dir}")
    print("-" * 50)

    # Run unit tests
    print("Running unit tests...")
    result1 = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir / "test_project_downloader.py"),
            "-v",
            "--tb=short",
        ],
        cwd=project_root,
        check=False,
    )

    print("\n" + "-" * 50)

    # Run integration tests
    print("Running integration tests...")
    result2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir / "test_project_downloader_integration.py"),
            "-v",
            "--tb=short",
        ],
        cwd=project_root,
        check=False,
    )

    print("\n" + "=" * 50)

    if result1.returncode == 0 and result2.returncode == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
