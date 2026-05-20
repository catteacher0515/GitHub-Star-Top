from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests
from fetcher import (
    fetch_new_repos,
    fetch_popular_repos,
    fetch_top_repos,
    fetch_top_repos_with_debug,
    fetch_trending_repos,
    get_quality_score,
    get_exclude_reason,
    should_exclude_repo,
)


def _mock_search_response(items):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"items": items}
    return resp


def _repo(
    full_name,
    description,
    language="Python",
    stars=1000,
    forks=100,
    created_at="2026-05-16T00:00:00Z",
    pushed_at="2026-05-19T00:00:00Z",
    license_data=None,
):
    return {
        "full_name": full_name,
        "name": full_name.split("/")[-1],
        "description": description,
        "stargazers_count": stars,
        "forks_count": forks,
        "language": language,
        "html_url": f"https://github.com/{full_name}",
        "created_at": created_at,
        "pushed_at": pushed_at,
        "updated_at": pushed_at,
        "license": license_data if license_data is not None else {"spdx_id": "MIT"},
    }


def test_should_exclude_repo_for_obvious_game_cheat_tool():
    repo = _repo("someone/gta-aimbot-menu", "Aimbot ESP cheat menu for GTA 5 online")
    assert should_exclude_repo(repo) is True
    assert "游戏相关词" in get_exclude_reason(repo)
    assert "外挂/作弊词" in get_exclude_reason(repo)


def test_should_exclude_repo_for_executor_or_hacks_style_projects():
    executor = _repo("thakur-works/Velocity-Executor", "Free Roblox script executor for PC with fast injection")
    hacks = _repo("PrimeKeeper58/blooket-hacks", "blooket hacks menu and helper tools")
    overlay = _repo("patchfighterway90/cs2-external-overlay", "external helper overlay for CS2 gamers")
    assert should_exclude_repo(executor) is True
    assert should_exclude_repo(hacks) is True
    assert should_exclude_repo(overlay) is True


def test_should_exclude_repo_for_hyphenated_overlay_and_autoclicker_variants():
    overlay = _repo("patchfighterway90/cs2-external-overlay", "Custom overlay utility for gamers")
    autoclicker = _repo("jiaoyanming0-bot/OPAutoClicker", "Auto clicker with Roblox AFK and Minecraft support")
    macro = _repo("someone/valorant-macro-kit", "Macro helper for Valorant players")
    assert should_exclude_repo(overlay) is True
    assert should_exclude_repo(autoclicker) is True
    assert should_exclude_repo(macro) is True


def test_should_exclude_repo_for_high_risk_standalone_keywords_without_game_name():
    hwid = _repo("manojmidhul92-art/Umbrella-HWID", "Advanced HWID changer with anti-cheat bypass support")
    vanguard = _repo("someone/kernel-bypass-tool", "Bypass Vanguard and BattlEye protections")
    eac = _repo("someone/eac-spoofer", "Spoofer for EAC protected environments")
    assert should_exclude_repo(hwid) is True
    assert should_exclude_repo(vanguard) is True
    assert should_exclude_repo(eac) is True


def test_should_keep_react_or_reaction_text_when_not_high_risk_repo():
    react_repo = _repo("cclank/cell-architecture-studio", "Interactive 3D cell architecture gallery built with React and Three.js")
    reaction_repo = _repo("lucasfrre/BongoCat-Desktop", "Live reaction desktop pet with OBS support")
    assert should_exclude_repo(react_repo) is False
    assert should_exclude_repo(reaction_repo) is False


def test_should_keep_creative_or_desktop_pet_projects():
    desktop_pet = _repo("lucasfrre/BongoCat-Desktop", "Desktop pet companion for your screen")
    modeling = _repo("TencentARC/Pixal3D", "AI-powered 3D modeling and generation workflow")
    assert should_exclude_repo(desktop_pet) is False
    assert should_exclude_repo(modeling) is False


def test_should_keep_entertainment_projects_but_exclude_emulator_launcher_and_crack_distribution_projects():
    wallpaper = _repo("PHjont/Wallpaper-Engine-Live-wallpaper-engine", "Live wallpaper engine for desktop setups")
    desktop_pet = _repo("mark9-droid/TomodachiPC", "Desktop pet companion inspired by virtual pets")
    emulator = _repo("pedrodg28/yuzu-emu", "Nintendo Switch emulator for desktop")
    rom = _repo("Flizorules05/ROM-MGBA-Pokemon-Emulator-PC", "ROM download pack and emulator setup for PC")
    launcher = _repo("arnabchoudhury404/hydra-launcher", "Game launcher for downloading and organizing titles")
    cracked = _repo("someone/office-crack-pack", "Pre-activated full version crack download toolkit")

    assert should_exclude_repo(wallpaper) is False
    assert should_exclude_repo(desktop_pet) is False
    assert should_exclude_repo(emulator) is True
    assert should_exclude_repo(rom) is True
    assert should_exclude_repo(launcher) is True
    assert should_exclude_repo(cracked) is True


