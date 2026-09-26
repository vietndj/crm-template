export async function onRequestPost({ request, env }) {
  try {
    const { rows, source = 'excel', filename = 'import' } = await request.json();

    if (!Array.isArray(rows) || rows.length === 0) {
      return new Response(JSON.stringify({ success: false, error: 'Invalid or empty rows array' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const import_log_id = crypto.randomUUID();
    let imported = 0;
    let skipped = 0;
    let errors = [];

    const now = new Date().toISOString();

    // Sequentially process items
    for (const [index, row] of rows.entries()) {
      try {
        let phone = row.phone ? String(row.phone).replace(/\\s+/g, '') : '';
        if (phone.startsWith('+84')) phone = '0' + phone.slice(3);
        if (phone.startsWith('84')) phone = '0' + phone.slice(2);

        if (!phone) {
          skipped++;
          errors.push({ row: index, error: 'Missing phone' });
          continue;
        }

        const existing = await env.DB.prepare('SELECT id FROM leads WHERE phone = ?').bind(phone).first();

        if (existing) {
          skipped++;
          continue;
        }

        const id = crypto.randomUUID();
        const insertQuery = `
          INSERT INTO leads (
            id, name, phone, email, source, status, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `;

        await env.DB.prepare(insertQuery).bind(
          id,
          row.name || 'Unknown',
          phone,
          row.email || null,
          source,
          'new',
          now,
          now
        ).run();

        imported++;
      } catch (err) {
        errors.push({ row: index, error: err.message });
      }
    }

    await env.DB.prepare(
      'INSERT INTO import_logs (id, source, filename, total_rows, imported, skipped, errors, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(
      import_log_id, source, filename, rows.length, imported, skipped, JSON.stringify(errors), now
    ).run();

    return new Response(JSON.stringify({
      success: true,
      data: { imported, skipped, errors, import_log_id }
    }), { headers: { 'Content-Type': 'application/json' } });

  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
