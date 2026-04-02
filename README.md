# 🌏 IRPredict 国际政治研判系统

一个支持多用户共享文献库的AI研判平台，帮助分析国际关系、反恐合作、国家安全等领域。

## 🎯 功能特性

- **👥 多用户系统** - 用户注册登录，朋友可共享使用
- **📚 文献共享库** - 上传PDF、Word、TXT等论文、新闻、数据文件
- **🧠 AI智能分析** - 基于文献库进行RAG智能问答
- **📊 多种分析类型** - 综合分析、历史背景、参与者、反恐研究、国家安全、趋势预测
- **💾 历史记录** - 保存分析历史，可回顾查看

## 🚀 本地运行（推荐）

### 1. 安装依赖

```bash
pip install -r requirements_local.txt
```

### 2. 启动服务

```bash
python local_app.py
```

### 3. 访问系统

打开浏览器访问：`http://localhost:5000`

---

## ☁️ 云端部署（如需）

如果未来需要在服务器上部署，请参考：

1. 创建 CloudBase 数据库集合：`users`, `documents`, `analyses`
2. 部署云函数：`cloudfunctions/document`, `cloudfunctions/auth`
3. 配置安全规则
4. 前端部署到静态托管
