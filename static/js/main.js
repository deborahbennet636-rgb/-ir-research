// 国际关系研判系统 - 前端交互逻辑（多用户版）

class IRResearchSystem {
    constructor() {
        this.currentView = 'research';
        this.analysisType = 'general';
        this.documents = [];
        this.currentUser = null;
        this.isLoggedIn = false;
        
        this.init();
    }

    init() {
        this.initLogin();
        this.initNavigation();
        this.initUpload();
        this.initAnalysis();
        this.initChat();
        this.checkLoginStatus();
    }

    // 登录系统
    initLogin() {
        const modal = document.getElementById('login-modal');
        const loginBtn = document.getElementById('login-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const usernameInput = document.getElementById('login-username');
        const nameInput = document.getElementById('login-name');

        loginBtn.addEventListener('click', () => this.login());
        
        [usernameInput, nameInput].forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.login();
            });
        });

        logoutBtn.addEventListener('click', () => this.logout());
    }

    async login() {
        const username = document.getElementById('login-username').value.trim();
        const name = document.getElementById('login-name').value.trim() || username;

        if (!username) {
            alert('请输入用户名');
            return;
        }

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, name})
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentUser = data;
                this.isLoggedIn = true;
                document.getElementById('login-modal').classList.remove('show');
                this.updateUserUI();
                this.loadDocuments();
                this.updateStats();
            } else {
                alert(data.error || '登录失败');
            }
        } catch (error) {
            alert('登录出错: ' + error.message);
        }
    }

    async logout() {
        try {
            await fetch('/api/logout', {method: 'POST'});
            this.currentUser = null;
            this.isLoggedIn = false;
            document.getElementById('login-modal').classList.add('show');
            this.updateUserUI();
        } catch (error) {
            console.error('登出失败:', error);
        }
    }

    async checkLoginStatus() {
        try {
            const response = await fetch('/api/user_info');
            const data = await response.json();
            
            if (data.logged_in) {
                this.currentUser = data;
                this.isLoggedIn = true;
                this.updateUserUI();
                this.loadDocuments();
                this.updateStats();
            } else {
                document.getElementById('login-modal').classList.add('show');
            }
        } catch (error) {
            console.error('检查登录状态失败:', error);
            document.getElementById('login-modal').classList.add('show');
        }
    }

    updateUserUI() {
        const userInfo = document.getElementById('user-info');
        const logoutBtn = document.getElementById('logout-btn');
        const contributorsPanel = document.getElementById('contributors-panel');
        
        if (this.isLoggedIn && this.currentUser) {
            document.getElementById('login-modal').classList.remove('show');
            userInfo.style.display = 'flex';
            logoutBtn.style.display = 'block';
            document.getElementById('current-user-name').textContent = this.currentUser.name;
            
            // 显示贡献者列表
            if (this.currentUser.users_count > 0) {
                contributorsPanel.style.display = 'block';
                this.updateContributors();
            }
        } else {
            userInfo.style.display = 'none';
            logoutBtn.style.display = 'none';
            contributorsPanel.style.display = 'none';
        }
    }

    async updateContributors() {
        try {
            const response = await fetch('/api/user_info');
            const data = await response.json();
            
            if (data.users_list) {
                const list = document.getElementById('contributors-list');
                list.innerHTML = data.users_list.map(user => `
                    <div class="contributor-item">
                        <span class="contributor-icon">👤</span>
                        <span>${user.name}</span>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('获取贡献者失败:', error);
        }
    }

    // 导航切换
    initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');
                const viewName = item.dataset.view;
                this.switchView(viewName);
            });
        });
    }

    switchView(viewName) {
        const views = document.querySelectorAll('.view');
        views.forEach(view => view.classList.remove('active'));
        const targetView = document.getElementById(`view-${viewName}`);
        if (targetView) {
            targetView.classList.add('active');
            this.currentView = viewName;
        }
    }

    // 文件上传
    initUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');
        const uploadProgress = document.getElementById('upload-progress');

        uploadBtn.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                this.uploadFiles(e.dataTransfer.files);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.uploadFiles(e.target.files);
            }
        });

        const resetBtn = document.getElementById('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (confirm('确定要重置知识库吗？这将删除所有已上传的文档。')) {
                    this.resetKnowledgeBase();
                }
            });
        }
    }

    async uploadFiles(files) {
        if (!this.isLoggedIn) {
            alert('请先登录');
            document.getElementById('login-modal').classList.add('show');
            return;
        }

        const uploadProgress = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');

        uploadProgress.style.display = 'block';
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);

            progressText.textContent = `正在上传 ${file.name}...`;
            progressFill.style.width = `${((i + 1) / files.length) * 100}%`;

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                if (!data.success) {
                    alert(`上传失败: ${data.error}`);
                }
            } catch (error) {
                alert(`上传出错: ${error.message}`);
            }
        }

        setTimeout(() => {
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0';
            this.loadDocuments();
            this.updateStats();
        }, 500);
    }

    async loadDocuments() {
        try {
            const response = await fetch('/api/documents');
            const data = await response.json();
            this.documents = data.documents || [];
            this.renderDocuments();
        } catch (error) {
            console.error('加载文档失败:', error);
        }
    }

    renderDocuments() {
        const container = document.getElementById('documents-table');
        const resetBtn = document.getElementById('reset-btn');

        if (this.documents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无文档，请先上传文献资料</p>
                </div>
            `;
            resetBtn.style.display = 'none';
            return;
        }

        resetBtn.style.display = this.currentUser?.is_admin ? 'block' : 'none';

        container.innerHTML = this.documents.map(doc => `
            <div class="doc-item">
                <div class="doc-info">
                    <span class="doc-icon">📄</span>
                    <div>
                        <div class="doc-name">${doc.filename}</div>
                        <div class="doc-meta">上传者: ${doc.uploader_name || doc.uploader} · ${doc.upload_time} · ${doc.chunk_count}个片段</div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async updateStats() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            document.getElementById('doc-count').textContent = data.documents_count || 0;
            
            const docResponse = await fetch('/api/documents');
            const docData = await docResponse.json();
            document.getElementById('chunk-count').textContent = docData.total_chunks || 0;
        } catch (error) {
            console.error('更新统计失败:', error);
        }
    }

    async resetKnowledgeBase() {
        if (!this.currentUser?.is_admin) {
            alert('只有管理员可以重置知识库');
            return;
        }

        try {
            const response = await fetch('/api/reset', {method: 'POST'});
            const data = await response.json();
            
            if (data.success) {
                alert('知识库已重置');
                this.loadDocuments();
                this.updateStats();
            }
        } catch (error) {
            alert(`重置失败: ${error.message}`);
        }
    }

    // 分析功能
    initAnalysis() {
        const typeBtns = document.querySelectorAll('.type-btn');
        const analyzeBtn = document.getElementById('analyze-btn');
        const clearBtn = document.getElementById('clear-btn');

        typeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                typeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.analysisType = btn.dataset.type;
            });
        });

        // 快捷主题标签点击事件
        document.querySelectorAll('.suggestion-tag').forEach(tag => {
            tag.addEventListener('click', () => {
                document.getElementById('topic-input').value = tag.dataset.topic;
            });
        });

        analyzeBtn.addEventListener('click', () => this.performAnalysis());
        clearBtn.addEventListener('click', () => {
            document.getElementById('result-placeholder').style.display = 'block';
            document.getElementById('result-content').style.display = 'none';
        });
    }

    async performAnalysis() {
        const topic = document.getElementById('topic-input').value.trim();
        
        if (!topic) {
            alert('请输入分析主题');
            return;
        }

        const useWeb = document.getElementById('use-web').checked;
        const useKnowledge = document.getElementById('use-knowledge').checked;

        if (!useWeb && !useKnowledge) {
            alert('请至少选择一个数据来源');
            return;
        }

        document.getElementById('result-placeholder').style.display = 'none';
        document.getElementById('result-content').style.display = 'none';
        document.getElementById('loading').style.display = 'block';

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    topic: topic,
                    type: this.analysisType,
                    use_web: useWeb
                })
            });

            const data = await response.json();
            document.getElementById('loading').style.display = 'none';

            if (!data.success) {
                alert(`分析失败: ${data.error}`);
                document.getElementById('result-placeholder').style.display = 'block';
                return;
            }

            // 显示来源类型标签
            let sourceTag = '';
            if (data.source_type === 'web') {
                sourceTag = '<span class="source-tag web">🌐 来源：网络搜索</span>';
            } else {
                sourceTag = '<span class="source-tag knowledge_base">📚 来源：知识库</span>';
            }

            document.getElementById('analysis-result').innerHTML = sourceTag + '<br><br>' + data.analysis;
            
            // 如果有网络来源，显示搜索结果
            if (data.sources && data.sources.length > 0) {
                const sourcesList = document.getElementById('sources-list');
                sourcesList.innerHTML = '<h3>📑 参考来源</h3>' + 
                    data.sources.map(s => `
                        <div class="search-result-item">
                            <a href="${s.url}" target="_blank">${s.title}</a>
                        </div>
                    `).join('');
            } else {
                document.getElementById('sources-list').innerHTML = '';
            }
            
            document.getElementById('result-content').style.display = 'block';

        } catch (error) {
            document.getElementById('loading').style.display = 'none';
            alert(`分析出错: ${error.message}`);
            document.getElementById('result-placeholder').style.display = 'block';
        }
    }

    // 对话功能
    initChat() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');

        const sendMessage = () => {
            const message = chatInput.value.trim();
            if (!message) return;
            this.sendChatMessage(message);
        };

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    async sendChatMessage(message) {
        const chatMessages = document.getElementById('chat-messages');
        
        const userMessage = document.createElement('div');
        userMessage.className = 'chat-message user';
        userMessage.innerHTML = `<div class="message-bubble">${this.escapeHtml(message)}</div>`;
        
        const placeholder = chatMessages.querySelector('.chat-placeholder');
        if (placeholder) placeholder.remove();
        
        chatMessages.appendChild(userMessage);
        document.getElementById('chat-input').value = '';

        const aiMessage = document.createElement('div');
        aiMessage.className = 'chat-message ai';
        aiMessage.innerHTML = '<div class="message-bubble">正在思考...</div>';
        chatMessages.appendChild(aiMessage);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message})
            });

            const data = await response.json();

            if (!data.success) {
                aiMessage.querySelector('.message-bubble').textContent = `错误: ${data.error}`;
                return;
            }

            aiMessage.querySelector('.message-bubble').textContent = data.answer;

            if (data.sources && data.sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.style.marginTop = '10px';
                sourcesDiv.style.fontSize = '12px';
                sourcesDiv.style.color = 'var(--text-secondary)';
                sourcesDiv.innerHTML = '<strong>参考来源:</strong><br>' + 
                    data.sources.map(s => `• ${s.content.substring(0, 100)}...`).join('<br>');
                aiMessage.querySelector('.message-bubble').appendChild(sourcesDiv);
            }

        } catch (error) {
            aiMessage.querySelector('.message-bubble').textContent = `出错: ${error.message}`;
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new IRResearchSystem();
});
