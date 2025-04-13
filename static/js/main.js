// Main JavaScript for Document Test Scenario Generator

document.addEventListener('DOMContentLoaded', function () {
    // Handle form submission with loading spinner
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function () {
            showLoadingSpinner('Test senaryoları oluşturuluyor... Bu işlem bir dakika kadar sürebilir.');
        });
    }

    // Initialize export buttons if they exist
    setupExportButtons();

    // Initialize editable content if on results page
    setupEditableContent();

    // Initialize playground if on results page
    setupPlayground();

    // Initialize test automation if on results page
    setupTestAutomation();

    // Initialize clipboard functionality
    setupClipboard();

    // Initialize file upload preview
    setupFileUploadPreview();

    // Initialize processing options
    setupProcessingOptions();

    // Initialize analytics chart if on analytics page
    setupAnalyticsChart();
});

/**
 * Shows a loading spinner overlay with custom message
 * @param {string} message - Message to display with the spinner
 */
function showLoadingSpinner(message) {
    const spinnerOverlay = document.createElement('div');
    spinnerOverlay.className = 'spinner-overlay';
    spinnerOverlay.innerHTML = `
        <div class="spinner-container">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Yükleniyor...</span>
            </div>
            <div class="spinner-message mt-3">
                ${message || 'İşleminiz gerçekleştiriliyor...'}
            </div>
        </div>
    `;
    document.body.appendChild(spinnerOverlay);
}

/**
 * Hides the loading spinner
 */
function hideLoadingSpinner() {
    const spinnerOverlay = document.querySelector('.spinner-overlay');
    if (spinnerOverlay) {
        spinnerOverlay.remove();
    }
}

/**
 * Sets up clipboard functionality for code copying
 */
function setupClipboard() {
    const copyBtns = document.querySelectorAll('.copy-btn');

    copyBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const targetId = this.getAttribute('data-clipboard-target');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                navigator.clipboard.writeText(targetElement.textContent).then(() => {
                    // Show success state
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i> Kopyalandı';
                    this.classList.add('btn-success');
                    this.classList.remove('btn-outline-secondary');

                    // Reset after 2 seconds
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.classList.remove('btn-success');
                        this.classList.add('btn-outline-secondary');
                    }, 2000);
                });
            }
        });
    });
}

/**
 * Sets up file upload preview functionality
 */
function setupFileUploadPreview() {
    const fileInput = document.getElementById('file');
    const filePreview = document.getElementById('filePreview');

    if (fileInput && filePreview) {
        fileInput.addEventListener('change', function () {
            // Clear previous preview
            filePreview.innerHTML = '';

            if (this.files && this.files.length > 0) {
                const file = this.files[0];

                // Create preview card
                const card = document.createElement('div');
                card.className = 'card border-0 shadow-sm mt-3';

                const fileIcon = getFileIcon(file.name);

                // Card body with file info
                card.innerHTML = `
                    <div class="card-body d-flex align-items-center">
                        <div class="file-icon me-3 fs-2 text-primary">
                            ${fileIcon}
                        </div>
                        <div class="file-info flex-grow-1">
                            <h6 class="mb-0 text-truncate" style="max-width: 250px;">${file.name}</h6>
                            <small class="text-muted">${formatFileSize(file.size)}</small>
                        </div>
                        <div class="file-remove">
                            <button type="button" class="btn btn-sm btn-outline-danger border-0" id="removeFile">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                `;

                filePreview.appendChild(card);

                // Handle remove file button
                const removeFileBtn = document.getElementById('removeFile');
                if (removeFileBtn) {
                    removeFileBtn.addEventListener('click', function () {
                        fileInput.value = '';
                        filePreview.innerHTML = '';
                    });
                }
            }
        });
    }
}

/**
 * Gets appropriate icon for file type
 * @param {string} filename - The filename to check
 * @returns {string} HTML for the appropriate icon
 */
