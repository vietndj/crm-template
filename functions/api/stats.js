export async function onRequestGet({ request, env }) {
  try {
    const [
      totalResult,
      newTodayResult,
      newThisWeekResult,
      newThisMonthResult,
      statusGroupsResult,
      sourceGroupsResult,
      industryGroupsResult,
      recentInteractionsResult
    ] = await Promise.all([
      env.DB.prepare('SELECT COUNT(*) as count FROM leads WHERE deleted_at IS NULL').first(),
      env.DB.prepare("SELECT COUNT(*) as count FROM leads WHERE deleted_at IS NULL AND date(created_at) = date('now')").first(),
      env.DB.prepare("SELECT COUNT(*) as count FROM leads WHERE deleted_at IS NULL AND date(created_at) >= date('now', '-7 days')").first(),
      env.DB.prepare("SELECT COUNT(*) as count FROM leads WHERE deleted_at IS NULL AND date(created_at) >= date('now', 'start of month')").first(),
      env.DB.prepare("SELECT status, COUNT(*) as count FROM leads WHERE deleted_at IS NULL GROUP BY status").all(),
      env.DB.prepare("SELECT source, COUNT(*) as count FROM leads WHERE deleted_at IS NULL GROUP BY source").all(),
      env.DB.prepare("SELECT industry, COUNT(*) as count FROM leads WHERE deleted_at IS NULL GROUP BY industry").all(),
      env.DB.prepare(`
        SELECT i.*, l.name as lead_name 
        FROM interactions i 
        JOIN leads l ON i.lead_id = l.id 
        ORDER BY i.created_at DESC LIMIT 10
      `).all()
    ]);

    const formatGroups = (results) => {
      return results.reduce((acc, row) => {
        acc[row.status || row.source || row.industry || 'unknown'] = row.count;
        return acc;
      }, {});
    };

    const stats = {
      total_leads: totalResult.count,
      new_today: newTodayResult.count,
      new_this_week: newThisWeekResult.count,
      new_this_month: newThisMonthResult.count,
      by_status: formatGroups(statusGroupsResult.results),
      by_source: formatGroups(sourceGroupsResult.results),
      by_industry: formatGroups(industryGroupsResult.results),
      recent_interactions: recentInteractionsResult.results,
      conversion_rate: '0.00%'
    };

    const wonCount = stats.by_status['won'] || 0;
    if (stats.total_leads > 0) {
      stats.conversion_rate = ((wonCount / stats.total_leads) * 100).toFixed(2) + '%';
    }

    return new Response(JSON.stringify({ success: true, data: stats }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ success: false, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
