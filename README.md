# ios-capture

Mac 上跑的 iPhone 抓包服务：mitmproxy + 网页控制台 + 给 agent 的命令行。

## 安装

```
./install.sh
```

装完自动打开 `http://本机IP:8899/`，页面会带你做三步：装证书、连代理、等连接。

## 使用

手机和电脑连同一个 Wi-Fi，代理指向 `本机IP:8080`（HTTP 节点，关掉手机端 MITM）。

- 页面：实时看请求、暂停抓包、清空记录、停止服务
- `cap`：给 agent 和终端用，见 `cap` 无参数输出
- 开机自启：LaunchAgent `com.ioscapture.server`

## 数据

`~/.ioscapture/data/session/`，服务和记录同生共死：停止服务或点清空即删除。

## 卸载

```
./uninstall.sh
```
