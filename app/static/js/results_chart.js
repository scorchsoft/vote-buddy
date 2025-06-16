document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('charts');
  if (!container) return;
  const url = container.dataset.url;
  const resp = await fetch(url);
  const data = await resp.json();
  const stage1Rows = data.tallies.filter(r => r.type === 'amendment');
  const stage2Rows = data.tallies.filter(r => r.type === 'motion');

  function makeData(rows) {
    return {
      labels: rows.map(r => r.text),
      datasets: [
        { label: 'For', data: rows.map(r => r.for), backgroundColor: '#00b894' },
        { label: 'Against', data: rows.map(r => r.against), backgroundColor: '#d63031' },
        { label: 'Abstain', data: rows.map(r => r.abstain), backgroundColor: '#fdcb6e' }
      ]
    };
  }

  new Chart(document.getElementById('stage1-chart'), {
    type: 'bar',
    data: makeData(stage1Rows),
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
  });

  new Chart(document.getElementById('stage2-chart'), {
    type: 'bar',
    data: makeData(stage2Rows),
    options: { responsive: true, scales: { y: { beginAtZero: true } } }
  });
});
