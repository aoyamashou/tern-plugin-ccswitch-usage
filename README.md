# Tern CC Switch 额度插件

在 Tern 状态栏显示 CC Switch **当前供应商**已启用的用量查询结果。点击片段或运行“打开 CC Switch 额度”可查看全部套餐并手动刷新。插件每五分钟自动查询一次；查询失败时保留上一次成功的列表。

插件只读 `~/.cc-switch/cc-switch.db`，按 CC Switch 保存的用量脚本查询额度，不会修改数据库。需本机安装 Python 3 和 Node.js。若 CC Switch 使用了自定义配置目录，可在 Tern 环境中设置 `CC_SWITCH_CONFIG_DIR`。

目前支持 CC Switch 的通用、New API 和自定义 JavaScript 用量脚本。`official_subscription`、`token_plan`、`balance`、`github_copilot` 由 CC Switch 应用内的专用查询实现；CC Switch 没有供外部读取这些结果的接口，详情面板会显示“需要 CC Switch 应用内查询”。只显示各应用当前供应商，不查询所有历史供应商。

```sh
tern plugin link /path/to/this/directory
tern plugin list
```

已启用的脚本会在本机执行并向其配置的额度接口发送请求，和在 CC Switch 内启用脚本一样，需要信任这些脚本及其来源。插件不会打印或保存 API Key。
