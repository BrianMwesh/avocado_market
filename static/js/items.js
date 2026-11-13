/* Line-item editor for quotes and invoices.
   - picks the product price automatically
   - recalculates each line and the document total as you type                */
(function () {
  "use strict";

  function money(value) {
    return "KES " + Number(value || 0).toLocaleString("en-KE", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function recalc(editor) {
    var total = 0;
    editor.querySelectorAll("[data-rows] tr").forEach(function (row) {
      var qty = parseFloat((row.querySelector(".js-qty") || {}).value || 0) || 0;
      var price = parseFloat((row.querySelector(".js-price") || {}).value || 0) || 0;
      var amount = qty * price;
      total += amount;
      var cell = row.querySelector(".js-amount");
      if (cell) cell.textContent = money(amount);
    });
    var totalCell = editor.querySelector(".js-total");
    if (totalCell) totalCell.textContent = money(total);
  }

  function wireRow(editor, row) {
    var product = row.querySelector(".js-product");
    var desc = row.querySelector("input[name='description']");
    var price = row.querySelector(".js-price");

    if (product) {
      product.addEventListener("change", function () {
        var opt = product.options[product.selectedIndex];
        if (!opt) return;
        var p = opt.getAttribute("data-price");
        if (p && price && !price.value) price.value = p;
        if (desc && !desc.value) desc.value = opt.getAttribute("data-name") || "";
        recalc(editor);
      });
    }

    row.querySelectorAll(".js-qty, .js-price").forEach(function (input) {
      input.addEventListener("input", function () { recalc(editor); });
    });

    var remove = row.querySelector(".js-remove");
    if (remove) {
      remove.addEventListener("click", function () {
        var rows = editor.querySelectorAll("[data-rows] tr");
        if (rows.length === 1) {
          rows[0].querySelectorAll("input").forEach(function (i) { i.value = ""; });
          rows[0].querySelectorAll("select").forEach(function (s) { s.selectedIndex = 0; });
          recalc(editor);
          return;
        }
        row.remove();
        recalc(editor);
      });
    }
  }

  document.querySelectorAll("[data-editor]").forEach(function (editor) {
    var rows = editor.querySelector("[data-rows]");
    editor.querySelectorAll("[data-rows] tr").forEach(function (row) {
      wireRow(editor, row);
    });

    var add = editor.querySelector("[data-add-row]");
    var template = editor.querySelector("[data-row-template]");
    if (add && template && rows) {
      add.addEventListener("click", function () {
        var clone = template.content.firstElementChild.cloneNode(true);
        rows.appendChild(clone);
        wireRow(editor, clone);
        recalc(editor);
      });
    }
    recalc(editor);
  });
})();
