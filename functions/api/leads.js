export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const page = parseInt(url.searchParams.get('page')) || 1;
  const limit = parseInt(url.searchParams.get('limit')) || 20;
  const search = url.searchParams.get('q') || '';
  const status = url.searchParams.get('status') || '';
  const source = url.searchParams.get('source') || '';
  const industry = url.searchParams.get('industry') || '';
  const sort = url.searchParams.get('sort') || 'created_at';
  const order = url.searchParams.get('order') === 'asc' ? 'ASC' : 'DESC';

  const offset = (page - 1) * limit;

  let whereClauses = ['deleted_at IS NULL'];
  let params = [];

  if (search) {
    whereClauses.push('(name LIKE ? OR phone LIKE ? OR email LIKE ?)');
    params.push(`%${search}%`, `%${search}%`, `%${search}%`);
  }
  if (status) {
    whereClauses.push('status = ?');
    params.push(status);
  }
  if (source) {
    whereClauses.push('source = ?');
    params.push(source);
  }
  if (industry) {
    whereClauses.push('industry = ?');
    params.push(industry);
  }

  const whereStr = whereClauses.length > 0 ? `WHERE ${whereClauses.join(' AND ')}` : '';
  const allowedSortColumns = ['created_at', 'updated_at', 'name', 'status', 'score'];
  const sortColumn = allowedSortColumns.includes(sort) ? sort : 'created_at';
  
  const query = `SELECT * FROM leads ${whereStr} ORDER BY ${sortColumn} ${order} LIMIT ? OFFSET ?`;
  const countQuery = `SELECT COUNT(*) as total FROM leads ${whereStr}`;

  try {
    const [dataResult, countResult] = await Promise.all([
      env.DB.prepare(query).bind(...params, limit, offset).all(),
      env.DB.prepare(countQuery).bind(...params).first()
    ]);

    return new Response(JSON.stringify({ 
      success: true, 
      data: dataResult.results,
      meta: {
        total: countResult.total,
        page,
        limit,
        totalPages: Math.ceil(countResult.total / limit)
      }
    }), { headers: { 'Content-Type': 'application/json' } });
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
    
    // Normalize phone
    let phone = data.phone || '';
    phone = phone.replace(/\\s+/g, '');
    if (phone.startsWith('+84')) phone = '0' + phone.slice(3);
    if (phone.startsWith('84')) phone = '0' + phone.slice(2);

    if (phone) {
      const existing = await env.DB.prepare('SELECT id FROM leads WHERE phone = ? AND deleted_at IS NULL').bind(phone).first();
      if (existing) {
        return new Response(JSON.stringify({ success: false, error: 'Phone number already exists' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    const insertQuery = `
      INSERT INTO leads (
        id, name, phone, email, facebook_url, zalo_phone, 
        industry, industry_slug, source, class, status, health, score, 
        notes, tags, assigned_to, company, address, custom_fields, created_at, updated_at
      ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
      ) RETURNING *
    `;

    const result = await env.DB.prepare(insertQuery).bind(
      id,
      data.name || '',
      phone,
      data.email || null,
      data.facebook_url || null,
      data.zalo_phone || null,
      data.industry || null,
      data.industry_slug || null,
      data.source || 'manual',
      data.class || null,
      data.status || 'new',
      data.health || null,
      data.score || 0,
      data.notes ? JSON.stringify(data.notes) : null,
      data.tags ? JSON.stringify(data.tags) : null,
      data.assigned_to || null,
      data.company || null,
      data.address || null,
      data.custom_fields ? JSON.stringify(data.custom_fields) : null,
      now,
      now
    ).first();

    return new Response(JSON.stringify({ success: true, data: result }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({ success: false, error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
