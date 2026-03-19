# 🌳 TreePage

Aggregatore di servizi e dashboard per operatori intranet.
Permette di creare dashboard personalizzate con link a servizi esterni, pagine HTML ospitate localmente e microservizi Python.

---

## Funzionalità

- **Dashboard per utente** – ogni operatore ha la propria schermata con le tile dei servizi
- **Tre tipi di tile** – link esterno, progetto HTML ospitato, microservizio Python
- **Pannello admin** – interfaccia web per gestire utenti, tile, progetti e script
- **Proxy integrato** – i microservizi Python vengono esposti tramite `/api/scripts/{nome}/`
- **Tema dark** – interfaccia responsive con tema scuro
- **Configurazione YAML** – nessun database, tutto su file

---

## Requisiti

- Python 3.11+
- Nginx
- Debian 12/13 (per il deploy in produzione)

---

## Avvio in sviluppo (locale)

```bash
git clone https://github.com/Thurillo/TreePage.git
cd TreePage

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload
```

L'app sarà disponibile su `http://localhost:8000`.

Al primo avvio viene creato automaticamente il file `auth.yaml` con le credenziali default:
- **Utente:** `admin`
- **Password:** `admin`

> Cambia la password subito dopo il primo accesso tramite il pannello admin.

---

## Installazione su Debian 13 LXC (produzione)

```bash
git clone https://github.com/Thurillo/TreePage.git
cd TreePage
sudo bash deploy/setup.sh
```

Lo script esegue automaticamente:
1. Installazione dipendenze di sistema (Python, Nginx)
2. Creazione utente di sistema `treepage`
3. Copia dei file in `/opt/treepage`
4. Creazione del virtualenv e installazione dipendenze Python
5. Installazione e avvio dei servizi systemd
6. Configurazione Nginx come reverse proxy

Al termine, l'applicazione è raggiungibile su `http://<IP-del-server>/`.

### URL principali

| URL | Descrizione |
|---|---|
| `http://<host>/` | Redirect alle dashboard |
| `http://<host>/dashboard/` | Lista di tutte le dashboard |
| `http://<host>/dashboard/<slug>` | Dashboard di un utente |
| `http://<host>/admin/` | Pannello di amministrazione |
| `http://<host>/api/docs` | Documentazione API automatica |

---

## Primo accesso e sicurezza

1. Aprire `http://<host>/admin/` – si verrà reindirizzati alla pagina di login
2. Accedere con `admin` / `admin`
3. Cliccare sull'icona 🔑 in alto a destra per **cambiare la password**
4. Per uscire, cliccare sull'icona 🚪 (logout)

> **Nota:** TreePage è pensato per reti intranet fidate. Non esporre il pannello admin su internet senza aggiungere ulteriore protezione (es. autenticazione Nginx, VPN).

---

## Aggiungere una dashboard utente

Dal pannello admin (`/admin/`):

1. Cliccare **Nuovo utente**
2. Inserire slug (es. `mario`), nome visualizzato e icona emoji
3. Aprire l'utente appena creato e aggiungere le tile desiderate

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
```

---

## Ospitare un progetto HTML

1. Dal pannello admin, sezione **Progetti**, creare un nuovo progetto (es. `mappa`)
2. Il progetto viene creato in `projects/mappa/` con un `index.html` di esempio
3. Sostituire `index.html` con il proprio contenuto HTML
4. Il progetto sarà disponibile su `/projects/mappa/`

Per caricare file via SCP/SFTP:

```bash
scp -r ./mia-app/* treepage@<host>:/opt/treepage/projects/mappa/
```

---

## Aggiungere un microservizio Python

I microservizi sono app FastAPI (o qualsiasi server HTTP) che girano su porte locali.

### 1. Creare lo script

```
scripts/
└── mio-script/
    ├── main.py
    └── requirements.txt
```

`main.py` di esempio:

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def index():
    return {"status": "ok"}
```

### 2. Registrare nel pannello admin

Nella sezione **Script**, inserire:
- Nome identificativo (slug)
- Nome visualizzato
- Porta (es. `8001`)

### 3. Avviare il servizio

```bash
sudo systemctl start treepage-script@mio-script
sudo systemctl enable treepage-script@mio-script  # avvio automatico
```

Il microservizio sarà accessibile tramite proxy su `/api/scripts/mio-script/`.

---

## Formato YAML di riferimento

### `users/<slug>.yaml`

```yaml
name: Nome Visualizzato
description: Descrizione opzionale
icon: "🧑"
tiles:
  - title: Titolo tile
    type: external        # external | project | script
    url: https://...      # per type: external
    project: slug-progetto  # per type: project
    script: nome-script   # per type: script
    icon: "🔗"
    description: Descrizione breve
    category: Categoria
    color: "#ff6b6b"      # colore bordo sinistro (opzionale)
```

### `scripts_registry.yaml`

```yaml
scripts:
  nome-script:
    name: Nome Visualizzato
    port: 8001
    description: Descrizione
    autostart: true
    path: /opt/treepage/scripts/nome-script
```

---

## Aggiornamento

```bash
cd /opt/treepage
sudo -u treepage git pull
sudo -u treepage .venv/bin/pip install -r requirements.txt
sudo systemctl restart treepage
```

---

## Note di sicurezza

- Cambiare la password admin dopo il primo accesso
- `auth.yaml` contiene la password in chiaro: non committarlo (è già in `.gitignore`)
- L'applicazione è progettata per intranet: non esporre direttamente su internet
- Per ambienti condivisi, considerare l'aggiunta di HTTPS (Let's Encrypt o certificato self-signed)
