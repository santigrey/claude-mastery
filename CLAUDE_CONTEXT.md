# CLAUDE CONTEXT ??? Project Ascension
# ANY CLAUDE INSTANCE MUST READ THIS BEFORE MODIFYING SYSTEM CONFIG
# Last updated: 2026-03-25

## IDENTITY
- Name: Sloan
- GitHub email: sloanz_j@icloud.com (iCloud ??? NOT gmail)
- Gmail: james.3sloan@gmail.com
- GitHub: github.com/santigrey

## MACHINES

| Machine | Alias | IP | SSH User | OS | Role |
|---------|-------|----|----------|----|------|
| Cortez | ??? | N/A | sloan | Windows 11 | Thin client, dev workstation, no GPU |
| JesAir | jesair | 192.168.1.155 | jes | macOS (M2) | Primary dev, claude-mastery repo |
| Mac Mini | macmini | 192.168.1.13 | jes | macOS | Command center |
| CiscoKid | ciscokid | 192.168.1.10 | jes | Ubuntu 22.04 | Control plane, pgvector, MCP server |
| TheBeast | thebeast | 192.168.1.152 | jes | Ubuntu | GPU inference, Ollama, Tesla T4 |
| SlimJim | slimjim | 192.168.1.40 | jes | Ubuntu | Edge node, Dell R340 |
| KaliPi | kalipi | 192.168.1.254 | sloan | Kali Linux | Pentesting, RPi5 |

## SSH RULES
- Username is jes on ALL hosts EXCEPT KaliPi which is sloan
- Cortez has TWO keys: id_ed25519 (passphrase-protected) and id_ed25519_mcp (no passphrase)
- Both keys are in authorized_keys on all hosts
- SSH config on Cortez lists both keys per host
- JesAir has keys: id_ed25519, id_ed25519_github, id_ed25519_mcp, id_rsa
- Mac Mini has keys: id_ed25519, id_ed25519_github

## GIT CONFIG
- git user.name: Sloan
- git user.email: sloanz_j@icloud.com
- NEVER change the git email. It is the iCloud account, NOT gmail.

## CORTEZ SOFTWARE STATE (as of 2026-03-25)
- Python 3.13.12 (303 packages)
- PyTorch 2.11.0+cpu (CPU only ??? no GPU on thin client)
- Ollama 0.18.2 (phi3:mini, tinyllama)
- Git 2.53.0
- Docker Desktop 29.2.1 (containers run on SERVERS, not Cortez)
- Python Scripts PATH: C:\Users\sloan\AppData\Local\Programs\Python\Python313\Scripts

## ARCHITECTURE RULES
1. Cortez is a THIN CLIENT ??? no GPU, no heavy compute
2. TheBeast handles GPU inference (Tesla T4, Ollama)
3. CiscoKid handles data/pgvector/MCP
4. Docker containers run on servers, not on Cortez
5. JesAir is primary dev with claude-mastery repo at ~/claude-mastery

## RULES FOR ANY CLAUDE INSTANCE
1. READ this file before modifying ANY system config
2. NEVER change git email ??? it is sloanz_j@icloud.com
3. NEVER overwrite SSH config without showing existing contents first
4. NEVER assume SSH usernames ??? they are documented above
5. ALWAYS audit existing state before changing config files
6. When in doubt, DIAGNOSE before modifying
7. Ask before installing software that changes system state

## REPOS
- claude-mastery: github.com/santigrey/claude-mastery (on JesAir at ~/claude-mastery)
- Clawdbot v0.1 running, evals at 100%

## ENVIRONMENT FILES
- JesAir venv: ~/claude-mastery/.venv
- API key: in ~/claude-mastery/.env on JesAir
- Cortez template: C:\Users\sloan\.env.template
