# 🌍 国际关系研判系统

一个基于AI的国际关系研究分析平台，支持文献研究、新闻追踪、趋势预测、模型对比等功能。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 功能特性

### 📚 核心功能
- **AI智能分析** - 支持多种AI模型（DeepSeek、Qwen等）进行国际关系分析
- **文献管理** - 上传、存储、查阅PDF文献资料
- **新闻追踪** - 自动搜索最新国际新闻，追踪热点事件
- **趋势预测** - 基于历史数据和当前动态，预测未来发展趋势

### 🔬 专业工具
- **多模型对比** - 同一问题多模型对比分析，评估分析质量
- **批量分析** - 批量处理多篇文献，快速提炼要点
- **文献精读** - AI辅助深度解读专业文献
- **知识库** - 收藏概念、理论、案例，构建个人知识体系

### 💡 智能特性
- **历史参考** - 分析时自动参考历史记录，识别变化趋势
- **追问机制** - 支持对分析结果追问，深入探讨
- **报告导出** - 生成Markdown格式分析报告
- **收藏功能** - 收藏重要分析结果，便于回顾

## 🚀 快速开始

### 1. 环境要求
- Python 3.8 或更高版本
- AI API密钥（见下方配置说明）

### 2. 安装步骤

```bash
# 克隆项目
git clone https://github.com/yourusername/ir-research-system.git
cd ir-research-system

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置API密钥

**重要**：在使用前，必须配置AI API密钥！

1. 复制配置文件：
```bash
# Windows
copy config_example.py config.py

# Linux/Mac
cp config_example.py config.py
```

2. 编辑 `config.py`，填入你的API密钥：

```python
AI_PROVIDERS = {
    'silicon': {
        'name': '硅基流动 DeepSeek-V3',
        'api_key': '这里填入你的API密钥',  # ← 替换这里
        'endpoint': 'https://api.siliconflow.cn/v1/chat/completions',
        'model': 'deepseek-ai/DeepSeek-V3',
        'default': True
    },
    # ... 其他模型配置
}
```

### 4. 启动服务

双击运行 `run.bat` 或在命令行执行：

```bash
python local_app.py
```

然后在浏览器中打开：**http://127.0.0.1:5000**

## 📖 API配置指南

### 推荐：硅基流动（免费额度）

1. 访问 [硅基流动官网](https://www.siliconflow.cn/)
2. 注册账号并登录
3. 进入「API密钥」页面，创建新密钥
4. 复制密钥，填入 `config.py`

**优势**：
- 提供免费额度
- 支持 DeepSeek-V3、DeepSeek-R1 等模型
- 国内访问速度快

### 其他可选平台

#### 阿里云百炼
1. 访问 [阿里云百炼](https://bailian.console.aliyun.com/)
2. 创建应用，获取API密钥

#### DeepSeek 官方
1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 充值余额，创建API密钥

#### OpenAI（需要代理）
1. 访问 [OpenAI](https://platform.openai.com/)
2. 充值并创建API密钥
3. 需要配置代理才能访问

## 📁 项目结构

```
ir-research-system/
├── local_app.py      # 主程序（Flask后端）
├── local_app.html    # 前端页面
├── config.py         # API配置文件 ← 重要！
├── config_example.py # 配置文件模板
├── requirements.txt  # Python依赖
├── run.bat          # Windows启动脚本
├── run.sh           # Linux/Mac启动脚本
└── README.md        # 说明文档
```

## 🎯 使用说明

### 基础分析流程
1. **上传文献** → 进入「文献库」，上传PDF文件
2. **进行搜索** → 进入「新闻搜索」，获取最新动态
3. **开始分析** → 输入主题，选择分析类型，点击分析
4. **追问深化** → 对结果进行追问，深入探讨
5. **导出报告** → 将分析结果导出为Markdown

### 分析类型说明
- **综合分析** - 全面多角度分析
- **历史背景** - 侧重历史脉络梳理
- **参与者分析** - 分析各方行为体
- **趋势预测** - 预测未来发展方向
- **国家安全** - 安全视角分析
- **反恐研究** - 反恐专题研究

## 🔧 常见问题

### Q: 启动报错 "No module named flask"
```bash
pip install -r requirements.txt
```

### Q: API调用失败
1. 检查 `config.py` 中的API密钥是否正确
2. 检查网络连接
3. 查看账户余额是否充足

### Q: 端口被占用
修改 `local_app.py` 中的端口号：
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # 改为你想要的端口
```

### Q: 如何添加自定义AI模型？
在 `config.py` 中添加新的配置：
```python
'my_model': {
    'name': '我的模型',
    'api_key': 'your-key',
    'endpoint': 'https://api.example.com/v1/chat/completions',
    'model': 'model-name',
    'default': False
}
```

## 📝 License

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系

如有问题，请通过 GitHub Issues 反馈。
