---
name: mobile-capture
description: 分析移动端设备（iOS/Android 手机、平板）的抓包数据。只要用户提出手机或平板 App 的抓包、抓包分析、接口分析、流量分析需求就使用本技能——例如"帮我抓包""抓一下手机请求""分析我刚抓的 App 请求""看看这个 App 调了哪些接口""这个 App 的 CDN 怎么选""拦截/改包/重放某个请求"，以及提到 Loon、Shadowrocket、Quantumult、Surge、mitmproxy、证书、代理抓包、手机连代理时。不用于电脑端程序的抓包。
---

# 移动端抓包分析

用户说"抓包""分析一下刚抓的请求"时，按下面流程走，不要问数据在哪、也不要让用户导出文件。

## 数据位置

`~/.mobilecapture/data/session/`

- `flows.jsonl`：请求记录，一行一条（t/m/host/path/st/cip/rq/rs）
- `bodies/`：超过长度上限的响应全文，flows 里显示为 `<full:文件名>`
- `meta.json`：本次会话开始时间

服务和记录同生共死：停止服务或点"清空"就删除，**分析要在停止之前完成**。

## 命令

```
cap status --json                    服务是否在跑、设备是否连上
cap digest                           摘要：域名 Top、状态码、接口样本
cap flows -n 80 --host bilibili      拉记录
cap show <序号>                      单条完整请求/响应（序号从 1 开始）
cap search <关键词>                   搜路径和 body
cap start / cap stop                 起停服务（停止会清空）
cap clear                            清空本次记录
cap qr                               代理节点链接和二维码地址
```

## 标准流程

1. `cap status --json`
   - 没在跑：`cap start`，把 `http://IP:8899/` 和二维码给用户，让他手机连上
   - `client.ip` 为空：设备还没连，先把连接问题解决
2. `cap digest` 看全貌，决定深挖哪个域名
3. `cap flows --host xxx` 看具体接口，必要时 `cap show`
4. 结论直接讲人话，不贴原始 JSON；需要原文时引用关键字段

## 连接方式（用户问起时）

- iOS：设置 → Wi-Fi → 代理 → 手动 → 填电脑 IP 和 8080；证书从 `http://IP:8899/ca` 装
- Android：Wi-Fi 高级选项 → 代理 → 手动；证书在"安装证书"里导入
- 代理软件（Loon/Shadowrocket）要用 HTTP 节点指向电脑，并关掉软件自身的 MITM

## 注意

- gRPC 接口只有路径没有字段（protobuf 二进制），要解析得另配 proto
- HTTPS 解密只在电脑做，手机端不要再开 MITM
- 视频分片默认不记录，日志里看不到 .m4s
