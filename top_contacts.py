#!/usr/bin/env python3
"""
Top 200 Contacts - Ranks your most messaged people across iMessage + WhatsApp
Usage: python3 top_contacts.py
"""

import sqlite3, os, sys, re, subprocess, argparse, glob

# Database paths
IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
ADDRESSBOOK_DIR = os.path.expanduser("~/Library/Application Support/AddressBook")
WHATSAPP_PATHS = [
    os.path.expanduser("~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite"),
    os.path.expanduser("~/Library/Containers/com.whatsapp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite"),
    os.path.expanduser("~/Library/Containers/desktop.WhatsApp/Data/Library/Application Support/WhatsApp/ChatStorage.sqlite"),
]

WHATSAPP_DB = None

# Timestamps
TS_2025_IMESSAGE = 1735689600
TS_2024_IMESSAGE = 1704067200
TS_2025_WHATSAPP = 757382400
TS_2024_WHATSAPP = 725846400

def extract_imessage_contacts():
    """Extract contacts from macOS AddressBook."""
    contacts = {}
    db_paths = glob.glob(os.path.join(ADDRESSBOOK_DIR, "Sources", "*", "AddressBook-v22.abcddb"))
    main_db = os.path.join(ADDRESSBOOK_DIR, "AddressBook-v22.abcddb")
    if os.path.exists(main_db): db_paths.append(main_db)
    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path)
            people = {}
            for row in conn.execute("SELECT ROWID, ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD WHERE ZFIRSTNAME IS NOT NULL OR ZLASTNAME IS NOT NULL"):
                name = f"{row[1] or ''} {row[2] or ''}".strip()
                if name: people[row[0]] = name
            for owner, phone in conn.execute("SELECT ZOWNER, ZFULLNUMBER FROM ZABCDPHONENUMBER WHERE ZFULLNUMBER IS NOT NULL"):
                if owner in people:
                    name = people[owner]
                    digits = re.sub(r'\D', '', str(phone))
                    if digits:
                        contacts[digits] = name
                        if len(digits) >= 10:
                            contacts[digits[-10:]] = name
                        if len(digits) >= 7:
                            contacts[digits[-7:]] = name
                        if len(digits) == 11 and digits.startswith('1'):
                            contacts[digits[1:]] = name
            for owner, email in conn.execute("SELECT ZOWNER, ZADDRESS FROM ZABCDEMAILADDRESS WHERE ZADDRESS IS NOT NULL"):
                if owner in people: contacts[email.lower().strip()] = people[owner]
            conn.close()
        except: pass
    return contacts

def extract_whatsapp_contacts():
    """Extract contact names from WhatsApp's ZWAPROFILEPUSHNAME table."""
    contacts = {}
    if not WHATSAPP_DB:
        return contacts
    try:
        conn = sqlite3.connect(WHATSAPP_DB)
        for row in conn.execute("SELECT ZJID, ZPUSHNAME FROM ZWAPROFILEPUSHNAME WHERE ZPUSHNAME IS NOT NULL"):
            jid, name = row
            if jid and name:
                contacts[jid] = name
        conn.close()
    except:
        pass
    return contacts

def get_name_imessage(handle, contacts):
    if '@' in handle:
        lookup = handle.lower().strip()
        if lookup in contacts: return contacts[lookup]
        return handle.split('@')[0]
    digits = re.sub(r'\D', '', str(handle))
    if digits in contacts: return contacts[digits]
    if len(digits) == 11 and digits.startswith('1'):
        if digits[1:] in contacts: return contacts[digits[1:]]
    if len(digits) >= 10 and digits[-10:] in contacts:
        return contacts[digits[-10:]]
    if len(digits) >= 7 and digits[-7:] in contacts:
        return contacts[digits[-7:]]
    return handle

def get_name_whatsapp(jid, contacts):
    if not jid:
        return "Unknown"
    if jid in contacts:
        return contacts[jid]
    if '@' in jid:
        phone = jid.split('@')[0]
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone.startswith('1'):
            return f"+1 ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        return f"+{phone}"
    return jid

def find_whatsapp_database():
    for path in WHATSAPP_PATHS:
        if os.path.exists(path):
            return path
    return None

