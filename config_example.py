# ==================== AI模型配置 ====================
# 请在这里填入你的API密钥

AI_PROVIDERS = {
    # 硅基流动 (推荐，免费额度)
    'silicon': {
        'name': '硅基流动 DeepSeek-V3',
        'api_key': 'YOUR_API_KEY_HERE',  # 替换为你的硅基流动API Key
        'endpoint': 'https://api.siliconflow.cn/v1/chat/completions',
        'model': 'deepseek-ai/DeepSeek-V3',
        'default': True
    },
    'silicon_r1': {
        'name': '🔥 DeepSeek-R1 (推理模型)',
        'api_key': 'YOUR_API_KEY_HERE',  # 替换为你的硅基流动API Key
        'endpoint': 'https://api.siliconflow.cn/v1/chat/completions',
        'model': 'deepseek-ai/DeepSeek-R1',
        'default': False,
        'reasoning': True
    },
    'silicon_pro': {
        'name': '硅基流动 DeepSeek-V2.5',
        'api_key': 'YOUR_API_KEY_HERE',
        'endpoint': 'https://api.siliconflow.cn/v1/chat/completions',
        'model': 'deepseek-ai/DeepSeek-V2.5',
        'default': False
    },
    
    # 阿里云百炼 (可选)
    'qwen': {
        'name': '阿里 Qwen2-72B',
        'api_key': 'YOUR_API_KEY_HERE',  # 替换为你的阿里云API Key
        'endpoint': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        'model': 'qwen-plus',
        'default': False
    },
    'qwen_coder': {
        'name': '阿里 Qwen2.5-Coder',
        'api_key': 'YOUR_API_KEY_HERE',
        'endpoint': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        'model': 'qwen-coder-plus',
        'default': False
    },
    
    # OpenAI (需要代理)
    'openai': {
        'name': 'OpenAI GPT-4',
        'api_key': 'YOUR_API_KEY_HERE',  # 替换为你的OpenAI API Key
        'endpoint': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-4',
        'default': False
    },
    
    # DeepSeek 官方
    'deepseek': {
        'name': 'DeepSeek 官方',
        'api_key': 'YOUR_API_KEY_HERE',  # 替换为你的DeepSeek API Key
        'endpoint': 'https://api.deepseek.com/v1/chat/completions',
        'model': 'deepseek-chat',
        'default': False
    }
}

# 默认使用的AI模型
DEFAULT_AI = 'silicon'

# ==================== 其他配置 ====================
SECRET_KEY = 'your-secret-key-change-this-in-production'
