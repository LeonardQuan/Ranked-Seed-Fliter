# -*- coding: utf-8 -*-
"""自动化任务执行"""

import time
import traceback


def type_text(text, delay=0.01):
    """模拟键盘逐字输入"""
    from pynput.keyboard import Controller
    kb = Controller()
    for char in str(text):
        kb.tap(char)
        time.sleep(delay)


def task(api_base, seed_info, log_queue, stats_callback):
    """自动化任务函数：在游戏主界面自动填入种子"""
    try:
        chosen_type_id, type_name, owseed, netherseed = seed_info
        log_queue.put(f"使用预加载种子：类型 {type_name}，主世界 {owseed}，下界 {netherseed}")
        from pynput.keyboard import Key, Controller
        kb = Controller()
        kb.tap(Key.tab)
        kb.tap(Key.enter)
        kb.tap(Key.tab)
        kb.tap(Key.tab)
        kb.tap(Key.tab)
        kb.tap(Key.enter)
        kb.tap(Key.tab)
        kb.tap(Key.tab)
        kb.tap(Key.enter)
        kb.tap(Key.enter)
        kb.tap(Key.enter)
        for _ in range(9):
            kb.tap(Key.tab)
        kb.tap(Key.enter)
        for _ in range(4):
            kb.tap(Key.tab)

        type_text(owseed)
        kb.tap(Key.tab)
        time.sleep(0.1)

        type_text(netherseed)
        kb.tap(Key.tab)

        type_text(owseed)

        for _ in range(3):
            kb.tap(Key.tab)
        kb.tap(Key.enter)

        log_queue.put("种子输入完成！")
        stats_callback(type_name, owseed, netherseed)
    except Exception as e:
        log_queue.put(f"任务出错：{str(e)}")
        log_queue.put(traceback.format_exc())
