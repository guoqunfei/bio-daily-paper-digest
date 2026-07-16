// Cloudflare Worker: 零操作文献反馈接收器
// 部署步骤：
// 1. 注册 Cloudflare (cloudflare.com) → Workers & Pages → Create a Service
// 2. 粘贴此代码
// 3. Settings → Variables → Add:
//    GITHUB_TOKEN = 你的 GitHub Personal Access Token (repo scope)
//    REPO_OWNER   = guoqunfei
//    REPO_NAME    = bio-daily-paper-digest
// 4. 保存，获得 Worker URL (如 https://bio-digest.yourname.workers.dev)
// 5. 将 URL 填入仓库 Secrets: FEEDBACK_WORKER_URL

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const action = url.searchParams.get('action');
    const paper = url.searchParams.get('paper');
    const user = url.searchParams.get('user');
    const origin = request.headers.get('Origin') || '*';

    // CORS 头
    const corsHeaders = {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    if (!action || !paper || !user) {
      return new Response('❌ 参数缺失：需要 action, paper, user', {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }

    if (!env.GITHUB_TOKEN || !env.REPO_OWNER || !env.REPO_NAME) {
      return new Response('❌ Worker 环境变量未配置', {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }

    const validActions = ['STAR', 'FOLLOW_UP', 'IGNORE'];
    const actionUpper = action.toUpperCase();
    if (!validActions.includes(actionUpper)) {
      return new Response('❌ 无效操作：仅支持 STAR, FOLLOW_UP, IGNORE', {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }

    try {
      // 调用 GitHub API 创建 Issue
      const issueUrl = `https://api.github.com/repos/${env.REPO_OWNER}/${env.REPO_NAME}/issues`;
      const response = await fetch(issueUrl, {
        method: 'POST',
        headers: {
          'Authorization': `token ${env.GITHUB_TOKEN}`,
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json',
          'User-Agent': 'BioDigest-Worker'
        },
        body: JSON.stringify({
          title: `[${actionUpper}] ${decodeURIComponent(paper)}`,
          body: `用户: ${decodeURIComponent(user)}\n操作: ${actionUpper}\n时间: ${new Date().toISOString()}\n\n---\n由 Cloudflare Worker 自动记录`,
          labels: ['feedback']
        })
      });

      if (!response.ok) {
        const error = await response.text();
        return new Response(`❌ GitHub API 错误: ${response.status}\n${error}`, {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'text/plain; charset=utf-8' }
        });
      }

      const result = await response.json();

      // 返回成功页面（HTML）
      const html = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>✅ 反馈已记录</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;max-width:600px;margin:60px auto;padding:20px;text-align:center;background:#f0fdf4;}
.card{background:#fff;border-radius:16px;padding:40px;box-shadow:0 4px 6px rgba(0,0,0,0.05);}
h1{color:#059669;font-size:28px;margin-bottom:8px;} 
p{color:#374151;font-size:16px;line-height:1.6;}
.badge{display:inline-block;background:#d1fae5;color:#059669;padding:8px 16px;border-radius:20px;font-size:14px;font-weight:600;margin:16px 0;}
.meta{color:#6b7280;font-size:13px;margin-top:24px;}
a{color:#2563eb;text-decoration:none;}
</style>
</head>
<body>
<div class="card">
<h1>✅ 反馈已记录</h1>
<div class="badge">${actionUpper}</div>
<p>文献: <strong>${decodeURIComponent(paper).substring(0, 60)}${decodeURIComponent(paper).length > 60 ? '...' : ''}</strong></p>
<p>用户: ${decodeURIComponent(user)}</p>
<p class="meta">该反馈将在明日文献推送中生效<br>您可以关闭此页面</p>
<p class="meta"><a href="https://github.com/${env.REPO_OWNER}/${env.REPO_NAME}/issues">查看所有反馈记录 →</a></p>
</div>
</body>
</html>`;

      return new Response(html, {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'text/html; charset=utf-8' }
      });

    } catch (e) {
      return new Response(`❌ 服务器错误: ${e.message}`, {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }
  }
};
