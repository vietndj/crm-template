export async function onRequestGet({ request, env, params }) {
  const { id } = params;
  try {
    const lead = await env.DB.prepare('SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL').bind(id).first();
    
    if (!lead) {
      return new Response(JSON.stringify({ success: false, error: 'Lead not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const interactions = await env.DB.prepare(
      'SELECT * FROM interactions WHERE lead_id = ? ORDER BY created_at DESC LIMIT 50'
    ).bind(id).all();

    lead.interactions = interactions.results;

    return new Response(JSON.stringify({ success: true, data: lead }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

export async function onRequestPut({ request, env, params }) {
  const { id } = params;
  try {
    const data = await request.json();
    const now = new Date().toISOString();
    
    // Check if exists
    const existing = await env.DB.prepare('SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL').bind(id).first();
    if (!existing) {
      return new Response(JSON.stringify({ success: false, error: 'Lead not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Build update query
    let updates = [];
    let values = [];
    for (const [key, value] of Object.entries(data)) {
      if (['id', 'created_at', 'deleted_at'].includes(key)) continue;
      updates.push(`${key} = ?`);
      // handle JSON fields
      if (['notes', 'tags', 'custom_fields'].includes(key) && value !== null) {
        values.push(JSON.stringify(value));
      } else {
        values.push(value);
      }
    }

    if (updates.length === 0) {
      return new Response(JSON.stringify({ success: true, data: existing }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    updates.push('updated_at = ?');
    values.push(now);
    values.push(id);

    const query = `UPDATE leads SET ${updates.join(', ')} WHERE id = ? RETURNING *`;
    const result = await env.DB.prepare(query).bind(...values).first();

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

export async function onRequestDelete({ request, env, params }) {
  const { id } = params;
  try {
    const now = new Date().toISOString();
    await env.DB.prepare('UPDATE leads SET deleted_at = ?, updated_at = ? WHERE id = ?').bind(now, now, id).run();
    return new Response(JSON.stringify({ success: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
