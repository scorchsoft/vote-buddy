document.addEventListener('DOMContentLoaded', () => {
  const noticeDays = parseInt(document.body.dataset.noticeDays || '14', 10);
  const agmField = document.getElementById('closes_at_stage2');
  if (!agmField) return;

  const toLocal = (date) => {
    const tz = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - tz).toISOString().slice(0, 16);
  };

  agmField.addEventListener('change', () => {
    const base = new Date(agmField.value);
    if (isNaN(base)) return;

    const opens2 = document.getElementById('opens_at_stage2');
    const closes1 = document.getElementById('closes_at_stage1');
    const opens1 = document.getElementById('opens_at_stage1');
    const notice = document.getElementById('notice_date');

    if (opens2 && !opens2.value) {
      const d = new Date(base);
      d.setDate(d.getDate() - 5);
      opens2.value = toLocal(d);
    }

    if (opens2 && closes1 && !closes1.value && opens2.value) {
      const d = new Date(opens2.value);
      d.setDate(d.getDate() - 1);
      closes1.value = toLocal(d);
    }

    if (closes1 && opens1 && !opens1.value && closes1.value) {
      const d = new Date(closes1.value);
      d.setDate(d.getDate() - 7);
      opens1.value = toLocal(d);
    }

    if (opens1 && notice && !notice.value && opens1.value) {
      const d = new Date(opens1.value);
      d.setDate(d.getDate() - noticeDays);
      notice.value = toLocal(d);
    }
  });
});
