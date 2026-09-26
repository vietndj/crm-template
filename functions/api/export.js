export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const format = url.searchParams.get('format') || 'json';

  try {
    const { results } = await env.DB.prepare('SELECT * FROM leads WHERE deleted_at IS NULL ORDER BY created_at DESC').all();

    if (format === 'csv') {
      if (results.length === 0) {
        return new Response('', { headers: { 'Content-Type': 'text/csv' } });
      }

      const headers = Object.keys(results[0]).join(',');
      const csvRows = results.map(row => {
        return Object.values(row).map(val => {
          if (val === null || val === undefined) return '""';
          const str = String(val).replace(/"/g, '""');
          return `"${str}"`;
        }).join(',');
      });

      const csvContent = [headers, ...csvRows].join('\\n');

      return new Response(csvContent, {
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
          'Content-Disposition': 'attachment; filename="leads_export.csv"'
        }
      });
    }

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