def test_fetch_top_repos_filters_disallowed_items_across_sources_and_backfills():
    trending_items = [
        _repo("bad/gta-mod-menu", "Undetected mod menu cheat for GTA V", stars=3000),
        _repo("good/creative-tool", "Useful AI design tool", stars=2900),
    ]
    popular_items = [
        _repo("bad/yuzu-emu", "Nintendo Switch emulator for desktop", stars=5200),
        _repo("good/desktop-pet", "Desktop pet companion", stars=2700),
        _repo("good/3d-studio", "Interactive 3D generation", stars=2600),
    ]
    new_items = [
        _repo("bad/office-crack-pack", "Pre-activated full version crack download toolkit", stars=1500),
    ]

    with patch("fetcher.fetch_trending_repos", return_value=trending_items):
        with patch("fetcher.fetch_popular_repos", return_value=popular_items):
            with patch("fetcher.fetch_new_repos", return_value=new_items):
                repos = fetch_top_repos(top=3, period="weekly")

    assert [repo["name"] for repo in repos] == [
        "good/creative-tool",
        "good/desktop-pet",
        "good/3d-studio",
    ]


def test_fetch_top_repos_with_debug_returns_excluded_details():
    trending_items = [
        _repo("bad/gta-mod-menu", "Undetected mod menu cheat for GTA V", stars=3000),
        _repo("good/creative-tool", "Useful AI design tool", stars=2900),
    ]
    popular_items = [
        _repo("bad/yuzu-emu", "Nintendo Switch emulator for desktop", stars=5200),
        _repo("good/desktop-pet", "Desktop pet companion", stars=2700),
    ]

    with patch("fetcher.fetch_trending_repos", return_value=trending_items):
        with patch("fetcher.fetch_popular_repos", return_value=popular_items):
            with patch("fetcher.fetch_new_repos", return_value=[]):
                kept, excluded = fetch_top_repos_with_debug(top=2, period="weekly")

    assert [repo["name"] for repo in kept] == [
        "good/creative-tool",
        "good/desktop-pet",
    ]
    assert excluded == [
        {
            "name": "bad/gta-mod-menu",
            "reason": "命中过滤：游戏相关词=gta；外挂/作弊词=mod menu",
        },
        {
            "name": "bad/yuzu-emu",
            "reason": "命中过滤：模拟器/ROM词=emulator",
        },
    ]


