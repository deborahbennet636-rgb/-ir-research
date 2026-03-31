// 国际关系研判系统 - HTTP 云函数

const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

// AI 配置 - 硅基流动
const API_KEY = process.env.SILICONFLOW_API_KEY || ''

const systemPrompts = {
  general: `你是一个专业的国际关系分析师。你的职责是：
1. 分析国际事件/主题背后的深层原因
2. 预测未来发展趋势
3. 评估各方立场和利益诉求
4. 提供专业的政策建议

请用专业、客观的语气进行分析。`,
  
  trend: `你是一个国际关系趋势预测专家。你的职责是：
1. 分析国际事件的发展趋势
2. 预测各方的下一步行动
3. 评估潜在风险和机遇

请基于历史数据和当前形势进行客观分析。`,
  
  stakeholder: `你是一个国际关系利益分析专家。你的职责是：
1. 识别事件中的各方利益相关者
2. 分析各方的立场、诉求和底线
3. 评估各方的影响力

请客观分析各方的动机和行为逻辑。`,
  
  policy: `你是一个国际政策分析师。你的职责是：
1. 解读相关国家的外交政策
2. 分析政策背后的逻辑
3. 评估政策的影响

请用专业的政策分析视角进行解读。`
}

exports.main = async (event, context) => {
  // HTTP 触发时，event 包含请求信息
  const { httpMethod, body } = event
  
  // CORS 头
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  }
  
  // 处理 OPTIONS 预检请求
  if (httpMethod === 'OPTIONS') {
    return {
      statusCode: 204,
      headers: corsHeaders,
      body: ''
    }
  }
  
  // 解析请求体 - 支持 HTTP 调用和云函数直接调用
  let requestBody = {}
  if (httpMethod) {
    // HTTP 调用
    try {
      requestBody = body ? JSON.parse(body) : {}
    } catch (e) {
      requestBody = {}
    }
  } else {
    // 直接调用（云函数 invoke）
    requestBody = event
  }
  
  const { action, topic, analysisType = 'general' } = requestBody
  
  // 分析接口
  if (action === 'analyze' || httpMethod === 'POST') {
    if (!topic) {
      return {
        statusCode: 400,
        headers: corsHeaders,
        body: JSON.stringify({ success: false, error: '请提供分析主题' })
      }
    }
    
    const userPrompt = `请对以下国际关系主题进行${analysisType}分析：

主题：${topic}

请提供详细、专业、有深度的分析。`
    
    try {
      const https = require('https')
      
      const postData = JSON.stringify({
        model: 'deepseek-ai/DeepSeek-V3',
        messages: [
          { role: 'system', content: systemPrompts[analysisType] || systemPrompts.general },
          { role: 'user', content: userPrompt }
        ],
        temperature: 0.7,
        max_tokens: 2000
      })
      
      const options = {
        hostname: 'api.siliconflow.cn',
        path: '/v1/chat/completions',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Length': Buffer.byteLength(postData)
        }
      }
      
      const result = await new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
          let data = ''
          res.on('data', (chunk) => data += chunk)
          res.on('end', () => resolve(data))
        })
        req.on('error', reject)
        req.write(postData)
        req.end()
      })
      
      const data = JSON.parse(result)
      
      if (data.error) {
        return {
          statusCode: 500,
          headers: corsHeaders,
          body: JSON.stringify({ success: false, error: data.error.message })
        }
      }
      
      return {
        statusCode: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          success: true,
          topic,
          analysisType,
          analysis: data.choices[0].message.content
        })
      }
    } catch (err) {
      return {
        statusCode: 500,
        headers: corsHeaders,
        body: JSON.stringify({ success: false, error: err.message })
      }
    }
  }
  
  // 健康检查
  return {
    statusCode: 200,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify({ success: true, status: 'ok' })
  }
}
