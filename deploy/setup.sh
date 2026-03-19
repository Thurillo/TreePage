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
    curl git

# ── 2. Utente di sistema ──────────────────────────────────
echo "[2/7] Creazione utente di sistema '$TREEPAGE_USER'..."
if ! id "$TREEPAGE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$TREEPAGE_USER"
fi

# ── 3. Directory di installazione ────────────────────────
echo "[3/7] Copia file in $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copia tutto tranne la directory deploy (già eseguita)
rsync -a --exclude '.git' --exclude 'deploy' --exclude '__pycache__' \
    "$REPO_DIR/" "$INSTALL_DIR/"

chown -R "$TREEPAGE_USER:$TREEPAGE_USER" "$INSTALL_DIR"

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
echo "  Dashboard:  http://$(hostname -I | awk '{print $1}')/"
echo "  Admin:      http://$(hostname -I | awk '{print $1}')/admin/"
echo "  API docs:   http://$(hostname -I | awk '{print $1}')/api/docs"
echo ""
echo "Comandi utili:"
echo "  systemctl status treepage"
echo "  journalctl -u treepage -f"
echo "  systemctl start treepage-script@example-script"
echo ""
