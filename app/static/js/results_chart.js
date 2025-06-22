async function initCharts() {
  const container = document.getElementById('charts');
  if (!container) return;
  const url = container.dataset.url;
  const resp = await fetch(url);
  const data = await resp.json();

  const stage1Grid = document.getElementById('stage1-grid');
  const stage2Grid = document.getElementById('stage2-grid');

  function createCard(title, id, grid) {
    const card = document.createElement('div');
    card.className = 'bp-card overflow-x-auto';
    const h3 = document.createElement('h3');
    h3.className = 'font-semibold mb-2';
    h3.textContent = title;
    const canvas = document.createElement('canvas');
    canvas.id = id;
    canvas.height = 240;
    canvas.className = 'w-full';
    card.appendChild(h3);
    card.appendChild(canvas);
    grid.appendChild(card);
    return canvas;
  }

  function countsData(row) {
    return {
      labels: ['For', 'Against', 'Abstain'],
      datasets: [{
        label: 'Votes',
        data: [row.for, row.against, row.abstain],
        backgroundColor: ['#00b894', '#d63031', '#fdcb6e']
      }]
    };
  }

  function percentData(row, effective) {
    let total = row.for + row.against + row.abstain;
    if (effective) total -= row.abstain;
    if (!total) total = 1;
    const labels = ['For', 'Against'];
    const values = [
      (row.for / total * 100).toFixed(1),
      (row.against / total * 100).toFixed(1)
    ];
    const colors = ['#00b894', '#d63031'];
    if (!effective) {
      labels.push('Abstain');
      values.push((row.abstain / total * 100).toFixed(1));
      colors.push('#fdcb6e');
    }
    return {
      labels,
      datasets: [{
        label: 'Percent',
        data: values,
        backgroundColor: colors
      }]
    };
  }

  function opts(yLabel, titleText) {
    return {
      responsive: true,
      scales: {
        x: { title: { display: true, text: 'Choice' } },
        y: {
          beginAtZero: true,
          max: yLabel.includes('%') ? 100 : undefined,
          ticks: {
            callback: v => yLabel.includes('%') ? v + '%' : v
          },
          title: { display: true, text: yLabel }
        }
      },
      plugins: { title: { display: true, text: titleText } }
    };
  }

  function renderRow(row, grid, prefix) {
    const short = row.text;
    const countCanvas = createCard(short + ' – Count', `${prefix}${row.id}-c`, grid);
    new Chart(countCanvas, {
      type: 'bar',
      data: countsData(row),
      options: opts('Votes', short + ' – Vote Count')
    });
    const pctCanvas = createCard(short + ' – %', `${prefix}${row.id}-p`, grid);
    new Chart(pctCanvas, {
      type: 'bar',
      data: percentData(row, false),
      options: opts('%', short + ' – Vote Share')
    });
    const effCanvas = createCard(short + ' – Effective %', `${prefix}${row.id}-e`, grid);
    new Chart(effCanvas, {
      type: 'bar',
      data: percentData(row, true),
      options: opts('%', short + ' – Effective Share')
    });
  }

  data.tallies.filter(r => r.type === 'amendment').forEach(r => renderRow(r, stage1Grid, 'a'));
  data.tallies.filter(r => r.type === 'motion').forEach(r => renderRow(r, stage2Grid, 'm'));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCharts);
} else {
  initCharts();
}
