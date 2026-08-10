from importlib.metadata import metadata

from scholartrace import __version__


def test_package_version_matches_current_release() -> None:
    assert __version__ == "0.4.0"


def test_package_declares_apache_2_license() -> None:
    assert metadata("scholartrace")["License-Expression"] == "Apache-2.0"
