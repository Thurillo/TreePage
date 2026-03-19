/* TreePage – main JS (no framework, pure vanilla) */

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
