# 国际关系研判系统 - 本地版
# 直接运行此文件即可启动服务

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import requests

# 加载环境变量配置
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ir-predict-secret-key-2024')

# Session配置
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # session有效期7天
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 配置CORS允许所有来源和credentials
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}}, expose_headers=["Content-Type", "Set-Cookie"])

# 启用详细日志
import logging
logging.basicConfig(level=logging.INFO)

# ==================== 配置导入 ====================
# 从config.py读取AI配置
try:
    from config import AI_PROVIDERS, DEFAULT_AI
except ImportError:
    print("=" * 50)
    print("错误：请先配置 API 密钥！")
    print("=" * 50)
    print()
    print("请按以下步骤操作：")
    print("1. 复制 config_example.py 为 config.py")
    print("   Windows: copy config_example.py config.py")
    print("   Linux/Mac: cp config_example.py config.py")
    print()
    print("2. 编辑 config.py，填入你的API密钥")
    print()
    print("3. 重新运行程序")
    print()
    exit(1)

# 检查是否配置了API Key
unconfigured = []
for key, provider in AI_PROVIDERS.items():
    if provider.get('api_key') in [None, '', 'YOUR_API_KEY_HERE']:
        unconfigured.append(provider['name'])

if unconfigured:
    print("=" * 50)
    print("警告：以下AI模型API Key未配置：")
    for name in unconfigured:
        print(f"  - {name}")
    print("请编辑 config.py 填入API密钥！")
    print("=" * 50)
    print()

# ==================== 多新闻媒体配置 ====================
NEWS_SOURCES = {
    'xinhua': {
        'name': '新华网',
        'url': 'http://www.xinhuanet.com/',
        'enabled': True,
        'type': 'official'
    },
    'people': {
        'name': '人民网',
        'url': 'http://www.people.com.cn/',
        'enabled': True,
        'type': 'official'
    },
    'global': {
        'name': '环球时报',
        'url': 'http://www.huanqiu.com/',
        'enabled': True,
        'type': 'official'
    },
    'bbc': {
        'name': 'BBC中文网',
        'url': 'https://www.bbc.com/zhongwen/simp',
        'enabled': True,
        'type': 'international'
    },
    'voa': {
        'name': 'VOA中文',
        'url': 'https://www.voachinese.com/',
        'enabled': True,
        'type': 'international'
    },
    'reuters': {
        'name': '路透社',
        'url': 'https://www.reuters.com/',
        'enabled': True,
        'type': 'international'
    }
}

# 配置
UPLOAD_FOLDER = 'uploads'
DATABASE_FILE = 'ir_predict.db'

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 系统提示词
SYSTEM_PROMPTS = {
    'general': """你是一位世界顶尖的国际关系专家，专注于国际政治分析与战略研究。
你的分析风格：
1. 引用权威学术理论（现实主义、自由主义、建构主义等）
2. 结合具体数据和案例
3. 深入分析各行为体的利益诉求、权力结构与战略意图
4. 提供多角度、平衡的分析视角
5. 预见可能的发展趋势与影响

请输出结构化、深度、有理有据的分析报告。""",
    
    'history': """你是一位资深国际关系史学家，精通国际关系史学术研究。
你的分析风格：
1. 追溯历史渊源，梳理发展脉络
2. 分析关键历史节点和转折点
3. 引用一手史料和权威研究
4. 将历史与现实紧密结合
5. 提供历史经验教训的深刻洞见

请输出具有历史深度和学术严谨性的分析。""",
    
    'actors': """你是一位国际政治战略分析专家，擅长进行多方博弈分析。
你的分析风格：
1. 识别所有相关行为体（国家、组织、机构等）
2. 分析各方的核心利益与战略目标
3. 评估各方的实力对比和资源优势
4. 预测各方的策略选择和行为模式
5. 揭示复杂的互动关系和潜在联盟

请输出全面深入的参与者分析。""",
    
    'counterterror': """你是一位国际反恐与安全研究专家，供职于顶级智库。
你的分析风格：
1. 基于最新全球反恐态势和情报
2. 分析双边和多边反恐合作机制
3. 评估情报共享、执法合作的法律框架
4. 关注极端主义意识形态和跨国网络
5. 提供政策建议和风险预警

请输出专业深刻的反恐研究分析。""",
    
    'security': """你是一位国家安全战略专家，专注于传统与非传统安全研究。
你的分析风格：
1. 识别多元安全威胁来源
2. 分析地缘政治安全格局
3. 评估新兴安全挑战（网络、气候、生物等）
4. 分析国家安全战略调整
5. 提供安全风险评估和政策建议

请输出全面的国家安全分析。""",
    
    'trends': """你是一位国际战略预测专家，擅长趋势分析和情景推演。
你的分析风格：
1. 基于当前态势进行趋势外推
2. 识别关键驱动因素和不确定因素
3. 进行多情景分析
4. 评估趋势的可能影响
5. 提供前瞻性的战略建议

请输出具有前瞻性的趋势预测分析。"""
}

# ==================== 数据库操作 ====================

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nickname TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 文献表
    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        filetype TEXT,
        content TEXT,
        user_id INTEGER,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # 新闻表
    c.execute('''CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT,
        source TEXT,
        url TEXT,
        publish_date TEXT,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # 分析记录表
    c.execute('''CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        analysis_type TEXT,
        result TEXT,
        use_literature INTEGER DEFAULT 0,
        use_news INTEGER DEFAULT 0,
        user_id INTEGER,
        ai_provider TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # 检查并添加 ai_provider 列（如果不存在）
    try:
        c.execute('SELECT ai_provider FROM analyses LIMIT 1')
    except:
        c.execute('ALTER TABLE analyses ADD COLUMN ai_provider TEXT')
    
    # 对话历史表（用于追问功能）
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (analysis_id) REFERENCES analyses(id)
    )''')
    
    # 知识库表 - 存储概念、理论、案例
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,  -- 概念/理论/案例/人物/事件
        title TEXT NOT NULL,
        content TEXT,
        tags TEXT,  -- 标签，逗号分隔
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # 论文大纲表
    c.execute('''CREATE TABLE IF NOT EXISTS outlines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        outline_content TEXT,  -- JSON格式存储大纲结构
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DATABASE_FILE)

# ==================== 辅助函数 ====================