function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();

    switch (extension) {
        case 'pdf':
            return '<i class="fas fa-file-pdf"></i>';
        case 'doc':
        case 'docx':
            return '<i class="fas fa-file-word"></i>';
        case 'xls':
        case 'xlsx':
            return '<i class="fas fa-file-excel"></i>';
        case 'ppt':
        case 'pptx':
            return '<i class="fas fa-file-powerpoint"></i>';
        case 'txt':
            return '<i class="fas fa-file-alt"></i>';
        case 'zip':
        case 'rar':
            return '<i class="fas fa-file-archive"></i>';
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
            return '<i class="fas fa-file-image"></i>';
        default:
            return '<i class="fas fa-file"></i>';
    }
}

/**
 * Formats file size in human-readable format
 * @param {number} bytes - The file size in bytes
 * @returns {string} Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Sets up processing options selection
 */
function setupProcessingOptions() {
    const aiProvider = document.getElementById('ai_provider');
    const llamaParseContainer = document.getElementById('llama_parse_container');
    const doclingContainer = document.getElementById('docling_container');
    const llmDataContainer = document.getElementById('llm_data_container');

    if (aiProvider && llamaParseContainer && doclingContainer && llmDataContainer) {
        // Initial setup based on current selection
        updateProcessingOptions();

        // Handle changes to AI provider
        aiProvider.addEventListener('change', updateProcessingOptions);

        // Handle changes to LLM data option
        const llmDataCheckbox = document.getElementById('llm_data');
        if (llmDataCheckbox) {
            llmDataCheckbox.addEventListener('change', updateProcessingOptions);
        }
    }

    function updateProcessingOptions() {
        const selectedProvider = aiProvider.value;
        const isLlmDataChecked = document.getElementById('llm_data').checked;

        // Show/hide LlamaParse option based on selection
        if (selectedProvider === 'openai' || selectedProvider === 'azure' || selectedProvider === 'api-url') {
            // OpenAI & Azure can use LlamaParse
            llamaParseContainer.classList.remove('d-none');

            // Only show Docling for OpenAI modes
            doclingContainer.classList.remove('d-none');
        } else {
            // Ollama & DeepSeek cannot use LlamaParse
            llamaParseContainer.classList.add('d-none');
            document.getElementById('llama_parse').checked = false;

            // Don't show Docling for non-OpenAI modes
            doclingContainer.classList.add('d-none');
            document.getElementById('use_docling').checked = false;
        }

        // Show/hide LLM data based on selection
        if (isLlmDataChecked) {
            // Show LlamaParse option if LLM data is selected
            llamaParseContainer.classList.remove('d-none');
        }
    }
}

/**
 * Sets up analytics chart display
 */
function setupAnalyticsChart() {
    const categoryChartCanvas = document.getElementById('categoryChart');
    const complexityChartCanvas = document.getElementById('complexityChart');

    if (categoryChartCanvas) {
        const categoryData = JSON.parse(categoryChartCanvas.dataset.chartData || '{}');
        new Chart(categoryChartCanvas, {
            type: 'pie',
            data: {
                labels: Object.keys(categoryData),
                datasets: [{
                    data: Object.values(categoryData),
                    backgroundColor: [
                        '#126e82',
                        '#51c4d3',
                        '#0a2342',
                        '#f2b705',
                        '#ff3e5f',
                        '#6e7582',
                        '#2e5eaa',
                        '#a72608'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }

    if (complexityChartCanvas) {
        const complexityData = JSON.parse(complexityChartCanvas.dataset.chartData || '{}');
        new Chart(complexityChartCanvas, {
            type: 'bar',
            data: {
                labels: Object.keys(complexityData),
                datasets: [{
                    label: 'Test Vakası Sayısı',
                    data: Object.values(complexityData),
                    backgroundColor: [
                        '#51c4d3',
                        '#126e82',
                        '#0a2342'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
}