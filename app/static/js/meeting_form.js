document.addEventListener('DOMContentLoaded', () => {
  const cfg = document.body.dataset;
  const noticeDays = parseInt(cfg.noticeDays || '14', 10);
  const stage1Days = parseInt(cfg.stage1Days || '7', 10);
  const stage2Days = parseInt(cfg.stage2Days || '5', 10);
  const stageGapDays = parseInt(cfg.stageGapDays || '1', 10);
  const runoffMinutes = parseInt(cfg.runoffMinutes || '2880', 10);
  const motionWindowDays = parseInt(cfg.motionWindowDays || '7', 10);
  const motionDeadlineGapDays = parseInt(cfg.motionDeadlineGapDays || '7', 10);

  const agmField = document.getElementById('closes_at_stage2');
  if (!agmField) return;

  const toLocal = (date) => {
    const tz = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - tz).toISOString().slice(0, 16);
  };

  function fillAll(force) {
    const base = new Date(agmField.value);
    if (isNaN(base)) return;

    const opens2 = document.getElementById('opens_at_stage2');
    const closes1 = document.getElementById('closes_at_stage1');
    const opens1 = document.getElementById('opens_at_stage1');
    const notice = document.getElementById('notice_date');
    const motionsOpen = document.getElementById('motions_opens_at');
    const motionsClose = document.getElementById('motions_closes_at');
    const amendsOpen = document.getElementById('amendments_opens_at');
    const amendsClose = document.getElementById('amendments_closes_at');

    const dStage2Open = new Date(base);
    dStage2Open.setDate(dStage2Open.getDate() - stage2Days);
    if (force || !opens2.value) opens2.value = toLocal(dStage2Open);

    const dStage1Close = new Date(dStage2Open);
    dStage1Close.setDate(dStage1Close.getDate() - stageGapDays - runoffMinutes / 1440);
    if (force || !closes1.value) closes1.value = toLocal(dStage1Close);

    const dStage1Open = new Date(dStage1Close);
    dStage1Open.setDate(dStage1Open.getDate() - stage1Days);
    if (force || !opens1.value) opens1.value = toLocal(dStage1Open);

    const dNotice = new Date(dStage1Open);
    dNotice.setDate(dNotice.getDate() - noticeDays);
    if (force || !notice.value) notice.value = toLocal(dNotice);

    const dMotionsClose = new Date(dNotice);
    dMotionsClose.setDate(dMotionsClose.getDate() - motionDeadlineGapDays);
    if (force || !motionsClose.value) motionsClose.value = toLocal(dMotionsClose);

    const dMotionsOpen = new Date(dMotionsClose);
    dMotionsOpen.setDate(dMotionsOpen.getDate() - motionWindowDays);
    if (force || !motionsOpen.value) motionsOpen.value = toLocal(dMotionsOpen);

    if (force || !amendsOpen.value) amendsOpen.value = toLocal(dNotice);

    const dAmendsClose = new Date(dStage1Open);
    dAmendsClose.setDate(dAmendsClose.getDate() - 7);
    if (force || !amendsClose.value) amendsClose.value = toLocal(dAmendsClose);
  }

  agmField.addEventListener('change', () => fillAll(false));

  const btn = document.getElementById('auto-populate-btn');
  if (btn) {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (confirm('Auto fill all dates? This will overwrite any existing values.')) {
        fillAll(true);
      }
    });
  }
});
