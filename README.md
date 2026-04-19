# EnumX – Full CPTS Automation Framework

```
███████╗███╗   ██╗██╗   ██╗███╗   ███╗██╗  ██╗
██╔════╝████╗  ██║██║   ██║████╗ ████║╚██╗██╔╝
█████╗  ██╔██╗ ██║██║   ██║██╔████╔██║ ╚███╔╝
██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║ ██╔██╗
███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║██╔╝ ██╗
╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝
```

> ⚠️ **For authorized penetration testing and CTF/lab environments only (HTB, CPTS, etc.)**

A fully interactive, modular Python recon-to-report automation tool built for the **HTB CPTS certification** workflow. Every module is prompted individually — you stay in control of what runs.

---

## Features

| Category | Tools / Techniques |
|---|---|
| **Recon** | Nmap (full/quick/custom + evasion), WAF detection, DNS, CRT.sh subdomains, VHOST brute |
| **Web** | whatweb, gobuster, feroxbuster, nikto, wfuzz, sqlmap, LFI probe, web shell test |
| **SMB** | Share discovery, credential × share access matrix, write test, enum4linux-ng, MS17-010 |
| **FTP** | Anonymous login, medusa, hydra brute |
| **SSH** | Banner enum, default creds, hydra brute |
| **LDAP** | Anonymous bind, naming context dump, full tree dump |
| **RDP** | Vuln check (MS12-020), ncrack/hydra brute |
| **SNMP** | Community string enum (snmpwalk) |
| **Databases** | MySQL, MSSQL (xp_cmdshell, xp_dirtree hash capture), PostgreSQL default creds |
| **Active Directory** | Kerbrute, AS-REP Roasting, Kerberoasting, BloodHound, password spray, PTH, DCSync, NTDS.dit |
| **Credentials** | hashcat, John, Responder + NTLM relay, CeWL wordlist generation |
| **Post-Linux** | linpeas auto-upload + critical findings parser, linux-exploit-suggester, checklist |
| **Post-Windows** | winpeas auto-upload, LSASS dump (pypykatz), SAM dump (secretsdump), checklist |
| **Lateral Movement** | evil-winrm, psexec, wmiexec, xfreerdp PTH |
| **Shells** | 6 reverse shell one-liners, msfvenom payloads (ELF/EXE/PHP/ASPX) |
| **Exploits** | searchsploit per service + auto-pull + auto-run matched exploits |
| **Reporting** | Markdown + HTML report, SMB access matrix table, HTB writeup skeleton, session log |

---

## Requirements

```bash
# Core
sudo apt install nmap smbclient enum4linux-ng netexec crackmapexec \
  hydra medusa ncrack gobuster feroxbuster nikto wfuzz sqlmap \
  snmpwalk ldap-utils impacket-scripts bloodhound.py \
  sshpass responder hashcat john kerbrute

# Python packages
pip3 install impacket pypykatz

# Optional
sudo apt install whatweb wafw00f feroxbuster nikto
```

> Most tools come pre-installed on **Kali Linux**.

---

## Usage

### Basic
```bash
python3 enumx_v4.py --target 10.10.10.10
```

### Full options
```bash
python3 enumx_v4.py \
  --target 10.10.10.10 \
  --lhost 10.10.14.5 \
  --domain inlanefreight.local \
  --dc-ip 10.10.10.10 \
  --creds creds.txt \
  --userlist users.txt \
  --passlist /usr/share/wordlists/rockyou.txt
```

### Skip nmap (use existing XML)
```bash
python3 enumx_v4.py --target 10.10.10.10 --skip-nmap --nmap-xml ./nmap.xml
```

### Arguments

| Flag | Description |
|---|---|
| `--target` | Target IP or hostname **(required)** |
| `--lhost` | Your IP for reverse shells and payloads |
| `--domain` | Active Directory domain name |
| `--dc-ip` | Domain Controller IP |
| `--creds` | Credentials file (`user:pass` per line) |
| `--userlist` | Default user list for brute force modules |
| `--passlist` | Default password list for brute force modules |
| `--skip-nmap` | Skip nmap, use existing XML with `--nmap-xml` |
| `--nmap-xml` | Path to existing nmap XML |
| `--no-color` | Disable colored output |

---

## Workflow

