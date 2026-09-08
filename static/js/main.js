// ===== MAIN JAVASCRIPT =====

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }, 5000);
    });
    
    // Enable tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// ===== TABLE EXPORT FUNCTIONS =====

// Function to export table to CSV
function exportToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let row of rows) {
        const rowData = [];
        const cols = row.querySelectorAll('th, td');
        for (let col of cols) {
            let text = col.innerText.trim();
            // Escape commas and quotes
            if (text.includes(',') || text.includes('"')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }
            rowData.push(text);
        }
        csv.push(rowData.join(','));
    }
    
    // Add BOM for UTF-8
    const csvContent = '\uFEFF' + csv.join('\n');
    downloadFile(csvContent, filename || 'export.csv', 'text/csv');
}

// Function to export table to Excel (via HTML table format)
function exportToExcel(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // Create HTML table with styles
    let html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" 
              xmlns:x="urn:schemas-microsoft-com:office:excel" 
              xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <meta charset="UTF-8">
            <!--[if gte mso 9]>
            <xml>
                <x:ExcelWorkbook>
                    <x:ExcelWorksheets>
                        <x:ExcelWorksheet>
                            <x:Name>Sheet1</x:Name>
                            <x:WorksheetOptions>
                                <x:DisplayGridlines/>
                            </x:WorksheetOptions>
                        </x:ExcelWorksheet>
                    </x:ExcelWorksheets>
                </x:ExcelWorkbook>
            </xml>
            <![endif]-->
            <style>
                table { border-collapse: collapse; width: 100%; }
                th { background: #1a237e; color: white; font-weight: bold; padding: 8px; border: 1px solid #000; }
                td { padding: 6px; border: 1px solid #000; }
            </style>
        </head>
        <body>
            ${table.outerHTML}
        </body>
        </html>
    `;
    
    downloadFile(html, filename || 'export.xls', 'application/vnd.ms-excel');
}

// Function to export table to PDF (via window.print)
function exportToPDF(tableId, title) {
    // Store original content
    const originalContent = document.body.innerHTML;
    
    // Create print-friendly version
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const printContent = `
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h1 style="text-align: center; color: #1a237e;">${title || 'Group List'}</h1>
            <hr>
            ${table.outerHTML}
            <p style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                Printed on ${new Date().toLocaleDateString()}
            </p>
        </div>
    `;
    
    document.body.innerHTML = printContent;
    window.print();
    
    // Restore original content
    document.body.innerHTML = originalContent;
    // Re-initialize event listeners
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

// Helper function to download file
function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType + ';charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ===== SEARCH FUNCTION =====

function searchTable(tableId, inputId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    
    if (!input || !table) return;
    
    input.addEventListener('keyup', function() {
        const searchText = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(function(row) {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchText) ? '' : 'none';
        });
    });
}

// ===== CLEAR SEARCH FUNCTION =====

function clearSearch(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.value = '';
        input.dispatchEvent(new Event('keyup'));
    }
              }
