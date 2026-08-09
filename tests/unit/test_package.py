from scholartrace import __version__


def test_package_version_matches_m0_release() -> None:
    assert __version__ == "0.0.1"
