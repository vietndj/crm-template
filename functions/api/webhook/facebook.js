export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const mode = url.searchParams.get('hub.mode');
  const token = url.searchParams.get('hub.verify_token');
  const challenge = url.searchParams.get('hub.challenge');

  const verifyToken = env.FB_VERIFY_TOKEN || 'crm_fb_verify_token';

  if (mode === 'subscribe' && token === verifyToken) {
    return new Response(challenge, { status: 200 });
  } else {
    return new Response('Forbidden', { status: 403 });
  }
}

export async function onRequestPost({ request, env }) {
  try {
    const body = await request.json();

    if (body.object !== 'page') {
      return new Response('Not Found', { status: 404 });
    }

    const now = new Date().toISOString();

    for (const entry of body.entry || []) {
      for (const change of entry.changes || []) {
        if (change.field === 'leadgen') {
          const leadInfo = change.value;
          const id = crypto.randomUUID();
          
          await env.DB.prepare(`
            INSERT INTO leads (id, source, status, created_at, updated_at, custom_fields) 
            VALUES (?, 'facebook', 'new', ?, ?, ?)
          `).bind(
            id, 
            now, 
            now, 
            JSON.stringify({ fb_lead_id: leadInfo.leadgen_id })
          ).run();
        }
      }
    }

    return new Response('EVENT_RECEIVED', { status: 200 });
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), { status: 500 });
  }
}
