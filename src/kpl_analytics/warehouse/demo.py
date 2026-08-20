from __future__ import annotations

import random
from datetime import date, timedelta

from kpl_analytics.warehouse.database import Warehouse

ROLE_POOLS = {
    "对抗路": [(518, "马超"), (514, "亚连"), (536, "夏洛特")],
    "打野": [(531, "镜"), (517, "大司命"), (502, "裴擒虎")],
    "中路": [(179, "女娲"), (110, "嬴政"), (152, "王昭君")],
    "发育路": [(199, "公孙离"), (112, "鲁班七号"), (519, "敖隐")],
    "游走": [(525, "鲁班大师"), (159, "朵莉亚"), (126, "夏侯惇")],
}

TEAMS = [
    ("10031", "杭州LGD.NBW", 0.54),
    ("10016", "佛山DRG", 0.52),
    ("10005", "成都AG超玩会", 0.58),
    ("10013", "重庆狼队", 0.56),
]

PLAYER_NAMES = {
    "对抗路": ["小落", "皖皖", "轩染", "归期"],
    "打野": ["小白熊", "花缘", "钟意", "小胖"],
    "中路": ["小名", "早点", "长生", "向鱼"],
    "发育路": ["小久", "梦岚", "一诺", "道崽"],
    "游走": ["小崽", "四宝", "大帅", "一笙"],
}

ITEMS = {
    "对抗路": [(1422, "抵抗之靴"), (1137, "暗影战斧"), (1333, "不祥征兆"), (1337, "贤者的庇护")],
    "打野": [(1522, "巡守利斧"), (1422, "抵抗之靴"), (1137, "暗影战斧"), (1334, "不死鸟之眼")],
    "中路": [(1423, "冷静之靴"), (1232, "回响之杖"), (1238, "博学者之怒"), (1239, "虚无法杖")],
    "发育路": [(1421, "急速战靴"), (1138, "破军"), (1141, "无尽战刃"), (1142, "泣血之刃")],
    "游走": [(1721, "近卫荣耀"), (1422, "抵抗之靴"), (1333, "不祥征兆"), (1332, "霸者重装")],
}

RUNES = {
    "对抗路": [(1504, "异变"), (2517, "隐匿"), (3514, "鹰眼")],
    "打野": [(1512, "宿命"), (2520, "狩猎"), (3509, "虚空")],
    "中路": [(1514, "梦魇"), (2520, "狩猎"), (3515, "心眼")],
    "发育路": [(1519, "祸源"), (2520, "狩猎"), (3514, "鹰眼")],
    "游走": [(1512, "宿命"), (2515, "调和"), (3509, "虚空")],
}

BAN_POOL = [(140, "关羽"), (157, "不知火舞"), (116, "韩信"), (171, "西施"), (132, "狄仁杰")]


