# -*- coding: utf-8 -*-
"""一键导入Ranked种子 Pro Max - 入口文件"""

import sys
import ctypes

# 全局持有互斥体句柄，防止被GC回收导致互斥体释放
_mutex_handle = None


def check_single_instance(mutex_name="Global\\SeedToolGUI_SingleInstance"):
    """检测程序是否已经运行，使用Windows命名互斥体"""
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    error = ctypes.get_last_error()
    if error == 183:  # ERROR_ALREADY_EXISTS
        if handle:
            kernel32.CloseHandle(handle)
        return False
    _mutex_handle = handle
    return True


if __name__ == "__main__":
    if not check_single_instance():
        ctypes.windll.user32.MessageBoxW(0, "该应用已经启动过了！", "提示", 0x40 | 0x0)
        sys.exit(0)

    # 启用高DPI感知（系统级：修复高缩放下最大化无法铺满屏幕的问题，
    # per-monitor v2 会让 Tk 尺寸计算错位）
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    from tkinter import Tk
    from gui_app import SeedToolGUI

    root = Tk()
    app = SeedToolGUI(root)
    root.mainloop()
