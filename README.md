#这是一个基于 Flask 和 SQLite 的简单语录服务器后端，用于实现在线语录的查询与上传
默认监听 `0.0.0.0:6673`，启动时自动创建 SQLite 数据库。

### Docker 部署

```bash
docker build -t yulu-server .
docker run -d -p 6673:6673 -v yulu_data:/data yulu-server
```

### 环境变量

| 变量名 | 默认值 | 说明 |
|---|---|---|
| `DB_FILE` | `quotes.db` | SQLite 数据库文件路径 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `6673` | 监听端口 |
| `FLASK_DEBUG` | `false` | 调试模式，设为 `true` 开启 |
| `DELETE_TOKEN` | `yulu_server` | 删除/清空操作的鉴权 token |

## 接口文档

### 1. 获取语录列表

GET /quotes?type=get&id={client_id}
或

```
POST /quotes
Content-Type: application/json

{
  "type": "get",
  "id": "client_1"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 是 | 固定为 `get` |
| `id` | string | 否 | 客户端标识，默认 `default` |

**响应 (200)**

```json
[
  {
    "id": 3,
    "message": "第一条语录",
    "created_at": "2026-08-18 19:22:56"
  },
  {
    "id": 1,
    "message": "第二条语录",
    "created_at": "2026-08-18 19:20:00"
  }
]
```

---

### 2. 上传语录

保存一条语录到指定客户端。

**请求**

```
POST /quotes
Content-Type: application/json

{
  "type": "upload",
  "id": "client_1",
  "message": "要保存的语录内容"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 是 | 固定为 `upload` |
| `id` | string | 否 | 客户端标识，默认 `default` |
| `message` | string | 是 | 语录内容，不能为空或纯空格 |

**响应 (200)**

```json
{
  "status": "success",
  "message": "语录保存成功",
  "quote_id": 4
}
```

**错误响应 (400)**

```json
{
  "error": "语录内容不能为空"
}
```

---

### 3. 删除单条语录

删除指定客户端的一条语录。**需要 token 鉴权。**

**请求**

```
POST /quotes
Content-Type: application/json

{
  "type": "delete",
  "id": "client_1",
  "quote_id": 3,
  "token": "yulu_server"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 是 | 固定为 `delete` |
| `id` | string | 否 | 客户端标识，默认 `default` |
| `quote_id` | int | 是 | 要删除的语录 ID |
| `token` | string | 是 | 管理员 token，由 `DELETE_TOKEN` 环境变量配置 |

**响应 (200)**

```json
{
  "status": "success",
  "message": "语录删除成功"
}
```

**错误响应**

| 状态码 | 说明 |
|---|---|
| 400 | 缺少 `quote_id` 或 `quote_id` 不是整数 |
| 403 | `token` 错误，无权限 |
| 404 | 语录不存在或不属于该客户端 |

---

### 4. 清空所有语录

清空指定客户端的全部语录。**需要 token 鉴权。**

**请求**

```
POST /quotes
Content-Type: application/json

{
  "type": "clear",
  "id": "client_1",
  "token": "yulu_server"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 是 | 固定为 `clear` |
| `id` | string | 否 | 客户端标识，默认 `default` |
| `token` | string | 是 | 管理员 token，由 `DELETE_TOKEN` 环境变量配置 |

**响应 (200)**

```json
{
  "status": "success",
  "message": "语录清空成功"
}
```

**错误响应 (403)**

```json
{
  "error": "无权限执行清空操作"
}
```

---

### 5. 获取统计信息

获取全局统计信息，包括总语录数、客户端数量和最近 5 条语录。

**请求**

```
GET /stats
```

**响应 (200)**

```json
{
  "total_quotes": 42,
  "total_clients": 3,
  "recent_quotes": [
    {
      "client_id": "client_1",
      "message": "最新语录",
      "created_at": "2026-08-18 19:22:56"
    }
  ]
}
```

---

## 调用示例

### JavaScript

```javascript
// 上传语录
await fetch("https://your-host:6673/quotes", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    type: "upload",
    id: "仙贝",
    message: "1114514"
  })
});

// 获取语录
await fetch("https://your-host:6673/quotes?type=get&id=user_1");

// 删除语录
await fetch("https://your-host:6673/quotes", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    type: "delete",
    id: "user_1",
    quote_id: 5,
    token: "your_token"
  })
});

// 清空语录
await fetch("https://your-host:6673/quotes", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    type: "clear",
    id: "user_1",
    token: "your_token"
  })
});
```

### curl

```bash
# 上传
curl -X POST http://localhost:6673/quotes \
  -H "Content-Type: application/json" \
  -d '{"type":"upload","id":"user_1","message":"你好世界"}'

# 获取
curl "http://localhost:6673/quotes?type=get&id=user_1"

# 删除
curl -X POST http://localhost:6673/quotes \
  -H "Content-Type: application/json" \
  -d '{"type":"delete","id":"user_1","quote_id":5,"token":"your_token"}'

# 清空
curl -X POST http://localhost:6673/quotes \
  -H "Content-Type: application/json" \
  -d '{"type":"clear","id":"user_1","token":"your_token"}'

# 统计
curl "http://localhost:6673/stats"
```
