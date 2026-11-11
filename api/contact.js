// Vercel serverless function: saves a contact-form message to Supabase and emails it to you via Resend.
// Needs these Vercel environment variables: RESEND_API_KEY, NOTIFY_EMAIL (and optionally FROM_EMAIL).
const SUPABASE_URL = 'https://oiztdngwarwhjbxtgsdx.supabase.co';
const SUPABASE_KEY = 'sb_publishable_gpIruorbcC0-VxG3bko_2Q_eU2FRWbN'; // publishable key, safe to be public

const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }
  let b = req.body;
  if (typeof b === 'string') { try { b = JSON.parse(b); } catch (e) { b = {}; } }
  b = b || {};
  if (b.website) return res.status(200).json({ ok: true }); // honeypot: bots fill this hidden field

  const name = String(b.name || '').trim().slice(0, 200);
  const email = String(b.email || '').trim().slice(0, 200);
  const topic = String(b.topic || 'Something else').trim().slice(0, 100);
  const message = String(b.message || '').trim().slice(0, 3000);
  if (!name || !message || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ error: 'Invalid input' });
  }

  let saved = false;
  let emailed = false;

  try {
    const r = await fetch(SUPABASE_URL + '/rest/v1/messages', {
      method: 'POST',
      headers: { apikey: SUPABASE_KEY, Authorization: 'Bearer ' + SUPABASE_KEY, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
      body: JSON.stringify([{ name, email, project_type: topic, message, is_read: false }]),
    });
    saved = r.ok;
    if (!r.ok) console.error('Supabase insert failed', r.status, await r.text());
  } catch (e) { saved = false; console.error('Supabase error', e && e.message); }

  const key = process.env.RESEND_API_KEY;
  const to = process.env.NOTIFY_EMAIL;
  if (!key || !to) console.error('Missing RESEND_API_KEY or NOTIFY_EMAIL');
  if (key && to) {
    try {
      const r = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + key, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: process.env.FROM_EMAIL || 'Portfolio <onboarding@resend.dev>',
          to: [to],
          reply_to: email,
          subject: 'New portfolio message from ' + name + ' (' + topic + ')',
          html: '<p><b>Name:</b> ' + esc(name) + '</p><p><b>Email:</b> ' + esc(email) + '</p><p><b>Topic:</b> ' + esc(topic) + '</p><p><b>Message:</b></p><p style="white-space:pre-wrap">' + esc(message) + '</p><p>Reply to this email to answer them directly.</p>',
        }),
      });
      emailed = r.ok;
      if (!r.ok) console.error('Resend failed', r.status, await r.text());
    } catch (e) { emailed = false; console.error('Resend error', e && e.message); }
  }

  if (saved || emailed) return res.status(200).json({ ok: true, saved, emailed });
  return res.status(502).json({ error: 'Could not deliver the message' });
};