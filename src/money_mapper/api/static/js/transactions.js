/**
 * Transactions page: infinite scroll, search, sort, and advanced filters.
 */

(function () {
    "use strict";

    // --- State ---
    var currentOffset = 0;
    var currentTotal = 0;
    var loading = false;
    var hasMore = true;
    var searchQuery = "";
    var debounceTimer = null;

    var sortColumn = null;
    var sortOrder = null;
    var minAmount = "";
    var maxAmount = "";
    var selectedCategories = [];
    var filtersVisible = false;

    // --- DOM references ---
    var tbody = document.querySelector("#transactions-table tbody");
    var searchInput = document.querySelector("#transaction-search");
    var clearButton = document.querySelector("#search-clear");
    var countDisplay = document.querySelector("#transaction-count");
    var loadingRow = document.querySelector("#loading-row");
    var exportLink = document.querySelector("#export-link");
    var exportAnchor = exportLink ? exportLink.querySelector("a") : null;

    var filtersToggle = document.querySelector("#filters-toggle");
    var filtersPanel = document.querySelector("#filters-panel");
    var filtersActiveIndicator = document.querySelector("#filters-active-indicator");
    var minAmountInput = document.querySelector("#filter-min-amount");
    var maxAmountInput = document.querySelector("#filter-max-amount");
    var categoryInput = document.querySelector("#filter-category-input");
    var categoryDatalist = document.querySelector("#category-datalist");
    var selectedCategoriesDiv = document.querySelector("#selected-categories");
    var applyFiltersBtn = document.querySelector("#apply-filters");
    var clearFiltersBtn = document.querySelector("#clear-filters");
    var sortableHeaders = document.querySelectorAll("th.sortable");

    if (!tbody || !searchInput) {
        return;
    }

    var table = document.querySelector("#transactions-table");
    currentTotal = parseInt(table.getAttribute("data-total") || "0", 10);
    currentOffset = tbody.querySelectorAll("tr:not(#loading-row)").length;
    hasMore = currentOffset < currentTotal;
    updateCount();

    // --- Infinite scroll ---
    window.addEventListener("scroll", function () {
        if (loading || !hasMore) return;
        var scrollBottom = window.innerHeight + window.scrollY;
        var pageHeight = document.documentElement.scrollHeight;
        if (pageHeight - scrollBottom < 200) {
            loadMore();
        }
    });

    // --- Search ---
    searchInput.addEventListener("input", function () {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            searchQuery = searchInput.value.trim();
            resetAndLoad();
        }, 300);
    });

    if (clearButton) {
        clearButton.addEventListener("click", function () {
            searchInput.value = "";
            searchQuery = "";
            resetAndLoad();
        });
    }

    // --- Filter panel toggle ---
    if (filtersToggle && filtersPanel) {
        filtersToggle.addEventListener("click", function () {
            filtersVisible = !filtersVisible;
            filtersPanel.style.display = filtersVisible ? "" : "none";
            filtersToggle.textContent = filtersVisible ? "Hide Filters" : "Show Filters";
            updateFiltersActiveIndicator();
        });
    }

    // --- Load categories for type-ahead ---
    fetch("/api/categories")
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!categoryDatalist || !data.categories) return;
            for (var i = 0; i < data.categories.length; i++) {
                var opt = document.createElement("option");
                opt.value = data.categories[i];
                categoryDatalist.appendChild(opt);
            }
        })
        .catch(function () { });

    // --- Category selection (type-ahead add) ---
    if (categoryInput) {
        categoryInput.addEventListener("change", function () {
            var val = categoryInput.value.trim();
            if (!val) return;
            if (selectedCategories.indexOf(val) === -1) {
                selectedCategories.push(val);
                renderSelectedCategories();
            }
            categoryInput.value = "";
        });
    }

    function renderSelectedCategories() {
        if (!selectedCategoriesDiv) return;
        while (selectedCategoriesDiv.firstChild) {
            selectedCategoriesDiv.removeChild(selectedCategoriesDiv.firstChild);
        }
        for (var i = 0; i < selectedCategories.length; i++) {
            (function (cat) {
                var tag = document.createElement("span");
                tag.style.cssText = "display:inline-block;background:#2c3e50;color:#fff;padding:2px 8px;margin:2px;border-radius:3px;font-size:0.85em";
                tag.textContent = cat + " ";
                var x = document.createElement("button");
                x.type = "button";
                x.textContent = "x";
                x.style.cssText = "background:none;border:none;color:#fff;cursor:pointer;padding:0 0 0 4px";
                x.addEventListener("click", function () {
                    var idx = selectedCategories.indexOf(cat);
                    if (idx !== -1) {
                        selectedCategories.splice(idx, 1);
                        renderSelectedCategories();
                        resetAndLoad();
                    }
                });
                tag.appendChild(x);
                selectedCategoriesDiv.appendChild(tag);
            })(selectedCategories[i]);
        }
    }

    // --- Apply / Clear Filters ---
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener("click", function () {
            var minVal = minAmountInput ? minAmountInput.value.trim() : "";
            var maxVal = maxAmountInput ? maxAmountInput.value.trim() : "";
            if (minVal && isNaN(parseFloat(minVal))) {
                minAmountInput.value = "";
                minVal = "";
            }
            if (maxVal && isNaN(parseFloat(maxVal))) {
                maxAmountInput.value = "";
                maxVal = "";
            }
            minAmount = minVal;
            maxAmount = maxVal;
            resetAndLoad();
        });
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener("click", function () {
            minAmount = "";
            maxAmount = "";
            selectedCategories = [];
            if (minAmountInput) minAmountInput.value = "";
            if (maxAmountInput) maxAmountInput.value = "";
            if (categoryInput) categoryInput.value = "";
            renderSelectedCategories();
            resetAndLoad();
        });
    }

    // --- Sort header clicks ---
    for (var i = 0; i < sortableHeaders.length; i++) {
        (function (th) {
            th.addEventListener("click", function () {
                var col = th.getAttribute("data-column");
                if (sortColumn !== col) {
                    sortColumn = col;
                    sortOrder = "asc";
                } else if (sortOrder === "asc") {
                    sortOrder = "desc";
                } else {
                    sortColumn = null;
                    sortOrder = null;
                }
                renderSortIndicators();
                resetAndLoad();
            });
        })(sortableHeaders[i]);
    }

    function renderSortIndicators() {
        for (var j = 0; j < sortableHeaders.length; j++) {
            var th = sortableHeaders[j];
            var ind = th.querySelector(".sort-indicator");
            if (!ind) continue;
            if (th.getAttribute("data-column") === sortColumn) {
                ind.textContent = sortOrder === "asc" ? " [A]" : " [D]";
            } else {
                ind.textContent = "";
            }
        }
    }

    // --- Core functions ---
    function buildQueryString(includePagination) {
        var parts = [];
        if (includePagination) {
            parts.push("offset=" + currentOffset);
            parts.push("limit=50");
        }
        if (searchQuery) parts.push("q=" + encodeURIComponent(searchQuery));
        if (sortColumn) {
            parts.push("sort=" + encodeURIComponent(sortColumn));
            parts.push("order=" + encodeURIComponent(sortOrder || "asc"));
        }
        if (minAmount) parts.push("min_amount=" + encodeURIComponent(minAmount));
        if (maxAmount) parts.push("max_amount=" + encodeURIComponent(maxAmount));
        if (selectedCategories.length > 0) {
            parts.push("categories=" + encodeURIComponent(selectedCategories.join(",")));
        }
        return parts.join("&");
    }

    function loadMore() {
        if (loading || !hasMore) return;
        loading = true;
        showLoading(true);

        var url = "/api/transactions?" + buildQueryString(true);

        fetch(url)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                appendTransactions(data.transactions);
                currentTotal = data.total;
                currentOffset += data.transactions.length;
                hasMore = data.has_more;
                updateCount();
                updateExportLink();
                updateFiltersActiveIndicator();
                loading = false;
                showLoading(false);
            })
            .catch(function () {
                loading = false;
                showLoading(false);
            });
    }

    function resetAndLoad() {
        var rows = tbody.querySelectorAll("tr:not(#loading-row)");
        for (var i = 0; i < rows.length; i++) {
            rows[i].remove();
        }
        currentOffset = 0;
        hasMore = true;
        loading = false;
        loadMore();
    }

    function appendTransactions(transactions) {
        for (var i = 0; i < transactions.length; i++) {
            var txn = transactions[i];
            var tr = document.createElement("tr");

            var tdDate = document.createElement("td");
            tdDate.textContent = txn.date;

            var tdMerchant = document.createElement("td");
            tdMerchant.textContent = txn.merchant;

            var tdAmount = document.createElement("td");
            tdAmount.className = txn.amount_type;
            tdAmount.textContent = "$" + txn.amount.toFixed(2);

            var tdCategory = document.createElement("td");
            var form = document.createElement("form");
            form.method = "post";
            form.action = "/transactions/" + txn.id;
            form.style.display = "inline";

            var input = document.createElement("input");
            input.type = "text";
            input.name = "category";
            input.value = txn.category;
            input.placeholder = "Enter category";
            input.required = true;

            var button = document.createElement("button");
            button.type = "submit";
            button.textContent = "Update";

            form.appendChild(input);
            form.appendChild(button);
            tdCategory.appendChild(form);

            tr.appendChild(tdDate);
            tr.appendChild(tdMerchant);
            tr.appendChild(tdAmount);
            tr.appendChild(tdCategory);

            if (loadingRow) {
                tbody.insertBefore(tr, loadingRow);
            } else {
                tbody.appendChild(tr);
            }
        }
    }

    function updateCount() {
        if (countDisplay) {
            var shown = Math.min(currentOffset, currentTotal);
            countDisplay.textContent = "Showing " + shown + " of " + currentTotal + " transactions";
        }
    }

    function showLoading(show) {
        if (loadingRow) {
            loadingRow.style.display = show ? "" : "none";
        }
    }

    function hasAdvancedFilters() {
        return minAmount !== "" || maxAmount !== "" || selectedCategories.length > 0;
    }

    function updateFiltersActiveIndicator() {
        if (!filtersActiveIndicator) return;
        if (hasAdvancedFilters() && !filtersVisible) {
            filtersActiveIndicator.style.display = "";
        } else {
            filtersActiveIndicator.style.display = "none";
        }
    }

    function updateExportLink() {
        if (!exportLink) return;
        if (currentTotal === 0) {
            exportLink.style.display = "none";
            return;
        }
        exportLink.style.display = "";
        if (exportAnchor) {
            var qs = buildQueryString(false);
            if (qs) {
                exportAnchor.href = "/transactions/export?" + qs;
                exportAnchor.textContent = "Export filtered results (CSV)";
            } else {
                exportAnchor.href = "/transactions/export";
                exportAnchor.textContent = "Export all transactions (CSV)";
            }
        }
    }
})();
