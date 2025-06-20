document.addEventListener('DOMContentLoaded', () => {
  const category = document.getElementById('category');
  const optionsGroup = document.getElementById('options-group');
  if (!category || !optionsGroup) return;

  const toggle = () => {
    if (category.value === 'multiple_choice') {
      optionsGroup.classList.remove('hidden');
    } else {
      optionsGroup.classList.add('hidden');
    }
  };

  category.addEventListener('change', toggle);
  toggle();
});
