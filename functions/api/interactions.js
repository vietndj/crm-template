export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const lead_id = url.searchParams.get('lead_id');
  const limit = parseInt(url.searchParams.get('limit')) || 50;

  if (!lead_id) {
    return new Response(JSON.stringify({ success: false, error: 'lead_id is required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const { results } = await env.DB.prepare(
      'SELECT * FROM interactions WHERE lead_id = ? ORDER BY created_at DESC LIMIT ?'
    ).bind(lead_id, limit).all();

    return new Response(JSON.stringify({ success: true, data: results }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

export async function onRequestPost({ request, env }) {
  try {
    const data = await request.json();
    const { lead_id, type, direction, content, duration, metadata } = data;

    if (!lead_id || !type || !content) {
      return new Response(JSON.stringify({ success: false, error: 'lead_id, type, and content are required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    const query = `
      INSERT INTO interactions (id, lead_id, type, direction, content, duration, metadata, created_by, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING *
    `;

    const result = await env.DB.prepare(query).bind(
      id,
      lead_id,
      type,
      direction || 'outbound',
      content,
      duration || null,
      metadata ? JSON.stringify(metadata) : null,
      'system',
      now
    ).first();

    return new Response(JSON.stringify({ success: true, data: result }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
