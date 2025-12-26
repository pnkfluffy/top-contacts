# Top 200 Contacts

> Original credit to [@nikunj](https://x.com/nikunj) and his project [wrap2025](https://github.com/kothari-nikunj/wrap2025)

Rank your most messaged people across iMessage and WhatsApp.

## Features

- **Top 200 ranking** - your most texted contacts, sorted by message count
- **Platform detection** - automatically finds iMessage and WhatsApp databases
- **Sent/received breakdown** - see who texts you vs who you text
- **Ratio indicators** - highlights one-sided conversations
- **Contact resolution** - maps phone numbers to names from your AddressBook

## Installation

### 1. Download the script

```bash
curl -O https://raw.githubusercontent.com/pnkfluffy/top-contacts/main/top_contacts.py
```

Or clone the repo:

```bash
git clone https://github.com/pnkfluffy/top-contacts.git
cd top-contacts
```

### 2. Grant Terminal access

The script needs to read your message databases:

**System Settings -> Privacy & Security -> Full Disk Access -> Add Terminal**

(Or iTerm/Warp if you use those)

### 3. Run it

```bash
python3 top_contacts.py
```

Your ranking will open in your browser automatically.

## Options

```bash
# Include 2024 data (default is 2025 only)
python3 top_contacts.py --include-2024

# Limit to top 50 contacts
python3 top_contacts.py -n 50

# Custom output filename
python3 top_contacts.py -o my_ranking.html
```

If you don't have enough 2025 messages yet, the script will automatically include 2024 data.

## Privacy

**100% Local** - Your data never leaves your computer

- No servers, no uploads, no tracking
- No external dependencies (Python stdlib only)
- All analysis happens locally
- Output is a single HTML file

You can ask claude to verify the code is safe.

## Requirements

- macOS (uses local message databases)
- Python 3 (pre-installed on macOS)
- Full Disk Access for Terminal
- For WhatsApp: WhatsApp desktop app installed with chat history

## How it works

The script reads your local message databases using SQLite queries:

- **iMessage**: `~/Library/Messages/chat.db`
- **WhatsApp**: `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`
- **Contacts**: `~/Library/Application Support/AddressBook/`

It queries for 1-on-1 conversations (excluding group chats), resolves identifiers to contact names, and generates a self-contained HTML file with an interactive ranking table.

## FAQ

**Q: Is this safe?**
A: Yes. The script only reads local databases, writes one HTML file, and makes zero network requests. No data is sent anywhere.

**Q: Why do I need Full Disk Access?**
A: Apple protects message databases. Terminal needs permission to read them.

**Q: Can I run this on iOS?**
A: No, iOS doesn't allow access to message databases. macOS only.

**Q: The names are showing as phone numbers**
A: The script tries to match identifiers to contact names. Some may not resolve if the formatting differs.

## License

MIT

