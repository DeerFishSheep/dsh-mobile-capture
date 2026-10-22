---
name: ios-capture
description: 分析 iPhone 抓包数据。用户说"抓包""刚抓了某个 App 的请求""分析一下流量""看看这个接口"时使用。本地服务由 ios-capture 提供，数据在 ~/.ioscapture/data/session/，操作用 cap 命令。
---

# iOS 抓包分析

用户提到"刚抓包了 XXX，帮我分析"时，按下面顺序做，不要问数据在哪。

## 数据位置

`~/.ioscapture/data/session/`

- `flows.jsonl` 请求记录，一行一条（host/path/status/cip/rs/rq）
- `bodies/` 大响应全文，flows 里对应字段显示为 `<full:文件名>`
- `meta.json` 本次会话开始时间

## 命令

```
cap status --json      服务是否在跑、手机是否连上
cap digest             摘要：域名 Top、状态码、接口样本
cap flows -n 80 --host bilibili    拉记录
cap show <序号>        单条完整请求/响应（序号从 1 开始）
cap search <关键词>     搜路径和 body
cap start / cap stop   起停服务（停止会清空记录）
cap clear              清空本次记录
cap qr                 节点链接和二维码地址
```

## 标准流程

1. `cap status --json`
   - 服务没跑 → `cap start`，然后把地址和二维码给用户，让手机连上
   - `client.ip` 为空 → 用户还没连，先解决连接
2. `cap digest` 看全貌
3. 按用户关心的域名 `cap flows --host xxx`，需要细节用 `cap show`
4. 结论直接说人话，不要贴原始 JSON

## 注意

- 停止服务会删除本次全部记录，分析要在停止之前完成
- gRPC 接口只有路径没有字段（protobuf 二进制）
- 手机端一定要关掉自己的 MITM，解密只在电脑做
