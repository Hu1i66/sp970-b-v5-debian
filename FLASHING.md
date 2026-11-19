# SP970-B-V5 刷机方法与恢复记录

适用样机为主板丝印 `SP970-B-V5`、后台硬件版 `SP970-HW-V5`，固件 `M8916_MD.B19.APE01/BP005`。下面的扇区地址来自这块样机，操作前用自己的原厂备份核对。安装会重建原厂 `userdata`，其中的原厂用户数据会被覆盖。

## 1. 先备份原厂闪存

这台样机通过原厂系统中已有的本地管理终端，从 `/dev/block/mmcblk0` 读取 eMMC 用户区主镜像。文件为 **3,909,091,328 字节**，含 27 个 GPT 分区。GPT 是记录分区名字、起点和范围的表。首次备份在 Android 运行时完成，正在写入的用户数据可能随读取时间变化。原厂系统未暴露独立的 `mmcblk0boot0` 和 `mmcblk0boot1`。

用 `inspect_gpt.py` 核对镜像的主、备 GPT 以及分区表 CRC，再单独保留本机的 `modemst1`、`modemst2`、`fsc`、`fsg` 和 `persist`。这些分区可能含设备专属的基带或校准参数，恢复时使用自己设备的备份。

## 2. 确认 9008 恢复口能读回

Fastboot 是引导程序提供的 USB 接口。样机断电后，按住实体复位键插 USB，约两秒后松开，Windows 可见 `18D1:D00D`。以 Fastboot 临时加载 `lk2nd-msm8916-23.1.img` 后，可在 lk2nd 中使用 `fastboot oem reboot-edl` 进入 `05C6:9008`。

9008 是高通的紧急下载模式（EDL）。这台样机还验证了直接进入 9008，现场以 Windows 硬件 ID 和 QDL 读回作判断依据。主线程还测试过 USB 焊脚触发，但可用记录里缺少可独立核对的焊脚定义和板级图，本文只给出已确认的软件入口。按键方向、手机型号和其他板次的测试点照片无法替代同板实测。

Windows 使用 QDL 2.9.1 的 `qud` 后端和与样机匹配的 eMMC Firehose 加载器。Firehose 是进入 9008 后装入设备内存的存储读写程序。以下只读命令的前 34 扇区在实测中与原厂备份逐字节一致。

```powershell
qdl.exe --backend=qud list
qdl.exe --backend=qud --storage=emmc PATH-TO-MATCHING-FIREHOSE read 0/0+34 gpt-prefix.bin
```

这张板还实测过用 9008 恢复原厂 `cache` 和 `aboot`。刷写前保留原厂引导及 GPT，可以继续使用上面经过验证的 Fastboot 恢复链。若 Windows 突然显示多个盘符，先查 USB 硬件 ID。此样机出现该现象时进入了 `9006`，内部闪存被暴露为磁盘。关闭 Windows 的格式化提示。

## 3. 最终可用的安装布局

扇区大小为 512 字节，地址从零开始。

| 项目 | 样机范围或长度 | 用途 |
| --- | --- | --- |
| `boot`（GPT 第 22 项） | 起始 396384，共 32768 扇区 | 存放自定义启动镜像 |
| `userdata`（GPT 第 27 项） | 起始 2428000，共 5206911 扇区 | 存放 Debian ext4 根文件系统及安装暂存区 |
| 安装暂存区起点 | LBA 6622304，相对 `userdata` 起点 4244304 扇区 | 存放 Debian 11 armhf 安装归档 |
| 暂存镜像实际写入 | 49909 扇区，25,553,408 字节 | 在安装器运行前写入并读回 |
| 最终初装启动镜像实际写入 | 从 LBA 396384 开始的 21056 扇区，10,780,672 字节 | 样机实测成功的镜像大小 |

安装流程保留了原厂的早期引导和 GPT。先写暂存镜像，再写对应的启动镜像，逐段读回核对。上电后，启动镜像里的安装器验证目标分区和暂存归档，调用 `mke2fs` 在 `userdata` 开头建立 **2 GiB** ext4 文件系统。暂存区位于这段文件系统之外。安装器解包系统，再由 `switch_root` 把根目录切到 eMMC 上的 Debian。BusyBox 提供安装阶段用到的基本命令。

启动镜像复用了板上原厂 boot 镜像的 32 位内核和设备树数据。设备树记录内存、GPIO 等板级硬件信息。自定义的早期启动文件负责创建缺失的块设备节点、准备运行目录、调用 BusyBox applet、携带 `mke2fs` 的 ARM 动态加载器和依赖库，并启动 Debian 的自定义 PID 1。PID 1 是内核启动的第一个用户态进程。

重建时，启动镜像与安装归档须配套。文件的实际写入长度按各自制品计算，表内长度只对应本次测试制品。最终 SSH 镜像使用独立版本，实测写入长度为 22192 扇区，其中包含为这台电脑生成的认证配置。

## 4. 启动与联网验证

1. 正常插电脑，确认 Windows 出现 RNDIS 网卡。实测 Debian 的 USB 侧地址为 `192.168.42.129`，Windows 接口没有默认网关。这样 Windows 继续走原有网络。
2. 以自己的 SSH 密钥登录 Debian。样机使用 Dropbear SSH，并在真实会话里执行了命令。检查 `cat /etc/os-release`、`dpkg --print-architecture`、`findmnt /` 和 `ps -p 1`，分别确认系统、架构、闪存根目录和 PID 1。
3. Windows 通过 SSH 向棒子提供代理，再让 APT 使用该代理。实测 `apt update` 完成。这一步为 Debian 提供软件更新通道，手机热点流量使用 SIM。
4. 独立热点依赖原厂 Wi-Fi 驱动和基带固件。样机由 hostapd 创建 Wi-Fi 热点，dnsmasq 分配客户端地址，基带用 QMI 控制拨号。QMI 是系统与高通基带通信的接口。样机还要求将 `rmnet0` 与基带配置为一致的原始 IP 数据格式。
5. 断电后插入已开通数据业务的中国移动 SIM。将棒子插入普通 USB 充电头，等热点出现。手机关闭自身移动数据，连热点后打开一个网页。样机通过了这项测试。

## 5. 故障对照

| 现象 | 样机上的判断和处理 |
| --- | --- |
| Fastboot 返回 `OKAY`，随后没有 Debian USB 标识 | 只确认引导程序接收了镜像。继续用 USB 标识、状态页或 SSH 确认系统实际运行 |
| Windows 弹出一批盘符 | 样机进入了 9006 磁盘模式，关闭格式化提示。实测可从 9008 恢复原厂 `aboot` |
| OpenStick 镜像写入成功但冷启动无结果 | 初次试刷失败。最终保留原厂引导并使用原厂内核和 Debian 11 armhf 用户空间 |
| 能读到 SIM，手机连热点后仍无法打开网页 | 分别检测基带注册、拨号状态、`rmnet0` 数据格式、热点 DHCP 和流量转发 |

## 上游资料

- [Qualcomm QDL](https://github.com/qualcomm/qdl)
- [lk2nd](https://github.com/msm8916-mainline/lk2nd)
- [OpenStick v1](https://github.com/OpenStick/OpenStick/releases/tag/v1)
- [微软 RNDIS 驱动说明](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/remote-ndis--rndis-2)
- [Debian 11 Dropbear 手册](https://manpages.debian.org/bullseye/dropbear-bin/dropbear.8.en.html)
- [苏苏小亮亮教程存档](https://blog.littlejake.net/archives/918/)
