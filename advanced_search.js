
// Advanced OTT Search Enhancement
document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('input[type="search"], input[name="q"], input[type="text"]');
  if(!search) return;

  let box = document.createElement('div');
  box.id = "live-search-box";
  box.style.cssText = "position:absolute;z-index:9999;background:#151515;border:1px solid #D4AF37;width:100%;max-height:350px;overflow:auto;border-radius:12px;display:none;";
  search.parentNode.style.position = "relative";
  search.parentNode.appendChild(box);

  const sampleTitles = [
    "Avengers","Avengers: Endgame","Avengers: Infinity War",
    "Iron Man","Captain America","Thor","Loki","Moon Knight",
    "Off Campus","Stranger Things","Breaking Bad"
  ];

  search.addEventListener('input', () => {
    const q = search.value.toLowerCase().trim();
    if(!q){ box.style.display='none'; return; }

    const results = sampleTitles.filter(x => x.toLowerCase().includes(q));
    box.innerHTML = results.map(r =>
      `<div style="padding:12px;cursor:pointer;font-size:18px">${r}</div>`
    ).join('');

    box.style.display = results.length ? 'block' : 'none';

    [...box.children].forEach(el => {
      el.onclick = () => {
        search.value = el.textContent;
        box.style.display = 'none';
      };
    });
  });
});
