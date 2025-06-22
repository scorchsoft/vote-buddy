async function initCharts() {
  const container = document.getElementById('charts');
  if (!container) return;
  const url = container.dataset.url;
  const resp = await fetch(url);
  const data = await resp.json();

  const stage1Grid = document.getElementById('stage1-grid');
  const stage2Grid = document.getElementById('stage2-grid');

  function createSectionHeading(title, href, grid) {
    const heading = document.createElement('h3');
    heading.className = 'font-semibold text-lg text-bp-blue mb-4 mt-6 first:mt-0 border-b border-bp-grey-200 pb-2';
    const link = document.createElement('a');
    link.href = href;
    link.className = 'hover:underline';
    link.textContent = title;
    heading.appendChild(link);
    grid.appendChild(heading);
  }

  function createCard(title, id, grid) {
    const card = document.createElement('div');
    card.className = 'bp-card overflow-x-auto';
    const h4 = document.createElement('h4');
    h4.className = 'font-medium mb-2 text-sm text-bp-grey-700';
    h4.textContent = title;
    const canvas = document.createElement('canvas');
    canvas.id = id;
    canvas.height = 240;
    canvas.className = 'w-full';
    card.appendChild(h4);
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
      plugins: { 
        title: { 
          display: true, 
          text: titleText,
          font: {
            size: 12
          }
        } 
      }
    };
  }

  function renderRow(row, grid, prefix) {
    const short = row.text;
    const base = prefix === 'm' ? container.dataset.motionUrl : container.dataset.amendUrl;
    const href = base + row.id;

    // Add section heading for this motion
    createSectionHeading(short, href, grid);
    
    // Create a container div for the 3 charts
    const chartsContainer = document.createElement('div');
    chartsContainer.className = 'grid grid-cols-1 md:grid-cols-3 gap-4 mb-8';
    grid.appendChild(chartsContainer);
    
    const countCanvas = createCard('Vote Count', `${prefix}${row.id}-c`, chartsContainer);
    new Chart(countCanvas, {
      type: 'bar',
      data: countsData(row),
      options: opts('Votes', short + ' – Vote Count')
    });
    const pctCanvas = createCard('Vote Share', `${prefix}${row.id}-p`, chartsContainer);
    new Chart(pctCanvas, {
      type: 'bar',
      data: percentData(row, false),
      options: opts('%', short + ' – Vote Share')
    });
    const effCanvas = createCard('Effective Share', `${prefix}${row.id}-e`, chartsContainer);
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
