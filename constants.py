# -*- coding: utf-8 -*-
"""结构类型与变种数据常量"""

# ---------------------------- 核心数据结构 ----------------------------
overworld_types = {
    1: "buried_treasure",
    2: "ruined_portal",
    3: "desert_temple",
    4: "village",
    5: "shipwreck",
    6: "random"
}
type_names = {
    1: "宝藏", 2: "废门", 3: "沙漠神殿", 4: "村庄", 5: "沉船", 6: "随机"
}

# 下界堡垒类型映射
nether_types = {
    "bridge": "桥",
    "treasure": "藏宝室",
    "housing": "居住区",
    "stables": "棚"
}

# 变种数据结构（按分类分组）
variations_data = {
    "overworld": {
        "village": [
            "biome:structure:desert",
            "biome:structure:plains",
            "biome:structure:savanna",
            "biome:structure:snowy_tundra",
            "biome:structure:taiga",
            "chest:structure:diamond",
            "chest:structure:obsidian"
        ],
        "desert_temple": [
            "chest:structure:diamond",
            "chest:structure:egap"
        ],
        "ruined_portal": [
            "chest:structure:egap",
            "chest:structure:golden_carrot",
            "chest:structure:looting_sword",
            "type:structure:completable",
            "type:structure:lava"
        ],
        "shipwreck": [
            "chest:structure:carrot",
            "chest:structure:diamond",
            "type:structure:normal",
            "type:structure:sideways",
            "type:structure:upsidedown"
        ],
        "buried_treasure": []  # 无变种
    },
    "bastion": {
        "bridge": [
            "bastion:single:1",
            "bastion:single:2",
            "bastion:triple:1",
            "bastion:triple:2"
        ],
        "treasure": [],
        "housing": [
            "bastion:single:1",
            "bastion:triple:1",
            "bastion:triple:2"
        ],
        "stables": [
            "bastion:good_gap:1",
            "bastion:good_gap:2",
            "bastion:single:1",
            "bastion:single:2",
            "bastion:single:3",
            "bastion:small_single:1",
            "bastion:small_single:2",
            "bastion:small_single:3",
            "bastion:triple:1",
            "bastion:triple:2",
            "bastion:triple:3"
        ]
    },
    "fortress": {
        "fortress": [
            "biome:fortress:basalt_deltas",
            "biome:fortress:crimson_forest",
            "biome:fortress:nether_wastes",
            "biome:fortress:soul_sand_valley",
            "biome:fortress:warped_forest"
        ]
    },
    "end": {
        "end_tower": [
            "end_tower:caged:back",
            "end_tower:caged:back_center",
            "end_tower:caged:front",
            "end_tower:caged:front_center"
        ],
        "end_spawn": ["end_spawn:buried"]
    }
}

# 变种字符串 -> 分类 的反向映射，用于API请求时过滤无关变种
_variation_category = {}
# 变种字符串 -> 具体结构类型（如"village"、"stables"）的精确映射
_variation_struct = {}
for _cat, _type_dict in variations_data.items():
    for _struct_type, _vars_list in _type_dict.items():
        for _var_str in _vars_list:
            _variation_category[_var_str] = _cat
            _variation_struct[_var_str] = _struct_type
