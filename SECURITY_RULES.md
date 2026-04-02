# 安全规则配置

## 数据库集合

### 1. documents（文献库）
```json
{
  "read": true,
  "write": "auth.uid != null"
}
```
- 所有登录用户可读取
- 仅登录用户可写入（上传文档）

### 2. analyses（分析记录）
```json
{
  "read": "auth.uid != null",
  "write": "auth.uid != null"
}
```
- 仅登录用户可读写自己的记录

### 3. users（用户）
```json
{
  "read": "auth.uid != null",
  "write": "auth.uid != null"
}
```
- 仅用户本人可读写自己的信息

## 云函数

### document 函数
```json
{
  "invoke": "auth.uid != null"
}
```
- 仅登录用户可调用

### auth 函数
```json
{
  "invoke": true
}
```
- 允许所有人调用（用于登录）

## 配置方法

在 CloudBase 控制台中：
1. 进入环境 -> 数据库
2. 选择集合 -> 安全规则
3. 粘贴对应的 JSON 规则

或在 MCP 工具中使用 `writeSecurityRule` 工具配置。