def call_ai(prompt, system_prompt=None, ai_provider=None):
    """调用AI模型，支持多提供商"""
    provider = AI_PROVIDERS.get(ai_provider or DEFAULT_AI)
    if not provider:
        return {"error": f"未知的AI提供商: {ai_provider}"}
    
    api_key = provider['api_key']
    if not api_key:
        return {"error": f"{provider['name']} 的API Key未配置"}
    
    try:
        if provider.get('anthropic'):
            # Anthropic API 格式不同
            response = requests.post(
                provider['endpoint'],
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': provider['model'],
                    'max_tokens': 2000,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ]
                },
                timeout=60
            )
        else:
            # OpenAI 兼容格式
            response = requests.post(
                provider['endpoint'],
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                json={
                    'model': provider['model'],
                    'messages': [
                        {'role': 'system', 'content': system_prompt or '你是一个专业的国际关系研究助手'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7,
                    'max_tokens': 4000
                },
                timeout=120
            )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']
                # 推理模型可能有 reasoning_content
                content = message.get('content', '')
                reasoning = message.get('reasoning_content', '')
                if reasoning and provider.get('reasoning'):
                    # 将推理过程附加到内容前面
                    content = f"【思考过程】\n{reasoning}\n\n【最终回答】\n{content}"
                return {"content": content}
            elif 'content' in result:
                return {"content": result['content']}
            else:
                return {"error": f"API返回格式异常: {result}"}
        else:
            return {"error": f"API请求失败: {response.status_code}, {response.text[:200]}"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时，请稍后重试"}
    except Exception as e:
        return {"error": f"调用失败: {str(e)}"}


def search_news_from_ai(topic, ai_provider=None):
    """搜索最新新闻 - 优先使用真实搜索，回退到AI"""
    import re
    from datetime import datetime
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    current_date = datetime.now().strftime("%Y年%m月%d日")
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    try:
        # 方法1: 尝试百度实时新闻搜索
        try:
            # 搜索特定领域的最新新闻
            search_queries = [
                f"{topic} 2025",
                f"{topic} 2026",
                f"{topic} 最新消息",
                f"国际 {topic} 2025"
            ]
            
            for query in search_queries:
                baidu_url = f"https://www.baidu.com/s?wd={requests.utils.quote(query)}&rn=10"
                resp = requests.get(baidu_url, headers=headers, timeout=12)
                
                if resp.status_code == 200:
                    # 提取新闻标题（更精准的正则）
                    news_items = re.findall(r'aria-label="([^"]+)"', resp.text)
                    
                    # 过滤掉太短或无意义的标题
                    valid_news = [n for n in news_items if len(n) > 10 and '百度' not in n and '首页' not in n][:8]
                    
                    if valid_news:
                        content = f"【{topic} - 搜索结果 {current_date}】\n\n"
                        for i, news in enumerate(valid_news, 1):
                            content += f"{i}. {news}\n"
                        
                        # 尝试获取更详细的摘要
                        try:
                            summaries = re.findall(r'aria-label="([^"]+)"', resp.text[:20000])
                            if len(summaries) > 8:
                                content += "\n📰 热门报道:\n"
                                for s in summaries[8:12]:
                                    if len(s) > 15:
                                        content += f"  • {s[:60]}...\n"
                        except:
                            pass
                        
                        return content
        except Exception as e:
            print(f"搜索失败: {e}")
        
        # 方法2: 回退到AI，但给出极其详细的最新信息要求
        provider = AI_PROVIDERS.get(ai_provider or DEFAULT_AI)
        if not provider:
            return "未知的AI提供商"
        
        api_key = provider['api_key']
        if not api_key:
            return f"{provider['name']} 的API Key未配置"
        
        # 基于2025-2026新闻的趋势分析
        prompt = f"""你是国际关系与地缘政治分析专家。请根据你的知识库，分析以下主题的最新动态：

【主题】：{topic}
【当前日期】：{current_year}年{current_month}月

【任务要求】：
1. 首先列出2025年至今（{current_year}年）的重大新闻事件和发展
2. 每条新闻需包含：具体日期、事件标题、简要说明
3. 基于这些最新动态，分析未来3-5年的发展趋势和可能走向
4. 结合国际关系理论（如现实主义、自由制度主义、建构主义等）给出专业解读
5. 指出可能的风险因素和不确定性

【分析框架】：
- 近期动态（2025-{current_year}年）
- 驱动因素分析
- 未来趋势预测
- 风险与不确定性
- 政策建议

请提供专业的分析报告："""

        response = requests.post(
            provider['endpoint'],
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json={
                'model': provider['model'],
                'messages': [
                    {'role': 'system', 'content': f'你是国际关系与地缘政治分析专家。今天是{current_date}。请基于你所掌握的最新信息进行分析，包括2025年以来的重要事件。对于不确定的信息可以标注来源。请给出专业、客观的分析。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.5,  # 适中温度，保证创造性和准确性
                'max_tokens': 3500
            },
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return f"【{topic} 动态分析与趋势预测 {current_date}】\n\n{content}"
            elif 'content' in result:
                return f"【{topic} 动态分析与趋势预测】\n\n{result['content']}"
        
        return "无法获取动态信息"
        
    except Exception as e:
        return f"搜索出错: {str(e)}"

# ==================== API 接口 ====================

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'local_app.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "message": "IRPredict 服务运行中"})

# 用户相关
@app.route('/api/user/register', methods=['POST'])
def register():
    """注册用户"""
    data = request.get_json()
    username = data.get('username', '').strip()
    nickname = data.get('nickname', username) or username
    
    if not username:
        return jsonify({"success": False, "error": "请输入用户名"}), 400
    
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO users (username, nickname) VALUES (?, ?)', (username, nickname))
        conn.commit()
        user_id = c.lastrowid
        session['user_id'] = user_id
        session['username'] = username
        session['nickname'] = nickname
        return jsonify({"success": True, "user_id": user_id, "username": username, "nickname": nickname})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": "用户名已存在"}), 400
    finally:
        conn.close()

@app.route('/api/user/login', methods=['POST'])
def login():
    """登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({"success": False, "error": "请输入用户名"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, nickname FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['nickname'] = user[2]
        return jsonify({"success": True, "user_id": user[0], "username": user[1], "nickname": user[2]})
    else:
        return jsonify({"success": False, "error": "用户不存在，请先注册"}), 404

@app.route('/api/user/logout', methods=['POST'])
def logout():
    """退出登录"""
    session.clear()
    return jsonify({"success": True})

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取当前用户信息"""
    user_id = session.get('user_id')
    if user_id:
        return jsonify({
            "logged_in": True,
            "user_id": user_id,
            "username": session.get('username'),
            "nickname": session.get('nickname')
        })
    return jsonify({"logged_in": False})

# 文献相关
@app.route('/api/documents', methods=['GET'])
def get_documents():
    """获取文献列表"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT id, title, filename, filetype, username, created_at 
                FROM documents ORDER BY created_at DESC''')
    docs = c.fetchall()
    conn.close()
    
    result = []
    for doc in docs:
        result.append({
            "id": doc[0],
            "title": doc[1],
            "filename": doc[2],
            "filetype": doc[3],
            "username": doc[4],
            "created_at": doc[5]
        })
    
    return jsonify({"success": True, "documents": result})

@app.route('/api/documents', methods=['POST'])
def upload_document():
    """上传文献"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "请选择文件"}), 400
    
    file = request.files['file']
    title = request.form.get('title', '').strip()
    
    if file.filename == '':
        return jsonify({"success": False, "error": "请选择文件"}), 400
    
    # 保存文件
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, f"{datetime.now().timestamp()}_{filename}")
    file.save(filepath)
    
    # 提取文本内容
    content = ""
    filetype = filename.split('.')[-1].lower()
    try:
        if filetype in ['txt', 'md', 'markdown']:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()[:5000]
        else:
            content = f"[{filetype.upper()} 文件，内容需解析]"
    except:
        content = "[文件内容读取失败]"
    
    # 保存到数据库
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO documents (title, filename, filepath, filetype, content, user_id, username)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (title or filename.replace(f'.{filetype}', ''), filename, filepath, 
               filetype, content, user_id, session.get('nickname')))
    conn.commit()
    doc_id = c.lastrowid
    conn.close()
    
    return jsonify({"success": True, "document_id": doc_id, "filename": filename})

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """删除文献"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT filepath, user_id FROM documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    
    if not doc:
        conn.close()
        return jsonify({"success": False, "error": "文献不存在"}), 404
    
    if doc[1] != user_id and session.get('username') != 'admin':
        conn.close()
        return jsonify({"success": False, "error": "无权限删除"}), 403
    
    try:
        if os.path.exists(doc[0]):
            os.remove(doc[0])
    except:
        pass
    
    c.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

# 新闻相关
@app.route('/api/news', methods=['GET'])
def get_news():
    """获取新闻列表"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT n.id, n.title, n.source, n.content, n.publish_date, u.username, n.created_at 
                    FROM news n 
                    LEFT JOIN users u ON n.user_id = u.id
                    ORDER BY n.created_at DESC LIMIT 50''')
        news_list = c.fetchall()
        conn.close()
        
        result = []
        for n in news_list:
            result.append({
                "id": n[0],
                "title": n[1],
                "source": n[2],
                "content": n[3],  # 返回完整内容
                "publish_date": n[4],
                "username": n[5],
                "created_at": n[6]
            })
        
        return jsonify({"success": True, "news": result})
    except Exception as e:
        logger.error("获取新闻失败: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/news', methods=['POST'])
def add_news():
    """添加新闻（手动输入）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    source = data.get('source', '').strip() or '手动添加'
    url = data.get('url', '').strip()
    publish_date = data.get('publish_date', '').strip()
    
    if not title:
        return jsonify({"success": False, "error": "请输入新闻标题"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO news (title, content, source, url, publish_date, user_id)
                VALUES (?, ?, ?, ?, ?, ?)''',
              (title, content, source, url, publish_date, user_id))
    conn.commit()
    news_id = c.lastrowid
    conn.close()
    
    return jsonify({"success": True, "news_id": news_id})

@app.route('/api/news/search', methods=['POST'])
def search_news():
    """AI搜索最新新闻"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        logger.error("新闻搜索失败: 用户未登录, session内容: %s", dict(session))
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    topic = data.get('topic', '').strip()
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    
    if not topic:
        return jsonify({"success": False, "error": "请输入搜索关键词"}), 400
    
    logger.info("开始搜索新闻: topic=%s, ai_provider=%s", topic, ai_provider)
    
    # 使用AI搜索最新新闻
    news_content = search_news_from_ai(topic, ai_provider)
    logger.info("AI返回结果: %s", news_content[:500] if news_content else "None")
    
    # 检查是否返回了错误信息（以特定错误前缀开头）
    is_error = False
    if news_content:
        error_prefixes = ["API请求失败", "请求超时", "网络请求失败", "搜索出错", "未知的AI", "API Key"]
        for prefix in error_prefixes:
            if news_content.startswith(prefix):
                is_error = True
                break
        # 同时检查内容长度，太短的可能也是错误
        if not is_error and len(news_content.strip()) < 50:
            is_error = True
    
    if news_content and not is_error and len(news_content.strip()) >= 50:
        # 成功返回内容，保存到数据库
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO news (title, content, source, user_id)
                    VALUES (?, ?, ?, ?)''',
                  (f"AI搜索: {topic}", news_content, "AI分析生成", user_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "news": news_content})
    else:
        # 返回了错误信息
        return jsonify({"success": False, "error": news_content or "搜索失败，请稍后重试"}), 500

@app.route('/api/news/<int:news_id>', methods=['DELETE'])
def delete_news(news_id):
    """删除新闻"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT user_id FROM news WHERE id = ?', (news_id,))
    news = c.fetchone()
    
    if not news:
        conn.close()
        return jsonify({"success": False, "error": "新闻不存在"}), 404
    
    if news[0] != user_id and session.get('username') != 'admin':
        conn.close()
        return jsonify({"success": False, "error": "无权限删除"}), 403
    
    c.execute('DELETE FROM news WHERE id = ?', (news_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

# RSS订阅配置 - 使用AI搜索获取最新新闻
RSS_FEEDS = {
    'xinhua': {
        'name': '新华网国际新闻',
        'topic': '2024 2025 最新国际政治 外交关系 全球热点',
        'name_cn': '新华网'
    },
    'people': {
        'name': '人民网国际新闻',
        'topic': '2024 2025 最新国际关系 国际形势 全球热点新闻',
        'name_cn': '人民网'
    },
    'huanqiu': {
        'name': '环球时报国际新闻',
        'topic': '2024 2025 最新国际新闻 地缘政治 国际关系',
        'name_cn': '环球时报'
    }
}

@app.route('/api/news/rss/<source>', methods=['POST'])
def fetch_rss(source):
    """通过AI搜索获取最新新闻"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    if source not in RSS_FEEDS:
        return jsonify({"success": False, "error": "不支持的新闻源"}), 400
    
    feed_info = RSS_FEEDS[source]
    topic = feed_info['topic']
    
    logger.info("开始获取最新新闻: %s, 主题: %s", source, topic)
    
    # 使用AI搜索最新新闻
    ai_provider = DEFAULT_AI
    news_content = search_news_from_ai(topic, ai_provider)
    
    if news_content and len(news_content.strip()) >= 50:
        # 检查是否返回错误
        is_error = False
        error_prefixes = ["API请求失败", "请求超时", "网络请求失败", "搜索出错", "未知的AI", "API Key"]
        for prefix in error_prefixes:
            if news_content.startswith(prefix):
                is_error = True
                break
        
        if not is_error:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''INSERT INTO news (title, content, source, user_id)
                        VALUES (?, ?, ?, ?)''',
                      (f"📰 {feed_info['name_cn']}最新动态", news_content, feed_info['name_cn'], user_id))
            conn.commit()
            conn.close()
            
            logger.info("成功获取并保存 %s 的最新新闻", feed_info['name_cn'])
            return jsonify({"success": True, "count": 1, "source": feed_info['name_cn']})
    
    return jsonify({"success": False, "error": "获取失败，请稍后重试"}), 500

# AI分析相关
@app.route('/api/analyze', methods=['POST'])
def analyze():
    """AI分析"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    topic = data.get('topic', '').strip()
    analysis_type = data.get('analysisType', 'general')
    use_literature = data.get('useLiterature', True)
    use_news = data.get('useNews', False)  # 新增：是否使用新闻
    auto_search_news = data.get('autoSearchNews', False)  # 新增：是否自动搜索最新新闻
    ai_provider = data.get('aiProvider', DEFAULT_AI)  # 获取AI提供商
    
    if not topic:
        return jsonify({"success": False, "error": "请输入研究主题"}), 400
    
    # 自动搜索新闻并保存到数据库
    auto_news_content = ""
    if auto_search_news:
        logger.info("自动搜索新闻: topic=%s", topic)
        auto_news = search_news_from_ai(topic, ai_provider)
        
        # 检查是否返回了错误信息
        is_error = False
        if auto_news:
            error_prefixes = ["API请求失败", "请求超时", "网络请求失败", "搜索出错", "未知的AI", "API Key"]
            for prefix in error_prefixes:
                if auto_news.startswith(prefix):
                    is_error = True
                    break
            if not is_error and len(auto_news.strip()) < 50:
                is_error = True
        
        if auto_news and not is_error and len(auto_news.strip()) >= 50:
            # 保存自动搜索的新闻到数据库
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''INSERT INTO news (title, content, source, user_id)
                        VALUES (?, ?, ?, ?)''',
                      (f"AI自动搜索: {topic}", auto_news, "AI分析生成", user_id))
            conn.commit()
            conn.close()
            logger.info("自动搜索的新闻已保存到数据库")
            auto_news_content = auto_news
        else:
            logger.warning("自动搜索新闻失败或返回内容过短")
    
    # 获取文献内容
    literature_context = ""
    if use_literature:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT title, content FROM documents ORDER BY created_at DESC LIMIT 5')
        docs = c.fetchall()
        conn.close()
        
        if docs:
            literature_context = "\n\n## 参考文献内容：\n"
            for i, doc in enumerate(docs):
                if doc[1]:
                    literature_context += f"\n【文档{i+1}】{doc[0]}\n{doc[1][:2000]}\n"
    
    # 获取新闻内容
    news_context = ""
    if use_news or auto_news_content:
        # 如果有自动搜索的新闻，先加入
        if auto_news_content:
            news_context = "\n\n## 自动搜索的最新新闻动态：\n" + auto_news_content[:3000] + "\n"
        
        # 再获取数据库中已有的新闻
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT title, content, source FROM news ORDER BY created_at DESC LIMIT 10')
        news_list = c.fetchall()
        conn.close()
        
        if news_list:
            news_context += "\n\n## 新闻库中的相关动态：\n"
            for i, news in enumerate(news_list):
                if news[1]:
                    source = news[2] or "未知来源"
                    news_context += f"\n【新闻{i+1}】{news[0]} (来源: {source})\n{news[1][:1000]}\n"
    
    system_prompt = SYSTEM_PROMPTS.get(analysis_type, SYSTEM_PROMPTS['general'])
    
    # 获取历史分析记录作为参考
    history_context = ""
    conn = get_db_connection()
    c = conn.cursor()
    # 查找与当前主题相关的历史分析（按关键词匹配）
    c.execute('''SELECT topic, result, created_at FROM analyses 
                ORDER BY created_at DESC LIMIT 50''')
    all_history = c.fetchall()
    
    # 计算相关度，取所有相关的历史记录
    related_history = []
    topic_keywords = topic.lower().split()
    for hist in all_history:
        hist_keywords = hist[0].lower().split()
        # 简单关键词匹配
        common = set(topic_keywords) & set(hist_keywords)
        if len(common) >= 1 or any(kw in hist_keywords for kw in topic_keywords[:3]):
            related_history.append((len(common), hist))
    
    # 按相关度排序，取所有匹配的历史记录
    related_history.sort(key=lambda x: -x[0])
    related_history = [h[1] for h in related_history]
    
    if related_history:
        history_context = "\n\n## 历史分析参考：\n"
        for i, hist in enumerate(related_history):
            history_context += f"\n【历史分析{i+1}】主题：{hist[0]} (时间: {hist[2]})\n{hist[1][:800]}\n"
    conn.close()
    
    # 构建提示词
    if use_literature and use_news:
        user_prompt = f"""请对以下国际关系主题进行{analysis_type}分析：
主题：{topic}
{history_context}
{literature_context}
{news_context}

要求：
1. 综合参考文献、最新新闻和历史分析进行分析
2. 基于国际关系理论分析
3. 客观中立、有理有据、结构清晰
4. 如涉及反恐、国家安全，请从专业角度分析
5. 如果有最新新闻，请结合时事进行分析
6. 如有历史分析参考，请对比分析，识别变化趋势"""

    elif use_literature:
        user_prompt = f"""请对以下国际关系主题进行{analysis_type}分析：
主题：{topic}
{history_context}
{literature_context}

要求：
1. 基于提供的参考文献和历史分析进行分析
2. 基于国际关系理论分析
3. 客观中立、有理有据、结构清晰
4. 如涉及反恐、国家安全，请从专业角度分析
5. 如有历史分析参考，请对比分析，识别变化趋势"""

    elif use_news:
        user_prompt = f"""请对以下国际关系主题进行{analysis_type}分析：
主题：{topic}
{history_context}
{news_context}

要求：
1. 基于最新新闻动态和历史分析进行分析
2. 基于国际关系理论分析
3. 客观中立、有理有据、结构清晰
4. 如涉及反恐、国家安全，请从专业角度分析
5. 如有历史分析参考，请对比分析，识别变化趋势"""

    else:
        user_prompt = f"""请对以下国际关系主题进行{analysis_type}分析：
主题：{topic}
{history_context}

要求：
1. 基于你的知识库和历史分析进行综合分析
2. 基于国际关系理论分析
3. 客观中立、有理有据、结构清晰
4. 如涉及反恐、国家安全，请从专业角度分析
5. 如有历史分析参考，请对比分析，识别变化趋势"""

    # 调用AI模型
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    result = call_ai(user_prompt, system_prompt, ai_provider)
    
    if 'error' in result:
        return jsonify({"success": False, "error": result['error']}), 500
    
    analysis_result = result.get('content', '')
    
    # 保存分析记录
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO analyses (topic, analysis_type, result, use_literature, use_news, user_id, ai_provider)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (topic, analysis_type, analysis_result, 1 if use_literature else 0, 1 if use_news else 0, user_id, ai_provider))
    conn.commit()
    analysis_id = c.lastrowid
    conn.close()
    
    # 返回结果，附带历史参考信息
    has_history_ref = len(related_history) > 0
    history_topics = [h[0] for h in related_history]
    
    return jsonify({
        "success": True, 
        "result": analysis_result, 
        "analysis_id": analysis_id,
        "has_history_ref": has_history_ref,
        "history_topics": history_topics
    })

# 分析历史
@app.route('/api/analyses', methods=['GET'])
def get_analyses():
    """获取分析历史"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT id, topic, analysis_type, use_literature, use_news, created_at 
                FROM analyses ORDER BY created_at DESC LIMIT 20''')
    records = c.fetchall()
    conn.close()
    
    type_names = {
        'general': '综合分析', 'history': '历史背景', 'actors': '参与者',
        'counterterror': '反恐研究', 'security': '国家安全', 'trends': '趋势预测'
    }
    
    result = []
    for r in records:
        sources = []
        if r[3]: sources.append('文献')
        if r[4]: sources.append('新闻')
        result.append({
            "id": r[0],
            "topic": r[1],
            "analysis_type": type_names.get(r[2], r[2]),
            "sources": '+'.join(sources) if sources else 'AI',
            "created_at": r[5]
        })
    
    return jsonify({"success": True, "analyses": result})

@app.route('/api/analysis/<int:analysis_id>', methods=['GET'])
def get_analysis_detail(analysis_id):
    """获取单个分析详情"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT id, topic, analysis_type, result, use_literature, use_news, 
                ai_provider, created_at 
                FROM analyses WHERE id = ?''', (analysis_id,))
    record = c.fetchone()
    
    # 同时获取相关的对话历史
    c.execute('''SELECT role, content, created_at 
                FROM conversations WHERE analysis_id = ? 
                ORDER BY created_at ASC''', (analysis_id,))
    conversations = c.fetchall()
    conn.close()
    
    if not record:
        return jsonify({"success": False, "error": "分析记录不存在"}), 404
    
    type_names = {
        'general': '综合分析', 'history': '历史背景', 'actors': '参与者',
        'counterterror': '反恐研究', 'security': '国家安全', 'trends': '趋势预测'
    }
    
    sources = []
    if record[4]: sources.append('文献')
    if record[5]: sources.append('新闻')
    
    return jsonify({
        "success": True,
        "analysis": {
            "id": record[0],
            "topic": record[1],
            "analysis_type": type_names.get(record[2], record[2]),
            "result": record[3],
            "sources": '+'.join(sources) if sources else 'AI',
            "ai_provider": record[6],
            "created_at": record[7]
        },
        "conversations": [
            {"role": conv[0], "content": conv[1], "created_at": conv[2]}
            for conv in conversations
        ]
    })

# 获取系统配置
@app.route('/api/config', methods=['GET'])
def get_config():
    """获取AI提供商和新闻源配置"""
    # 过滤掉敏感信息
    ai_providers = []
    for key, provider in AI_PROVIDERS.items():
        ai_providers.append({
            'id': key,
            'name': provider['name'],
            'enabled': bool(provider.get('api_key')),
            'default': provider.get('default', False)
        })
    
    # 新闻源
    news_sources = []
    for key, source in NEWS_SOURCES.items():
        news_sources.append({
            'id': key,
            'name': source['name'],
            'url': source['url'],
            'enabled': source.get('enabled', True),
            'type': source.get('type', 'other')
        })
    
    return jsonify({
        "success": True,
        "aiProviders": ai_providers,
        "newsSources": news_sources
    })

# 对话追问
@app.route('/api/chat', methods=['POST'])
def chat():
    """继续对话追问"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    analysis_id = data.get('analysisId')
    question = data.get('question', '').strip()
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    
    if not analysis_id:
        return jsonify({"success": False, "error": "缺少分析ID"}), 400
    if not question:
        return jsonify({"success": False, "error": "请输入问题"}), 400
    
    # 获取原始分析内容
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT topic, analysis_type, result FROM analyses WHERE id = ? AND user_id = ?', 
              (analysis_id, user_id))
    analysis = c.fetchone()
    
    if not analysis:
        conn.close()
        return jsonify({"success": False, "error": "分析记录不存在"}), 404
    
    topic, analysis_type, original_result = analysis
    
    # 保存用户问题
    c.execute('INSERT INTO conversations (analysis_id, role, content) VALUES (?, ?, ?)',
              (analysis_id, 'user', question))
    conn.commit()
    
    # 获取对话历史
    c.execute('SELECT role, content FROM conversations WHERE analysis_id = ? ORDER BY created_at',
              (analysis_id,))
    history = c.fetchall()
    conn.close()
    
    # 构建对话上下文
    context = f"以下是关于「{topic}」的分析报告：\n\n{original_result}\n\n"
    context += "对话历史：\n"
    for role, content in history:
        role_name = "用户" if role == "user" else "助手"
        context += f"{role_name}：{content}\n"
    
    # 调用AI
    system_prompt = SYSTEM_PROMPTS.get(analysis_type, SYSTEM_PROMPTS['general'])
    format_instruction = """
请用清晰易读的格式回答：
1. 使用适当的换行和段落分隔
2. 每个要点单独成段
3. 使用数字列表或符号列表组织内容
4. 涉及指标对比时，使用表格或分行列出
5. 关键结论加粗或单独标注"""
    result = call_ai(f"{context}\n\n请回答用户的问题：{question}\n{format_instruction}", system_prompt, ai_provider)
    
    if 'error' in result:
        return jsonify({"success": False, "error": result['error']}), 500
    
    answer = result.get('content', '')
    
    # 保存AI回答
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO conversations (analysis_id, role, content) VALUES (?, ?, ?)',
              (analysis_id, 'assistant', answer))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "answer": answer})

