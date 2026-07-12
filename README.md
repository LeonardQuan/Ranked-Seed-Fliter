# 🎯 一键导入 Ranked 种子 Pro Max

一个帮你**模拟 Ranked 比赛种子、一键自动填写**的桌面工具。专为 Minecraft 速通 Ranked 模式设计，通过 API 获取符合条件的种子并自动填入游戏。

## ✨ 功能特性

- 🔍 **多结构类型支持** — 宝藏、废门、沙漠神殿、村庄、沉船，支持随机
- 🌋 **下界结构筛选** — 下界堡垒（桥/藏宝室/居住区/棚）+ 堡垒遗迹变种
- 🎛️ **精细变种控制** — 支持选择/排除特定变种（钻石箱、附魔金苹果、倒置沉船等）
- ⏱️ **完成时间过滤** — 按完成时间（completion time）筛选种子
- ⚖️ **ELO 加权模式** — 根据 ELO 分段智能调整结构权重
- 🎹 **快捷键自动填写** — `F5` 一键填入种子，`F6` 退出，无需切出游戏
- 🚀 **预加载机制** — 后台预取种子，点击即用
- 🧵 **多线程** — 网络请求、预取、任务执行均异步，界面不卡顿
- 🎨 **现代 UI** — 清爽配色，支持高 DPI

## 🖥️ 界面预览

| 主世界结构 | 下界结构 | 变种筛选 |
|:---:|:---:|:---:|
| 村庄、沙漠神殿、沉船、废门、宝藏、随机 | 下界堡垒类型 + 堡垒遗迹变种 | 钻石箱、附魔金苹果、倒置沉船等 |

## 📦 安装与运行

### 环境要求

- Windows 10 / 11
- Python 3.8+
- Minecraft Java Edition（用于自动填写）

### 安装依赖

```bash
pip install requests pynput
```

> 注意：`tkinter` 为 Python 标准库，无需额外安装。

### 运行

```bash
python Ranked.py
```

### 打包为 EXE

使用 PyInstaller 打包为独立可执行文件：

```bash
pip install pyinstaller
pyinstaller Ranked.spec
```

打包后的 `dist/Ranked.exe` 可直接运行，无需 Python 环境。

## 🎮 使用方法

1. 启动程序，选择想要的**主世界结构**（可多选）
2. 可选：选择**下界结构**和**变种**筛选条件
3. 可选：设置**完成时间**过滤、开启 **ELO 加权**
4. 点击「获取种子」或等待后台预加载
5. 进入 Minecraft 游戏主界面
6. 按 **F5** 自动填写种子
7. 按 **F6** 退出自动填写模式

## 🏗️ 项目结构

```
Ranked-Seed-Fliter/
├── Ranked.py          # 程序入口（单实例检测 + DPI 感知）
├── gui_app.py         # GUI 主界面（Tkinter）
├── api_client.py      # HTTP 请求 + 种子获取逻辑
├── constants.py       # 结构类型、变种数据常量
├── task_runner.py     # 自动填写任务（pynput 键盘模拟）
├── Ranked.spec        # PyInstaller 打包配置
├── assets/            # 图标与预览图片
└── README.md
```

## 🔧 配置

程序运行后会在同目录生成 `config.json`，保存你的 API 地址、热键设置等偏好。

## 📄 许可证

MIT License

---

**Made with ❤️ for Minecraft Speedrunning Community**
