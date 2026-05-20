/* Drag-to-reorder support for djangocms-custom-content m2m admin widgets.
 *
 * Targets any <select multiple> with the class
 * "djangocms-custom-content-m2m-sortable". Waits for django's stock select2
 * autocomplete to wrap the element, then makes the chip list sortable.
 *
 * Reordering rewrites the <option> order on the underlying <select>, so
 * Django's form processing receives the chosen order via the submitted
 * sequence of values. The form field's clean() restores order in Python.
 */
(function () {
    function ensureSelect2(select, callback) {
        function tick() {
            var chips = select.parentElement &&
                select.parentElement.querySelector(".select2-selection__rendered");
            if (chips) {
                callback(chips);
            } else {
                setTimeout(tick, 50);
            }
        }
        tick();
    }

    function stampChipValues(select, chipList) {
        var chips = chipList.querySelectorAll(".select2-selection__choice");
        var options = select.selectedOptions;
        var count = Math.min(chips.length, options.length);
        for (var i = 0; i < count; i++) {
            chips[i].dataset.optionValue = options[i].value;
        }
    }

    function attachSortable(select) {
        if (typeof Sortable === "undefined") {
            return;
        }
        ensureSelect2(select, function (chipList) {
            if (chipList.dataset.cmsccSortableInit === "1") {
                return;
            }
            chipList.dataset.cmsccSortableInit = "1";

            function closeSelect2() {
                if (window.django && window.django.jQuery) {
                    window.django.jQuery(select).select2("close");
                }
            }

            new Sortable(chipList, {
                animation: 150,
                draggable: ".select2-selection__choice",
                onStart: function () {
                    stampChipValues(select, chipList);
                    closeSelect2();
                },
                onSort: function () {
                    var values = Array.from(
                        chipList.querySelectorAll(".select2-selection__choice")
                    )
                        .map(function (chip) {
                            return chip.dataset.optionValue;
                        })
                        .filter(Boolean);
                    var optionsByValue = {};
                    Array.from(select.options).forEach(function (option) {
                        optionsByValue[option.value] = option;
                    });
                    values.forEach(function (value) {
                        var option = optionsByValue[value];
                        if (option) {
                            select.appendChild(option);
                        }
                    });
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                },
            });
        });
    }

    function init() {
        document
            .querySelectorAll("select.djangocms-custom-content-m2m-sortable")
            .forEach(attachSortable);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