# 获取对话历史
@app.route('/api/chat/<int:analysis_id>', methods=['GET'])
def get_chat_history(analysis_id):
    """获取某个分析的对话历史"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM analyses WHERE id = ? AND user_id = ?', (analysis_id, user_id))
    if not c.fetchone():
        conn.close()
        return jsonify({"success": False, "error": "分析记录不存在"}), 404
    
    c.execute('SELECT role, content, created_at FROM conversations WHERE analysis_id = ? ORDER BY created_at',
              (analysis_id,))
    history = c.fetchall()
    conn.close()
    
    messages = []
    for role, content, created_at in history:
        messages.append({
            "role": role,
            "content": content,
            "created_at": created_at
        })
    
    return jsonify({"success": True, "history": messages})

# ==================== 知识库API ====================
@app.route('/api/knowledge', methods=['GET'])
def get_knowledge():
    """获取知识库列表"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    category = request.args.get('category', '')
    conn = get_db_connection()
    c = conn.cursor()
    
    if category:
        c.execute('''SELECT id, category, title, content, tags, created_at 
                    FROM knowledge WHERE user_id = ? AND category = ? 
                    ORDER BY created_at DESC''', (user_id, category))
    else:
        c.execute('''SELECT id, category, title, content, tags, created_at 
                    FROM knowledge WHERE user_id = ? ORDER BY created_at DESC''', (user_id,))
    
    items = c.fetchall()
    conn.close()
    
    result = []
    for item in items:
        result.append({
            "id": item[0],
            "category": item[1],
            "title": item[2],
            "content": item[3],
            "tags": item[4],
            "created_at": item[5]
        })
    
    return jsonify({"success": True, "knowledge": result})

