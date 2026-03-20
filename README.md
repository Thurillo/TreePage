# 🌳 TreePage

**Aggregatore di servizi e dashboard per operatori intranet.**

TreePage consente di creare dashboard personalizzate per ogni operatore, raggruppando in un'unica schermata link a servizi esterni, pagine HTML ospitate localmente e microservizi Python.

---

## Funzionalità

- **Dashboard per utente** – ogni operatore ha la propria schermata con tile dei servizi
- **3 tipi di tile** – link esterno, progetto HTML statico, microservizio Python proxato
- **Pannello admin protetto** – login con sessione per gestire utenti, tile, progetti e script
- **Cambio password** – aggiornabile direttamente dall'interfaccia web
- **Flash messages** – feedback visivo per ogni operazione nell'admin
- **Proxy integrato** – i microservizi Python vengono esposti su `/api/scripts/{nome}/`
- **Zero database** – configurazione su file YAML, nessuna dipendenza esterna
- **Tema dark** – interfaccia responsive con tema scuro

---

## Struttura del progetto

```
TreePage/
├── main.py                    # Entry point FastAPI + SessionMiddleware
├── config.py                  # Gestione YAML, auth, flash messages
├── requirements.txt
├── auth.yaml                  # Credenziali admin (auto-generato, NON in git)
├── scripts_registry.yaml      # Registro dei microservizi Python
│
├── routers/
│   ├── admin.py               # CRUD utenti/tile/script (protetto da login)
│   ├── dashboard.py           # Dashboard pubbliche degli operatori
│   └── scripts_proxy.py       # Proxy HTTP verso i microservizi
│
├── templates/
│   ├── base.html              # Layout base con topbar
│   ├── users_list.html        # Lista dashboard disponibili
│   ├── dashboard.html         # Dashboard di un operatore
│   └── admin/
│       ├── index.html         # Pannello admin principale
│       ├── user_edit.html     # Editor utente e tile
│       ├── login.html         # Pagina di login
│       └── change_password.html
│
├── static/
│   ├── css/style.css
│   └── js/app.js
│
├── users/                     # Un file YAML per operatore
│   └── admin.yaml
│
├── projects/                  # Pagine HTML ospitate (servite da Nginx in prod)
│   └── example-project/
│       └── index.html
│
├── scripts/                   # Microservizi Python
│   └── example-script/
│       ├── main.py
│       └── requirements.txt
│
├── deploy/
│   ├── setup.sh               # Script di installazione per Debian 13
│   ├── treepage.service       # Systemd service per il backend
│   └── treepage-script@.service  # Template service per i microservizi
│
└── nginx/
    └── treepage.conf          # Configurazione Nginx
```

---

## Avvio rapido (sviluppo locale)

```bash
git clone https://github.com/Thurillo/TreePage.git
cd TreePage

python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

pip install -r requirements.txt
uvicorn main:app --reload
```

L'app sarà disponibile su `http://localhost:8000`.

### Primo accesso

Al primo avvio viene creato automaticamente `auth.yaml` con le credenziali predefinite:

| Campo    | Valore  |
|----------|---------|
| Utente   | `admin` |
| Password | `admin` |

> **Cambia immediatamente la password** dalla pagina `http://localhost:8000/admin/change-password` (icona 🔑 in alto a destra dopo il login).

---

## Installazione su Debian 12/13 LXC (produzione)

### Prerequisiti

| Requisito | Dettaglio |
|-----------|-----------|
| Sistema operativo | Debian 12 (Bookworm) o Debian 13 (Trixie) |
| Accesso | Root o utente con `sudo` |
| Connessione internet | Necessaria durante l'installazione |

> Tutto il software necessario (Python 3, pip, venv, Nginx, git) viene **installato automaticamente** dallo script. Non è necessario installare nulla prima, tranne `git` per clonare il repository.

### Passo 1 — Installa git e clona il repository

Su una Debian appena installata `git` potrebbe non essere presente. Installalo con:

```bash
apt-get update && apt-get install -y git
```

Poi clona il repository:

```bash
git clone https://github.com/Thurillo/TreePage.git
cd TreePage
```

### Passo 2 — Esegui lo script di installazione

```bash
sudo bash deploy/setup.sh
```

Lo script esegue automaticamente tutto il resto:

