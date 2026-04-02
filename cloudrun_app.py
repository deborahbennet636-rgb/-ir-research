"""
国际关系研究系统 - CloudRun 部署版本
"""
import os
import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 从环境变量获取 API Key
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY', '')

# 系统提示词
SYSTEM_PROMPTS = {
    'general': """你是一位专业的国际关系研究员。擅长分析国家间的政治、经济、外交关系。
请基于提供的资料或知识，进行客观、专业、有深度的分析。
分析结构：1.背景概述 2.各方立场 3.影响因素 4.未来展望""",
    
    'history': """你是一位历史学家，擅长分析国际事件的历史背景和演变进程。
请详细分析指定主题的历史渊源、发展脉络和重要节点。""",
    
    'actors': """你是一位国际关系专家，擅长分析国际事件中的各方参与者。
请分析各方的利益诉求、立场态度、实力对比和互动关系。""",
    
    'trends': """你是一位战略分析师，擅长预测国际形势的发展趋势。
请基于现有信息和数据，分析主题的发展趋势和可能走向。"""
}

def call_siliconflow(messages, model='deepseek-ai/DeepSeek-V3'):
    """调用 SiliconFlow API"""
    if not SILICONFLOW_API_KEY:
        return None, "API Key 未配置"
    
    url = 'https://api.siliconflow.cn/v1/chat/completions'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SILICONFLOW_API_KEY}'
    }
    
    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 2000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content'], None
        else:
            return None, f"API 错误: {response.status_code}"
    except Exception as e:
        return None, str(e)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """分析主题"""
    data = request.get_json() or {}
    topic = data.get('topic', '')
    analysis_type = data.get('analysisType', 'general')
    
    if not topic:
        return jsonify({"success": False, "error": "请输入研究主题"}), 400
    
    # 构建提示词
    system_prompt = SYSTEM_PROMPTS.get(analysis_type, SYSTEM_PROMPTS['general'])
    user_prompt = f"""请对以下国际关系主题进行{analysis_type}分析：
主题：{topic}

要求：1. 基于国际关系理论分析 2. 客观中立 3. 有理有据 4. 结构清晰"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    result, error = call_siliconflow(messages)
    
    if error:
        return jsonify({"success": False, "error": error}), 500
    
    return jsonify({
        "success": True,
        "result": result,
        "topic": topic,
        "analysisType": analysis_type
    })

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>国际关系研究系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            color: #fff;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        input, select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #4a90d9;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #4a90d9, #6a5acd);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }
        .result.show { display: block; }
        .result h3 { color: #333; margin-bottom: 15px; }
        .result-content {
            white-space: pre-wrap;
            line-height: 1.8;
            color: #555;
        }
        .loading { text-align: center; color: #666; display: none; }
        .loading.show { display: block; }
        .error { color: #e74c3c; text-align: center; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌏 国际关系研究系统</h1>
        <div class="card">
            <div class="form-group">
                <label>研究主题</label>
                <input type="text" id="topic" placeholder="例如：中美关系、俄乌冲突" value="中美关系">
            </div>
            <div class="form-group">
                <label>分析类型</label>
                <select id="analysisType">
                    <option value="general">综合分析</option>
                    <option value="history">历史背景</option>
                    <option value="actors">主要参与者</option>
                    <option value="trends">趋势预测</option>
                </select>
            </div>
            <button id="analyzeBtn" onclick="analyze()">开始分析</button>
            <div class="loading" id="loading">分析中，请稍候...</div>
            <div class="error" id="error"></div>
            <div class="result" id="result">
                <h3>分析结果</h3>
                <div class="result-content" id="resultContent"></div>
            </div>
        </div>
    </div>
    <script>
        const API_BASE = '';
        
        async function analyze() {
            const topic = document.getElementById('topic').value.trim();
            const type = document.getElementById('analysisType').value;
            
            if (!topic) { alert('请输入研究主题'); return; }
            
            const btn = document.getElementById('analyzeBtn');
            const loading = document.getElementById('loading');
            const resultDiv = document.getElementById('result');
            const resultContent = document.getElementById('resultContent');
            const errorDiv = document.getElementById('error');
            
            btn.disabled = true;
            loading.classList.add('show');
            resultDiv.classList.remove('show');
            errorDiv.textContent = '';
            
            try {
                const res = await fetch(API_BASE + '/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic, analysisType: type })
                });
                
                const data = await res.json();
                
                if (data.success) {
                    resultContent.textContent = data.result;
                    resultDiv.classList.add('show');
                } else {
                    errorDiv.textContent = data.error || '分析失败';
                }
            } catch (e) {
                errorDiv.textContent = '连接失败: ' + e.message;
            } finally {
                btn.disabled = false;
                loading.classList.remove('show');
            }
        }
    </script>
</body>
</html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
