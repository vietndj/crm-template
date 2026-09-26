export async function onRequestGet({ request, env }) {
  try {
    const { results } = await env.DB.prepare('SELECT * FROM config').all();
    const configMap = results.reduce((acc, row) => {
      acc[row.key] = row.value;
      return acc;
    }, {});

    return new Response(JSON.stringify({ success: true, data: configMap }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

export async function onRequestPut({ request, env }) {
  try {
    const { key, value } = await request.json();
    if (!key) {
      return new Response(JSON.stringify({ success: false, error: 'Key is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const now = new Date().toISOString();
    
    // UPSERT
    const query = `
      INSERT INTO config (key, value, updated_at) 
      VALUES (?, ?, ?) 
      ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    `;
    
    await env.DB.prepare(query).bind(key, String(value), now).run();

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
