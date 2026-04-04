/**
 * Transactions page: infinite scroll and search.
 *
 * Loads additional transactions as the user scrolls near the bottom of the page.
 * Provides debounced search that queries the /api/transactions endpoint.
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

    // --- DOM references ---
    var tbody = document.querySelector("#transactions-table tbody");
    var searchInput = document.querySelector("#transaction-search");
    var clearButton = document.querySelector("#search-clear");
    var countDisplay = document.querySelector("#transaction-count");
    var loadingRow = document.querySelector("#loading-row");
    var exportLink = document.querySelector("#export-link");
    var exportAnchor = exportLink ? exportLink.querySelector("a") : null;

    if (!tbody || !searchInput) {
        return; // Not on the transactions page
    }

    // Read initial state from the table's data attributes
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

    // --- Core functions ---

    function loadMore() {
        if (loading || !hasMore) return;
        loading = true;
        showLoading(true);

        var url = "/api/transactions?offset=" + currentOffset + "&limit=50";
        if (searchQuery) {
            url += "&q=" + encodeURIComponent(searchQuery);
        }

        fetch(url)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                appendTransactions(data.transactions);
                currentTotal = data.total;
                currentOffset += data.transactions.length;
                hasMore = data.has_more;
                updateCount();
                updateExportLink();
                loading = false;
                showLoading(false);
            })
            .catch(function () {
                loading = false;
                showLoading(false);
            });
    }

    function resetAndLoad() {
        // Clear existing rows (except loading row)
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
            // Create the inline update form
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

            // Insert before loading row if it exists, otherwise append
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

    function updateExportLink() {
        if (!exportLink) return;
        if (currentTotal === 0) {
            exportLink.style.display = "none";
            return;
        }
        exportLink.style.display = "";
        if (exportAnchor) {
            if (searchQuery) {
                exportAnchor.href = "/transactions/export?q=" + encodeURIComponent(searchQuery);
                exportAnchor.textContent = "Export filtered results (CSV)";
            } else {
                exportAnchor.href = "/transactions/export";
                exportAnchor.textContent = "Export all transactions (CSV)";
            }
        }
    }
})();
