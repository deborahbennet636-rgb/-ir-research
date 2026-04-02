/**
 * IRPredict 云函数 - 文档管理模块
 * 处理文档上传、文本提取、查询
 */
const cloud = require('wx-server-sdk')
const axios = require('axios')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

// 硅基流动API配置
const SILICON_API_KEY = 'sk-qxabzdrpzcjuhsjcwoxzadtkeboffmqfnqrqiywxqwbsgcrq'

// 系统提示词
const SYSTEM_PROMPTS = {
  general: `你是一位专业的国际关系研究员。擅长分析国家间的政治、经济、外交关系。
请基于提供的资料或知识，进行客观、专业、有深度的分析。
分析结构：1.背景概述 2.各方立场 3.影响因素 4.未来展望`,
  
  history: `你是一位历史学家，擅长分析国际事件的历史背景和演变进程。
请详细分析指定主题的历史渊源、发展脉络和重要节点。`,
  
  actors: `你是一位国际关系专家，擅长分析国际事件中的各方参与者。
请分析各方的利益诉求、立场态度、实力对比和互动关系。`,
  
  counterterror: `你是一位反恐研究专家，擅长分析国际反恐合作、国家安全战略。
请从全球反恐形势、双多边合作、情报共享、法律框架等角度进行分析。`,
  
  security: `你是一位国家安全专家，擅长分析传统安全与非传统安全威胁。
请分析安全挑战的来源、影响及应对策略。`
}

// 调用硅基流动API
async function callSiliconFlow(messages, model = 'deepseek-ai/DeepSeek-V3') {
  try {
    const response = await axios.post(
      'https://api.siliconflow.cn/v1/chat/completions',
      {
        model: model,
        messages: messages,
        temperature: 0.7,
        max_tokens: 3000,
        stream: false
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${SILICON_API_KEY}`
        },
        timeout: 60000
      }
    )
    return response.data.choices[0].message.content
  } catch (error) {
    console.error('API调用错误:', error.message)
    throw new Error(`AI服务调用失败: ${error.message}`)
  }
}

// 1. 获取文档列表
async function getDocuments() {
  const result = await db.collection('documents')
    .orderBy('createdAt', 'desc')
    .get()
  return result.data
}

// 2. 上传文档（添加文献记录）
async function addDocument(data) {
  const result = await db.collection('documents').add({
    data: {
      title: data.title || data.fileName,
      fileName: data.fileName,
      fileUrl: data.fileUrl || '',
      fileType: data.fileType || 'txt',
      content: data.content || '',
      uploadUser: data.openid,
      uploadUserName: data.uploadUserName || '用户',
      tags: data.tags || [],
      createdAt: new Date()
    }
  })
  return result
}

// 3. AI分析
async function analyzeWithAI(topic, analysisType, contextDocs, openid) {
  // 构建上下文
  let context = ''
  if (contextDocs && contextDocs.length > 0) {
    context = '\n\n## 参考文献内容：\n'
    contextDocs.forEach((doc, i) => {
      context += `\n【文档${i+1}】${doc.title}\n${doc.content.substring(0, 2000)}\n`
    })
  }
  
  const systemPrompt = SYSTEM_PROMPTS[analysisType] || SYSTEM_PROMPTS.general
  const userPrompt = `请对以下国际关系主题进行${analysisType}分析：\n主题：${topic}${context}
  
要求：
1. 基于提供的参考文献（如有）进行分析
2. 基于国际关系理论分析
3. 客观中立、有理有据、结构清晰
4. 如涉及反恐、国家安全，请从专业角度分析`

  const result = await callSiliconFlow([
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt }
  ])
  
  // 保存分析记录
  await db.collection('analyses').add({
    data: {
      topic: topic,
      analysisType: analysisType,
      result: result,
      userId: openid,
      referencedDocs: contextDocs ? contextDocs.map(d => d._id) : [],
      createdAt: new Date()
    }
  })
  
  return result
}

// 主入口
exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext()
  const openid = wxContext.OPENID
  const action = event.action
  
  try {
    switch (action) {
      case 'getDocuments':
        return { success: true, data: await getDocuments() }
        
      case 'addDocument':
        const docData = {
          ...event.data,
          openid: openid,
          uploadUserName: event.userName || '用户'
        }
        return { success: true, data: await addDocument(docData) }
        
      case 'analyze':
        // 获取相关文档
        const docs = await getDocuments()
        const analysisResult = await analyzeWithAI(
          event.topic,
          event.analysisType || 'general',
          docs,
          openid
        )
        return { success: true, result: analysisResult }
        
      case 'getOpenid':
        return { success: true, openid: openid }
        
      default:
        return { success: false, error: '未知操作' }
    }
  } catch (error) {
    console.error('Error:', error)
    return { success: false, error: error.message }
  }
}