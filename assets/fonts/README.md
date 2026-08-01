# 字体

本仓库暂不捆绑第三方字体，避免在未确认许可证文件的情况下传播字体二进制。

`compose_poster.py` 按以下顺序寻找字体：品牌配置中的路径、此目录下的 `.ttf/.otf`、Windows 微软雅黑、Linux Noto Sans CJK、macOS PingFang。若要分发完全自包含的版本，可在此放入获得再分发许可的中文字体及其许可证，并在 `data/brand_profile.yaml` 中配置路径。
