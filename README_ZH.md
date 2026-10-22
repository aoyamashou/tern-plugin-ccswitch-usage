# Tern CC Switch 额度插件

[English](README.md) | **简体中文**

在 Tern 状态栏显示 CC Switch 各应用**当前供应商**的用量查询结果。点击状态栏片段，或在命令面板运行 **打开 CC Switch 额度**，可打开原生详情面板，查看全部套餐并手动刷新。插件每五分钟查询一次；如果无法读取数据库，会保留上次加载的结果并显示错误。

## 环境要求

- 支持窗口插件的 Tern
- CC Switch 数据与 Tern 窗口位于同一台电脑
- Tern 的 `PATH` 中可以运行 Python 3 和 Node.js

插件以只读方式打开 `~/.cc-switch/cc-switch.db`，不会修改 CC Switch 数据。如果 CC Switch 使用自定义配置目录，可在 Tern 环境中设置 `CC_SWITCH_CONFIG_DIR` 指向该目录。

## 安装

```sh
tern plugin link /path/to/tern-plugin-ccswitch-usage
tern plugin list
```

需要先在 CC Switch 中为供应商启用用量查询。如果看不到状态栏片段，请先开启 Tern 状态栏。

## 支持的查询

插件运行当前供应商已保存的**通用**、**New API** 和**自定义 JavaScript** 用量脚本。状态栏最多显示三个供应商；详情面板显示所有已查询供应商。

`official_subscription`、`token_plan`、`balance` 和 `github_copilot` 由 CC Switch 应用内部查询。CC Switch 没有提供外部读取这些结果的本地接口，因此插件会对这些类型显示说明，而不是额度。插件不会查询非当前供应商。

已启用的脚本会在本机执行，并向配置的额度接口发送请求。请只启用可信来源的脚本。插件不会打印或保存 API Key。
