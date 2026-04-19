 # EnumX – Full CPTS Automation Framework
    2
    3 ```
    4 ███████╗███╗   ██╗██╗   ██╗███╗   ███╗██╗  ██╗
    5 ██╔════╝████╗  ██║██║   ██║████╗ ████║╚██╗██╔╝
    6 █████╗  ██╔██╗ ██║██║   ██║██╔████╔██║ ╚███╔╝
    7 ██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║ ██╔██╗
    8 ███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║██╔╝ ██╗
    9 ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝
   10 ```
   11
   12 > ⚠️ **For authorized penetration testing and CTF/lab environments only (HTB, CPTS, etc.)**
   13
   14 A fully interactive, modular Python recon-to-report automation tool built for the **HTB CPTS certification** wo
      rkflow. Every module is prompted individually — you stay in control of what runs.
   15
   16 ---
   17
   18 ## Features
   19
   20 | Category | Tools / Techniques |
   21 |---|---|
   22 | **Recon** | Nmap (full/quick/custom + evasion), WAF detection, DNS, CRT.sh subdomains, VHOST brute |
   23 | **Web** | whatweb, gobuster, feroxbuster, nikto, wfuzz, sqlmap, LFI probe, web shell test |
   24 | **SMB** | Share discovery, credential × share access matrix, write test, enum4linux-ng, MS17-010 |
   25 | **FTP** | Anonymous login, medusa, hydra brute |
   26 | **SSH** | Banner enum, default creds, hydra brute |
   27 | **LDAP** | Anonymous bind, naming context dump, full tree dump |
   28 | **RDP** | Vuln check (MS12-020), ncrack/hydra brute |
   29 | **SNMP** | Community string enum (snmpwalk) |
   30 | **Databases** | MySQL, MSSQL (xp_cmdshell, xp_dirtree hash capture), PostgreSQL default creds |
   31 | **Active Directory** | Kerbrute, AS-REP Roasting, Kerberoasting, BloodHound, password spray, PTH, DCSync, NTD
      S.dit |
   32 | **Credentials** | hashcat, John, Responder + NTLM relay, CeWL wordlist generation |
   33 | **Post-Linux** | linpeas auto-upload + critical findings parser, linux-exploit-suggester, checklist |
   34 | **Post-Windows** | winpeas auto-upload, LSASS dump (pypykatz), SAM dump (secretsdump), checklist |
   35 | **Lateral Movement** | evil-winrm, psexec, wmiexec, xfreerdp PTH |
   36 | **Shells** | 6 reverse shell one-liners, msfvenom payloads (ELF/EXE/PHP/ASPX) |
   37 | **Exploits** | searchsploit per service + auto-pull + auto-run matched exploits |
   38 | **Reporting** | Markdown + HTML report, SMB access matrix table, HTB writeup skeleton, session log |
   39
   40 ---
   41
   42 ## Requirements
   43
   44 ```bash
   45 # Core
   46 sudo apt install nmap smbclient enum4linux-ng netexec crackmapexec \
   47   hydra medusa ncrack gobuster feroxbuster nikto wfuzz sqlmap \
   48   snmpwalk ldap-utils impacket-scripts bloodhound.py \
   49   sshpass responder hashcat john kerbrute
   50
   51 # Python packages
   52 pip3 install impacket pypykatz
   53
   54 # Optional
   55 sudo apt install whatweb wafw00f feroxbuster nikto
   56 ```
   57
   58 > Most tools come pre-installed on **Kali Linux**.
   59
   60 ---
   61
   62 ## Usage
   63
   64 ### Basic
   65 ```bash
   66 python3 enumx_v4.py --target 10.10.10.10
   67 ```
   68
   69 ### Full options
   70 ```bash
   71 python3 enumx_v4.py \
   72   --target 10.10.10.10 \
   73   --lhost 10.10.14.5 \
   74   --domain inlanefreight.local \
   75   --dc-ip 10.10.10.10 \
   76   --creds creds.txt \
   77   --userlist users.txt \
   78   --passlist /usr/share/wordlists/rockyou.txt
   79 ```
   80
   81 ### Skip nmap (use existing XML)
   82 ```bash
   83 python3 enumx_v4.py --target 10.10.10.10 --skip-nmap --nmap-xml ./nmap.xml
   84 ```
   85
   86 ### Arguments
   87
   88 | Flag | Description |
   89 |---|---|
   90 | `--target` | Target IP or hostname **(required)** |
   91 | `--lhost` | Your IP for reverse shells and payloads |
   92 | `--domain` | Active Directory domain name |
   93 | `--dc-ip` | Domain Controller IP |
   94 | `--creds` | Credentials file (`user:pass` per line) |
   95 | `--userlist` | Default user list for brute force modules |
   96 | `--passlist` | Default password list for brute force modules |
   97 | `--skip-nmap` | Skip nmap, use existing XML with `--nmap-xml` |
   98 | `--nmap-xml` | Path to existing nmap XML |
   99 | `--no-color` | Disable colored output |
  100
  101 ---
  102
  103 ## Workflow
  104
  105 ```
  106 Target IP
  107     │
  108     ▼
  109 ┌─────────────────┐
  110 │   Nmap Scan     │  Full / Quick / Custom + optional IDS evasion
  111 └────────┬────────┘
  112          │
  113          ▼
  114 ┌─────────────────────┐
  115 │  Machine Profiler   │  Auto-detects: Windows DC / MSSQL / Linux Web / etc.
  116 │  + HTB Hints        │  Suggests attack path + warns on unusual ports
  117 └────────┬────────────┘
  118          │
  119          ▼  (each module prompted individually)
  120     ┌────┴─────┐
  121     │  Service │──► HTTP → Web Attacks (gobuster/nikto/sqlmap/LFI/wfuzz)
  122     │  Dispatch│──► SMB  → Share discovery + access matrix per user
  123     │          │──► FTP  → Anonymous + brute
  124     │          │──► SSH  → Default creds + hydra
  125     │          │──► LDAP → Anonymous bind + dump
  126     │          │──► RDP  → Vuln check + brute
  127     │          │──► SNMP → Community strings
  128     │          │──► DB   → MySQL/MSSQL/PgSQL default creds + xp_cmdshell
  129     └────┬─────┘
  130          │
  131          ▼
  132 ┌──────────────────┐
  133 │  AD Attacks      │  Kerbrute → ASREPRoast → Kerberoast → BloodHound
  134 │                  │  Password spray → PTH → DCSync → NTDS dump
  135 └────────┬─────────┘
  136          │
  137          ▼
  138 ┌──────────────────┐
  139 │  Post-Exploit    │  linpeas auto-upload → critical findings parsed
  140 │                  │  winpeas upload → LSASS/SAM dump parsing
  141 │                  │  linux-exploit-suggester
  142 └────────┬─────────┘
  143          │
  144          ▼
  145 ┌──────────────────┐
  146 │  Lateral Move    │  evil-winrm / psexec / wmiexec / xfreerdp PTH
  147 └────────┬─────────┘
  148          │
  149          ▼
  150 ┌──────────────────┐
  151 │  Searchsploit    │  Per service → auto-pull exploit → ask to run
  152 └────────┬─────────┘
  153          │
  154          ▼
  155 ┌──────────────────┐
  156 │  Reports         │  report.md + report.html + writeup_skeleton.md
  157 │                  │  session_log.txt (every command + output)
  158 └──────────────────┘
  159 ```
  160
  161 ---
  162
  163 ## SMB Access Matrix
  164
  165 After SMB enumeration, EnumX builds a full access matrix showing which user has access to which share and at wh
      at permission level:
  166
  167 ```
  168 | Share    | anonymous | administrator | john   | alice  |
  169 |----------|-----------|---------------|--------|--------|
  170 | ADMIN$   | -         | READ/WRITE    | -      | -      |
  171 | C$       | -         | READ/WRITE    | -      | -      |
  172 | IPC$     | READ      | READ/WRITE    | READ   | READ   |
  173 | Users    | -         | READ/WRITE    | READ   | READ   |
  174 | Finance  | -         | READ/WRITE    | -      | READ/WRITE |
  175 ```
  176
  177 Write access is automatically tested and flagged as **CRITICAL** (potential RCE via SCF/DLL drop).
  178 File listings for each accessible share are saved to `enumx_out/<target>/<ts>/smb/listing_<share>_<user>.txt`.
  179
  180 ---
  181
  182 ## Output Structure
  183
  184 ```
  185 enumx_out/
  186 └── 10.10.10.10/
  187     └── 20250419-143022/
  188         ├── nmap.xml / nmap.txt
  189         ├── session_log.txt          # every command + timestamp + output
  190         ├── report.md                # full markdown report
  191         ├── report.html              # styled HTML report
  192         ├── writeup_skeleton.md      # HTB-style writeup template
  193         ├── recon/                   # WAF, DNS, CRT.sh, VHOST
  194         ├── web/                     # gobuster, nikto, sqlmap, LFI, wfuzz
  195         ├── smb/                     # shares, access matrix, file listings
  196         ├── ftp/                     # anonymous login, brute results
  197         ├── ssh/                     # banner, cred test, hydra
  198         ├── ldap/                    # naming contexts, full dump
  199         ├── rdp/                     # vuln check, brute
  200         ├── snmp/                    # community string results
  201         ├── db/                      # mysql/mssql/postgresql results
  202         ├── ad/                      # kerbrute, asrep, kerberoast, bloodhound, dcsync
  203         ├── creds/                   # hashcat, john, responder, cewl
  204         ├── post_linux/              # linpeas, les, checklist
  205         ├── post_windows/            # winpeas, pypykatz, secretsdump, checklist
  206         ├── lateral/                 # lateral movement notes
  207         ├── shells/                  # reverse shells, msfvenom payloads
  208         └── searchsploit/            # per-service exploit results
  209 ```
  210
  211 ---
  212
  213 ## Credentials File Format
  214
  215 ```
  216 administrator:Password123
  217 john:Welcome1
  218 alice:Summer2024!
  219 ```
  220
  221 Pass with `--creds creds.txt`. All credentials are automatically tested against every discovered SMB share, SSH
      , DB, WinRM, and AD modules.
  222
  223 ---
  224
  225 ## Report Output
  226
  227 ### HTML Report
  228 Dark-themed, color-coded by severity (CRITICAL / HIGH / MEDIUM / INFO). Includes:
  229 - Credentials found (top of report)
  230 - Full findings table with severity
  231 - Timeline (every event with timestamp)
  232 - SMB access matrix
  233
  234 ### Writeup Skeleton
  235 Auto-generated `writeup_skeleton.md` pre-filled with:
  236 - Discovered services
  237 - High/critical findings
  238 - Screenshot placeholders (`[screenshot: name.png]`)
  239 - Flags table
  240 - Key takeaways section
  241
  242 ---
  243
  244 ## Example Creds File
  245
  246 ```
  247 # creds.txt
  248 administrator:Password123!
  247 # creds.txt
  248 administrator:Password123!
  249 svc-backup:Backup2024
  250 john.doe:Welcome1
  251 ```
  252
  253 ---
  254
  255 ## Disclaimer
  256
  257 This tool is intended **only** for:
  258 - Authorized penetration testing engagements
  259 - CTF competitions (HackTheBox, TryHackMe, etc.)
  260 - Security certification labs (CPTS, OSCP, etc.)
  261 - Educational and research purposes
  262
  263 **Do not use against systems you do not have explicit written permission to test.**
  264
  265 ---
  266
  267 ## Author
  268
  269 **0xZoro** – CPTS student | HTB enthusiast
  270 Notes & Cheatsheet: [0xzoro.gitbook.io](https://0xzoro.gitbook.io/0xzoro/cpts/cpts-cheat-sheet)