| Step | Cosa fa |
|------|---------|
| 1/7 | Installa Python 3, pip, venv, Nginx, curl, git |
| 2/7 | Crea l'utente di sistema `treepage` (nologin, nessuna shell) |
| 3/7 | Copia i file dell'applicazione in `/opt/treepage` |
| 4/7 | Crea il virtualenv Python e installa le dipendenze |
| 5/7 | Installa e **abilita** i servizi systemd (avvio automatico al boot) |
| 6/7 | Configura Nginx come reverse proxy e lo avvia |
| 7/7 | Mostra l'URL di accesso e le credenziali predefinite |

Al termine viene mostrato l'indirizzo IP con cui accedere all'app.

### Passo 3 — Primo accesso e cambio password

1. Aprire `http://<IP-del-server>/admin/`
2. Fare login con `admin` / `admin`
3. Cliccare 🔑 in alto a destra e **cambiare subito la password**

### URL principali

| URL | Descrizione |
|-----|-------------|
| `http://<host>/` | Redirect alle dashboard |
| `http://<host>/dashboard/` | Lista di tutte le dashboard |
| `http://<host>/dashboard/<slug>` | Dashboard di un operatore |
| `http://<host>/admin/` | Pannello admin (richiede login) |
| `http://<host>/admin/login` | Pagina di accesso |
| `http://<host>/api/docs` | Documentazione API automatica |

---

## Avvio automatico al riavvio

**Non è necessario fare nulla dopo un riavvio del server.** TreePage e Nginx sono registrati come servizi systemd e si avviano automaticamente.

Questo è garantito da:

| Servizio | Abilitato automaticamente |
|----------|--------------------------|
| `treepage` (backend FastAPI) | ✅ `systemctl enable` eseguito da `setup.sh` |
| `nginx` (reverse proxy) | ✅ abilitato di default su Debian |

Per verificarlo:

```bash
systemctl is-enabled treepage   # output: enabled
systemctl is-enabled nginx      # output: enabled
```

### Microservizi Python

I microservizi aggiuntivi (`treepage-script@`) **non** sono abilitati automaticamente. Dopo averli registrati nel pannello admin, abilita l'avvio automatico con:

```bash
sudo systemctl enable treepage-script@nome-script
```

---

## Persistenza dei dati

**No, non si perdono dati in caso di riavvio improvviso.**

Tutti i dati di TreePage sono salvati come **file su disco**, non in memoria:

| Dove | Cosa contiene |
|------|---------------|
| `/opt/treepage/users/*.yaml` | Dashboard e tile di ogni operatore |
| `/opt/treepage/projects/` | Pagine HTML ospitate |
| `/opt/treepage/scripts/` | Codice dei microservizi Python |
| `/opt/treepage/scripts_registry.yaml` | Registro dei microservizi |
| `/opt/treepage/auth.yaml` | Credenziali admin |

L'unica cosa che viene persa al riavvio sono le **sessioni di login attive**: dopo il riavvio del server l'amministratore dovrà fare nuovamente login nel pannello admin. Nessun dato utente viene perso.

### Backup consigliato

Per un backup completo è sufficiente copiare l'intera directory `/opt/treepage`:

```bash
# Backup manuale
tar -czf treepage-backup-$(date +%F).tar.gz /opt/treepage

# Backup automatico giornaliero con cron (aggiungere con: crontab -e)
0 3 * * * tar -czf /root/treepage-backup-$(date +\%F).tar.gz /opt/treepage
```

---

## Utilizzo del pannello admin

### Accesso

Aprire `/admin/` – se non autenticati si viene reindirizzati automaticamente a `/admin/login`.

Credenziali predefinite: `admin` / `admin`

**Icone nella topbar (solo da autenticati):**
- 🔑 – Cambio password
- 🚪 – Logout

### Creare una dashboard utente

1. Admin → **Nuovo utente**
2. Compilare: slug (es. `mario`), nome visualizzato, emoji
3. Aprire l'utente e aggiungere le tile

In alternativa, creare manualmente `users/<slug>.yaml`:

```yaml
name: Mario Rossi
description: Dashboard operatore
icon: "👷"
tiles:
  - title: Gestionale
    type: external
    url: http://192.168.1.10:8080
    icon: "📋"
    description: ERP aziendale
    category: Lavoro
  - title: Report settimanale
    type: project
    project: report-html
    icon: "📊"
    description: Report generato in HTML
    category: Report
```

### Tipi di tile