```
Target IP
    │
    ▼
┌─────────────────┐
│   Nmap Scan     │  Full / Quick / Custom + optional IDS evasion
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Machine Profiler   │  Auto-detects: Windows DC / MSSQL / Linux Web / etc.
│  + HTB Hints        │  Suggests attack path + warns on unusual ports
└────────┬────────────┘
         │
         ▼  (each module prompted individually)
    ┌────┴─────┐
    │  Service │──► HTTP → Web Attacks (gobuster/nikto/sqlmap/LFI/wfuzz)
    │  Dispatch│──► SMB  → Share discovery + access matrix per user
    │          │──► FTP  → Anonymous + brute
    │          │──► SSH  → Default creds + hydra
    │          │──► LDAP → Anonymous bind + dump
    │          │──► RDP  → Vuln check + brute
    │          │──► SNMP → Community strings
    │          │──► DB   → MySQL/MSSQL/PgSQL default creds + xp_cmdshell
    └────┬─────┘
         │
         ▼
┌──────────────────┐
│  AD Attacks      │  Kerbrute → ASREPRoast → Kerberoast → BloodHound
│                  │  Password spray → PTH → DCSync → NTDS dump
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Post-Exploit    │  linpeas auto-upload → critical findings parsed
│                  │  winpeas upload → LSASS/SAM dump parsing
│                  │  linux-exploit-suggester
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Lateral Move    │  evil-winrm / psexec / wmiexec / xfreerdp PTH
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Searchsploit    │  Per service → auto-pull exploit → ask to run
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Reports         │  report.md + report.html + writeup_skeleton.md
│                  │  session_log.txt (every command + output)
└──────────────────┘
```

---

## SMB Access Matrix

After SMB enumeration, EnumX builds a full access matrix showing which user has access to which share and at what permission level:

```
| Share    | anonymous | administrator | john   | alice  |
|----------|-----------|---------------|--------|--------|
| ADMIN$   | -         | READ/WRITE    | -      | -      |
| C$       | -         | READ/WRITE    | -      | -      |
| IPC$     | READ      | READ/WRITE    | READ   | READ   |
| Users    | -         | READ/WRITE    | READ   | READ   |
| Finance  | -         | READ/WRITE    | -      | READ/WRITE |
```

Write access is automatically tested and flagged as **CRITICAL** (potential RCE via SCF/DLL drop).  
File listings for each accessible share are saved to `enumx_out/<target>/<ts>/smb/listing_<share>_<user>.txt`.

---

## Output Structure

```
enumx_out/
└── 10.10.10.10/
    └── 20250419-143022/
        ├── nmap.xml / nmap.txt
        ├── session_log.txt          # every command + timestamp + output
        ├── report.md                # full markdown report
        ├── report.html              # styled HTML report
        ├── writeup_skeleton.md      # HTB-style writeup template
        ├── recon/                   # WAF, DNS, CRT.sh, VHOST
        ├── web/                     # gobuster, nikto, sqlmap, LFI, wfuzz
        ├── smb/                     # shares, access matrix, file listings
        ├── ftp/                     # anonymous login, brute results
        ├── ssh/                     # banner, cred test, hydra
        ├── ldap/                    # naming contexts, full dump
        ├── rdp/                     # vuln check, brute
        ├── snmp/                    # community string results
        ├── db/                      # mysql/mssql/postgresql results
        ├── ad/                      # kerbrute, asrep, kerberoast, bloodhound, dcsync
        ├── creds/                   # hashcat, john, responder, cewl
        ├── post_linux/              # linpeas, les, checklist
        ├── post_windows/            # winpeas, pypykatz, secretsdump, checklist
        ├── lateral/                 # lateral movement notes
        ├── shells/                  # reverse shells, msfvenom payloads
        └── searchsploit/            # per-service exploit results
```

---

## Credentials File Format

```
administrator:Password123
john:Welcome1
alice:Summer2024!
```

Pass with `--creds creds.txt`. All credentials are automatically tested against every discovered SMB share, SSH, DB, WinRM, and AD modules.

---

## Report Output

### HTML Report
Dark-themed, color-coded by severity (CRITICAL / HIGH / MEDIUM / INFO). Includes:
- Credentials found (top of report)
- Full findings table with severity
- Timeline (every event with timestamp)
- SMB access matrix

### Writeup Skeleton
Auto-generated `writeup_skeleton.md` pre-filled with:
- Discovered services
- High/critical findings
- Screenshot placeholders (`[screenshot: name.png]`)
- Flags table
- Key takeaways section

---

## Example Creds File

```
# creds.txt
administrator:Password123!
svc-backup:Backup2024
john.doe:Welcome1
```

---

## Disclaimer

This tool is intended **only** for:
- Authorized penetration testing engagements
- CTF competitions (HackTheBox, TryHackMe, etc.)
- Security certification labs (CPTS, OSCP, etc.)
- Educational and research purposes

**Do not use against systems you do not have explicit written permission to test.**

---

## Author

**0xZoro** – CPTS student | HTB enthusiast  
Notes & Cheatsheet: [0xzoro.gitbook.io](https://0xzoro.gitbook.io/0xzoro/cpts/cpts-cheat-sheet)
