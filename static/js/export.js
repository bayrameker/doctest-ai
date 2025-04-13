/**
 * Doctest Test Senaryo Üreteci - Dışa Aktarma JS Dosyası
 * Test senaryolarını dışa aktarma işlevlerini içerir
 */

/**
 * Sets up export functionality for the generated scenarios
 */
function setupExportButtons() {
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    const exportTextBtn = document.getElementById('exportTextBtn');
    const exportCsvBtn = document.getElementById('exportCsvBtn');

    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', function () {
            exportScenarios('json');
        });
    }

    if (exportTextBtn) {
        exportTextBtn.addEventListener('click', function () {
            exportScenarios('text');
        });
    }

    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function () {
            exportScenarios('csv');
        });
    }
}

/**
 * Exports the generated scenarios in the specified format
 * @param {string} format - The format to export ('json', 'text', or 'csv')
 */
function exportScenarios(format) {
    const scenariosDataElement = document.getElementById('scenariosData');
    if (!scenariosDataElement) {
        console.error('Scenarios data element not found');
        return;
    }

    try {
        const data = JSON.parse(scenariosDataElement.textContent);
        let content, filename, contentType;

        switch (format) {
            case 'json':
                content = JSON.stringify(data, null, 2);
                filename = `test_scenarios_${formatDateForFilename()}.json`;
                contentType = 'application/json';
                break;
            case 'csv':
                content = convertToCsv(data);
                filename = `test_scenarios_${formatDateForFilename()}.csv`;
                contentType = 'text/csv';
                break;
            case 'text':
            default:
                content = convertToText(data);
                filename = `test_scenarios_${formatDateForFilename()}.txt`;
                contentType = 'text/plain';
                break;
        }

        downloadFile(content, filename, contentType);
    } catch (e) {
        console.error('Error exporting scenarios:', e);
        alert('Senaryolar dışa aktarılırken bir hata oluştu.');
    }
}

/**
 * Creates and triggers a file download
 * @param {string} content - The content to download
 * @param {string} filename - The name of the file
 * @param {string} contentType - The MIME type of the file
 */
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';

    document.body.appendChild(a);
    a.click();

    setTimeout(function () {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);
}

/**
 * Formats the current date for use in filenames
 * @returns {string} A formatted date string (YYYY-MM-DD)
 */
function formatDateForFilename() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Converts scenario data to a text format
 * @param {Object} data - The scenario data
 * @returns {string} The formatted text
 */
function convertToText(data) {
    let text = `TEST SENARYOLARI RAPORU\n`;
    text += `Oluşturulma Tarihi: ${new Date().toLocaleString('tr-TR')}\n\n`;

    if (data.document_name) {
        text += `Belge: ${data.document_name}\n`;
    }

    text += `AI Modeli: ${data.ai_model || 'Belirtilmemiş'}\n\n`;

    if (data.summary) {
        text += `ÖZET\n${data.summary}\n\n`;
    }

    text += `SENARYOLAR\n\n`;

    data.scenarios.forEach((scenario, index) => {
        text += `#${index + 1} - ${scenario.title}\n`;

        if (scenario.priority) {
            text += `Öncelik: ${scenario.priority}\n`;
        }

        if (scenario.description) {
            text += `Açıklama: ${scenario.description}\n`;
        }

        text += `\n`;

        if (scenario.test_cases && scenario.test_cases.length > 0) {
            scenario.test_cases.forEach((testCase, testIndex) => {
                text += `  Test Vakası ${testIndex + 1}: ${testCase.title || ''}\n`;

                if (testCase.steps) {
                    text += `  Adımlar:\n`;
                    const steps = testCase.steps.split('\n');
                    steps.forEach((step, stepIndex) => {
                        if (step.trim()) {
                            text += `    ${stepIndex + 1}. ${step.trim()}\n`;
                        }
                    });
                }

                if (testCase.expected_results) {
                    text += `  Beklenen Sonuçlar:\n`;
                    const results = testCase.expected_results.split('\n');
                    results.forEach((result, resultIndex) => {
                        if (result.trim()) {
                            text += `    ${resultIndex + 1}. ${result.trim()}\n`;
                        }
                    });
                }

                text += `\n`;
            });
        }

        text += `---------------------------------------\n\n`;
    });

    return text;
}

/**
 * Converts scenario data to CSV format
 * @param {Object} data - The scenario data
 * @returns {string} The CSV formatted text
 */
function convertToCsv(data) {
    // CSV başlık satırı
    let csv = 'Senaryo ID,Senaryo Başlığı,Öncelik,Açıklama,Test Vakası ID,Test Vakası Başlığı,Test Adımları,Beklenen Sonuçlar\n';

    // Her senaryo için satır oluştur
    data.scenarios.forEach((scenario, scenarioIndex) => {
        const scenarioId = scenarioIndex + 1;
        const scenarioTitle = escapeCsvField(scenario.title || '');
        const priority = escapeCsvField(scenario.priority || '');
        const description = escapeCsvField(scenario.description || '');

        if (scenario.test_cases && scenario.test_cases.length > 0) {
            // Her test vakası için bir satır
            scenario.test_cases.forEach((testCase, testIndex) => {
                const testId = `${scenarioId}.${testIndex + 1}`;
                const testTitle = escapeCsvField(testCase.title || '');
                const steps = escapeCsvField(testCase.steps || '');
                const expectedResults = escapeCsvField(testCase.expected_results || '');

                csv += `${scenarioId},${scenarioTitle},${priority},${description},${testId},${testTitle},${steps},${expectedResults}\n`;
            });
        } else {
            // Test vakası yoksa boş bir satır
            csv += `${scenarioId},${scenarioTitle},${priority},${description},,,,\n`;
        }
    });

    return csv;
}

/**
 * Escapes special characters for CSV format
 * @param {string} field - The field to escape
 * @returns {string} The escaped field
 */
function escapeCsvField(field) {
    if (typeof field !== 'string') {
        return '';
    }

    // Eğer içinde virgül, çift tırnak veya yeni satır varsa, çift tırnak içine al
    if (field.includes(',') || field.includes('"') || field.includes('\n') || field.includes('\r')) {
        // Çift tırnakları iki çift tırnak yaparak escape et
        return `"${field.replace(/"/g, '""')}"`;
    }

    return field;
}