import speakmot.updater as updater


def test_parses_tags_with_and_without_prefix():
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("0.4.1") == (0, 4, 1)


def test_unparsable_tag_is_lowest():
    assert updater.parse_version("") == (0,)
    assert updater.parse_version("release") == (0,)


def test_compares_versions_numerically_not_alphabetically():
    assert updater.is_newer("v0.10.0", "0.9.0")
    assert not updater.is_newer("v0.9.0", "0.10.0")


def test_same_version_is_not_newer():
    assert not updater.is_newer("v1.0.0", "1.0.0")


def test_check_reports_available_update(monkeypatch):
    monkeypatch.setattr(
        updater,
        "fetch_latest",
        lambda url=updater.RELEASES_URL: {
            "tag_name": "v9.0.0",
            "html_url": "https://example.invalid/release",
        },
    )
    available, version, page = updater.check("0.4.1")
    assert available
    assert version == "9.0.0"
    assert page == "https://example.invalid/release"


def test_check_survives_network_errors(monkeypatch):
    def boom(url=updater.RELEASES_URL):
        raise OSError("нет сети")

    monkeypatch.setattr(updater, "fetch_latest", boom)
    assert updater.check("0.4.1") == (False, "", "")
