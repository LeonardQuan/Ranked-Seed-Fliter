# -*- coding: utf-8 -*-
"""GUI 主界面 - SeedToolGUI 类"""

import json
import random
import os
import sys
import threading
import queue
import traceback
from tkinter import *
from tkinter import scrolledtext, messagebox, filedialog, ttk

from constants import (overworld_types, type_names, nether_types,
                       variations_data, _variation_category, _variation_struct)
from api_client import fetch_seed, api_get
from task_runner import task


class SeedToolGUI:
    # 现代浅色精修配色（参考 Notion / Linear light）
    COLORS = {
        'bg': '#f8fafc',
        'card_bg': '#ffffff',
        'primary': '#4f46e5',
        'primary_hover': '#4338ca',
        'primary_light': '#eef2ff',
        'primary_border': '#c7d2fe',
        'success': '#059669',
        'success_bg': '#ecfdf5',
        'warning': '#d97706',
        'warning_bg': '#fffbeb',
        'danger': '#dc2626',
        'danger_bg': '#fef2f2',
        'text': '#0f172a',
        'text_secondary': '#475569',
        'text_muted': '#94a3b8',
        'border': '#e2e8f0',
        'border_strong': '#cbd5e1',
        'input_bg': '#f8fafc',
        'header_bg': '#ffffff',
        'hover_bg': '#f1f5f9',
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Ranked 种子工具")
        self.root.geometry("1200x780"); self.root.eval("tk::PlaceWindow . center")
        self.root.resizable(True, True)
        self.root.configure(bg=self.COLORS['bg'])

        # 配置统一存到 %APPDATA%\RankedSeedTool，不再在 exe/工作目录旁边生成 json
        _config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'RankedSeedTool')
        try:
            os.makedirs(_config_dir, exist_ok=True)
            _config_path = os.path.join(_config_dir, 'config.json')
            # 兼容旧版本：如果 exe 目录/工作目录下已有 config.json，迁移过来
            _legacy = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
                                   else os.getcwd(), 'config.json')
            if not os.path.exists(_config_path) and os.path.exists(_legacy):
                import shutil
                shutil.copy2(_legacy, _config_path)
            self.config_path = _config_path
        except Exception:
            # AppData 不可用时退回原行为
            self.config_path = os.path.join(os.getcwd(), 'config.json')

        self._setup_styles()

        self.default_api = "http://43.143.231.104:8001"
        self.api_base = StringVar(value=self.default_api)
        self.selected_overworld = set()
        self.selected_nether = set()
        self.selected_variations = set()
        self.excluded_variations = set()
        from pynput.keyboard import Key
        self.start_hotkey = Key.f5
        self.exit_hotkey = Key.f6
        self.hotkey_capturing = None
        self.stats_count = 0
        self.listener = None
        self.log_queue = queue.Queue()

        self.prefetched_seed = None
        self.prefetch_lock = threading.Lock()
        self.prefetch_thread = None
        self.last_available_counts = 0
        self.prefetch_fail_count = 0

        self.completion_min = StringVar(value="")
        self.completion_sec = StringVar(value="")
        self.variation_text = StringVar(value="")

        self.use_elo = BooleanVar(value=False)
        self.elo_option = StringVar(value="1200+")
        self.fun_mode = BooleanVar(value=False)   # 趣味模式
        self._fun_toggle = False   # 交替标志：False=宝藏, True=废门
        self.custom_weights = {1: IntVar(value=20), 2: IntVar(value=20), 3: IntVar(value=20),
                               4: IntVar(value=20), 5: IntVar(value=20)}
        self.weight_total = IntVar(value=100)
        self.weight_debounce_id = None

        self.create_main_layout()
        self.load_config()
        self.process_log_queue()
        self.start_listener()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.trigger_prefetch()

    def _setup_styles(self):
        """配置 ttk 现代样式"""
        style = ttk.Style()
        style.theme_use('clam')

        self.FONT_TITLE = ("微软雅黑", 16, "bold")
        self.FONT_HEADING = ("微软雅黑", 11, "bold")
        self.FONT_BODY = ("微软雅黑", 10)
        self.FONT_SMALL = ("微软雅黑", 9)
        self.FONT_MONO = ("Consolas", 11)
        self.FONT_MONO_BIG = ("Consolas", 13, "bold")

        style.configure('TFrame', background=self.COLORS['bg'])
        style.configure('Card.TFrame', background=self.COLORS['card_bg'])
        style.configure('TLabel', background=self.COLORS['bg'], foreground=self.COLORS['text'], font=self.FONT_BODY)
        style.configure('Card.TLabel', background=self.COLORS['card_bg'], foreground=self.COLORS['text'], font=self.FONT_BODY)
        style.configure('Heading.TLabel', font=self.FONT_HEADING, foreground=self.COLORS['text'])
        style.configure('Muted.TLabel', background=self.COLORS['card_bg'], foreground=self.COLORS['text_muted'], font=self.FONT_SMALL)
        style.configure('Seed.TLabel', font=self.FONT_MONO, foreground=self.COLORS['primary'])
        style.configure('Success.TLabel', foreground=self.COLORS['success'], font=self.FONT_BODY)
        style.configure('Warning.TLabel', foreground=self.COLORS['warning'], font=self.FONT_BODY)
        style.configure('Danger.TLabel', foreground=self.COLORS['danger'], font=self.FONT_BODY)
        style.configure('TButton', font=self.FONT_BODY, padding=(12, 6))
        style.configure('Primary.TButton', background=self.COLORS['primary'])
        style.configure('Small.TButton', font=self.FONT_SMALL, padding=(8, 4))
        style.configure('TEntry', fieldbackground=self.COLORS['input_bg'], padding=6)
        style.configure('TCheckbutton', background=self.COLORS['card_bg'], font=self.FONT_BODY)
        style.configure('TRadiobutton', background=self.COLORS['card_bg'], font=self.FONT_BODY)
        style.configure('TNotebook', background=self.COLORS['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', font=self.FONT_BODY, padding=(16, 8))
        style.map('TNotebook.Tab', background=[('selected', self.COLORS['card_bg'])],
                  foreground=[('selected', self.COLORS['primary'])])
        style.configure('TScrollbar', background=self.COLORS['border'])

    def _create_card(self, parent, title, **pack_kw):
        ipadx = pack_kw.pop('ipadx', 0)
        card = Frame(parent, bg=self.COLORS['card_bg'], highlightbackground=self.COLORS['border'],
                     highlightthickness=1, padx=18+ipadx, pady=14)
        header = Frame(card, bg=self.COLORS['card_bg'])
        header.pack(fill='x', pady=(0, 10))
        ttk.Label(header, text=title, style='Heading.TLabel').pack(side=LEFT)
        body = Frame(card, bg=self.COLORS['card_bg'])
        body.pack(fill='x')
        card.pack(**pack_kw)
        return card, body

    def _create_separator(self, parent):
        sep = Frame(parent, height=1, bg=self.COLORS['border'])
        sep.pack(fill='x', pady=4)

    def _create_status_badge(self, parent, text, color_key, pack_side='left', pack_padx=0):
        dot_colors = {'success': '#22c55e', 'warning': '#f59e0b', 'danger': '#ef4444',
                      'info': '#4f8cff', 'muted': '#94a3b8'}
        color = dot_colors.get(color_key, '#94a3b8')
        badge = Frame(parent, bg=self.COLORS['card_bg'])
        dot = Label(badge, text="●", fg=color, bg=self.COLORS['card_bg'], font=("Arial", 8))
        dot.pack(side=LEFT, padx=(0, 4))
        label = Label(badge, text=text, fg=self.COLORS['text_secondary'], bg=self.COLORS['card_bg'],
                      font=self.FONT_SMALL)
        label.pack(side=LEFT)
        badge.pack(side=pack_side, padx=pack_padx)
        return dot, label

    # ===================== 主布局 =====================
    def create_main_layout(self):
        # ---- 白色 header + 底部分割线（Notion 风格）----
        header = Frame(self.root, bg=self.COLORS['header_bg'], height=56)
        header.pack(fill='x')
        header.pack_propagate(False)
        # 底部细分割线
        sep = Frame(header, bg=self.COLORS['border'], height=1)
        sep.pack(side=BOTTOM, fill='x')
        inner_header = Frame(header, bg=self.COLORS['header_bg'])
        inner_header.pack(fill='both', padx=24, pady=10)
        title_lbl = Label(inner_header, text="Ranked 种子工具",
                          fg=self.COLORS['text'], bg=self.COLORS['header_bg'], font=self.FONT_TITLE)
        title_lbl.pack(side=LEFT)
        # Pro Max 徽章（靛蓝 pill）
        badge = Label(inner_header, text=" Pro Max ", fg='white', bg=self.COLORS['primary'],
                      font=("微软雅黑", 9, "bold"), padx=2, pady=0)
        badge.pack(side=LEFT, padx=(10, 0), pady=(4, 0))
        # 右侧热键提示
        hint = Label(inner_header, text="F5 启动 · F6 退出", fg=self.COLORS['text_muted'],
                     bg=self.COLORS['header_bg'], font=self.FONT_SMALL)
        hint.pack(side=RIGHT)

        # ---- Main content: full-width, no centering ----
        self.main_frame = Frame(self.root, bg=self.COLORS['bg'])
        self.main_frame.pack(fill='both', expand=True, padx=14, pady=(14, 8))

        # Left: scrollable settings area (flexible width)
        left_container = Frame(self.main_frame, bg=self.COLORS['bg'])
        left_container.pack(side=LEFT, fill='both', expand=True)
        left_container.pack_propagate(False)

        self.left_canvas = Canvas(left_container, bg=self.COLORS['bg'], borderwidth=0, highlightthickness=0)
        scrollbar = Scrollbar(left_container, orient=VERTICAL, command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=scrollbar.set)

        self.left_interior = Frame(self.left_canvas, bg=self.COLORS['bg'])
        win_id = self.left_canvas.create_window((0, 0), window=self.left_interior, anchor=NW)
        self.left_interior.bind("<Configure>", self._on_left_configure)
        self.left_canvas.bind("<Configure>", lambda e: self.left_canvas.itemconfig(
            1, width=e.width - 4))

        self.left_canvas.pack(side=LEFT, fill='both', expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Right: info panel (fixed-ish width)
        self.right_frame = Frame(self.main_frame, bg=self.COLORS['bg'], width=340)
        self.right_frame.pack(side=RIGHT, fill='y')
        self.right_frame.pack_propagate(False)
        self.create_right_panel(self.right_frame)

        self.create_setting_cards()

        # 鼠标滚轮支持
        self._bind_mousewheel_recursive(self.left_canvas, self._on_left_mousewheel)
        self._bind_mousewheel_recursive(self.left_interior, self._on_left_mousewheel)

    def _on_left_configure(self, event):
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))


    # ===================== 右侧面板 =====================
    def create_right_panel(self, parent):
        info_card, info_body = self._create_card(parent, "📦 种子信息", fill='x', pady=(0, 10), ipadx=8)

        self.info_type_label = Label(info_body, text="类型：--", fg=self.COLORS['primary'],
                                     bg=self.COLORS['card_bg'], font=self.FONT_HEADING, anchor='w')
        self.info_type_label.pack(fill='x')
        self.info_ow_label = Label(info_body, text="主世界：--", fg=self.COLORS['text'],
                                   bg=self.COLORS['card_bg'], font=self.FONT_MONO_BIG, anchor='w')
        self.info_ow_label.pack(fill='x', pady=(6, 0))
        self.info_nether_label = Label(info_body, text="下界：--", fg=self.COLORS['text_secondary'],
                                       bg=self.COLORS['card_bg'], font=self.FONT_MONO_BIG, anchor='w')
        self.info_nether_label.pack(fill='x', pady=(2, 0))

        self._create_separator(info_card)

        stats_body = Frame(info_card, bg=self.COLORS['card_bg'])
        stats_body.pack(fill='x')
        self.count_label = Label(stats_body, text="已筛选：0 次", fg=self.COLORS['text_secondary'],
                                 bg=self.COLORS['card_bg'], font=self.FONT_SMALL)
        self.count_label.pack(side=LEFT)
        self.available_label = Label(stats_body, text="可用种子：--", fg=self.COLORS['text_secondary'],
                                     bg=self.COLORS['card_bg'], font=self.FONT_SMALL)
        self.available_label.pack(side=RIGHT)

        status_row = Frame(info_card, bg=self.COLORS['card_bg'])
        status_row.pack(fill='x', pady=(4, 0))
        self.prefetch_dot = Label(status_row, text="●", fg=self.COLORS['text_muted'],
                                   bg=self.COLORS['card_bg'], font=("Arial", 8))
        self.prefetch_dot.pack(side=LEFT, padx=(0, 4))
        self.prefetch_label = Label(status_row, text="预加载：空闲", fg=self.COLORS['text_muted'],
                                     bg=self.COLORS['card_bg'], font=self.FONT_SMALL)
        self.prefetch_label.pack(side=LEFT)

        # 日志面板（浅色终端风：米白底 + 深灰字）
        log_card, log_body = self._create_card(parent, "📝 操作日志", fill='both', expand=True, pady=(0, 0), ipadx=8)
        log_card.configure(bg=self.COLORS['card_bg'])

        btn_row = Frame(log_body, bg=self.COLORS['card_bg'])
        btn_row.pack(fill='x', pady=(0, 6))
        self._ghost_button(btn_row, "清空", self.clear_log).pack(side=LEFT, padx=(0, 6))
        self._ghost_button(btn_row, "导出", self.export_log).pack(side=LEFT)

        self.log_area = scrolledtext.ScrolledText(
            log_body, height=14, bg='#fbfcfe', fg='#334155',
            insertbackground=self.COLORS['text'], font=("Consolas", 10),
            relief='flat', borderwidth=1, padx=10, pady=8,
            selectbackground='#e2e8f0', state='disabled'
        )
        self.log_area.pack(fill='both', expand=True)
        self._bind_mousewheel_recursive(self.log_area, self._on_log_mousewheel)

        warn = Frame(parent, bg=self.COLORS['bg'])
        warn.pack(fill='x', pady=(8, 0))
        Label(warn, text="⚠ 仅在游戏主界面使用热键，否则可能造成严重后果",
              fg=self.COLORS['danger'], bg=self.COLORS['bg'], font=self.FONT_SMALL).pack(anchor='w')

    def _ghost_button(self, parent, text, command):
        """次按钮：白底细边框（ghost 风格）"""
        return Button(parent, text=text, command=command,
                      bg=self.COLORS['card_bg'], fg=self.COLORS['text_secondary'],
                      font=self.FONT_SMALL, relief='solid', padx=12, pady=3,
                      activebackground=self.COLORS['hover_bg'],
                      activeforeground=self.COLORS['text'],
                      cursor='hand2', borderwidth=1)

    def _styled_button(self, parent, text, command, size='normal'):
        if size == 'small':
            btn = Button(parent, text=text, command=command,
                         bg=self.COLORS['primary'], fg='white',
                         font=self.FONT_SMALL, relief='flat', padx=10, pady=3,
                         activebackground=self.COLORS['primary_hover'], activeforeground='white',
                         cursor='hand2', borderwidth=0)
        else:
            btn = Button(parent, text=text, command=command,
                         bg=self.COLORS['primary'], fg='white',
                         font=self.FONT_BODY, relief='flat', padx=16, pady=6,
                         activebackground=self.COLORS['primary_hover'], activeforeground='white',
                         cursor='hand2', borderwidth=0)
        return btn

    # ===================== 左侧设置卡片 =====================
    def create_setting_cards(self):
        parent = self.left_interior

        # API 设置
        api_card, api_body = self._create_card(parent, "⚙️ API 设置", fill='x', pady=(0, 10))
        api_row = Frame(api_body, bg=self.COLORS['card_bg'])
        api_row.pack(fill='x')
        self.api_entry = Entry(api_row, textvariable=self.api_base, width=48,
                               bg=self.COLORS['input_bg'], relief='solid',
                               borderwidth=1, font=self.FONT_BODY, fg=self.COLORS['text'],
                               insertbackground=self.COLORS['text'])
        self.api_entry.pack(side=LEFT, fill='x', expand=True, padx=(0, 8))
        Label(api_row, text="默认: 43.143.231.104:8001", fg=self.COLORS['text_muted'],
              bg=self.COLORS['card_bg'], font=self.FONT_SMALL).pack(side=RIGHT)

        def on_api_entry_change(event=None):
            current = self.api_base.get().strip()
            if not current:
                self.api_base.set(self.default_api)
                self.log_queue.put(f"API地址已重置为默认：{self.default_api}")
        self.api_entry.bind("<KeyRelease>", on_api_entry_change)

        # 开局类型
        type_card, type_body = self._create_card(parent, "🎯 开局类型", fill='x', pady=(0, 10))
        grid_frame = Frame(type_body, bg=self.COLORS['card_bg'])
        grid_frame.pack(fill='x')
        Label(type_body, text="点击切换，全不选 = 全部随机", fg=self.COLORS['text_muted'],
              bg=self.COLORS['card_bg'], font=self.FONT_SMALL).pack(fill='x', pady=(0, 6))
        self._load_type_images()

        self.type_vars = {}
        self.type_btns = {}
        for i in range(1, 7):
            var = IntVar()
            if i == 6:
                self.random_var = var
                var.set(1)
            else:
                self.type_vars[i] = var

            def make_cmd(tid=i, v=var):
                return lambda: self._toggle_type_btn(tid, v)
            btn = self._create_image_button(grid_frame, i, make_cmd())
            btn.grid(row=(i-1)//3, column=(i-1)%3, padx=6, pady=6, ipadx=20, ipady=6, sticky='ew')
            grid_frame.grid_columnconfigure((i-1)%3, weight=1)
            self.type_btns[i] = btn

        self._update_type_btn_appearance()
        btn_frame = Frame(type_body, bg=self.COLORS['card_bg'])
        btn_frame.pack(fill='x', pady=(8, 0))
        self._ghost_button(btn_frame, "全选", self.select_all_overworld).pack(side=LEFT, padx=(0, 6))
        self._ghost_button(btn_frame, "全不选", self.select_none_overworld).pack(side=LEFT)

        # 趣味模式按钮
        self.fun_row = Frame(type_body, bg=self.COLORS['card_bg'])
        self.fun_row.pack(fill='x', pady=(10, 0))
        Label(self.fun_row, text="来把爽的", bg=self.COLORS['card_bg'],
              fg=self.COLORS['text'], font=self.FONT_HEADING).pack(side=LEFT, padx=(0, 10))
        self.btn_fun = Button(self.fun_row, text="开启趣味模式",
                              command=self.toggle_fun_mode,
                              bg=self.COLORS['warning_bg'], fg=self.COLORS['warning'],
                              font=self.FONT_BODY, relief='solid', padx=14, pady=5,
                              activebackground=self.COLORS['warning'],
                              activeforeground='white',
                              cursor='hand2', borderwidth=1, anchor='w')
        self.btn_fun.pack(side=LEFT)
        Label(self.fun_row, text="废门(附魔剑+金萝卜+可完成) / 宝藏 随机 → 末地Open",
              bg=self.COLORS['card_bg'], fg=self.COLORS['text_muted'],
              font=self.FONT_SMALL).pack(side=LEFT, padx=(8, 0))

        # Elo 权重
        elo_card, elo_body = self._create_card(parent, "📊 Elo 权重设置", fill='x', pady=(0, 10))
        self.elo_check_btn = Button(elo_body, text="启用 Elo 权重",
                                    command=self._toggle_elo,
                                    bg=self.COLORS['card_bg'], fg=self.COLORS['text_secondary'],
                                    font=self.FONT_BODY, relief='solid', padx=10, pady=4,
                                    activebackground=self.COLORS['hover_bg'],
                                    cursor='hand2', borderwidth=1, anchor='w')
        self.elo_check_btn.pack(fill='x')

        self.elo_radio_frame = Frame(elo_body, bg=self.COLORS['card_bg'])
        self.elo_radio_frame.pack(fill='x', pady=(8, 0))
        for txt, val in [("1200+", "1200+"), ("600-1200", "600-1200"), ("0-599", "0-599"), ("自定义", "自定义")]:
            Radiobutton(self.elo_radio_frame, text=txt, variable=self.elo_option, value=val,
                        command=self.on_elo_option_change,
                        bg=self.COLORS['card_bg'], font=self.FONT_SMALL,
                        activebackground=self.COLORS['card_bg'],
                        selectcolor=self.COLORS['card_bg']).pack(side=LEFT, padx=4)

        self.custom_frame = Frame(elo_body, bg=self.COLORS['card_bg'])
        self.custom_frame.pack(fill='x', pady=(8, 0))
        self.weight_sliders = {}
        types_order = [1, 2, 3, 4, 5]
        for i, tid in enumerate(types_order):
            col_frame = Frame(self.custom_frame, bg=self.COLORS['card_bg'])
            col_frame.pack(side=LEFT, padx=6)
            Label(col_frame, text=type_names[tid], bg=self.COLORS['card_bg'],
                  fg=self.COLORS['text_secondary'], font=self.FONT_SMALL).pack()
            slider = Scale(col_frame, from_=0, to=100, orient=HORIZONTAL,
                           variable=self.custom_weights[tid], length=72,
                           command=self.on_weight_slider_change,
                           bg=self.COLORS['card_bg'], fg=self.COLORS['primary'],
                           troughcolor=self.COLORS['border'], highlightthickness=0,
                           font=self.FONT_SMALL, borderwidth=0)
            slider.pack()
            self.weight_sliders[tid] = slider

        sum_row = Frame(self.custom_frame, bg=self.COLORS['card_bg'])
        sum_row.pack(side=LEFT, padx=10)
        Label(sum_row, text="总和:", bg=self.COLORS['card_bg'],
              fg=self.COLORS['text_secondary'], font=self.FONT_SMALL).pack(side=LEFT)
        Label(sum_row, textvariable=self.weight_total, bg=self.COLORS['card_bg'],
              fg=self.COLORS['primary'], font=self.FONT_BODY).pack(side=LEFT, padx=(4, 8))
        self._styled_button(sum_row, "均衡", self.balance_weights, 'small').pack(side=LEFT)
        self.update_elo_state()

        # 热键设置
        hk_card, hk_body = self._create_card(parent, "⌨️ 热键设置", fill='x', pady=(0, 10))
        hk_row = Frame(hk_body, bg=self.COLORS['card_bg'])
        hk_row.pack(fill='x')
        Label(hk_row, text="启动:", bg=self.COLORS['card_bg'], font=self.FONT_BODY,
              fg=self.COLORS['text_secondary']).pack(side=LEFT, padx=(0, 6))
        self.btn_start_hotkey = Button(hk_row, text="F5", width=9, relief='solid', borderwidth=1,
                                       bg=self.COLORS['input_bg'], font=self.FONT_BODY,
                                       command=lambda: self.capture_hotkey('start'), cursor='hand2')
        self.btn_start_hotkey.pack(side=LEFT, padx=(0, 16))
        Label(hk_row, text="退出:", bg=self.COLORS['card_bg'], font=self.FONT_BODY,
              fg=self.COLORS['text_secondary']).pack(side=LEFT, padx=(0, 6))
        self.btn_exit_hotkey = Button(hk_row, text="F6", width=9, relief='solid', borderwidth=1,
                                      bg=self.COLORS['input_bg'], font=self.FONT_BODY,
                                      command=lambda: self.capture_hotkey('exit'), cursor='hand2')
        self.btn_exit_hotkey.pack(side=LEFT)
        Label(hk_row, text="（点击按钮后按目标键）", bg=self.COLORS['card_bg'],
              fg=self.COLORS['text_muted'], font=self.FONT_SMALL).pack(side=LEFT, padx=(12, 0))
        self.start_hotkey_text = StringVar(value="F5")
        self.exit_hotkey_text = StringVar(value="F6")

        # 高级 / 百宝箱
        toggle_row = Frame(parent, bg=self.COLORS['bg'])
        toggle_row.pack(fill='x', pady=(0, 10))

        self.btn_advanced = Button(toggle_row, text="🔧 高级设置  ▾", command=self.toggle_advanced,
                                    bg=self.COLORS['card_bg'], fg=self.COLORS['text'],
                                    font=self.FONT_BODY, relief='solid', padx=14, pady=8,
                                    activebackground=self.COLORS['hover_bg'], cursor='hand2', borderwidth=1, anchor='w')
        self.btn_advanced.pack(fill='x', pady=(0, 2))

        self.frame_advanced = Frame(parent, bg=self.COLORS['bg'])
        self.create_advanced_panel()
        self.frame_advanced.pack(fill='x', pady=(0, 10))

        self.btn_toolbox = Button(toggle_row, text="🧰 百宝箱  ▾", command=self.toggle_toolbox,
                                   bg=self.COLORS['card_bg'], fg=self.COLORS['text'],
                                   font=self.FONT_BODY, relief='solid', padx=14, pady=8,
                                   activebackground=self.COLORS['hover_bg'], cursor='hand2', borderwidth=1, anchor='w')
        self.btn_toolbox.pack(fill='x')
        self.frame_toolbox = Frame(parent, bg=self.COLORS['bg'])
        self.create_toolbox_panel()

    def _load_type_images(self):
        import os as _os
        if getattr(sys, 'frozen', False):
            base = _os.path.join(sys._MEIPASS, 'assets')
        else:
            base = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'assets')

        icon_files = {
            1: 'buried_treasure_icon.png', 2: 'ruined_portal_icon.png',
            3: 'desert_temple_icon.png', 4: 'village_icon.png',
            5: 'shipwreck_icon.png', 6: 'random_icon.png',
        }
        self.type_images = {}
        for tid, fname in icon_files.items():
            path = _os.path.join(base, fname)
            try:
                img = PhotoImage(file=path)
                img = img.subsample(max(1, img.width() // 64), max(1, img.height() // 64))
                self.type_images[tid] = img
            except Exception:
                self.type_images[tid] = None

        # 下界堡垒类型图片（真实渲染图，64x64 缩略）
        self.nether_images = {}
        nether_img_files = {
            'bridge': 'bastion_bridge.png',
            'treasure': 'bastion_treasure.png',
            'housing': 'bastion_housing.png',
            'stables': 'bastion_stables.png',
        }
        for key, fname in nether_img_files.items():
            path = _os.path.join(base, fname)
            try:
                img = PhotoImage(file=path)
                # 缩到 64x64
                w, h = img.width(), img.height()
                factor = max(1, max(w, h) // 64)
                if factor > 1:
                    img = img.subsample(factor, factor)
                self.nether_images[key] = img
            except Exception:
                self.nether_images[key] = None

        # 维度图片（用于 Tab 图标，16x16 小图）
        self.dim_images = {}
        dim_img_files = {
            'overworld': 'overworld.png',
            'bastion': 'bastion_treasure.png',  # 堡垒用藏宝室图代表
            'fortress': 'fortress.png',
            'end': 'end.png',
        }
        for key, fname in dim_img_files.items():
            path = _os.path.join(base, fname)
            try:
                img = PhotoImage(file=path)
                w, h = img.width(), img.height()
                factor = max(1, max(w, h) // 16)
                if factor > 1:
                    img = img.subsample(factor, factor)
                self.dim_images[key] = img
            except Exception:
                self.dim_images[key] = None

        # emoji 兜底（图片加载失败时用）
        self.nether_icons = {
            'bridge': '🌉',
            'treasure': '💎',
            'housing': '🏠',
            'stables': '🛖',
        }
        self.dim_icons = {
            'overworld': '🌍',
            'bastion': '🏰',
            'fortress': '🔥',
            'end': '🌌',
        }

    def _create_image_button(self, parent, type_id, command):
        btn_frame = Frame(parent, bg=self.COLORS['card_bg'],
                          highlightbackground=self.COLORS['border'],
                          highlightthickness=1, cursor='hand2')
        btn_frame.bind('<Button-1>', lambda e: command())
        img = self.type_images.get(type_id)
        if img:
            img_lbl = Label(btn_frame, image=img, bg=self.COLORS['card_bg'], cursor='hand2')
            img_lbl.image = img
            img_lbl.pack(pady=(8, 2))
            img_lbl.bind('<Button-1>', lambda e: command())
        txt = type_names[type_id]
        text_lbl = Label(btn_frame, text=txt, bg=self.COLORS['card_bg'],
                         fg=self.COLORS['text'], font=self.FONT_SMALL, cursor='hand2')
        text_lbl.pack(pady=(0, 6))
        text_lbl.bind('<Button-1>', lambda e: command())
        btn_frame._children_widgets = []
        for child in btn_frame.winfo_children():
            btn_frame._children_widgets.append(child)
        return btn_frame

    def _update_image_button_style(self, btn_frame, selected):
        if selected:
            bg, border, fg = self.COLORS['primary_light'], self.COLORS['primary'], self.COLORS['primary']
        else:
            bg, border, fg = self.COLORS['card_bg'], self.COLORS['border'], self.COLORS['text']
        btn_frame.config(bg=bg, highlightbackground=border)
        for child in btn_frame._children_widgets:
            try:
                child.config(bg=bg)
                if isinstance(child, Label) and child.cget('text') in type_names.values():
                    child.config(fg=fg)
            except Exception:
                pass

    def _toggle_type_btn(self, tid, var):
        var.set(1 if var.get() == 0 else 0)
        self._update_type_btn_appearance()
        self.on_overworld_change()

    def _update_type_btn_appearance(self):
        for i in range(1, 7):
            var = self.random_var if i == 6 else self.type_vars[i]
            self._update_image_button_style(self.type_btns[i], var.get() == 1)

    def _toggle_elo(self):
        self.use_elo.set(not self.use_elo.get())
        self.on_elo_toggle()

    def select_all_overworld(self):
        for i in range(1, 6):
            self.type_vars[i].set(1)
        self.random_var.set(0)
        self._update_type_btn_appearance()
        self.on_overworld_change()

    def select_none_overworld(self):
        for i in range(1, 6):
            self.type_vars[i].set(0)
        self.random_var.set(0)
        self._update_type_btn_appearance()
        self.on_overworld_change()

    # ===================== 趣味模式 =====================
    def toggle_fun_mode(self):
        """切换趣味模式：随机废门或宝藏，预设最优变种"""
        if self.fun_mode.get():
            # 关闭趣味模式：恢复默认状态
            self.fun_mode.set(False)
            self.btn_fun.config(text="开启趣味模式", fg=self.COLORS['warning'])
            # 重新启用开局类型按钮
            for i in range(1, 6):
                btn = self.type_btns[i]
                btn.config(cursor='hand2')
                tid = i
                var = self.type_vars[i]
                cmd = lambda t=tid, v=var: self._toggle_type_btn(t, v)
                btn.bind('<Button-1>', lambda e, c=cmd: c())
                for child in btn._children_widgets:
                    child.config(cursor='hand2')
                    child.bind('<Button-1>', lambda e, c=cmd: c())
            self.random_var.set(1)
            self._update_type_btn_appearance()
            # 恢复Elo开关
            if hasattr(self, '_saved_use_elo'):
                self.use_elo.set(self._saved_use_elo)
            self.update_elo_state()
            # 清除趣味变种
            self.clear_all_variations()
            self.log_queue.put("趣味模式已关闭，恢复默认配置")
        else:
            # 开启趣味模式
            self.fun_mode.set(True)
            self._fun_toggle = False   # 重置交替：从宝藏开始
            self.btn_fun.config(text="趣味模式已开启", fg='white', bg=self.COLORS['warning'])
            # 取消所有开局类型选择
            for i in range(1, 6):
                self.type_vars[i].set(0)
            self.random_var.set(0)
            self._update_type_btn_appearance()
            # 禁用开局类型按钮
            for i in range(1, 6):
                btn = self.type_btns[i]
                btn.config(cursor='arrow')
                btn.unbind('<Button-1>')
                for child in btn._children_widgets:
                    child.config(cursor='arrow')
                    child.unbind('<Button-1>')
            # 关闭Elo（保存原状态）
            self._saved_use_elo = self.use_elo.get()
            self.use_elo.set(False)
            self.update_elo_state()
            # 清空下界和变种选择
            for key in self.nether_vars:
                self.nether_vars[key].set(0)
            self._update_nether_btn_appearance()
            self.clear_all_variations()
            self.variation_text.set("")
            self.log_queue.put("趣味模式已开启！随机废门（附魔剑+金萝卜+可完成）/宝藏，末地Open")

        self.update_selected_overworld()
        self.update_selected_nether()
        self.update_selected_variations()
        self.save_config()
        self.prefetched_seed = None
        self.last_available_counts = 0
        self.trigger_prefetch()

    def clear_all_variations(self):
        """清除所有变种选择"""
        for var_str in self.var_include:
            self.var_include[var_str].set(0)
            self._update_var_btn_appearance(var_str)
        for var_str in self.var_exclude:
            self.var_exclude[var_str].set(0)
            self._update_var_btn_appearance(var_str)

    # ===================== 高级设置面板 =====================
    def create_advanced_panel(self):
        self.var_include = {}
        self.var_exclude = {}
        self._var_include_btns = {}
        self._var_exclude_btns = {}

        nether_card, nether_body = self._create_card(self.frame_advanced, "🏰 下界堡垒类型（可多选）",
                                                      fill='x', pady=(0, 8))
        self.nether_vars = {}
        self.nether_btns = {}
        # 2×2 网格布局
        nether_grid = Frame(nether_body, bg=self.COLORS['card_bg'])
        nether_grid.pack(fill='x')
        for idx, (key, name) in enumerate(nether_types.items()):
            var = IntVar()
            # 优先用真实图片，失败用 emoji
            img = self.nether_images.get(key)
            icon = self.nether_icons.get(key, '❓')
            # 卡片式按钮：图片/图标在上，文字在下
            btn_frame = Frame(nether_grid, bg=self.COLORS['card_bg'],
                              highlightbackground=self.COLORS['border'],
                              highlightthickness=1, cursor='hand2')
            row, col = idx // 2, idx % 2
            btn_frame.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')
            nether_grid.grid_columnconfigure(col, weight=1)
            # 图片或 emoji
            if img:
                icon_lbl = Label(btn_frame, image=img, bg=self.COLORS['card_bg'], cursor='hand2')
                icon_lbl.image = img  # 防 GC
            else:
                icon_lbl = Label(btn_frame, text=icon, font=("Segoe UI Emoji", 20),
                                 bg=self.COLORS['card_bg'], cursor='hand2')
            icon_lbl.pack(pady=(8, 2))
            # 文字
            text_lbl = Label(btn_frame, text=name, font=self.FONT_SMALL,
                             bg=self.COLORS['card_bg'], fg=self.COLORS['text'],
                             cursor='hand2')
            text_lbl.pack(pady=(0, 6))
            # 绑定点击
            def make_cmd(k=key, v=var):
                return lambda: self._toggle_nether_btn(k, v)
            cmd = make_cmd()
            btn_frame.bind('<Button-1>', lambda e, c=cmd: c())
            icon_lbl.bind('<Button-1>', lambda e, c=cmd: c())
            text_lbl.bind('<Button-1>', lambda e, c=cmd: c())
            # 存引用
            btn_frame._icon_lbl = icon_lbl
            btn_frame._text_lbl = text_lbl
            self.nether_vars[key] = var
            self.nether_btns[key] = btn_frame

        var_card, var_body = self._create_card(self.frame_advanced, "🧬 变种筛选", fill='x', pady=(0, 8))
        self.var_notebook = ttk.Notebook(var_body)
        self.var_notebook.pack(fill='both', expand=True)

        self.overworld_var_frame = Frame(self.var_notebook, bg=self.COLORS['card_bg'])
        self.var_notebook.add(self.overworld_var_frame, text="主世界")
        self.create_variation_group(self.overworld_var_frame, "overworld")

        self.bastion_var_frame = Frame(self.var_notebook, bg=self.COLORS['card_bg'])
        self.var_notebook.add(self.bastion_var_frame, text="下界堡垒")
        self.create_variation_group(self.bastion_var_frame, "bastion")

        self.fortress_var_frame = Frame(self.var_notebook, bg=self.COLORS['card_bg'])
        self.var_notebook.add(self.fortress_var_frame, text="下界要塞")
        self.create_variation_group(self.fortress_var_frame, "fortress")

        self.end_var_frame = Frame(self.var_notebook, bg=self.COLORS['card_bg'])
        self.var_notebook.add(self.end_var_frame, text="末地")
        self.create_variation_group(self.end_var_frame, "end")

        extra_row = Frame(var_body, bg=self.COLORS['card_bg'])
        extra_row.pack(fill='x', pady=(8, 0))
        Label(extra_row, text="其他（逗号分隔）:", bg=self.COLORS['card_bg'],
              fg=self.COLORS['text_secondary'], font=self.FONT_SMALL).pack(side=LEFT, padx=(0, 6))
        Entry(extra_row, textvariable=self.variation_text, width=28,
              bg=self.COLORS['input_bg'], relief='solid', borderwidth=1,
              font=self.FONT_BODY).pack(side=LEFT, padx=(0, 4))
        self._styled_button(extra_row, "清除", lambda: self.variation_text.set(""), 'small').pack(side=LEFT)

        time_card, time_body = self._create_card(self.frame_advanced, "⏱️ 完成时间上限（留空=不限制）",
                                                  fill='x', pady=(0, 0))
        Label(time_body, text="分钟:", bg=self.COLORS['card_bg'], font=self.FONT_BODY).pack(side=LEFT, padx=(0, 4))
        Spinbox(time_body, from_=0, to=59, textvariable=self.completion_min, width=5,
                bg=self.COLORS['input_bg'], font=self.FONT_BODY).pack(side=LEFT, padx=(0, 10))
        Label(time_body, text="秒:", bg=self.COLORS['card_bg'], font=self.FONT_BODY).pack(side=LEFT, padx=(0, 4))
        Spinbox(time_body, from_=0, to=59, textvariable=self.completion_sec, width=5,
                bg=self.COLORS['input_bg'], font=self.FONT_BODY).pack(side=LEFT)

    def _toggle_nether_btn(self, key, var):
        var.set(1 if var.get() == 0 else 0)
        self._update_nether_btn_appearance()
        self.on_nether_change()

    def _update_nether_btn_appearance(self):
        for key, var in self.nether_vars.items():
            btn_frame = self.nether_btns[key]
            if var.get() == 1:
                bg, border = self.COLORS['primary_light'], self.COLORS['primary']
                fg = self.COLORS['primary']
            else:
                bg, border = self.COLORS['card_bg'], self.COLORS['border']
                fg = self.COLORS['text']
            btn_frame.config(bg=bg, highlightbackground=border)
            try:
                btn_frame._icon_lbl.config(bg=bg)
                btn_frame._text_lbl.config(bg=bg, fg=fg)
            except Exception:
                pass

    def create_variation_group(self, parent, category):
        data = variations_data[category]
        for struct_type, vars_list in data.items():
            if not vars_list:
                continue
            # Compact card, packed horizontally
            frame = Frame(parent, bg=self.COLORS['card_bg'], highlightbackground=self.COLORS['border'],
                          highlightthickness=1, padx=10, pady=8)
            frame.pack(side=LEFT, anchor=NW, padx=4, pady=4)
            # 结构类型标题（带图标）
            struct_icons = {
                'village': '🏘️', 'desert_temple': '🏜️', 'ruined_portal': '🌀',
                'shipwreck': '🚢', 'buried_treasure': '💰',
                'bridge': '🌉', 'treasure': '💎', 'housing': '🏠', 'stables': '🛖',
                'fortress': '🔥', 'end_tower': '🗼', 'end_spawn': '🌌'
            }
            icon = struct_icons.get(struct_type, '📦')
            Label(frame, text=f"{icon} {struct_type}", bg=self.COLORS['card_bg'],
                  fg=self.COLORS['primary'], font=("微软雅黑", 10, "bold")).pack(anchor='w', pady=(0, 6))
            for var_str in vars_list:
                var_row = Frame(frame, bg=self.COLORS['card_bg'])
                var_row.pack(fill='x', anchor='w', pady=1)
                Label(var_row, text=var_str, bg=self.COLORS['card_bg'],
                      font=("Consolas", 9), fg=self.COLORS['text_secondary'],
                      width=24, anchor='w').pack(side=LEFT, padx=(0, 6))

                inc_var = IntVar(value=0)
                exc_var = IntVar(value=0)
                self.var_include[var_str] = inc_var
                self.var_exclude[var_str] = exc_var

                btn_inc = Button(var_row, text="✓", font=("Arial", 10, "bold"),
                                 bg=self.COLORS['success_bg'], fg=self.COLORS['success'],
                                 activebackground=self.COLORS['success'], activeforeground='white',
                                 relief='solid', padx=4, pady=1, borderwidth=1,
                                 highlightbackground=self.COLORS['success'],
                                 highlightthickness=1,
                                 cursor='hand2', width=2,
                                 command=lambda vs=var_str, iv=inc_var, ev=exc_var:
                                     self._toggle_var_include(vs, iv, ev))
                btn_inc.pack(side=LEFT, padx=(0, 1))

                btn_exc = Button(var_row, text="✗", font=("Arial", 10, "bold"),
                                 bg=self.COLORS['danger_bg'], fg=self.COLORS['danger'],
                                 activebackground=self.COLORS['danger'], activeforeground='white',
                                 relief='solid', padx=4, pady=1, borderwidth=1,
                                 highlightbackground=self.COLORS['danger'],
                                 highlightthickness=1,
                                 cursor='hand2', width=2,
                                 command=lambda vs=var_str, iv=inc_var, ev=exc_var:
                                     self._toggle_var_exclude(vs, iv, ev))
                btn_exc.pack(side=LEFT)

                self._var_include_btns[var_str] = btn_inc
                self._var_exclude_btns[var_str] = btn_exc

            self._styled_button(frame, "清除",
                                lambda vs=vars_list: self.clear_variation_group(vs),
                                'small').pack(pady=(3, 0))

    def _toggle_var_include(self, var_str, inc_var, exc_var):
        if inc_var.get() == 1:
            inc_var.set(0)
        else:
            inc_var.set(1)
            exc_var.set(0)
        self._update_var_btn_appearance(var_str)
        self.on_variation_change()

    def _toggle_var_exclude(self, var_str, inc_var, exc_var):
        if exc_var.get() == 1:
            exc_var.set(0)
        else:
            exc_var.set(1)
            inc_var.set(0)
        self._update_var_btn_appearance(var_str)
        self.on_variation_change()

    def _update_var_btn_appearance(self, var_str):
        inc_var = self.var_include.get(var_str)
        exc_var = self.var_exclude.get(var_str)
        btn_inc = self._var_include_btns.get(var_str)
        btn_exc = self._var_exclude_btns.get(var_str)
        if btn_inc and inc_var:
            if inc_var.get() == 1:
                btn_inc.config(bg=self.COLORS['success'], fg='white',
                               activebackground=self.COLORS['success'], activeforeground='white',
                               highlightbackground=self.COLORS['success'])
            else:
                btn_inc.config(bg=self.COLORS['success_bg'], fg=self.COLORS['success'],
                               activebackground=self.COLORS['success'], activeforeground='white',
                               highlightbackground=self.COLORS['success'])
        if btn_exc and exc_var:
            if exc_var.get() == 1:
                btn_exc.config(bg=self.COLORS['danger'], fg='white',
                               activebackground=self.COLORS['danger'], activeforeground='white',
                               highlightbackground=self.COLORS['danger'])
            else:
                btn_exc.config(bg=self.COLORS['danger_bg'], fg=self.COLORS['danger'],
                               activebackground=self.COLORS['danger'], activeforeground='white',
                               highlightbackground=self.COLORS['danger'])

    def clear_variation_group(self, var_strings):
        for s in var_strings:
            if s in self.var_include:
                self.var_include[s].set(0)
            if s in self.var_exclude:
                self.var_exclude[s].set(0)
            self._update_var_btn_appearance(s)
        self.on_variation_change()

    def create_toolbox_panel(self):
        card, body = self._create_card(self.frame_toolbox, "🔍 比赛查询", fill='x', pady=(0, 8))

        query_row = Frame(body, bg=self.COLORS['card_bg'])
        query_row.pack(fill='x')
        Label(query_row, text="比赛ID:", bg=self.COLORS['card_bg'], font=self.FONT_BODY).pack(side=LEFT, padx=(0, 6))
        self.match_id_entry = Entry(query_row, width=14,
                                     bg=self.COLORS['input_bg'], relief='solid', borderwidth=1,
                                     font=self.FONT_BODY)
        self.match_id_entry.pack(side=LEFT, padx=(0, 8))
        self._styled_button(query_row, "查询", self.query_match).pack(side=LEFT)

        self.match_result_text = StringVar()
        self.match_result_message = Message(body, textvariable=self.match_result_text,
                                             width=320, justify=LEFT,
                                             bg=self.COLORS['card_bg'], fg=self.COLORS['text_secondary'],
                                             font=self.FONT_SMALL)
        self.match_result_message.pack(fill='x', pady=(8, 4))
        self._styled_button(body, "导入到基本界面", self.import_match).pack(pady=(4, 0))
        Label(body, text="注意：因种子值查询失败，仅导入结构和变种，可能导致条件过于严格",
              fg=self.COLORS['warning'], bg=self.COLORS['card_bg'],
              font=self.FONT_SMALL, wraplength=300, justify='left').pack(pady=(8, 0))

    # ---------- Elo ----------
    def on_elo_toggle(self):
        self.update_elo_state()
        self.save_config()
        self.trigger_prefetch()

    def update_elo_state(self):
        enabled = self.use_elo.get()
        if enabled:
            self.elo_check_btn.config(text="✓ 启用 Elo 权重", fg=self.COLORS['primary'])
        else:
            self.elo_check_btn.config(text="启用 Elo 权重", fg=self.COLORS['text_secondary'])

        if enabled:
            for i in range(1, 6):
                self.type_vars[i].set(0)
            self._update_type_btn_appearance()
            if not self.elo_radio_frame.winfo_ismapped():
                self.elo_radio_frame.pack(fill='x', pady=(8, 0))
            self.on_elo_option_change()
        else:
            self.elo_radio_frame.pack_forget()
            self.custom_frame.pack_forget()

        for i in range(1, 6):
            btn = self.type_btns[i]
            if enabled:
                btn.config(cursor='arrow')
                btn.unbind('<Button-1>')
                for child in btn._children_widgets:
                    child.config(cursor='arrow')
                    child.unbind('<Button-1>')
            else:
                btn.config(cursor='hand2')
                tid = i
                var = self.type_vars[i]
                cmd = lambda t=tid, v=var: self._toggle_type_btn(t, v)
                btn.bind('<Button-1>', lambda e, c=cmd: c())
                for child in btn._children_widgets:
                    child.config(cursor='hand2')
                    child.bind('<Button-1>', lambda e, c=cmd: c())

    def on_elo_option_change(self):
        if not self.use_elo.get():
            return
        option = self.elo_option.get()
        if option == "1200+":
            weights = {1: 20, 2: 20, 3: 20, 4: 20, 5: 20}
            self.custom_frame.pack_forget()
        elif option == "600-1200":
            weights = {1: 0, 2: 20, 3: 25, 4: 30, 5: 25}
            self.custom_frame.pack_forget()
        elif option == "0-599":
            weights = {1: 0, 2: 0, 3: 30, 4: 55, 5: 15}
            self.custom_frame.pack_forget()
        else:
            if not self.custom_frame.winfo_ismapped():
                self.custom_frame.pack(fill='x', pady=(8, 0))
            self.update_weight_total()
            return
        for tid, val in weights.items():
            self.custom_weights[tid].set(val)
        self.update_weight_total()
        self.save_config()
        self.trigger_prefetch()

    def on_weight_slider_change(self, value):
        self.update_weight_total()
        if self.weight_debounce_id:
            self.root.after_cancel(self.weight_debounce_id)
        self.weight_debounce_id = self.root.after(500, self._delayed_weight_action)

    def _delayed_weight_action(self):
        self.save_config()
        self.trigger_prefetch()
        self.weight_debounce_id = None

    def balance_weights(self):
        total = sum(self.custom_weights[tid].get() for tid in range(1, 6))
        if total == 0:
            for tid in range(1, 6):
                self.custom_weights[tid].set(20)
        else:
            factor = 100 / total
            for tid in range(1, 6):
                self.custom_weights[tid].set(round(self.custom_weights[tid].get() * factor))
        self.update_weight_total()
        self.save_config()
        self.trigger_prefetch()

    def update_weight_total(self):
        total = sum(self.custom_weights[tid].get() for tid in range(1, 6))
        self.weight_total.set(total)

    # ---------- 事件处理 ----------
    def on_overworld_change(self):
        self.update_selected_overworld()
        self.save_config()
        self.prefetched_seed = None
        self.last_available_counts = 0
        self.trigger_prefetch()

    def update_selected_overworld(self):
        self.selected_overworld.clear()
        for tid, var in self.type_vars.items():
            if var.get() == 1:
                self.selected_overworld.add(tid)
        if self.random_var.get() == 1:
            self.selected_overworld.clear()
            for var in self.type_vars.values():
                var.set(0)
            self.random_var.set(1)
        self._update_type_btn_appearance()

    def on_nether_change(self):
        self.update_selected_nether()
        self.save_config()
        self.prefetched_seed = None
        self.last_available_counts = 0
        self.trigger_prefetch()

    def update_selected_nether(self):
        self.selected_nether.clear()
        for key, var in self.nether_vars.items():
            if var.get() == 1:
                self.selected_nether.add(key)
        self._update_nether_btn_appearance()

    def on_variation_change(self):
        self.update_selected_variations()
        self.save_config()
        self.prefetched_seed = None
        self.last_available_counts = 0
        self.trigger_prefetch()

    def update_selected_variations(self):
        self.selected_variations.clear()
        self.excluded_variations.clear()
        for var_str, var in self.var_include.items():
            if var.get() == 1:
                self.selected_variations.add(var_str)
        for var_str, var in self.var_exclude.items():
            if var.get() == 1:
                self.excluded_variations.add(var_str)
        extra = self.variation_text.get().strip()
        if extra:
            for v in extra.split(','):
                v = v.strip()
                if v:
                    self.selected_variations.add(v)

    # ---------- 高级/百宝箱切换 ----------
    def toggle_advanced(self):
        if self.frame_advanced.winfo_ismapped():
            self.frame_advanced.pack_forget()
            self.btn_advanced.config(text="高级设置  ▾")
        else:
            self.frame_advanced.pack(fill='x', pady=(0, 10))
            self.btn_advanced.config(text="高级设置  ▴")
            if self.frame_toolbox.winfo_ismapped():
                self.frame_toolbox.pack_forget()
                self.btn_toolbox.config(text="百宝箱  ▾")

    def toggle_toolbox(self):
        if self.frame_toolbox.winfo_ismapped():
            self.frame_toolbox.pack_forget()
            self.btn_toolbox.config(text="百宝箱  ▾")
        else:
            self.frame_toolbox.pack(fill='x', pady=(0, 10))
            self.btn_toolbox.config(text="百宝箱  ▴")
            if self.frame_advanced.winfo_ismapped():
                self.frame_advanced.pack_forget()
                self.btn_advanced.config(text="高级设置  ▾")

    # ---------- 预加载 ----------
    def _prefetch_status(self, text, color):
        self.prefetch_dot.config(fg=color)
        self.prefetch_label.config(text=text, fg=color)

    def trigger_prefetch(self):
        with self.prefetch_lock:
            if self.last_available_counts > 1000 and self.prefetched_seed is not None:
                self.log_queue.put("预加载跳过：可用种子充足（>1000），按热键时实时获取即可")
                self.root.after(0, lambda: self._prefetch_status("预加载：跳过（种子充足）", self.COLORS['primary']))
                return
            if self.prefetch_thread and self.prefetch_thread.is_alive():
                self.log_queue.put("预加载正在进行，稍后重新尝试...")
                self.root.after(3000, self.trigger_prefetch)
                return
            self.prefetch_fail_count = 0
            self.prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
            self.prefetch_thread.start()

    def _prefetch_worker(self):
        self.root.after(0, lambda: self._prefetch_status("预加载：正在获取...", self.COLORS['warning']))
        api_base = self.api_base.get().rstrip('/')

        # 趣味模式：随机废门/宝藏，预设变种
        if self.fun_mode.get():
            # 严格交替：宝藏→废门→宝藏→废门...
            self._fun_toggle = not self._fun_toggle
            selected_overworld_list = [2 if self._fun_toggle else 1]  # toggle: False=宝藏(1), True=废门(2)
            selected_nether_list = []
            # 清除原有变种，设置趣味模式变种
            self.selected_variations.clear()
            self.excluded_variations.clear()
            if selected_overworld_list[0] == 2:  # 废门
                self.selected_variations.update([
                    "type:structure:completable",
                    "chest:structure:looting_sword",
                    "chest:structure:golden_carrot"
                ])
            completion_ms = None
            tid, tname, ow, nether, avail = fetch_seed(api_base, selected_overworld_list, selected_nether_list,
                                                       self.selected_variations, completion_ms,
                                                       self.excluded_variations)
            with self.prefetch_lock:
                self.prefetched_seed = (tid, tname, ow, nether)
            self.last_available_counts = avail
            self.root.after(0, self.update_display_with_seed, tname, ow, nether)
            self.root.after(0, lambda: self.available_label.config(text=f"可用种子：{avail}"))
            self.root.after(0, lambda: self._prefetch_status(f"预加载：就绪 ({tname})", self.COLORS['success']))
            self.log_queue.put(f"趣味预加载成功：{tname} - {ow} (可用:{avail})")
            self.prefetch_fail_count = 0
            return

        if self.use_elo.get():
            option = self.elo_option.get()
            if option == "自定义":
                possible_types = [tid for tid in range(1, 6) if self.custom_weights[tid].get() > 0]
                if possible_types:
                    weights = [self.custom_weights[tid].get() for tid in possible_types]
                    overworld_choice = random.choices(possible_types, weights=weights)[0]
                    selected_overworld_list = [overworld_choice]
                else:
                    selected_overworld_list = list(range(1, 6))
            else:
                possible_types = [tid for tid in range(1, 6) if self.custom_weights[tid].get() > 0]
                if possible_types:
                    weights = [self.custom_weights[tid].get() for tid in possible_types]
                    overworld_choice = random.choices(possible_types, weights=weights)[0]
                    selected_overworld_list = [overworld_choice]
                else:
                    selected_overworld_list = list(range(1, 6))
        else:
            selected_overworld_list = list(self.selected_overworld)

        selected_nether_list = list(self.selected_nether)
        self.update_selected_variations()
        completion_ms = None
        if self.completion_min.get() or self.completion_sec.get():
            try:
                minutes = int(self.completion_min.get() or 0)
                seconds = int(self.completion_sec.get() or 0)
                completion_ms = (minutes * 60 + seconds) * 1000
            except:
                completion_ms = None

        try:
            tid, tname, ow, nether, avail = fetch_seed(api_base, selected_overworld_list, selected_nether_list,
                                                       self.selected_variations, completion_ms,
                                                       self.excluded_variations)
            with self.prefetch_lock:
                self.prefetched_seed = (tid, tname, ow, nether)
            self.last_available_counts = avail
            self.root.after(0, self.update_display_with_seed, tname, ow, nether)
            self.root.after(0, lambda: self.available_label.config(text=f"可用种子：{avail}"))
            self.root.after(0, lambda: self._prefetch_status(f"预加载：就绪 ({tname})", self.COLORS['success']))
            self.log_queue.put(f"预加载成功：{tname} - {ow} (可用:{avail})")
            self.prefetch_fail_count = 0
        except Exception as e:
            self.prefetch_fail_count += 1
            self.root.after(0, lambda: self._prefetch_status("预加载：失败", self.COLORS['danger']))
            self.log_queue.put(f"预加载失败（{self.prefetch_fail_count}/5）：{str(e)}")
            self.log_queue.put(traceback.format_exc())
            if self.last_available_counts > 1000:
                self.log_queue.put("预加载放弃重试：当前条件可用种子充足（>1000），按热键时实时获取")
                self.root.after(0, lambda: self._prefetch_status("预加载：跳过（种子充足）", self.COLORS['primary']))
                return
            if self.prefetch_fail_count >= 5:
                self.log_queue.put("预加载连续失败5次，请检查筛选条件或网络连接后手动重新选择条件")
                self.root.after(0, lambda: self._prefetch_status("预加载：多次失败，已停止", self.COLORS['danger']))
            else:
                delay_sec = (2 ** self.prefetch_fail_count) * 1000
                self.log_queue.put(f"将在 {delay_sec // 1000} 秒后自动重试...")
                self.root.after(delay_sec, self.trigger_prefetch)

    def update_display_with_seed(self, type_name, owseed, netherseed):
        self.info_type_label.config(text=f"类型：{type_name}")
        self.info_ow_label.config(text=f"主世界种子：{owseed}")
        self.info_nether_label.config(text=f"下界种子：{netherseed}")

    # ---------- 百宝箱查询 ----------
    def query_match(self):
        match_id = self.match_id_entry.get().strip()
        if not match_id.isdigit():
            self.log_queue.put(f"查询失败：比赛ID必须为数字（输入：{match_id}）")
            self.match_result_text.set("")
            return
        api_base = self.api_base.get().rstrip('/')
        url = f"{api_base}/api/v2/seed/{match_id}"
        self.log_queue.put(f"正在请求种子值：{url}")

        owseed = None
        netherseed = None
        seed_success = False
        try:
            resp = api_get(url, timeout=15, max_retries=2)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    seeds = data['data']['seeds']
                    owseed = seeds['overworldSeed']
                    netherseed = seeds['netherSeed']
                    seed_success = True
        except Exception as e:
            self.log_queue.put(f"请求种子值异常：{str(e)}")

        url_info = f"{api_base}/api/v2/seedinfo/{match_id}"
        overworld_type = "未知"
        nether_type = "未知"
        variations = []
        info_success = False
        try:
            resp_info = api_get(url_info, timeout=15, max_retries=2)
            if resp_info.status_code == 200:
                data_info = resp_info.json()
                if data_info.get('success'):
                    overworld_type = data_info['data'].get('overworld', '未知')
                    nether_type = data_info['data'].get('nether', '未知')
                    raw_variations = data_info['data'].get('variations', [])
                    if isinstance(raw_variations, str):
                        try:
                            variations = json.loads(raw_variations)
                        except:
                            variations = [raw_variations]
                    elif isinstance(raw_variations, list):
                        variations = raw_variations
                    info_success = True
        except Exception as e:
            self.log_queue.put(f"请求详细信息异常：{str(e)}")

        self.match_result = {
            'overworld_type': overworld_type,
            'nether_type': nether_type,
            'variations': variations,
            'owseed': owseed,
            'netherseed': netherseed
        }

        seed_display = f"{owseed} / {netherseed}" if seed_success else "获取失败（服务器错误）"
        var_display = ', '.join(str(v) for v in variations) if variations else "无"
        self.match_result_text.set(
            f"主世界类型: {overworld_type}\n"
            f"下界类型: {nether_type}\n"
            f"变种: {var_display}\n"
            f"种子: {seed_display}"
        )
        if info_success:
            self.log_queue.put(f"查询比赛ID {match_id} 成功（类型信息）")
        else:
            self.log_queue.put(f"查询比赛ID {match_id} 失败：无法获取任何信息")

    def import_match(self):
        if not hasattr(self, 'match_result'):
            messagebox.showinfo("提示", "请先查询一个比赛ID")
            return
        ow_type = self.match_result['overworld_type'].lower()
        type_map = {
            'buried_treasure': 1, 'ruined_portal': 2,
            'desert_temple': 3, 'village': 4, 'shipwreck': 5
        }
        if ow_type in type_map:
            tid = type_map[ow_type]
            self.select_none_overworld()
            self.type_vars[tid].set(1)
        nether_type = self.match_result['nether_type'].lower()
        if nether_type in self.nether_vars:
            self.nether_vars[nether_type].set(1)
        variations = self.match_result.get('variations', [])
        if variations:
            if isinstance(variations, list):
                var_str = ','.join(str(v) for v in variations)
            else:
                var_str = str(variations)
            self.variation_text.set(var_str)
        self.on_overworld_change()
        self.on_nether_change()
        self.on_variation_change()
        messagebox.showinfo("导入成功", "已导入主世界/下界类型，变种已填入文本框")

    # ---------- 热键 ----------
    def capture_hotkey(self, hotkey_type):
        self.hotkey_capturing = hotkey_type
        btn = self.btn_start_hotkey if hotkey_type == 'start' else self.btn_exit_hotkey
        btn.config(text="按下任意键...", relief=SUNKEN)
        from pynput import keyboard
        self.capture_listener = keyboard.Listener(on_press=self.on_capture_press)
        self.capture_listener.start()

    def on_capture_press(self, key):
        if self.capture_listener:
            self.capture_listener.stop()
        self.root.after(0, self.set_hotkey, key)
        return False

    def set_hotkey(self, key):
        if self.hotkey_capturing == 'start':
            self.start_hotkey = key
            btn_text = self.key_to_str(key)
            self.btn_start_hotkey.config(text=btn_text, relief=RAISED)
            self.start_hotkey_text.set(btn_text)
        elif self.hotkey_capturing == 'exit':
            self.exit_hotkey = key
            btn_text = self.key_to_str(key)
            self.btn_exit_hotkey.config(text=btn_text, relief=RAISED)
            self.exit_hotkey_text.set(btn_text)
        self.hotkey_capturing = None
        self.save_config()
        self.restart_listener()

    def key_to_str(self, key):
        if hasattr(key, 'char') and key.char is not None:
            return key.char.upper()
        elif hasattr(key, 'name'):
            return key.name.upper()
        return str(key)

    def str_to_key(self, s):
        if len(s) == 1:
            from pynput.keyboard import KeyCode
            return KeyCode.from_char(s.lower())
        else:
            from pynput.keyboard import Key
            try:
                return getattr(Key, s.lower())
            except AttributeError:
                return Key.f5

    # ---------- 配置 ----------
    def save_config(self):
        config = {
            'api_base': self.api_base.get(),
            'selected_overworld': list(self.selected_overworld),
            'random_checked': self.random_var.get(),
            'selected_nether': list(self.selected_nether),
            'selected_variations': list(self.selected_variations),
            'excluded_variations': list(self.excluded_variations),
            'variation_text': self.variation_text.get(),
            'completion_min': self.completion_min.get(),
            'completion_sec': self.completion_sec.get(),
            'use_elo': self.use_elo.get(),
            'elo_option': self.elo_option.get(),
            'custom_weights': {str(k): v.get() for k, v in self.custom_weights.items()},
            'start_hotkey': self.start_hotkey_text.get(),
            'exit_hotkey': self.exit_hotkey_text.get()
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log_queue.put(f"保存配置失败：{e}")

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'api_base' in config:
                self.api_base.set(config['api_base'])
            selected = config.get('selected_overworld', [])
            for tid in selected:
                if tid in self.type_vars:
                    self.type_vars[tid].set(1)
            # 随机按钮状态必须显式恢复，否则残留默认勾选会在下面
            # update_selected_overworld() 里把刚恢复的主世界类型清空
            self.random_var.set(1 if config.get('random_checked', 0) else 0)
            self.update_selected_overworld()
            nether = config.get('selected_nether', [])
            for key in nether:
                if key in self.nether_vars:
                    self.nether_vars[key].set(1)
            self.update_selected_nether()
            vars_list = config.get('selected_variations', [])
            for v in vars_list:
                if v in self.var_include:
                    self.var_include[v].set(1)
                    self._update_var_btn_appearance(v)
            excluded_list = config.get('excluded_variations', [])
            for v in excluded_list:
                if v in self.var_exclude:
                    self.var_exclude[v].set(1)
                    self._update_var_btn_appearance(v)
            self.variation_text.set(config.get('variation_text', ''))
            self.update_selected_variations()
            self.completion_min.set(config.get('completion_min', ''))
            self.completion_sec.set(config.get('completion_sec', ''))
            self.use_elo.set(config.get('use_elo', False))
            self.elo_option.set(config.get('elo_option', '1200+'))
            weights = config.get('custom_weights', {})
            for k, v in weights.items():
                if int(k) in self.custom_weights:
                    self.custom_weights[int(k)].set(v)
            self.update_elo_state()
            self.update_weight_total()
            if 'start_hotkey' in config:
                self.start_hotkey = self.str_to_key(config['start_hotkey'])
                self.btn_start_hotkey.config(text=config['start_hotkey'])
                self.start_hotkey_text.set(config['start_hotkey'])
            if 'exit_hotkey' in config:
                self.exit_hotkey = self.str_to_key(config['exit_hotkey'])
                self.btn_exit_hotkey.config(text=config['exit_hotkey'])
                self.exit_hotkey_text.set(config['exit_hotkey'])
        except Exception as e:
            self.log_queue.put(f"加载配置失败：{e}")

    # ---------- 热键监听 ----------
    def start_listener(self):
        def on_press(key):
            if key == self.start_hotkey:
                threading.Thread(target=self.run_task, daemon=True).start()
            elif key == self.exit_hotkey:
                self.root.after(0, self.on_closing)
        from pynput import keyboard
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

    def restart_listener(self):
        if self.listener:
            self.listener.stop()
        self.start_listener()

    # ---------- 任务执行 ----------
    def run_task(self):
        api_base = self.api_base.get().rstrip('/')
        with self.prefetch_lock:
            if self.prefetched_seed is not None:
                seed_info = self.prefetched_seed
                self.prefetched_seed = None
                self.log_queue.put("使用预加载种子开始任务...")
                task(api_base, seed_info, self.log_queue, self.update_stats)
                self.root.after(0, self.trigger_prefetch)
            else:
                self.log_queue.put("没有预加载种子，将实时获取...")
                try:
                    # 趣味模式：随机废门/宝藏 + 预设变种
                    if self.fun_mode.get():
                        self.selected_variations.clear()
                        self.excluded_variations.clear()
                        # 严格交替：宝藏→废门→宝藏→废门...
                        self._fun_toggle = not self._fun_toggle
                        selected_overworld = [2 if self._fun_toggle else 1]  # toggle: False=宝藏(1), True=废门(2)
                        selected_nether = []
                        if selected_overworld[0] == 2:  # 废门
                            self.selected_variations.update([
                                "type:structure:completable",
                                "chest:structure:looting_sword",
                                "chest:structure:golden_carrot"
                            ])
                        completion_ms = None
                    elif self.use_elo.get():
                        option = self.elo_option.get()
                        possible_types = [tid for tid in range(1, 6) if self.custom_weights[tid].get() > 0]
                        if possible_types:
                            weights = [self.custom_weights[tid].get() for tid in possible_types]
                            overworld_choice = random.choices(possible_types, weights=weights)[0]
                            selected_overworld = [overworld_choice]
                        else:
                            selected_overworld = list(range(1, 6))
                    else:
                        selected_overworld = list(self.selected_overworld)
                    if not self.fun_mode.get():
                        selected_nether = list(self.selected_nether)
                        self.update_selected_variations()
                        completion_ms = None
                        if self.completion_min.get() or self.completion_sec.get():
                            try:
                                minutes = int(self.completion_min.get() or 0)
                                seconds = int(self.completion_sec.get() or 0)
                                completion_ms = (minutes * 60 + seconds) * 1000
                            except:
                                pass
                    else:
                        selected_nether = []
                    tid, tname, ow, nether, avail = fetch_seed(api_base, selected_overworld, selected_nether,
                                                               self.selected_variations, completion_ms,
                                                               self.excluded_variations)
                    seed_info = (tid, tname, ow, nether)
                    task(api_base, seed_info, self.log_queue, self.update_stats)
                except Exception as e:
                    self.log_queue.put(f"实时获取种子失败：{e}")
                    self.log_queue.put(traceback.format_exc())
                finally:
                    self.root.after(0, self.trigger_prefetch)

    def update_stats(self, type_name, owseed, netherseed):
        self.stats_count += 1
        self.info_type_label.config(text=f"类型：{type_name}")
        self.info_ow_label.config(text=f"主世界种子：{owseed}")
        self.info_nether_label.config(text=f"下界种子：{netherseed}")
        self.count_label.config(text=f"已筛选：{self.stats_count} 次")

    # ---------- 日志 ----------
    def clear_log(self):
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, END)
        self.log_area.config(state='disabled')

    def export_log(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                   filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                content = self.log_area.get(1.0, END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("导出成功", f"日志已保存到：{file_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"保存文件时出错：{e}")

    def _bind_mousewheel_recursive(self, widget, handler):
        widget.bind("<MouseWheel>", handler)
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child, handler)

    def _on_log_mousewheel(self, event):
        self.log_area.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_left_mousewheel(self, event):
        self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_area.config(state='normal')
                self.log_area.insert(END, msg + "\n")
                self.log_area.see(END)
                self.log_area.config(state='disabled')
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    def on_closing(self):
        if self.listener:
            self.listener.stop()
        self.save_config()
        self.root.destroy()
