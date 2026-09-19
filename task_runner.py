# -*- coding: utf-8 -*-
"""自动化任务执行"""

import time
import traceback


def type_text(text, delay=0.005):
    """模拟键盘逐字输入（保守提速：10ms → 5ms，仍在 Windows 键盘队列安全区间）"""
    from pynput.keyboard import Controller
    kb = Controller()
    for char in str(text):
        kb.tap(char)
        time.sleep(delay)


def task(api_base, seed_info, log_queue, stats_callback):
    """自动化任务函数：在 MC 1.16.1 界面自动填入种子并进入游戏

    流程（按 F5 时游戏停在主菜单）：
        1. tab×1 → Singleplayer 聚焦
        2. enter  → 进入选档列表
        3. tab×3 → Create New World 聚焦
        4. enter  → 进入创建世界基础页
        5. tab×2 → 游戏难度按钮组聚焦
        6. enter×3 → 切到 Easy（简单模式）
        7. tab×4 → More World Options 聚焦
        8. enter  → 进入详细设置页
        9. tab×3 → advseed 标签聚焦
       10. enter  → 进入 advseed 子页
       11. tab×4 → 主世界种子输入框聚焦
       12. 输入 owseed
       13. tab×1 → 地狱种子输入框聚焦
       14. 输入 netherseed
       15. enter  → 进入游戏
    """
    try:
        chosen_type_id, type_name, owseed, netherseed = seed_info
        log_queue.put(f"使用预加载种子：类型 {type_name}，主世界 {owseed}，下界 {netherseed}")
        from pynput.keyboard import Key, Controller
        kb = Controller()

        # === 1. 主菜单 → Singleplayer ===
        time.sleep(0.3)
        kb.tap(Key.tab); time.sleep(0.25)
        kb.tap(Key.enter); time.sleep(0.5)

        # === 2. 选档列表 → Create New World ===
        for _ in range(3):
            kb.tap(Key.tab); time.sleep(0.1)
        kb.tap(Key.enter); time.sleep(0.6)

        # === 3. 基础页 → 切难度 → More World Options ===
        for _ in range(2):
            kb.tap(Key.tab); time.sleep(0.1)
        # enter×3 切换难度（默认 Normal → Hard → Peaceful → Easy）
        for _ in range(3):
            kb.tap(Key.enter); time.sleep(0.15)
        time.sleep(0.2)
        for _ in range(4):
            kb.tap(Key.tab); time.sleep(0.1)
        kb.tap(Key.enter); time.sleep(0.5)

        # === 4. 详细页 → advseed → 主世界种子 → 地狱种子 → 创建 ===
        for _ in range(3):
            kb.tap(Key.tab); time.sleep(0.1)
        kb.tap(Key.enter); time.sleep(0.4)
        for _ in range(4):
            kb.tap(Key.tab); time.sleep(0.1)
        time.sleep(0.2)

        # 主世界种子
        type_text(owseed, delay=0.01)
        time.sleep(0.15)
        kb.tap(Key.tab); time.sleep(0.15)

        # 地狱种子
        type_text(netherseed, delay=0.01)
        time.sleep(0.15)

        # 创建并进入游戏
        kb.tap(Key.enter)

        log_queue.put("种子输入完成！")
        stats_callback(type_name, owseed, netherseed)
    except Exception as e:
        log_queue.put(f"任务出错：{str(e)}")
        log_queue.put(traceback.format_exc())
