from unittest.mock import MagicMock, patch

from fetcher import fetch_top_repos, should_exclude_repo


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
