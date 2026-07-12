# -*- coding: utf-8 -*-
"""HTTP 请求工具与种子获取"""

import requests
import random
import time

from constants import (overworld_types, type_names,
                       _variation_category, _variation_struct)

# ---------------------------- HTTP 请求工具（带重试）----------------------------
_http_session = None


def _get_session():
    """获取或创建全局 requests.Session（线程安全）"""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update({
            "User-Agent": "RankedSeedTool/2.0",
            "Accept": "application/json",
            "Connection": "keep-alive",
        })
        # 连接池：最多保留10个连接，适配多线程
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0,  # 我们自己控制重试
            pool_block=False,
        )
        _http_session.mount("http://", adapter)
        _http_session.mount("https://", adapter)
    return _http_session


def api_get(url, timeout=15, max_retries=3):
    """
    带重试机制的 GET 请求
    - timeout: 单次请求超时秒数（默认15秒）
    - max_retries: 最大重试次数（默认3次）
    - 使用指数退避：第1次重试等1秒，第2次等2秒，第3次等4秒
    """
    session = _get_session()
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            return resp
        except requests.exceptions.Timeout:
            last_error = f"请求超时（{timeout}秒）"
        except requests.exceptions.ConnectionError as e:
            last_error = f"连接失败：{e}"
        except requests.exceptions.RequestException as e:
            last_error = f"请求异常：{e}"

        if attempt < max_retries:
            wait = 2 ** attempt  # 指数退避：1s, 2s, 4s
            time.sleep(wait)

    raise Exception(last_error)


def fetch_seed(api_base, selected_overworld, selected_nether, selected_variations,
               completion_ms, excluded_variations=None):
    """从API获取种子，支持多条件筛选（含剔除变种）"""
    if not selected_overworld:
        overworld_choice = random.choice(list(overworld_types.keys()))
    else:
        overworld_choice = random.choice(selected_overworld)

    if selected_nether:
        nether_choice = random.choice(selected_nether)
    else:
        nether_choice = None

    url = f"{api_base}/api/v2/seed?overworld={overworld_types[overworld_choice]}"
    if nether_choice:
        url += f"&nether={nether_choice}"

    overworld_type_str = overworld_types[overworld_choice]  # 如 "village"

    if selected_variations:
        allowed_vars = []
        for v in selected_variations:
            cat = _variation_category.get(v)
            struct = _variation_struct.get(v)
            if cat == "overworld":
                if struct == overworld_type_str:
                    allowed_vars.append(v)
            elif cat == "bastion" and nether_choice:
                if struct == nether_choice:
                    allowed_vars.append(v)
            elif cat == "fortress" and nether_choice:
                if struct == nether_choice:
                    allowed_vars.append(v)
            elif cat == "end":
                allowed_vars.append(v)
        if allowed_vars:
            url += "&variations=" + ",".join(allowed_vars)

    # 剔除变种：同样根据实际类型过滤，只有对应当前类型的剔除才生效
    if excluded_variations:
        excluded_vars = []
        for v in excluded_variations:
            cat = _variation_category.get(v)
            struct = _variation_struct.get(v)
            if cat == "overworld":
                if struct == overworld_type_str:
                    excluded_vars.append(v)
            elif cat == "bastion" and nether_choice:
                if struct == nether_choice:
                    excluded_vars.append(v)
            elif cat == "fortress" and nether_choice:
                if struct == nether_choice:
                    excluded_vars.append(v)
            elif cat == "end":
                excluded_vars.append(v)
        if excluded_vars:
            url += "&without=" + ",".join(excluded_vars)

    if completion_ms:
        url += f"&completion={completion_ms}"

    try:
        response = api_get(url, timeout=15, max_retries=3)
        if response.status_code != 200:
            error_msg = response.text[:200] if response.text else "无响应内容"
            raise Exception(f"API返回HTTP {response.status_code}：{error_msg}")
        data = response.json()
        if not data.get('success'):
            raise Exception(f"API返回错误：{data.get('message', '未知错误')}")
        seed_data = data['data']
        return (overworld_choice, type_names[overworld_choice],
                seed_data['overworldSeed'], seed_data['netherSeed'],
                seed_data.get('availableCounts', 0))
    except Exception as e:
        raise Exception(f"获取种子失败：{str(e)}")