@app.route('/api/knowledge', methods=['POST'])
def add_knowledge():
    """添加知识条目"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    category = data.get('category', '').strip()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    tags = data.get('tags', '').strip()
    
    if not category or not title:
        return jsonify({"success": False, "error": "请选择分类并输入标题"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO knowledge (category, title, content, tags, user_id)
                VALUES (?, ?, ?, ?, ?)''', (category, title, content, tags, user_id))
    knowledge_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "id": knowledge_id})

@app.route('/api/knowledge/<int:knowledge_id>', methods=['DELETE'])
def delete_knowledge(knowledge_id):
    """删除知识条目"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT user_id FROM knowledge WHERE id = ?', (knowledge_id,))
    item = c.fetchone()
    
    if not item:
        conn.close()
        return jsonify({"success": False, "error": "知识条目不存在"}), 404
    
    if item[0] != user_id and session.get('username') != 'admin':
        conn.close()
        return jsonify({"success": False, "error": "无权限删除"}), 403
    
    c.execute('DELETE FROM knowledge WHERE id = ?', (knowledge_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

# ==================== 论文辅助API ====================
@app.route('/api/outline', methods=['POST'])
def generate_outline():
    """生成论文大纲"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    topic = data.get('topic', '').strip()
    outline_type = data.get('outlineType', 'paper')  # paper/thesis/proposal
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    
    if not topic:
        return jsonify({"success": False, "error": "请输入研究主题"}), 400
    
    # 获取知识库相关内容
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT title, content, tags FROM knowledge WHERE user_id = ? ORDER BY created_at DESC LIMIT 10')
    knowledge = c.fetchall()
    conn.close()
    
    knowledge_context = ""
    if knowledge:
        knowledge_context = "\n\n## 相关知识库内容：\n"
        for k in knowledge:
            knowledge_context += f"- {k[0]}: {k[2] or '无标签'}\n"
    
    # 构建提示词
    if outline_type == 'paper':
        prompt = f"""请为以下主题生成一篇学术论文大纲：
主题：{topic}
{knowledge_context}

要求：
1. 包括题目、摘要、关键词
2. 结构包括：引言、文献综述、理论框架、研究方法、结果分析、结论、参考文献
3. 每个章节给出2-3个小节标题
4. 格式为标准的学术论文结构"""
    elif outline_type == 'thesis':
        prompt = f"""请为以下主题生成一篇学位论文（本科/硕士）大纲：
主题：{topic}
{knowledge_context}

要求：
1. 包括题目、摘要、关键词
2. 结构包括：绪论、文献综述、理论基础、研究设计、实证分析、结论与建议
3. 详细到三级标题
4. 适合本科或硕士论文"""
    else:  # proposal
        prompt = f"""请为以下主题生成一份研究计划书大纲：
主题：{topic}
{knowledge_context}

要求：
1. 包括：研究背景、研究意义、文献综述、研究问题、研究方法、预期成果、创新点
2. 结构清晰、逻辑严密
3. 适合申报课题或课程论文"""

    # 调用AI生成
    system_prompt = "你是一个学术论文写作专家，擅长生成结构清晰、逻辑严密的论文大纲。"
    outline_result = call_ai(prompt, system_prompt, ai_provider)
    
    # 保存到数据库
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO outlines (title, topic, outline_content, user_id)
                VALUES (?, ?, ?, ?)''', 
              (f"{topic} - 大纲", topic, outline_result, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "outline": outline_result})

@app.route('/api/outline', methods=['GET'])
def get_outlines():
    """获取已生成的大纲列表"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, topic, created_at FROM outlines WHERE user_id = ? ORDER BY created_at DESC',
              (user_id,))
    outlines = c.fetchall()
    conn.close()
    
    result = []
    for o in outlines:
        result.append({
            "id": o[0],
            "title": o[1],
            "topic": o[2],
            "created_at": o[3]
        })
    
    return jsonify({"success": True, "outlines": result})

# ==================== 文献分析API ====================
@app.route('/api/analyze/documents', methods=['POST'])
def analyze_documents():
    """分析文献库，生成可视化分析"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json()
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    doc_ids = data.get('docIds', [])  # 选择的文献ID列表，为空则分析全部
    
    logger.info("文献分析请求: doc_ids=%s, ai_provider=%s", doc_ids, ai_provider)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 获取文献（根据选择的ID或全部）- 显示所有有内容的文献
    if doc_ids:
        placeholders = ','.join(['?'] * len(doc_ids))
        c.execute(f'SELECT id, title, content FROM documents WHERE content IS NOT NULL AND content != "" AND id IN ({placeholders})', 
                  doc_ids)
    else:
        c.execute('SELECT id, title, content FROM documents WHERE content IS NOT NULL AND content != ""')
    docs = c.fetchall()
    logger.info("查询到 %d 条文献", len(docs))
    
    # 获取所有知识库
    c.execute('SELECT category, title, tags FROM knowledge WHERE user_id = ?', (user_id,))
    knowledge = c.fetchall()
    
    # 获取所有新闻
    c.execute('SELECT title, source FROM news WHERE user_id = ?', (user_id,))
    news = c.fetchall()
    
    conn.close()
    
    if not docs:
        return jsonify({"success": False, "error": "请选择要分析的文献"}), 400
    
    # 构建分析内容
    doc_info = []
    for d in docs:
        doc_info.append({"id": d[0], "title": d[1], "content": d[2][:500] if d[2] else ""})
    
    doc_titles = [d['title'] for d in doc_info if d['title']]
    knowledge_summary = f"知识库共{len(knowledge)}条，其中分类分布："
    for cat in ['概念', '理论', '案例', '人物', '事件']:
        count = sum(1 for k in knowledge if k[0] == cat)
        if count:
            knowledge_summary += f"{cat}{count}条、"
    
    # 构建详细prompt
    docs_content = "\n\n".join([f"【文献{i+1}】{d['title']}\n{d['content']}" 
                                for i, d in enumerate(doc_info) if d['content']])
    
    prompt = f"""请对以下文献进行深度分析（共{len(docs)}篇）：

## 待分析文献：
{docs_content}

## 参考信息：
- 知识库：{knowledge_summary}
- 新闻动态：共{len(news)}条

请生成以下分析：
1. 文献概述：每篇文献的核心观点和研究结论
2. 主题提取：从文献中提取主要研究主题和关键词
3. 理论框架：识别文献使用的国际关系理论（现实主义、自由制度主义、建构主义等）
4. 研究方法：识别文献使用的研究方法（案例研究、比较研究、量化分析等）
5. 研究发现：总结文献的主要发现和贡献
6. 不足与展望：指出文献的局限性及未来研究方向
7. 与其他文献的关联：分析文献之间的关系和互补性

请用结构化格式输出，包含标题和清晰的层次结构。"""

    system_prompt = "你是一个学术文献分析专家，擅长提取研究主题、理论框架、研究方法，并进行对比分析。"
    analysis_result = call_ai(prompt, system_prompt, ai_provider)
    
    # 自动提取关键概念保存到知识库
    if analysis_result and len(analysis_result.strip()) > 100:
        try:
            extract_prompt = f"""从以下文献分析结果中提取关键概念和术语，格式要求：
- 每行一个概念，格式：概念名称 | 分类(概念/理论/人物/事件) | 简短解释

分析结果：
{analysis_result[:3000]}

请提取5-10个最重要的概念。"""

            extracted = call_ai(extract_prompt, "你是一个知识提取专家，擅长从文本中提取关键概念。", ai_provider)
            
            if extracted and not extracted.startswith("API"):
                conn = get_db_connection()
                c = conn.cursor()
                
                # 解析提取的概念并保存
                for line in extracted.strip().split('\n'):
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            title = parts[0].strip()
                            category = parts[1].strip()
                            content = parts[2].strip() if len(parts) > 2 else ""
                            
                            # 只保存概念和理论
                            if category in ['概念', '理论']:
                                c.execute('''INSERT INTO knowledge (category, title, content, tags, user_id)
                                            VALUES (?, ?, ?, ?, ?)''', 
                                          (category, title, content, "自动提取", user_id))
                conn.commit()
                conn.close()
                logger.info("自动提取并保存了关键概念")
        except Exception as e:
            logger.error("自动保存概念失败: %s", str(e))
    
    return jsonify({"success": True, "analysis": analysis_result, "docCount": len(docs)})

@app.route('/api/documents/list', methods=['GET'])
def list_documents_simple():
    """获取文献列表（用于选择）- 返回所有有内容的文献"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    logger.info("获取文献列表: user_id=%s", user_id)
    
    # 显示所有有内容的文献（不限制用户，方便分析共享文献）
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, username, created_at FROM documents WHERE content IS NOT NULL AND content != "" ORDER BY created_at DESC')
    docs = c.fetchall()
    conn.close()
    
    logger.info("查询到 %d 条文献", len(docs))
    result = [{"id": d[0], "title": d[1], "username": d[2], "created_at": d[3]} for d in docs]
    return jsonify({"success": True, "documents": result})

# ==================== 文献精读API ====================
@app.route('/api/analyze/document/<int:doc_id>', methods=['POST'])
def analyze_single_document(doc_id):
    """对单篇文献进行精读分析"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    try:
        data = request.get_json() or {}
        ai_provider = data.get('aiProvider', DEFAULT_AI)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT title, content, filepath, filetype FROM documents WHERE id = ?', (doc_id,))
        doc = c.fetchone()
        conn.close()
        
        if not doc:
            return jsonify({"success": False, "error": "文献不存在"}), 404
        
        title, content, filepath, filetype = doc
        logger.info("文献ID=%d, title=%s, filepath=%s, filetype=%s", doc_id, title, filepath, filetype)
        
        # 如果没有提取过内容，尝试从PDF提取
        extracted = False
        pdf_content = None
        if not content and filepath and filetype == 'pdf':
            # 尝试多个可能的路径
            possible_paths = [
                filepath,
                os.path.join(os.getcwd(), 'uploads', os.path.basename(filepath)),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', os.path.basename(filepath))
            ]
            
            for try_path in possible_paths:
                logger.info("尝试路径: %s", try_path)
                if os.path.exists(try_path):
                    try:
                        import pypdf
                        with open(try_path, 'rb') as f:
                            reader = pypdf.PdfReader(f)
                            full_text = ""
                            for page in reader.pages[:20]:
                                text = page.extract_text()
                                if text:
                                    full_text += text + "\n"
                            pdf_content = full_text[:15000]
                            logger.info("从PDF提取成功: %d 字符", len(pdf_content))
                            extracted = True
                            break
                    except Exception as e:
                        logger.error("PDF读取失败: %s, 错误: %s", try_path, str(e))
                        continue
            
            if not extracted:
                logger.error("所有尝试的PDF路径都无法读取")
                return jsonify({"success": False, "error": "无法读取PDF文件，请确认文件完整"}), 400
        
        # 使用提取的内容或已有内容
        content = pdf_content if pdf_content is not None else content
    
    except Exception as e:
        logger.error("获取文献失败: %s", str(e))
        return jsonify({"success": False, "error": f"获取文献失败: {str(e)}"}), 500

    try:
        # 检查内容
        if not content or not content.strip():
            logger.error("无法提取PDF内容，可能是扫描版图片PDF")
            return jsonify({"success": False, "error": "无法提取PDF内容。该PDF可能是扫描版图片格式，建议使用文字版PDF或先手动复制文字内容上传为txt文件"}), 400
        
        actual_content = content.strip()
        logger.info("文献内容长度: %d 字符", len(actual_content))
        
        # 精读分析
        prompt = f"""请对以下学术文献进行深度精读分析：

文献标题：{title}

文献内容：
{content[:12000]}

请生成以下分析：
1. 【文献摘要】用200字概括文章核心论点
2. 【研究问题】作者试图回答什么问题
3. 【理论框架】使用了什么国际关系理论（现实主义/自由制度主义/建构主义等）
4. 【研究方法】案例研究/比较研究/量化分析/文献综述
5. 【核心论点】作者的主要观点
6. 【重要发现】文章的关键发现或结论
7. 【学术贡献】对学科的贡献
8. 【研究不足】可能的局限性
9. 【关键词】3-5个核心关键词
10. 【适用场景】适合用于什么类型的研究或课程

请用清晰的Markdown格式输出。"""

        system_prompt = "你是一个学术论文精读专家，擅长快速把握论文核心观点、研究方法和学术价值。"
        ai_result = call_ai(prompt, system_prompt, ai_provider)
        
        # 处理返回值，可能是字典或字符串
        if isinstance(ai_result, dict):
            if 'error' in ai_result:
                logger.error("AI调用失败: %s", ai_result['error'])
                return jsonify({"success": False, "error": f"AI调用失败: {ai_result['error']}"}), 500
            analysis_result = ai_result.get('content', '')
        else:
            analysis_result = ai_result if isinstance(ai_result, str) else str(ai_result)
        
        if not analysis_result:
            return jsonify({"success": False, "error": "AI返回为空"}), 500
        
        # 自动保存核心概念到知识库
        if not analysis_result.startswith("API"):
            try:
                conn = get_db_connection()
                c = conn.cursor()
                
                # 提取关键词保存
                keyword_prompt = f"""从以下文献分析中提取关键词，格式要求：每行一个词，不要编号

分析结果：
{analysis_result[:2000]}"""

                keywords = call_ai(keyword_prompt, "你是一个关键词提取专家", ai_provider)
                
                if keywords and not keywords.startswith("API"):
                    # 提取摘要
                    import re
                    summary_match = re.search(r'【文献摘要】(.*?)(?=【|$)', analysis_result, re.DOTALL)
                    summary = summary_match.group(1).strip()[:300] if summary_match else ""
                    
                    # 保存为概念
                    c.execute('''INSERT INTO knowledge (category, title, content, tags, user_id)
                                VALUES (?, ?, ?, ?, ?)''',
                              (f"📖 {title}", title, summary, keywords.strip() + ",文献精读", user_id))
                    conn.commit()
                conn.close()
            except Exception as e:
                logger.error("保存精读概念失败: %s", str(e))
        
        return jsonify({"success": True, "analysis": analysis_result, "title": title})
    
    except Exception as e:
        logger.error("精读分析失败: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": f"分析失败: {str(e)}"}), 500


# ==================== 模型对比功能 ====================
@app.route('/api/analyze/compare', methods=['POST'])
def compare_models():
    """使用多个模型对比分析同一问题"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()
    selected_models = data.get('models', [])  # 选择的模型列表
    selected_docs = data.get('documents', [])  # 引用的文献ID
    
    if not topic:
        return jsonify({"success": False, "error": "请输入分析主题"}), 400
    
    if not selected_models:
        return jsonify({"success": False, "error": "请选择至少一个模型"}), 400
    
    # 获取选择的文献内容
    context = ""
    if selected_docs:
        conn = get_db_connection()
        c = conn.cursor()
        placeholders = ','.join(['?'] * len(selected_docs))
        c.execute(f'SELECT title, content FROM documents WHERE id IN ({placeholders})', selected_docs)
        docs = c.fetchall()
        conn.close()
        
        for doc in docs:
            if doc[1]:
                context += f"\n\n## 文献: {doc[0]}\n{doc[1][:3000]}\n"
    
    # 对每个模型进行分析
    results = []
    for model_id in selected_models:
        provider = AI_PROVIDERS.get(model_id)
        if not provider or not provider.get('api_key'):
            results.append({"model": model_id, "error": "模型未配置"})
            continue
        
        prompt = f"""请对以下国际关系主题进行深度分析：

主题：{topic}

{'参考上下文：' + context if context else ''}

请从以下角度进行分析：
1. 历史背景
2. 主要参与者
3. 利益分析
4. 趋势预测
5. 可能的影响

请用专业的学术风格回答，500字左右。"""
        
        result = call_ai(prompt, "你是一位资深的国际关系研究专家", model_id)
        
        # 处理返回结果
        if isinstance(result, dict) and 'error' in result:
            content = f"错误: {result['error']}"
        elif isinstance(result, dict):
            content = result.get('content', '')
        else:
            content = str(result) if result else "无结果"
        
        results.append({
            "model": model_id,
            "name": provider.get('name', model_id),
            "analysis": content
        })
    
    return jsonify({"success": True, "results": results, "topic": topic})


# ==================== 批量分析功能 ====================
@app.route('/api/analyze/batch', methods=['POST'])
def batch_analyze():
    """批量分析多篇文献"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json() or {}
    doc_ids = data.get('documentIds', [])
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    
    if not doc_ids:
        return jsonify({"success": False, "error": "请选择要分析的文献"}), 400
    
    # 获取文献
    conn = get_db_connection()
    c = conn.cursor()
    placeholders = ','.join(['?'] * len(doc_ids))
    c.execute(f'SELECT id, title, content FROM documents WHERE id IN ({placeholders})', doc_ids)
    docs = c.fetchall()
    conn.close()
    
    results = []
    for doc in docs:
        doc_id, title, content = doc
        if not content or len(content.strip()) < 50:
            results.append({"id": doc_id, "title": title, "status": "skip", "reason": "内容太少"})
            continue
        
        prompt = f"""请简要分析以下文献，100字以内：

标题：{title}
内容：{content[:2000]}

请给出：1.核心观点 2.研究方法"""
        
        result = call_ai(prompt, "你是一位学术文献分析专家", ai_provider)
        
        if isinstance(result, dict):
            analysis = result.get('content', result.get('error', '分析失败'))
        else:
            analysis = str(result) if result else "无结果"
        
        results.append({"id": doc_id, "title": title, "analysis": analysis, "status": "success"})
        
        # 保存分析结果到数据库
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''INSERT INTO analyses (user_id, topic, analysis_type, result, document_ids, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))''',
                      (user_id, title, '批量分析', analysis, str(doc_id)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("保存批量分析结果失败: %s", str(e))
    
    return jsonify({"success": True, "results": results})


# ==================== 文献自动摘要 ====================
@app.route('/api/documents/summarize/<int:doc_id>', methods=['POST'])
def summarize_document(doc_id):
    """自动生成文献摘要"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json() or {}
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT title, content, filepath, filetype FROM documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    conn.close()
    
    if not doc:
        return jsonify({"success": False, "error": "文献不存在"}), 404
    
    title, content, filepath, filetype = doc
    
    # 如果没有内容，尝试从PDF提取
    if not content and filepath and filetype == 'pdf':
        import os
        possible_paths = [
            filepath,
            os.path.join(os.getcwd(), 'uploads', os.path.basename(filepath)),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', os.path.basename(filepath))
        ]
        for try_path in possible_paths:
            if os.path.exists(try_path):
                try:
                    import pypdf
                    with open(try_path, 'rb') as f:
                        reader = pypdf.PdfReader(f)
                        full_text = ""
                        for page in reader.pages[:10]:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n"
                        content = full_text[:8000]
                except:
                    pass
                break
    
    if not content or len(content.strip()) < 50:
        return jsonify({"success": False, "error": "文献内容太少，无法生成摘要"}), 400
    
    prompt = f"""请为以下学术文献生成一个简洁的摘要，200字以内：

标题：{title}

内容：
{content[:5000]}

请按以下格式输出：
【摘要】：...
【关键词】：3-5个
【研究方法】：...
【核心结论】：..."""
    
    result = call_ai(prompt, "你是一位学术论文摘要专家", ai_provider)
    
    if isinstance(result, dict):
        summary = result.get('content', result.get('error', '生成失败'))
    else:
        summary = str(result) if result else "生成失败"
    
    # 保存摘要到数据库
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE documents SET content = ? WHERE id = ?', (content + f"\n\n===AI摘要===\n{summary}", doc_id))
        conn.commit()
        conn.close()
    except:
        pass
    
    return jsonify({"success": True, "summary": summary, "title": title})


# ==================== 批量导出报告 ====================
@app.route('/api/export/report', methods=['POST'])
def export_report():
    """导出分析报告为Markdown格式"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json() or {}
    analysis_ids = data.get('analysisIds', [])  # 要导出的分析ID
    doc_ids = data.get('documentIds', [])  # 要导出的文献ID
    export_type = data.get('type', 'analyses')  # analyses 或 documents
    
    report_content = f"""# 国际政治研判报告

生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
    
    if export_type == 'analyses':
        if not analysis_ids:
            return jsonify({"success": False, "error": "请选择要导出的分析"}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        placeholders = ','.join(['?'] * len(analysis_ids))
        c.execute(f'SELECT topic, analysis_type, result, created_at FROM analyses WHERE id IN ({placeholders})', analysis_ids)
        analyses = c.fetchall()
        conn.close()
        
        for a in analyses:
            report_content += f"""## {a[1]}: {a[0]}

**时间**: {a[3]}

{a[2]}

---

"""
    
    elif export_type == 'documents':
        if not doc_ids:
            return jsonify({"success": False, "error": "请选择要导出的文献"}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        placeholders = ','.join(['?'] * len(doc_ids))
        c.execute(f'SELECT title, content, username, created_at FROM documents WHERE id IN ({placeholders})', doc_ids)
        docs = c.fetchall()
        conn.close()
        
        for d in docs:
            report_content += f"""## {d[0]}

**上传者**: {d[2]} | **时间**: {d[3]}

{d[1][:5000] if d[1] else '(无内容)'}

---

"""
    
    return jsonify({"success": True, "report": report_content, "filename": f"研判报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"})


# ==================== 收藏/标注功能 ====================
@app.route('/api/favorites', methods=['GET', 'POST', 'DELETE'])
def favorites():
    """管理收藏的分析结果和文献"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if request.method == 'GET':
        # 获取收藏列表
        c.execute('SELECT id, item_type, item_id, title, note, created_at FROM favorites WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        favs = c.fetchall()
        conn.close()
        
        result = [{"id": f[0], "type": f[1], "itemId": f[2], "title": f[3], "note": f[4], "createdAt": f[5]} for f in favs]
        return jsonify({"success": True, "favorites": result})
    
    elif request.method == 'POST':
        # 添加收藏
        data = request.get_json() or {}
        item_type = data.get('itemType', 'analysis')  # analysis 或 document
        item_id = data.get('itemId')
        title = data.get('title', '')
        note = data.get('note', '')
        
        if not item_id:
            return jsonify({"success": False, "error": "请指定要收藏的项目"}), 400
        
        # 检查是否已收藏
        c.execute('SELECT id FROM favorites WHERE user_id = ? AND item_type = ? AND item_id = ?', 
                  (user_id, item_type, item_id))
        if c.fetchone():
            conn.close()
            return jsonify({"success": False, "error": "已经收藏过该项目"}), 400
        
        c.execute('INSERT INTO favorites (user_id, item_type, item_id, title, note, created_at) VALUES (?, ?, ?, ?, ?, datetime("now"))',
                  (user_id, item_type, item_id, title, note))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "收藏成功"})
    
    elif request.method == 'DELETE':
        # 删除收藏
        fav_id = request.args.get('id', type=int)
        if not fav_id:
            return jsonify({"success": False, "error": "请指定要删除的收藏"}), 400
        
        c.execute('DELETE FROM favorites WHERE id = ? AND user_id = ?', (fav_id, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "取消收藏成功"})


@app.route('/api/favorites/<int:fav_id>', methods=['PUT'])
def update_favorite(fav_id):
    """更新收藏备注"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json() or {}
    note = data.get('note', '')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE favorites SET note = ? WHERE id = ? AND user_id = ?', (note, fav_id, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "更新成功"})


# ==================== 热点追踪功能 ====================
@app.route('/api/trends/track', methods=['POST'])
def track_trends():
    """追踪特定主题的最新动态"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    data = request.get_json() or {}
    topics = data.get('topics', [])  # 追踪的主题列表
    ai_provider = data.get('aiProvider', DEFAULT_AI)
    
    if not topics:
        return jsonify({"success": False, "error": "请指定要追踪的主题"}), 400
    
    results = []
    for topic in topics:
        # 使用AI搜索最新动态 - 更强调最新信息
        prompt = f"""你是一位专业的国际新闻分析专家。请搜索并分析以下主题的**最新动态**（2025年至今）：

主题：{topic}

重要要求：
1. 必须搜索2025年1月到2026年4月的最新事件和新闻
2. 如果没有最新信息，请明确说明
3. 请列出：
   - 最新事件（3-5条，必须是2025年后的）
   - 各方反应
   - 未来趋势预测

请用中文回答，简洁明了。如果无法获取最新信息，请直接说明"无法获取最新信息"。"""

        result = call_ai(prompt, "你是一位实时国际新闻分析专家，关注最新发生的事件和动态", ai_provider)
        
        if isinstance(result, dict):
            content = result.get('content', result.get('error', '搜索失败'))
        else:
            content = str(result) if result else "无结果"
        
        results.append({"topic": topic, "analysis": content})
        
        # 保存到追踪历史
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''INSERT INTO trends (user_id, topic, analysis, created_at)
                        VALUES (?, ?, ?, datetime('now'))''',
                      (user_id, topic, content))
            conn.commit()
            conn.close()
        except:
            pass
    
    return jsonify({"success": True, "results": results})


@app.route('/api/trends/history', methods=['GET'])
def trends_history():
    """获取追踪历史"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "请先登录"}), 401
    
    topic = request.args.get('topic', '')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if topic:
        c.execute('SELECT topic, analysis, created_at FROM trends WHERE user_id = ? AND topic LIKE ? ORDER BY created_at DESC', 
                  (user_id, f'%{topic}%'))
    else:
        c.execute('SELECT topic, analysis, created_at FROM trends WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    
    history = c.fetchall()
    conn.close()
    
    result = [{"topic": h[0], "analysis": h[1], "createdAt": h[2]} for h in history]
    return jsonify({"success": True, "history": result})


# ==================== 初始化新表 ====================
def init_extra_tables():
    """初始化额外的数据库表"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 收藏表
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        item_type TEXT NOT NULL,
        item_id INTEGER NOT NULL,
        title TEXT,
        note TEXT,
        created_at TEXT
    )''')
    
    # 趋势追踪表
    c.execute('''CREATE TABLE IF NOT EXISTS trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        analysis TEXT,
        created_at TEXT
    )''')
    
    conn.commit()
    conn.close()


# 启动应用
if __name__ == '__main__':
    init_db()
    init_extra_tables()  # 初始化新表
    print("=" * 50)
    print("IRPredict 国际政治研判系统")
    print("=" * 50)
    print("本地服务已启动：http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)