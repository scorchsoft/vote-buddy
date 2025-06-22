async function initCharts() {
  const container = document.getElementById('charts');
  if (!container) return;
  const url = container.dataset.url;
  const resp = await fetch(url);
  const data = await resp.json();
  const stage1Rows = data.tallies.filter(r => r.type === 'amendment');
  const stage2Rows = data.tallies.filter(r => r.type === 'motion');
  const modeSelect = document.getElementById('share-mode');

  function percent(value, row, effective) {
    let denom = row.for + row.against + row.abstain;
    if (effective) denom -= row.abstain;
    if (!denom) return 0;
    return ((value / denom) * 100).toFixed(1);
  }

  function makeData(rows, effective) {
    return {
      labels: rows.map(r => r.text),
      datasets: [
        { label: 'For', data: rows.map(r => percent(r.for, r, effective)), backgroundColor: '#00b894' },
        { label: 'Against', data: rows.map(r => percent(r.against, r, effective)), backgroundColor: '#d63031' },
        { label: 'Abstain', data: rows.map(r => percent(r.abstain, r, effective)), backgroundColor: '#fdcb6e' }
      ]
    };
  }

  function tooltip(rows) {
    return ctx => {
      const row = rows[ctx.dataIndex];
      const key = ctx.dataset.label.toLowerCase();
      const count = row[key];
      const pct = percent(count, row, modeSelect.value === 'effective');
      return `${ctx.dataset.label}: ${pct}% (${count})`;
    };
  }

  function chartOpts(rows) {
    return {
      responsive: true,
      scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } },
      plugins: { tooltip: { callbacks: { label: tooltip(rows) } } }
    };
  }

  let stage1Chart = new Chart(document.getElementById('stage1-chart'), {
    type: 'bar',
    data: makeData(stage1Rows, modeSelect.value === 'effective'),
    options: chartOpts(stage1Rows)
  });

  let stage2Chart = new Chart(document.getElementById('stage2-chart'), {
    type: 'bar',
    data: makeData(stage2Rows, modeSelect.value === 'effective'),
    options: chartOpts(stage2Rows)
  });

  modeSelect.addEventListener('change', () => {
    const eff = modeSelect.value === 'effective';
    stage1Chart.data = makeData(stage1Rows, eff);
    stage1Chart.options.plugins.tooltip.callbacks.label = tooltip(stage1Rows);
    stage1Chart.update();
    stage2Chart.data = makeData(stage2Rows, eff);
    stage2Chart.options.plugins.tooltip.callbacks.label = tooltip(stage2Rows);
    stage2Chart.update();
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCharts);
} else {
  initCharts();
}
