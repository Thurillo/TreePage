/* TreePage – main JS (no framework, pure vanilla) */

// Copy text to clipboard and briefly highlight the triggering button
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    // Visual feedback: find the button that triggered the call
    const btn = event && event.currentTarget;
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = '✅';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    }
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  });
}

// Open <details> panels that have a child with class 'error'
document.querySelectorAll('details').forEach(d => {
  if (d.querySelector('.error')) d.open = true;
});

// Flash messages: auto-dismiss after 4s
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => el.remove(), 4000);
});

// Tile type selector (admin user_edit) – fallback in case
// the inline onchange is not present
const tileTypeSelect = document.getElementById('tile-type-select');
if (tileTypeSelect) {
  tileTypeSelect.addEventListener('change', e => {
    if (typeof tileTypeChanged === 'function') tileTypeChanged(e.target.value);
  });
}
