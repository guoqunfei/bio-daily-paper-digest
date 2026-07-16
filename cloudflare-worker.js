/**
 * Cloudflare Worker - Zero-ops trigger endpoint for Bio Daily Paper Digest
 * Cloudflare Worker 无服务器端点：支持 Webhook 触发、健康检查、状态查询
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // Health check
    if (path === '/health' || path === '/') {
      return new Response(JSON.stringify({
        status: 'ok',
        service: 'bio-daily-paper-digest',
        version: 'v6',
        timestamp: new Date().toISOString()
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // Trigger daily digest via GitHub Actions
    if (path === '/trigger/daily') {
      const authHeader = request.headers.get('Authorization');
      const expectedToken = env.TRIGGER_TOKEN;

      if (expectedToken && authHeader !== `Bearer ${expectedToken}`) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      try {
        // Trigger GitHub Actions workflow_dispatch
        const githubToken = env.GITHUB_TOKEN;
        const repo = env.GITHUB_REPO || 'guoqunfei/bio-daily-paper-digest';

        if (!githubToken) {
          return new Response(JSON.stringify({ error: 'GitHub token not configured' }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }

        const response = await fetch(
          `https://api.github.com/repos/${repo}/actions/workflows/daily-digest.yml/dispatches`,
          {
            method: 'POST',
            headers: {
              'Authorization': `token ${githubToken}`,
              'Accept': 'application/vnd.github.v3+json',
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ref: 'main' })
          }
        );

        if (response.ok) {
          return new Response(JSON.stringify({
            status: 'triggered',
            message: 'Daily digest workflow dispatched',
            timestamp: new Date().toISOString()
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } else {
          const error = await response.text();
          return new Response(JSON.stringify({ error: `GitHub API error: ${error}` }), {
            status: 502,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }
    }

    // Get latest digest status
    if (path === '/status') {
      return new Response(JSON.stringify({
        status: 'active',
        last_check: new Date().toISOString(),
        endpoints: [
          '/health',
          '/trigger/daily',
          '/status'
        ]
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
};
