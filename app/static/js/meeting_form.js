document.addEventListener('DOMContentLoaded', () => {
  const cfg = document.body.dataset;
  const noticeDays = parseInt(cfg.noticeDays || '3', 10);  // Reduced Final Notice buffer to 3 days
  const stage1Days = parseInt(cfg.stage1Days || '5', 10);  // Reduced Stage 1 to 5 days for e-ballots
  const stage2Days = parseInt(cfg.stage2Days || '5', 10);
  const stageGapDays = parseInt(cfg.stageGapDays || '1', 10);
  const runoffMinutes = parseInt(cfg.runoffMinutes || '2880', 10);
  const motionWindowDays = parseInt(cfg.motionWindowDays || '7', 10);
  const motionDeadlineGapDays = parseInt(cfg.motionDeadlineGapDays || '0', 10);  // Motions open immediately
  const amendmentWindowDays = parseInt(cfg.amendmentWindowDays || '5', 10);  // Extended amendment window to 5 days

  const agmField = document.getElementById('closes_at_stage2');
  if (!agmField) return;

  // Sync the display field with the main AGM date field
  const stage2ClosesDisplay = document.getElementById('stage2_closes_display');
  
  function syncStage2Display() {
    if (stage2ClosesDisplay && agmField.value) {
      stage2ClosesDisplay.value = agmField.value;
    }
  }

  // Sync on change
  agmField.addEventListener('change', syncStage2Display);
  agmField.addEventListener('input', syncStage2Display);
  
  // Initial sync
  syncStage2Display();

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
    const initialNotice = document.getElementById('initial_notice_date');
    const notice = document.getElementById('notice_date');
    const motionsOpen = document.getElementById('motions_opens_at');
    const motionsClose = document.getElementById('motions_closes_at');
    const amendsOpen = document.getElementById('amendments_opens_at');
    const amendsClose = document.getElementById('amendments_closes_at');

    // 1. Stage 2 Closes = AGM - 3 days (recommended processing gap)
    const dStage2Close = new Date(base);
    dStage2Close.setDate(dStage2Close.getDate() - 3);

    // 2. Stage 2 Opens = Stage 2 Closes - 5 days
    const dStage2Open = new Date(dStage2Close);
    dStage2Open.setDate(dStage2Open.getDate() - stage2Days);
    if (force || !opens2.value) opens2.value = toLocal(dStage2Open);

    // 3. Stage 1 Closes = Stage 2 Opens - 1 day (gap)
    const dStage1Close = new Date(dStage2Open);
    dStage1Close.setDate(dStage1Close.getDate() - stageGapDays - runoffMinutes / 1440);
    if (force || !closes1.value) closes1.value = toLocal(dStage1Close);

    // 4. Stage 1 Opens = Stage 1 Closes - 5 days
    const dStage1Open = new Date(dStage1Close);
    dStage1Open.setDate(dStage1Open.getDate() - stage1Days);
    if (force || !opens1.value) opens1.value = toLocal(dStage1Open);

    // 5. Final Notice = Stage 1 Opens - 3 days
    const dNotice = new Date(dStage1Open);
    dNotice.setDate(dNotice.getDate() - noticeDays);
    if (force || !notice.value) notice.value = toLocal(dNotice);

    // 6. Amendments Close = Final Notice - 2 days (grace period to process amendments)
    const dAmendsClose = new Date(dNotice);
    dAmendsClose.setDate(dAmendsClose.getDate() - 2);
    if (force || !amendsClose.value) amendsClose.value = toLocal(dAmendsClose);

    // 7. Amendments Open = Amendments Close - 5 days
    const dAmendsOpen = new Date(dAmendsClose);
    dAmendsOpen.setDate(dAmendsOpen.getDate() - amendmentWindowDays);
    if (force || !amendsOpen.value) amendsOpen.value = toLocal(dAmendsOpen);

    // 8. Motions Close = Amendments Open - 1 day (grace period)
    const dMotionsClose = new Date(dAmendsOpen);
    dMotionsClose.setDate(dMotionsClose.getDate() - 1);
    if (force || !motionsClose.value) motionsClose.value = toLocal(dMotionsClose);

    // 9. Initial Notice = Motions Close - 21 days
    const dInitialNotice = new Date(dMotionsClose);
    dInitialNotice.setDate(dInitialNotice.getDate() - 21);
    if (force || !initialNotice.value) initialNotice.value = toLocal(dInitialNotice);

    // 10. Motions Open = Initial Notice (same day - Day-One opening)
    const dMotionsOpen = new Date(dInitialNotice);
    if (force || !motionsOpen.value) motionsOpen.value = toLocal(dMotionsOpen);
    
    // Sync the Stage 2 Closes display field (shows the actual Stage 2 close date)
    if (stage2ClosesDisplay) {
      stage2ClosesDisplay.value = toLocal(dStage2Close);
    }
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
