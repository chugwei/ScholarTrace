from importlib.metadata import metadata

from scholartrace import __version__


def test_package_version_matches_m0_release() -> None:
    assert __version__ == "0.0.1"


def test_package_declares_apache_2_license() -> None:
    assert metadata("scholartrace")["License-Expression"] == "Apache-2.0"
