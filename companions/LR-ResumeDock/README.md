# LR ResumeDock

**被打断后，不用重找思路。离开前留一句，回来就从下一步开始。**

[English](README.en.md) · [StudyPet](https://github.com/LLR6/LR-StudyPet)

![真实界面，演示数据](preview.png)

给学习、论文写作和编码用的离线续接工具。它关心的是“下一步具体做什么”。

- 多项目书签：已做到哪、回来第一步、资料入口。
- 已保存书签编辑后自动保存；新建后先点保存。
- 置顶小浮窗，5 分钟计时支持暂停；项目切换不会改变正在计时的归属。
- 本地文件或 HTTPS 资料入口，手动点击打开。
- 归档与恢复，Markdown 导出。
- SQLite 本机持久保存；无账号、AI 服务或使用埋点。

## 启动

Windows 源码：安装 Python 3.12/3.13，完整下载此目录，双击 `Start.cmd`，第一次自动安装依赖。
跨平台：`python -m pip install -r requirements.txt`，再运行 `python app.py`。
Windows 便携构建产物在 StudyPet 的 [Actions](https://github.com/LLR6/LR-StudyPet/actions)，名称 `LR-ResumeDock-Windows`。下载并完整解压后运行 `Start.cmd`，无需另装 Python。

Windows 下载也会发布在 [星梨下载页](https://github.com/LLR6/LR-StudyPet/releases)。独立仓库尚未创建，当前目录可单独下载、运行和打包。

## 30 秒案例

任务写“修复登录测试”；已做到哪写“已排除路由问题”；回来第一步写“检查测试夹具里的用户角色”。保存，打开续接浮窗，开始 5 分钟。不需要监控编辑器或键盘。

数据在 `%LOCALAPPDATA%\LR-ResumeDock\resume.sqlite3`；非 Windows 为 `~/.local/share/LR-ResumeDock`。导出包含你的书签内容。定时数据在结束时保存，程序崩溃会丢失该段尚未保存的计时；书签独立自动保存。没有屏幕识别、自动判断学习成果或云同步。

## 开发

`python -m unittest -v`；`python app.py --smoke-test` 在临时目录验证界面并生成示例预览。
`python -m PyInstaller --windowed --name LR-ResumeDock app.py` 打包。

源码 MIT · LR。Qt/Python 依赖许可见 THIRD_PARTY.md。