def test_fetch_trending_repos_parses_weekly_page_and_loads_repo_details():
    trending_html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed"><a href="/good/trending-one">good / trending-one</a></h2>
    </article>
    <article class="Box-row">
      <h2 class="h3 lh-condensed"><a href="/good/trending-two">good / trending-two</a></h2>
    </article>
    """

    def mock_get(url, headers=None, params=None, timeout=None):
        if url == "https://github.com/trending?since=weekly":
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.text = trending_html
            return resp
        if url == "https://api.github.com/repos/good/trending-one":
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = _repo("good/trending-one", "First trending repo", stars=3200, forks=320)
            return resp
        if url == "https://api.github.com/repos/good/trending-two":
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = _repo("good/trending-two", "Second trending repo", stars=2800, forks=280)
            return resp
        raise AssertionError(f"unexpected url: {url}")

    with patch("fetcher.requests.get", side_effect=mock_get):
        repos = fetch_trending_repos(limit=2, period="weekly")

    assert [repo["full_name"] for repo in repos] == [
        "good/trending-one",
        "good/trending-two",
    ]


def test_fetch_popular_repos_uses_quality_thresholds():
    def mock_get(url, headers=None, params=None, timeout=None):
        assert url == "https://api.github.com/search/repositories"
        assert params["sort"] == "stars"
        assert params["order"] == "desc"
        assert "stars:>=3000" in params["q"]
        assert "archived:false" in params["q"]
        assert "fork:false" in params["q"]
        assert "pushed:>=" in params["q"]
        return _mock_search_response([_repo("good/popular-repo", "Quality repo", stars=4200)])

    with patch("fetcher.requests.get", side_effect=mock_get):
        repos = fetch_popular_repos(limit=1)

    assert [repo["full_name"] for repo in repos] == ["good/popular-repo"]


def test_fetch_top_repos_weekly_uses_source_mix_and_backfills_from_popular_pool():
    trending_items = [
        _repo("trend/repo-1", "Trending repo 1", stars=2100, created_at="2026-05-18T00:00:00Z"),
        _repo("trend/repo-2", "Trending repo 2", stars=2050, created_at="2026-05-17T00:00:00Z"),
        _repo("trend/repo-3", "Trending repo 3", stars=2000, created_at="2026-05-16T00:00:00Z"),
        _repo("trend/repo-4", "Trending repo 4", stars=1950, created_at="2026-05-15T00:00:00Z"),
    ]
    popular_items = [
        _repo("popular/repo-1", "Popular repo 1", stars=50000, created_at="2020-01-01T00:00:00Z"),
        _repo("popular/repo-2", "Popular repo 2", stars=48000, created_at="2019-01-01T00:00:00Z"),
        _repo("popular/repo-3", "Popular repo 3", stars=46000, created_at="2018-01-01T00:00:00Z"),
        _repo("popular/repo-4", "Popular repo 4", stars=44000, created_at="2017-01-01T00:00:00Z"),
        _repo("popular/repo-5", "Popular repo 5", stars=42000, created_at="2016-01-01T00:00:00Z"),
    ]
    new_items = [
        _repo("new/repo-1", "New repo 1", stars=1200, created_at="2026-05-19T00:00:00Z"),
    ]

    with patch("fetcher.fetch_trending_repos", return_value=trending_items, create=True) as mock_trending:
        with patch("fetcher.fetch_popular_repos", return_value=popular_items, create=True) as mock_popular:
            with patch("fetcher.fetch_new_repos", return_value=new_items, create=True) as mock_new:
                repos = fetch_top_repos(top=10, period="weekly")

    assert [repo["name"] for repo in repos] == [
        "trend/repo-1",
        "trend/repo-2",
        "trend/repo-3",
        "trend/repo-4",
        "popular/repo-1",
        "popular/repo-2",
        "popular/repo-3",
        "new/repo-1",
        "popular/repo-4",
        "popular/repo-5",
    ]
    assert repos[4]["created_at"] == "2020-01-01T00:00:00Z"
    mock_trending.assert_called_once_with(limit=6, period="weekly", lang=None)
    mock_popular.assert_called_once_with(limit=5, lang=None)
    mock_new.assert_called_once_with(limit=1, period="weekly", lang=None)


def test_get_quality_score_penalizes_meta_skill_and_marketing_noise():
    product_repo = _repo(
        "good/runtime-tool",
        "Fast runtime and CLI for building production apps",
        stars=12000,
        forks=1500,
    )
    meta_skill_repo = _repo(
        "someone/native-feel-skill",
        "Agent skill for designing desktop apps that feel native",
        stars=1400,
        forks=30,
    )
    marketing_repo = _repo(
        "someone/ai-to-earn-fast",
        "Use AI to earn money online with passive income workflows",
        stars=15000,
        forks=60,
    )

    with patch("fetcher._now_utc", return_value=datetime.fromisoformat("2026-05-20T00:00:00+00:00")):
        assert get_quality_score(product_repo) > get_quality_score(meta_skill_repo)
        assert get_quality_score(meta_skill_repo) > get_quality_score(marketing_repo)


def test_fetch_top_repos_limits_meta_skill_density_and_backfills_with_product_repos():
    trending_items = [
        _repo("trend/skill-one", "Agent skill for coding workflows", stars=12000),
        _repo("trend/skill-two", "Agent skills for code reviews", stars=11000),
        _repo("trend/skill-three", "Prompt skill pack for automation", stars=9000),
        _repo("trend/product-one", "Production browser automation framework", stars=8000),
        _repo("trend/product-two", "Compiler and runtime for modern apps", stars=7500),
    ]
    popular_items = [
        _repo("popular/product-one", "Database engine for production systems", stars=60000),
        _repo("popular/product-two", "Developer platform and SDK", stars=50000),
        _repo("popular/product-three", "Code search engine for large repos", stars=40000),
        _repo("popular/product-four", "Observability platform for teams", stars=30000),
    ]

    with patch("fetcher.fetch_trending_repos", return_value=trending_items):
        with patch("fetcher.fetch_popular_repos", return_value=popular_items):
            with patch("fetcher.fetch_new_repos", return_value=[]):
                repos = fetch_top_repos(top=8, period="weekly")

    names = [repo["name"] for repo in repos]
    assert "trend/skill-three" not in names
    assert names[:4] == [
        "trend/product-one",
        "trend/product-two",
        "trend/skill-one",
        "trend/skill-two",
    ]
    assert "popular/product-three" in names


def test_fetch_popular_repos_retries_after_ssl_error_and_succeeds():
    page1 = [
        _repo("good/creative-tool", "Useful AI design tool", stars=2900),
    ]

    with patch(
        "fetcher.requests.get",
        side_effect=[requests.exceptions.SSLError("ssl eof"), _mock_search_response(page1)],
    ) as mock_get:
        with patch("fetcher.time.sleep") as mock_sleep:
            repos = fetch_popular_repos(limit=1)

    assert [repo["full_name"] for repo in repos] == ["good/creative-tool"]
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_fetch_popular_repos_raises_runtime_error_after_retry_exhausted():
    with patch(
        "fetcher.requests.get",
        side_effect=requests.exceptions.SSLError("ssl eof"),
    ):
        with patch("fetcher.time.sleep"):
            with pytest.raises(RuntimeError) as exc:
                fetch_popular_repos(limit=1)

    assert "GitHub API 请求失败" in str(exc.value)
    assert "已重试 3 次" in str(exc.value)
