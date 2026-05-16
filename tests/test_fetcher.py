from unittest.mock import MagicMock, patch

import pytest
import requests
from fetcher import fetch_top_repos, should_exclude_repo, get_exclude_reason, fetch_top_repos_with_debug


def _mock_search_response(items):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"items": items}
    return resp


def _repo(full_name, description, language="Python", stars=1000, forks=100, created_at="2026-05-16T00:00:00Z"):
    return {
        "full_name": full_name,
        "description": description,
        "stargazers_count": stars,
        "forks_count": forks,
        "language": language,
        "html_url": f"https://github.com/{full_name}",
        "created_at": created_at,
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


def test_fetch_top_repos_filters_obvious_game_cheats_and_backfills():
    page1 = [
        _repo("bad/gta-mod-menu", "Undetected mod menu cheat for GTA V", stars=3000),
        _repo("good/creative-tool", "Useful AI design tool", stars=2900),
        _repo("bad/cs2-aimbot", "Aimbot triggerbot ESP for CS2", stars=2800),
        _repo("bad/valorant-triggerbot", "Undetected triggerbot cheat for Valorant", stars=2750),
        _repo("bad/apex-esp", "ESP cheat overlay for Apex", stars=2740),
        _repo("bad/fortnite-cheat", "External cheat menu for Fortnite", stars=2730),
        _repo("bad/pubg-bypass", "Bypass anti cheat for PUBG", stars=2720),
        _repo("bad/roblox-aimbot", "Aimbot utility for Roblox", stars=2710),
        _repo("bad/minecraft-injector", "DLL injector cheat loader for Minecraft", stars=2705),
        _repo("bad/warzone-spoofer", "HWID spoofer for Warzone", stars=2701),
        _repo("bad/csgo-wallhack", "Wallhack cheat for CSGO", stars=2700),
        _repo("bad/gta-cheats", "Trainer cheats for GTA Online", stars=2699),
        _repo("bad/valorant-esp", "ESP menu for Valorant", stars=2698),
        _repo("bad/pubg-mod-menu", "Mod menu for PUBG", stars=2697),
        _repo("bad/apex-aimbot", "Aimbot for Apex", stars=2696),
        _repo("bad/fortnite-spoofer", "Spoofer for Fortnite", stars=2695),
        _repo("bad/roblox-cheat", "Cheat loader for Roblox", stars=2694),
        _repo("bad/cs2-injector", "Injector for CS2 cheat DLL", stars=2693),
        _repo("bad/gta-spoofer", "Spoofer for GTA V", stars=2692),
        _repo("bad/valorant-bypass", "Bypass anti cheat system", stars=2691),
        _repo("bad/apex-triggerbot", "Triggerbot for Apex", stars=2690),
        _repo("bad/csgo-aimbot", "Aimbot helper for CSGO", stars=2689),
        _repo("bad/warzone-cheat", "Cheat utility for Warzone", stars=2688),
        _repo("bad/minecraft-mod-menu", "Mod menu cheat for Minecraft", stars=2687),
        _repo("bad/fortnite-wallhack", "Wallhack for Fortnite", stars=2686),
        _repo("bad/pubg-spoofer", "Spoofer cheat for PUBG", stars=2685),
        _repo("bad/gta-injector", "Injector for GTA mods", stars=2684),
        _repo("bad/cs2-esp", "ESP overlay for CS2", stars=2683),
        _repo("bad/apex-cheat", "Cheat pack for Apex", stars=2682),
        _repo("bad/fortnite-aimbot", "Aimbot script for Fortnite", stars=2681),
    ]
    page2 = [
        _repo("good/desktop-pet", "Desktop pet companion", stars=2700),
        _repo("good/3d-studio", "Interactive 3D generation", stars=2600),
    ]

    with patch("fetcher.requests.get", side_effect=[_mock_search_response(page1), _mock_search_response(page2)]):
        repos = fetch_top_repos(top=3, period="weekly")

    assert [repo["name"] for repo in repos] == [
        "good/creative-tool",
        "good/desktop-pet",
        "good/3d-studio",
    ]


def test_fetch_top_repos_with_debug_returns_excluded_details():
    page1 = [
        _repo("bad/gta-mod-menu", "Undetected mod menu cheat for GTA V", stars=3000),
        _repo("good/creative-tool", "Useful AI design tool", stars=2900),
        _repo("bad/cs2-aimbot", "Aimbot triggerbot ESP for CS2", stars=2800),
        _repo("bad/valorant-triggerbot", "Undetected triggerbot cheat for Valorant", stars=2750),
        _repo("bad/apex-esp", "ESP cheat overlay for Apex", stars=2740),
        _repo("bad/fortnite-cheat", "External cheat menu for Fortnite", stars=2730),
        _repo("bad/pubg-bypass", "Bypass anti cheat for PUBG", stars=2720),
        _repo("bad/roblox-aimbot", "Aimbot utility for Roblox", stars=2710),
        _repo("bad/minecraft-injector", "DLL injector cheat loader for Minecraft", stars=2705),
        _repo("bad/warzone-spoofer", "HWID spoofer for Warzone", stars=2701),
        _repo("bad/csgo-wallhack", "Wallhack cheat for CSGO", stars=2700),
        _repo("bad/gta-cheats", "Trainer cheats for GTA Online", stars=2699),
        _repo("bad/valorant-esp", "ESP menu for Valorant", stars=2698),
        _repo("bad/pubg-mod-menu", "Mod menu for PUBG", stars=2697),
        _repo("bad/apex-aimbot", "Aimbot for Apex", stars=2696),
        _repo("bad/fortnite-spoofer", "Spoofer for Fortnite", stars=2695),
        _repo("bad/roblox-cheat", "Cheat loader for Roblox", stars=2694),
        _repo("bad/cs2-injector", "Injector for CS2 cheat DLL", stars=2693),
        _repo("bad/gta-spoofer", "Spoofer for GTA V", stars=2692),
        _repo("bad/valorant-bypass", "Bypass anti cheat system", stars=2691),
        _repo("bad/apex-triggerbot", "Triggerbot for Apex", stars=2690),
        _repo("bad/csgo-aimbot", "Aimbot helper for CSGO", stars=2689),
        _repo("bad/warzone-cheat", "Cheat utility for Warzone", stars=2688),
        _repo("bad/minecraft-mod-menu", "Mod menu cheat for Minecraft", stars=2687),
        _repo("bad/fortnite-wallhack", "Wallhack for Fortnite", stars=2686),
        _repo("bad/pubg-spoofer", "Spoofer cheat for PUBG", stars=2685),
        _repo("bad/gta-injector", "Injector for GTA mods", stars=2684),
        _repo("bad/cs2-esp", "ESP overlay for CS2", stars=2683),
        _repo("bad/apex-cheat", "Cheat pack for Apex", stars=2682),
        _repo("bad/fortnite-aimbot", "Aimbot script for Fortnite", stars=2681),
    ]
    page2 = [
        _repo("good/desktop-pet", "Desktop pet companion", stars=2700),
    ]

    with patch("fetcher.requests.get", side_effect=[_mock_search_response(page1), _mock_search_response(page2)]):
        kept, excluded = fetch_top_repos_with_debug(top=2, period="weekly")

    assert [repo["name"] for repo in kept] == [
        "good/creative-tool",
        "good/desktop-pet",
    ]
    assert excluded[0] == {
        "name": "bad/gta-mod-menu",
        "reason": "命中过滤：游戏相关词=gta；外挂/作弊词=mod menu",
    }
    assert len(excluded) == 29


def test_fetch_top_repos_retries_after_ssl_error_and_succeeds():
    page1 = [
        _repo("good/creative-tool", "Useful AI design tool", stars=2900),
    ]

    with patch(
        "fetcher.requests.get",
        side_effect=[requests.exceptions.SSLError("ssl eof"), _mock_search_response(page1)],
    ) as mock_get:
        with patch("fetcher.time.sleep") as mock_sleep:
            repos = fetch_top_repos(top=1, period="weekly")

    assert [repo["name"] for repo in repos] == ["good/creative-tool"]
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_fetch_top_repos_raises_runtime_error_after_retry_exhausted():
    with patch(
        "fetcher.requests.get",
        side_effect=requests.exceptions.SSLError("ssl eof"),
    ):
        with patch("fetcher.time.sleep"):
            with pytest.raises(RuntimeError) as exc:
                fetch_top_repos(top=1, period="weekly")

    assert "GitHub API 请求失败" in str(exc.value)
    assert "已重试 3 次" in str(exc.value)