| Tipo | Chiave YAML | Descrizione |
|------|-------------|-------------|
| `external` | `url: https://...` | Link a qualsiasi URL esterno o interno |
| `project` | `project: slug` | Pagina HTML ospitata in `projects/<slug>/` |
| `script` | `script: nome` | Microservizio Python proxato da TreePage |

---

## Ospitare un progetto HTML

### Tramite il pannello admin

1. Admin → sezione **Progetti** → **Crea progetto** (inserire uno slug, es. `mappa`)
2. Il progetto viene creato in `projects/mappa/` con un `index.html` di esempio
3. Sostituire il contenuto con il proprio HTML

### Via SCP/SFTP

```bash
# Copia locale → server
scp -r ./mia-app/* root@<host>:/opt/treepage/projects/mappa/
```

Il progetto sarà accessibile su `/projects/mappa/` (servito direttamente da Nginx in produzione).

---

## Aggiungere un microservizio Python

I microservizi sono app FastAPI (o qualsiasi server HTTP ASGI) che girano su porte locali.

### 1. Struttura dello script

```
scripts/
└── mio-script/
    ├── main.py
    └── requirements.txt   # dipendenze aggiuntive (opzionale)
```

`main.py` minimo:

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def index():
    return {"status": "ok", "service": "mio-script"}
```

### 2. Registrare nel pannello admin

Admin → sezione **Script** → **Aggiungi script**:
- Nome (slug, es. `mio-script`)
- Nome visualizzato
- Porta (es. `8001`)

### 3. Avviare e abilitare il servizio systemd

```bash
sudo systemctl start  treepage-script@mio-script   # avvia ora
sudo systemctl enable treepage-script@mio-script   # avvio automatico al boot
sudo systemctl status treepage-script@mio-script   # verifica stato
```

Il microservizio sarà proxato su `/api/scripts/mio-script/`.

### Porte consigliate

| Range | Uso |
|-------|-----|
| `8001–8099` | Microservizi TreePage |
| `8000` | Backend TreePage (riservato) |

---

## Aggiornamento

```bash
cd /opt/treepage

# 1. Aggiorna il codice
sudo -u treepage git pull

# 2. Aggiorna le dipendenze Python (se requirements.txt è cambiato)
sudo -u treepage .venv/bin/pip install -r requirements.txt

# 3. Riavvia il backend
sudo systemctl restart treepage
```

---

## Comandi utili

```bash
# Stato dei servizi
systemctl status treepage
systemctl status nginx
systemctl status treepage-script@example-script

# Log in tempo reale
journalctl -u treepage -f
journalctl -u treepage-script@example-script -f

# Verificare l'avvio automatico
systemctl is-enabled treepage     # → enabled
systemctl is-enabled nginx        # → enabled

# Riavvio manuale
systemctl restart treepage

# Avviare/fermare/abilitare uno script
systemctl start  treepage-script@mio-script
systemctl stop   treepage-script@mio-script
systemctl enable treepage-script@mio-script
```

---

## Formato YAML di riferimento

### `users/<slug>.yaml`

```yaml
name: Nome Visualizzato
description: Descrizione breve (opzionale)
icon: "🧑"
tiles:
  - title: Titolo della tile
    type: external          # external | project | script
    url: https://...        # per type: external
    project: slug-progetto  # per type: project
    script: nome-script     # per type: script
    icon: "🔗"
    description: Descrizione breve
    category: Nome Categoria
    color: "#ff6b6b"        # colore bordo sinistro (opzionale)
```

### `scripts_registry.yaml`

```yaml
scripts:
  nome-script:
    name: Nome Visualizzato
    port: 8001
    description: Descrizione del servizio
    autostart: true
    path: /opt/treepage/scripts/nome-script
```

### `auth.yaml` *(auto-generato, non in git)*

```yaml
username: admin
password: la-tua-password
secret_key: <stringa esadecimale a 64 caratteri generata automaticamente>
```

---

## Sicurezza

- `auth.yaml` è escluso da git (contiene la password in chiaro)
- Cambiare la password predefinita `admin/admin` subito dopo l'installazione
- TreePage è pensato per reti **intranet fidate**: non esporre il pannello admin su internet senza protezione aggiuntiva
- Il servizio systemd usa `NoNewPrivileges=true` e `ProtectSystem=strict`
- Nginx aggiunge gli header `X-Frame-Options`, `X-Content-Type-Options` e `Referrer-Policy`
- Per ambienti esposti, valutare l'aggiunta di HTTPS (Let's Encrypt o certificato self-signed)
