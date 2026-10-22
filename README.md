# dsh-mobile-capture

Mac 上跑的 iPhone 抓包服务：mitmproxy + 网页控制台 + 给 agent 的命令行。

## 依赖

- macOS
- Homebrew（没有就装：https://brew.sh）

mitmproxy 由安装脚本自动安装，Python 环境自动创建，不用手动准备。

## 安装

```
./install.sh
```

装完自动打开 `http://本机IP:8899/`，页面会带你做三步：装证书、连代理、等连接。

## 使用

手机和电脑连同一个 Wi-Fi，代理指向 `本机IP:8080`（HTTP 节点，关掉手机端 MITM）。

- 页面：实时看请求、暂停抓包、清空记录、停止服务
- `cap`：给 agent 和终端用，见 `cap` 无参数输出
- 开机自启：LaunchAgent `com.dsh-mobile-capture.server`

## 数据

`~/.dsh-mobile-capture/data/session/`，服务和记录同生共死：停止服务或点清空即删除。

## 卸载

```
./uninstall.sh
```
