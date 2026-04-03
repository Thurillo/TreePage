#!/usr/bin/env bash
# =============================================================
# TreePage – Setup script per Debian 13 (Trixie) su LXC
# Uso: bash setup.sh
# =============================================================

set -euo pipefail

INSTALL_DIR="/opt/treepage"
TREEPAGE_USER="treepage"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================"
echo "  TreePage – Installazione su Debian 13"
echo "========================================"

# ── 1. Dipendenze di sistema ──────────────────────────────
echo "[1/7] Installazione dipendenze di sistema..."
apt-get update -q
apt-get install -y -q \
    python3 python3-pip python3-venv \
    nginx \
    curl git rsync

# ── 2. Utente di sistema ──────────────────────────────────
echo "[2/7] Creazione utente di sistema '$TREEPAGE_USER'..."
if ! id "$TREEPAGE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$TREEPAGE_USER"
fi

# ── 3. Directory di installazione ────────────────────────
echo "[3/7] Configurazione directory $INSTALL_DIR..."

REMOTE_URL=$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)
CURRENT_BRANCH=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

if [ -n "$REMOTE_URL" ]; then
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "     Repository esistente – aggiornamento..."
        git -c safe.directory="$INSTALL_DIR" -C "$INSTALL_DIR" fetch origin "$CURRENT_BRANCH"
        git -c safe.directory="$INSTALL_DIR" -C "$INSTALL_DIR" reset --hard FETCH_HEAD
    else
        echo "     Clone da $REMOTE_URL (branch: $CURRENT_BRANCH)..."
        rm -rf "$INSTALL_DIR"
        git clone --branch "$CURRENT_BRANCH" "$REMOTE_URL" "$INSTALL_DIR"
    fi
else
    echo "     Nessun remote trovato – copia locale con rsync..."
    mkdir -p "$INSTALL_DIR"
    rsync -a --exclude '.git' --exclude 'deploy' --exclude '__pycache__' \
        "$REPO_DIR/" "$INSTALL_DIR/"
fi

chown -R "$TREEPAGE_USER:$TREEPAGE_USER" "$INSTALL_DIR"

# ── 3b. Dati utente: copia i default solo se non esistono già ────
echo "     Ripristino dati utente (se assenti)..."
DEFAULTS_DIR="$REPO_DIR/deploy/defaults"
if [ -d "$DEFAULTS_DIR/users" ]; then
    mkdir -p "$INSTALL_DIR/users"
    for f in "$DEFAULTS_DIR/users/"*.yaml; do
        [ -f "$f" ] || continue
        dest="$INSTALL_DIR/users/$(basename "$f")"
        if [ ! -f "$dest" ]; then
            cp "$f" "$dest"
            echo "     Creato utente default: $(basename "$f")"
        fi
    done
fi
chown -R "$TREEPAGE_USER:$TREEPAGE_USER" "$INSTALL_DIR/users" 2>/dev/null || true

# ── 4. Virtual environment Python ────────────────────────
echo "[4/7] Creazione virtual environment Python..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

echo "     Installazione dipendenze script di esempio..."
if [ -f "$INSTALL_DIR/scripts/example-script/requirements.txt" ]; then
    "$INSTALL_DIR/venv/bin/pip" install \
        -r "$INSTALL_DIR/scripts/example-script/requirements.txt" -q
fi

# ── 5. Systemd services ───────────────────────────────────
echo "[5/7] Installazione servizi systemd..."
cp "$REPO_DIR/deploy/treepage.service"          /etc/systemd/system/
cp "$REPO_DIR/deploy/treepage-script@.service"  /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now treepage

# ── 5b. Sudoers: permette a treepage di riavviare il servizio ─
SUDOERS_FILE="/etc/sudoers.d/treepage"
mkdir -p /etc/sudoers.d
cat > "$SUDOERS_FILE" <<'SUDOERS'
# Permette all'utente treepage di riavviare i servizi TreePage senza password
treepage ALL=(ALL) NOPASSWD: /bin/systemctl restart treepage
treepage ALL=(ALL) NOPASSWD: /bin/systemctl restart treepage-script@*
SUDOERS
chmod 0440 "$SUDOERS_FILE"

# ── 6. Nginx ──────────────────────────────────────────────
echo "[6/7] Configurazione Nginx..."
cp "$REPO_DIR/nginx/treepage.conf" /etc/nginx/sites-available/treepage
ln -sf /etc/nginx/sites-available/treepage /etc/nginx/sites-enabled/treepage

# Rimuovi default se presente
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable --now nginx
systemctl reload nginx

# ── 7. Fine ───────────────────────────────────────────────
echo "[7/7] Installazione completata!"
echo ""
echo "  Dashboard:  http://$(hostname -I | cut -d' ' -f1)/"
echo "  Admin:      http://$(hostname -I | cut -d' ' -f1)/admin/"
echo "  API docs:   http://$(hostname -I | cut -d' ' -f1)/api/docs"
echo ""
echo "  ⚠  Primo accesso al pannello admin:"
echo "     Utente:   admin"
echo "     Password: admin"
echo "     → Cambia subito la password da /admin/change-password"
echo ""
echo "Comandi utili:"
echo "  systemctl status treepage"
echo "  journalctl -u treepage -f"
echo "  systemctl start treepage-script@example-script"
echo ""