def check_access():
    global WHATSAPP_DB
    has_imessage = False
    has_whatsapp = False

    if os.path.exists(IMESSAGE_DB):
        try:
            conn = sqlite3.connect(IMESSAGE_DB)
            conn.execute("SELECT 1 FROM message LIMIT 1")
            conn.close()
            has_imessage = True
        except:
            pass

    WHATSAPP_DB = find_whatsapp_database()
    if WHATSAPP_DB:
        try:
            conn = sqlite3.connect(WHATSAPP_DB)
            conn.execute("SELECT 1 FROM ZWAMESSAGE LIMIT 1")
            conn.close()
            has_whatsapp = True
        except:
            pass

    if not has_imessage and not has_whatsapp:
        print("\n[!] ACCESS DENIED - Neither iMessage nor WhatsApp accessible")
        print("   System Settings -> Privacy & Security -> Full Disk Access -> Add Terminal")
        subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles'])
        sys.exit(1)

    return has_imessage, has_whatsapp

def q_imessage(sql):
    conn = sqlite3.connect(IMESSAGE_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r

def q_whatsapp(sql):
    conn = sqlite3.connect(WHATSAPP_DB)
    r = conn.execute(sql).fetchall()
    conn.close()
    return r

def get_top_imessage(ts_start, limit=200):
    """Get top contacts from iMessage (1-on-1 chats only)."""
    one_on_one_cte = """
        WITH chat_participants AS (
            SELECT chat_id, COUNT(*) as participant_count
            FROM chat_handle_join
            GROUP BY chat_id
        ),
        one_on_one_messages AS (
            SELECT m.ROWID as msg_id
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat_participants cp ON cmj.chat_id = cp.chat_id
            WHERE cp.participant_count = 1
        )
    """
    return q_imessage(f"""{one_on_one_cte}
        SELECT h.id, COUNT(*) t, SUM(CASE WHEN m.is_from_me=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.is_from_me=0 THEN 1 ELSE 0 END)
        FROM message m JOIN handle h ON m.handle_id=h.ROWID
        WHERE (m.date/1000000000+978307200)>{ts_start}
        AND m.ROWID IN (SELECT msg_id FROM one_on_one_messages)
        AND NOT (LENGTH(REPLACE(REPLACE(h.id, '+', ''), '-', '')) BETWEEN 5 AND 6 AND REPLACE(REPLACE(h.id, '+', ''), '-', '') GLOB '[0-9]*')
        GROUP BY h.id ORDER BY t DESC LIMIT {limit}
    """)

def get_top_whatsapp(ts_start, limit=200):
    """Get top contacts from WhatsApp (DMs only)."""
    one_on_one_cte = """
        WITH dm_sessions AS (
            SELECT Z_PK, ZCONTACTJID FROM ZWACHATSESSION WHERE ZSESSIONTYPE = 0
        ),
        dm_messages AS (
            SELECT m.Z_PK as msg_id, m.ZCHATSESSION, s.ZCONTACTJID
            FROM ZWAMESSAGE m JOIN dm_sessions s ON m.ZCHATSESSION = s.Z_PK
        )
    """
    return q_whatsapp(f"""{one_on_one_cte}
        SELECT dm.ZCONTACTJID, COUNT(*) t, SUM(CASE WHEN m.ZISFROMME=1 THEN 1 ELSE 0 END), SUM(CASE WHEN m.ZISFROMME=0 THEN 1 ELSE 0 END)
        FROM ZWAMESSAGE m JOIN dm_messages dm ON m.Z_PK = dm.msg_id
        WHERE m.ZMESSAGEDATE>{ts_start} GROUP BY dm.ZCONTACTJID ORDER BY t DESC LIMIT {limit}
    """)

def gen_html(contacts, path, year, has_imessage, has_whatsapp):
    """Generate HTML ranking page."""
    platforms = []
    if has_imessage: platforms.append("iMessage")
    if has_whatsapp: platforms.append("WhatsApp")
    platform_str = " + ".join(platforms)
    
    total_msgs = sum(c['total'] for c in contacts)
    
    rows_html = ""
    for i, c in enumerate(contacts, 1):
        source_icon = "📱" if c['source'] == 'imessage' else "💬"
        sent = c['sent'] or 0
        received = c['received'] or 0
        if sent == 0 and received == 0:
            ratio_badge = '<span class="ratio balanced">—</span>'
        elif sent == 0:
            ratio_badge = f'<span class="ratio them">↓ all them</span>'
        elif received == 0:
            ratio_badge = f'<span class="ratio you">↑ all you</span>'
        else:
            ratio = sent / received
            if ratio > 1.5:
                ratio_badge = f'<span class="ratio you">↑ {ratio:.1f}x you</span>'
            elif ratio < 0.67:
                ratio_badge = f'<span class="ratio them">↓ {1/ratio:.1f}x them</span>'
            else:
                ratio_badge = '<span class="ratio balanced">≈ balanced</span>'
        
        rows_html += f'''
        <tr>
            <td class="rank">{i}</td>
            <td class="name">{c['name']}</td>
            <td class="source">{source_icon}</td>
            <td class="total">{c['total']:,}</td>
            <td class="sent">{c['sent']:,}</td>
            <td class="received">{c['received']:,}</td>
            <td class="ratio-cell">{ratio_badge}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Top 200 Contacts - {year}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>✨</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #7d8590;
    --green: #3fb950;
    --yellow: #d29922;
    --blue: #58a6ff;
    --purple: #a371f7;
    --pink: #db61a2;
    --imessage: #3fb950;
    --whatsapp: #25D366;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 40px 20px;
}}

.container {{
    max-width: 1000px;
    margin: 0 auto;
}}

header {{
    text-align: center;
    margin-bottom: 40px;
}}

h1 {{
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 8px;
    background: linear-gradient(90deg, var(--imessage), var(--whatsapp));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.subtitle {{
    color: var(--muted);
    font-size: 16px;
}}

.stats {{
    display: flex;
    justify-content: center;
    gap: 48px;
    margin: 32px 0;
    padding: 24px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
}}

.stat {{
    text-align: center;
}}

.stat-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 600;
    color: var(--green);
}}

.stat-label {{
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 4px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}}

th {{
    background: rgba(255,255,255,0.03);
    padding: 14px 16px;
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border);
}}

th.num {{ text-align: right; }}

td {{
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
}}

tr:last-child td {{ border-bottom: none; }}

tr:hover {{ background: rgba(255,255,255,0.02); }}

.rank {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: var(--muted);
    width: 50px;
}}

tr:nth-child(1) .rank {{ color: #ffd700; }}
tr:nth-child(2) .rank {{ color: #c0c0c0; }}
tr:nth-child(3) .rank {{ color: #cd7f32; }}

.name {{
    font-weight: 500;
    max-width: 250px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.source {{
    width: 40px;
    text-align: center;
    font-size: 16px;
}}

.total, .sent, .received {{
    font-family: 'JetBrains Mono', monospace;
    text-align: right;
    width: 100px;
}}

.total {{ font-weight: 600; color: var(--blue); }}
.sent {{ color: var(--green); }}
.received {{ color: var(--yellow); }}

.ratio-cell {{ width: 120px; }}

.ratio {{
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
}}

.ratio.you {{
    background: rgba(63,185,80,0.15);
    color: var(--green);
}}

.ratio.them {{
    background: rgba(210,153,34,0.15);
    color: var(--yellow);
}}

.ratio.balanced {{
    background: rgba(88,166,255,0.15);
    color: var(--blue);
}}

.footer {{
    text-align: center;
    margin-top: 32px;
    color: var(--muted);
    font-size: 13px;
}}

@media (max-width: 768px) {{
    .stats {{ flex-direction: column; gap: 20px; }}
    th, td {{ padding: 10px 12px; font-size: 12px; }}
    .name {{ max-width: 120px; }}
    .ratio {{ font-size: 10px; padding: 3px 6px; }}
}}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>✨ Top 200 Contacts ✨</h1>
        <p class="subtitle">{platform_str} • {year}</p>
    </header>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{len(contacts)}</div>
            <div class="stat-label">People</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_msgs:,}</div>
            <div class="stat-label">Total Messages</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sum(c['sent'] for c in contacts):,}</div>
            <div class="stat-label">Sent</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sum(c['received'] for c in contacts):,}</div>
            <div class="stat-label">Received</div>
        </div>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Name</th>
                <th>📱</th>
                <th class="num">Total</th>
                <th class="num">Sent</th>
                <th class="num">Received</th>
                <th>Ratio</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    
    <div class="footer">
        Generated by top_contacts.py
    </div>
</div>
</body></html>'''

    with open(path, 'w') as f:
        f.write(html)
    return path

def main():
    parser = argparse.ArgumentParser(description='Rank your top 200 most messaged contacts')
    parser.add_argument('--output', '-o', default='top_contacts.html')
    parser.add_argument('--include-2024', action='store_true', help='Include 2024 data (default is 2025 only)')
    parser.add_argument('--limit', '-n', type=int, default=200, help='Number of contacts to show')
    args = parser.parse_args()

    print("\n" + "="*50)
    print("  TOP CONTACTS RANKER")
    print("="*50 + "\n")

    print("[*] Checking access...")
    has_imessage, has_whatsapp = check_access()

    platforms = []
    if has_imessage:
        platforms.append("iMessage")
        print(f"    ✓ iMessage: {IMESSAGE_DB}")
    if has_whatsapp:
        platforms.append("WhatsApp")
        print(f"    ✓ WhatsApp: {WHATSAPP_DB}")

    print(f"\n[*] Platforms: {' + '.join(platforms)}")

    print("[*] Loading contacts...")
    imessage_contacts = extract_imessage_contacts() if has_imessage else {}
    whatsapp_contacts = extract_whatsapp_contacts() if has_whatsapp else {}
    print(f"    ✓ {len(imessage_contacts)} from AddressBook, {len(whatsapp_contacts)} from WhatsApp")

    # Determine year
    year = "2024" if args.include_2024 else "2025"

    # Check if we have enough 2025 data
    if not args.include_2024:
        total_2025 = 0
        if has_imessage:
            r = q_imessage(f"SELECT COUNT(*) FROM message WHERE (date/1000000000+978307200)>{TS_2025_IMESSAGE}")
            total_2025 += r[0][0]
        if has_whatsapp:
            r = q_whatsapp(f"SELECT COUNT(*) FROM ZWAMESSAGE WHERE ZMESSAGEDATE>{TS_2025_WHATSAPP}")
            total_2025 += r[0][0]

        if total_2025 < 100:
            print(f"    ⚠️  Only {total_2025} msgs in 2025, using 2024")
            year = "2024"

    # Get timestamps
    if year == "2024":
        ts_imessage = TS_2024_IMESSAGE
        ts_whatsapp = TS_2024_WHATSAPP
    else:
        ts_imessage = TS_2025_IMESSAGE
        ts_whatsapp = TS_2025_WHATSAPP

    print(f"\n[*] Fetching top {args.limit} contacts for {year}...")
    
    all_contacts = []
    
    if has_imessage:
        print("    Querying iMessage...")
        for h, total, sent, received in get_top_imessage(ts_imessage, args.limit):
            name = get_name_imessage(h, imessage_contacts)
            all_contacts.append({
                'name': name,
                'handle': h,
                'total': total,
                'sent': sent,
                'received': received,
                'source': 'imessage'
            })
        print(f"    ✓ {len(all_contacts)} iMessage contacts")

    if has_whatsapp:
        print("    Querying WhatsApp...")
        wa_count = 0
        for h, total, sent, received in get_top_whatsapp(ts_whatsapp, args.limit):
            name = get_name_whatsapp(h, whatsapp_contacts)
            all_contacts.append({
                'name': name,
                'handle': h,
                'total': total,
                'sent': sent,
                'received': received,
                'source': 'whatsapp'
            })
            wa_count += 1
        print(f"    ✓ {wa_count} WhatsApp contacts")

    # Sort by total and dedupe by name (keep higher count)
    print("\n[*] Deduplicating and ranking...")
    name_counts = {}
    for entry in all_contacts:
        name = entry['name']
        if name not in name_counts or entry['total'] > name_counts[name]['total']:
            name_counts[name] = entry
    
    ranked = sorted(name_counts.values(), key=lambda x: -x['total'])[:args.limit]
    print(f"    ✓ {len(ranked)} unique contacts ranked")

    print(f"\n[*] Generating HTML...")
    gen_html(ranked, args.output, year, has_imessage, has_whatsapp)
    print(f"    ✓ Saved to {args.output}")

    # Print top 10 to terminal
    print(f"\n{'='*50}")
    print(f"  TOP 10 PREVIEW")
    print(f"{'='*50}")
    for i, c in enumerate(ranked[:10], 1):
        icon = "📱" if c['source'] == 'imessage' else "💬"
        print(f"  {i:2}. {icon} {c['name'][:30]:30} {c['total']:,}")
    print(f"{'='*50}\n")

    subprocess.run(['open', args.output])
    print("Done!\n")

if __name__ == '__main__':
    main()

