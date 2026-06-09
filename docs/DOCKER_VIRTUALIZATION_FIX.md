# Docker Desktop — « Virtualization support not detected »

## Diagnostic actuel (Windows 11 Famille)

| Contrôle | État détecté | Action |
|----------|--------------|--------|
| **Virtualisation CPU (BIOS)** | Vous indiquez **activée** ; WMI peut rester `False` jusqu’au **redémarrage** | Redémarrer une fois après BIOS |
| **WSL2** | **Non installé** (`wsl` → sous-système absent) | **Bloquant actuel** — voir ci-dessous |
| **Hyper-V complet** | **Non disponible** sur édition Famille | Normal — utiliser **moteur WSL2** uniquement |
| **Docker Desktop** | Installé ; `com.docker.service` arrêté | Démarre après WSL2 OK |

Sur **Windows 11 Famille**, Docker doit utiliser le backend **WSL 2** (pas Hyper-V classique). Sans WSL installé, Docker affiche souvent *Virtualization support not detected* même avec le BIOS correct.

---

## Étape 1 — Activer la virtualisation dans le BIOS (obligatoire)

1. **Redémarrer** le PC.
2. Ouvrir le BIOS Lenovo : touche **F1** ou **F2** au démarrage (ou menu **Novo** : petit bouton latéral → BIOS Setup).
3. Chercher une option du type :
   - **Intel Virtualization Technology** → **Enabled**
   - ou **VT-x** / **Virtualization** → **Enabled**
   - Sur certains Lenovo : *Configuration* → *Intel Virtual Technology*
4. **Sauvegarder** (F10) et redémarrer sous Windows.

### Vérifier sous Windows (après redémarrage)

PowerShell :

```powershell
(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled
```

**Attendu :** `True`

Ou lancer :

```powershell
.\scripts\check_virtualization.ps1
```

---

## Étape 2 — Installer WSL2 (bloquant actuel — PowerShell **administrateur**)

**Script automatique (recommandé) :**

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee
# Clic droit PowerShell → Exécuter en tant qu'administrateur
.\scripts\enable_wsl2_for_docker.ps1
```

**Ou manuellement :**

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart
wsl --install
```

**Redémarrer Windows** (obligatoire en général), puis :

```powershell
wsl --set-default-version 2
wsl --update
wsl --status
wsl -l -v
```

**Attendu :** WSL version **2**, une distribution (ex. Ubuntu) en cours d’exécution ou « Stopped ».

### Si `wsl --install` échoue — activation manuelle

Toujours en **admin** :

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Redémarrer, puis :

```powershell
wsl --install
```

---

## Étape 3 — Hyper-V (si nécessaire)

Docker Desktop sur Windows utilise en général le backend **WSL2** (recommandé). Hyper-V complet n’est pas toujours requis.

Si Docker demande encore Hyper-V (édition **Pro/Enterprise**) :

```powershell
# Admin
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All
```

**Windows Home :** pas de Hyper-V complet — rester sur **WSL2** dans Docker Desktop → Settings → General → *Use the WSL 2 based engine*.

---

## Étape 4 — Docker Desktop sur backend WSL2

1. Lancer **Docker Desktop**.
2. **Settings** (engrenage) → **General** :
   - cocher **Use the WSL 2 based engine**
   - décocher **Use the Hyper-V backend** (si visible ; souvent absent sur Famille)
3. **Settings** → **Resources** → **WSL integration** :
   - activer votre distribution (ex. Ubuntu)
4. **Apply & restart**.
5. Vérifier :

```powershell
docker info
```

Sans erreur « virtualization ». Le contexte doit mentionner WSL.

---

## Étape 5 — Reprendre la validation téléconsultation

Quand `docker info` fonctionne :

```powershell
cd C:\Users\wandassai\Downloads\plateforme-sante-guinee

# 1) Jitsi local
.\scripts\start_jitsi_dev.ps1

# 2) Tunnel Jitsi (terminal séparé, laisser ouvert)
.\scripts\tunnel\start-jitsi-cloudflared.ps1
# Copier l’URL puis :
.\scripts\apply_jitsi_tunnel_domain.ps1 -TunnelUrl "https://XXXX.trycloudflare.com"

# 3) Redémarrer backend + frontend
.\scripts\qa_start_backend.ps1
cd frontend-sante\frontend ; npm run dev:tunnel

# 4) Tunnel app (iPhone)
.\scripts\tunnel\start-cloudflared.ps1

# 5) Appel réel
# Médecin : http://localhost:5173/consultation/16
# Patient : https://APP-XXX.trycloudflare.com/consultation/16
```

Grille GO/NO GO : [`docs/TELECONSULT_REAL_CALL_PROCEDURE.md`](TELECONSULT_REAL_CALL_PROCEDURE.md)

---

## Ordre des priorités

```text
BIOS VT-x = True  →  WSL2 installé  →  Docker running  →  Jitsi  →  tunnels  →  appel PC ↔ iPhone
```

Ne pas installer/configurer WSL2 tant que le BIOS n’expose pas la virtualisation (`VirtualizationFirmwareEnabled = True`).
