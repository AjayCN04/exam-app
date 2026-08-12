document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("examform");
  if (!form) return;

  const totalQ = form.querySelectorAll("fieldset.question").length;

  function refresh() {
    let answered = 0;
    form.querySelectorAll("fieldset.question").forEach(function (fs) {
      const checked = fs.querySelector("input:checked");
      fs.classList.toggle("answered", !!checked);
      fs.querySelectorAll("label.option").forEach(function (label) {
        label.classList.toggle("selected", label.querySelector("input").checked);
      });
      if (checked) answered++;
    });
    const label = document.getElementById("progress-label");
    const fill = document.getElementById("progress-fill");
    if (label) label.innerHTML = "<strong>" + answered + "</strong> of " + totalQ + " answered";
    if (fill) fill.style.width = (totalQ ? (answered / totalQ * 100) : 0) + "%";
  }

  // Make radios deselectable: clicking an already-checked option clears it.
  // Native radios can only switch to a different option, never back to "none" —
  // so track prior state on mousedown, then undo the click if it was already checked.
  form.querySelectorAll('input[type="radio"]').forEach(function (radio) {
    radio.addEventListener("mousedown", function () {
      const group = form.querySelectorAll('input[name="' + this.name + '"]');
      group.forEach(function (r) {
        r.dataset.wasChecked = r.checked ? "1" : "0";
      });
    });
    radio.addEventListener("click", function () {
      if (this.dataset.wasChecked === "1") {
        this.checked = false;
      }
      refresh();
    });
  });

  // Checkboxes (multi-select questions) are natively toggleable, unlike
  // radios, so they don't need the deselect hack above — just re-run
  // refresh() on click so the progress bar/label stay in sync.
  form.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
    checkbox.addEventListener("click", refresh);
  });

  refresh();
});
