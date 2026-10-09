# LR DeskTidy

**桌面文件太乱？先看每个文件去哪，再整理，还能撤销。**

[English](README.en.md) · [StudyPet](https://github.com/LLR6/LR-StudyPet)

![真实预览界面，演示数据](preview.png)

本地文件整理工具，面向桌面和下载资料目录。把“建议你整理”变成可预览的实际操作。

- 只扫描当前目录的一层文档、图片、压缩包和媒体；不移动文件夹、程序或快捷方式。
- 展示每个文件的目标路径，可取消勾选。
- 按内容哈希提示重复文件，所有副本均保留。
- 目标重名自动加编号，执行时再次验证；原文件变化则停止。
- 移动历史写入当前目录 `.lr-desktidy`，支持撤销最近一次。
- 原位置被占用或整理后的文件已修改，撤销跳过并解释；不覆盖新文件。
- 哈希和文件移动在后台线程执行；不联网，无账号。

## 启动

Windows 源码：安装 Python 3.12/3.13，双击 `Start.cmd`。
跨平台：`python -m pip install -r requirements.txt`，再 `python app.py`。
无需 Python 的 Windows 便携构建产物见 StudyPet 的 [Actions](https://github.com/LLR6/LR-StudyPet/actions)，名称 `LR-DeskTidy-Windows`。
独立仓库尚未创建，当前目录可单独运行和打包。

## 使用

选择目录 → 生成预览 → 取消不想移动的项目 → 确认整理。
需要还原时点“撤销最近一次”。未成功撤销的项目继续留在历史中，可排除冲突后再试。

单文件上限 128 MB，每次最多 500 个；大文件和不支持的文件类型不参与整理。内容重复提示只比较当前预览里的文件，不代表全磁盘查重。
不要同时用其他工具重命名或编辑正在整理的文件。Linux/macOS 的移动使用同文件系统硬链接与解除原链接，文件系统不支持硬链接时会失败并保留历史。Windows 使用不覆盖目标的重命名。
空分类目录不会自动删除；历史请保留，移动整份目录后原历史路径不再有效。工具用于日常人工整理，不是备份系统。部分失败时可用已写入的历史撤销成功移动的文件。

## 开发

`python -m unittest -v` 验证改动后停止、冲突保留、修改后跳过、部分失败恢复、路径约束和撤销。
`python app.py --smoke-test` 在临时目录执行完整预览/移动/撤销流程。
`python -m PyInstaller --windowed --name LR-DeskTidy app.py` 打包。

源码 MIT · LR。Qt/Python 依赖许可见 THIRD_PARTY.md。
