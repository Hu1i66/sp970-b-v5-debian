# SP970-B-V5 上的 Debian 11

在一块骁龙 410 随身 Wi-Fi 上，用该板的原厂 Linux 3.10.28 内核启动 Debian 11 armhf。系统从板载 eMMC 开机，Windows 可经普通 USB 网卡和 SSH 管理。插入中国移动 SIM 后，设备只接充电头也能自动拨号并开热点。

- [刷机方法、分区布局和恢复记录](FLASHING.md)
- [博客稿](BLOG.md)
- [只读 GPT 校验工具](inspect_gpt.py)

## 实测型号

| 项目 | 值 |
| --- | --- |
| 主板丝印 | `SP970-B-V5` |
| 原厂管理页硬件版本 | `SP970-HW-V5` |
| 原厂固件版本 | `M8916_MD.B19.APE01/BP005` |
| 平台 | Qualcomm MSM8916 |
| 最终系统 | Debian 11 Bullseye，`armhf`（32 位 ARM） |
| 最终内核 | 此单板的原厂 Linux 3.10.28 |

## 实测功能

| 功能 | 验收方式 |
| --- | --- |
| 从闪存冷启动 | 普通插电后确认 eMMC 上的 ext4 根文件系统已挂载，Debian 的启动脚本成为 1 号进程 |
| USB SSH | Windows 用密钥登录并执行命令，原有 RNDIS 驱动可用 |
| Debian 借电脑上网 | SSH 代理承载 APT 流量，实际运行 `apt update`，Windows 默认路由保持原样 |
| 独立 4G 热点 | 中国移动 SIM，APN 为 `CMNET`。只接充电头冷启动，手机关闭移动数据后连棒子的热点并成功打开网页 |

RNDIS 把 USB 连接呈现为一块网卡。armhf 表示 Debian 的 32 位 ARM 软件包架构。当前公开稿提供实验记录、安装逻辑、分区范围和备份校验工具。最终启动镜像仍含原厂组件，可公开重建的打包入口需要另行补齐。照着文档核对分区前，可先用下面的命令分析自己设备的原厂备份。

```text
python inspect_gpt.py stock-emmc-userarea.bin
```

## 参考项目

- [OpenStick v1](https://github.com/OpenStick/OpenStick/releases/tag/v1)
- [lk2nd](https://github.com/msm8916-mainline/lk2nd)
- [Qualcomm QDL](https://github.com/qualcomm/qdl)
- [Debian 11 armhf 安装手册](https://www.debian.org/releases/bullseye/armhf/)
- [苏苏小亮亮教程存档](https://blog.littlejake.net/archives/918/)

## 许可证

本仓库的原创文档和 Python 工具使用 [MIT](LICENSE)。外部项目沿用各自的许可证。