def seed_demo(warehouse: Warehouse, battle_count: int = 72) -> dict[str, int]:
    """Create deterministic, clearly-labelled demo data for first-run exploration."""

    random.seed(39039)
    warehouse.clear()
    start = date.today() - timedelta(days=500)
    roles = list(ROLE_POOLS)

    with warehouse.connect() as connection:
        connection.execute(
            "INSERT INTO leagues VALUES (?, ?, ?, ?, ?)",
            ["demo-kpl", "KPL 本地演示赛季", "demo", start.isoformat(), date.today().isoformat()],
        )
        for battle_no in range(battle_count):
            match_no = battle_no // 3
            team1_index = match_no % len(TEAMS)
            team2_index = (match_no * 3 + 1) % len(TEAMS)
            if team2_index == team1_index:
                team2_index = (team2_index + 1) % len(TEAMS)
            team1, team2 = TEAMS[team1_index], TEAMS[team2_index]
            match_id = f"demo-match-{match_no:03d}"
            battle_id = f"demo-battle-{battle_no:03d}"
            game_date = start + timedelta(days=battle_no * 7)

            if battle_no % 3 == 0:
                connection.execute(
                    "INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        match_id,
                        "demo-kpl",
                        match_id,
                        "常规赛",
                        5,
                        game_date.isoformat(),
                        team1[0],
                        team1[1],
                        team2[0],
                        team2[1],
                    ],
                )

            picks: dict[int, list[tuple[int, str, str]]] = {1: [], 2: []}
            for role in roles:
                first = ROLE_POOLS[role][(battle_no + roles.index(role)) % 3]
                second = ROLE_POOLS[role][(battle_no + roles.index(role) + 1) % 3]
                picks[1].append((first[0], first[1], role))
                picks[2].append((second[0], second[1], role))

            draft_edge = sum((hero_id % 11) / 100 for hero_id, _, _ in picks[1]) - sum(
                (hero_id % 11) / 100 for hero_id, _, _ in picks[2]
            )
            probability_team1 = max(0.2, min(0.8, 0.5 + team1[2] - team2[2] + draft_edge))
            winning_camp = 1 if random.random() < probability_team1 else 2
            duration_ms = random.randint(720, 1320) * 1000
            connection.execute(
                "INSERT INTO battles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    battle_id,
                    match_id,
                    battle_no % 3 + 1,
                    game_date.isoformat(),
                    duration_ms,
                    winning_camp,
                    2,
                    True,
                ],
            )

            for camp, team in ((1, team1), (2, team2)):
                is_win = camp == winning_camp
                kills = random.randint(9, 18) if is_win else random.randint(2, 11)
                deaths = random.randint(2, 11) if is_win else random.randint(9, 18)
                connection.execute(
                    "INSERT INTO team_battles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        battle_id,
                        camp,
                        team[0],
                        team[1],
                        is_win,
                        kills,
                        deaths,
                        kills * 2 + random.randint(4, 10),
                        random.randint(47_000, 62_000) + (4_000 if is_win else 0),
                        random.randint(6, 9) if is_win else random.randint(1, 5),
                        random.randint(2, 5) if is_win else random.randint(0, 3),
                    ],
                )

            banned = [hero for pool in ROLE_POOLS.values() for hero in pool] + BAN_POOL
            banned = [
                hero
                for hero in banned
                if hero[0] not in {p[0] for side in picks.values() for p in side}
            ]
            actions: list[tuple[int, str, tuple[int, str]]] = []
            for index, hero in enumerate(banned[:10]):
                actions.append((1 + index % 2, "ban", hero))
            for pick_no in range(5):
                for camp in (1, 2):
                    hero = picks[camp][pick_no]
                    actions.append((camp, "pick", (hero[0], hero[1])))
            pick_index = 0
            for action_index, (camp, action_type, hero) in enumerate(actions, start=1):
                if action_type == "pick":
                    pick_index += 1
                connection.execute(
                    "INSERT INTO bp_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        battle_id,
                        action_index,
                        camp,
                        action_type,
                        hero[0],
                        hero[1],
                        action_index,
                        pick_index or None,
                    ],
                )

            for camp, (team_id, team_name, _) in ((1, team1), (2, team2)):
                for role_index, (hero_id, hero_name, role) in enumerate(picks[camp]):
                    roster_index = team1_index if camp == 1 else team2_index
                    player_name = PLAYER_NAMES[role][roster_index]
                    player_key = f"{team_id}:{player_name}".lower()
                    is_win = camp == winning_camp
                    deaths = random.randint(0, 3 if is_win else 6)
                    kills = random.randint(0, 6) + (1 if is_win else 0)
                    assists = random.randint(2, 12) + (2 if is_win else 0)
                    gold = random.randint(7_500, 13_000)
                    connection.execute(
                        """INSERT INTO player_battles VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            battle_id,
                            player_key,
                            player_name,
                            f"{team_name}.{player_name}",
                            team_id,
                            team_name,
                            camp,
                            role_index + 1,
                            role,
                            hero_id,
                            hero_name,
                            is_win,
                            kills,
                            deaths,
                            assists,
                            gold,
                            random.randint(180_000, 620_000),
                            random.randint(35_000, 145_000),
                            random.randint(55_000, 240_000),
                            random.uniform(45, 82),
                            random.uniform(4.8, 10.8),
                            bool(is_win and role_index == battle_no % 5),
                        ],
                    )
                    inventory = ITEMS[role]
                    for slot, (item_id, item_name) in enumerate(inventory, start=1):
                        connection.execute(
                            "INSERT INTO player_items VALUES (?, ?, ?, ?, ?)",
                            [battle_id, player_key, slot, item_id, item_name],
                        )
                    for rune_id, rune_name in RUNES[role]:
                        connection.execute(
                            "INSERT INTO player_runes VALUES (?, ?, ?, ?, ?)",
                            [battle_id, player_key, str(rune_id), rune_name, 10],
                        )

        connection.execute("INSERT INTO metadata VALUES ('data_mode', 'demo')")
        connection.execute(
            "INSERT INTO metadata VALUES ('built_at', ?)",
            [date.today().isoformat()],
        )
    return {
        "leagues": 1,
        "matches": (battle_count + 2) // 3,
        "battles": battle_count,
        "players": battle_count * 10,
    }
