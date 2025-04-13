/**
 * Doctest Test Senaryo Üreteci - Playground JS Dosyası
 * Test senaryosu playground işlevlerini içerir
 */

/**
 * Sets up the playground functionality for interactive test scenario editing
 */
function setupPlayground() {
    const scenarioSelect = document.getElementById('scenarioSelect');
    const playgroundContainer = document.getElementById('playgroundContainer');
    const playgroundTitle = document.getElementById('playgroundTitle');
    const playgroundPriority = document.getElementById('playgroundPriority');
    const playgroundDescription = document.getElementById('playgroundDescription');
    const playgroundSteps = document.getElementById('playgroundSteps');
    const playgroundExpectedResults = document.getElementById('playgroundExpectedResults');
    const resetPlaygroundBtn = document.getElementById('resetPlaygroundBtn');
    const savePlaygroundBtn = document.getElementById('savePlaygroundBtn');

    if (!scenarioSelect) return;

    // Global variable to store original scenario data
    let originalScenarioData = null;
    let currentScenarioIndex = -1;

    // Load test scenarios data from the page
    const testScenariosData = getTestScenariosData();

    // Klavye kısayollarını ayarla
    document.addEventListener('keydown', function (e) {
        // Ctrl+Enter ile kaydet
        if (e.ctrlKey && e.key === 'Enter' && savePlaygroundBtn && currentScenarioIndex !== -1) {
            e.preventDefault();
            savePlaygroundBtn.click();
        }

        // Escape ile sıfırla
        if (e.key === 'Escape' && resetPlaygroundBtn && currentScenarioIndex !== -1) {
            e.preventDefault();
            resetPlaygroundBtn.click();
        }
    });

    scenarioSelect.addEventListener('change', function () {
        const selectedIndex = this.value;
        if (!selectedIndex) {
            playgroundContainer.classList.add('d-none');
            return;
        }

        currentScenarioIndex = parseInt(selectedIndex);
        const scenario = testScenariosData.scenarios[currentScenarioIndex];
        originalScenarioData = JSON.parse(JSON.stringify(scenario));

        // Populate the playground with scenario data
        playgroundTitle.value = scenario.title || '';
        playgroundPriority.value = scenario.priority || 'Orta';
        playgroundDescription.value = scenario.description || '';

        // Get test steps and expected results from the first test case
        if (scenario.test_cases && scenario.test_cases.length > 0) {
            const testCase = scenario.test_cases[0];
            playgroundSteps.textContent = testCase.steps || '';
            playgroundExpectedResults.textContent = testCase.expected_results || '';
        } else {
            playgroundSteps.textContent = '';
            playgroundExpectedResults.textContent = '';
        }

        // Show the playground container
        playgroundContainer.classList.remove('d-none');

        // Initialize code highlighting if Prism.js is available
        if (typeof Prism !== 'undefined') {
            Prism.highlightElement(playgroundSteps);
            Prism.highlightElement(playgroundExpectedResults);
        }
    });

    // Düzenlenebilir kod alanlarını aktif et
    if (playgroundSteps) {
        makeEditable(playgroundSteps);
    }

    if (playgroundExpectedResults) {
        makeEditable(playgroundExpectedResults);
    }

    // Handle reset button click
    if (resetPlaygroundBtn) {
        resetPlaygroundBtn.addEventListener('click', function () {
            if (!originalScenarioData || currentScenarioIndex === -1) return;

            // Reset form values to original data
            playgroundTitle.value = originalScenarioData.title || '';
            playgroundPriority.value = originalScenarioData.priority || 'Orta';
            playgroundDescription.value = originalScenarioData.description || '';

            if (originalScenarioData.test_cases && originalScenarioData.test_cases.length > 0) {
                const testCase = originalScenarioData.test_cases[0];
                playgroundSteps.textContent = testCase.steps || '';
                playgroundExpectedResults.textContent = testCase.expected_results || '';

                // Re-highlight if Prism.js is available
                if (typeof Prism !== 'undefined') {
                    Prism.highlightElement(playgroundSteps);
                    Prism.highlightElement(playgroundExpectedResults);
                }
            }

            // Başarı mesajı göster
            const infoAlert = document.createElement('div');
            infoAlert.className = 'alert alert-info mt-3';
            infoAlert.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Senaryo orijinal haline döndürüldü.';
            playgroundContainer.appendChild(infoAlert);

            // 3 saniye sonra mesajı kaldır
            setTimeout(() => {
                infoAlert.remove();
            }, 3000);
        });
    }

    // Handle save button click
    if (savePlaygroundBtn) {
        savePlaygroundBtn.addEventListener('click', function () {
            if (currentScenarioIndex === -1) return;

            // Show loading overlay
            const loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'loading-overlay';
            loadingOverlay.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Kaydediliyor...</span>
                </div>
                <div class="mt-2">Senaryo güncelleniyor...</div>
            `;
            playgroundContainer.appendChild(loadingOverlay);

            // Get updated values
            const updatedData = {
                scenario_set_id: testScenariosData.id,
                scenario_index: currentScenarioIndex,
                title: playgroundTitle.value,
                priority: playgroundPriority.value,
                description: playgroundDescription.value,
                steps: playgroundSteps.textContent,
                expected_results: playgroundExpectedResults.textContent
            };

            // Send update request to server
            fetch('/api/update_playground', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedData)
            })
                .then(response => response.json())
                .then(data => {
                    // Remove loading overlay
                    loadingOverlay.remove();

                    if (data.success) {
                        // Update was successful
                        const successAlert = document.createElement('div');
                        successAlert.className = 'alert alert-success mt-3';
                        successAlert.innerHTML = '<i class="fas fa-check-circle me-2"></i>Senaryo başarıyla güncellendi!';
                        playgroundContainer.appendChild(successAlert);

                        // Update local data
                        const scenario = testScenariosData.scenarios[currentScenarioIndex];
                        scenario.title = updatedData.title;
                        scenario.priority = updatedData.priority;
                        scenario.description = updatedData.description;

                        if (scenario.test_cases && scenario.test_cases.length > 0) {
                            scenario.test_cases[0].steps = updatedData.steps;
                            scenario.test_cases[0].expected_results = updatedData.expected_results;
                        } else if (updatedData.steps || updatedData.expected_results) {
                            // Eğer senaryo test senaryosu yoksa ve kullanıcı adımlar veya beklenen sonuçlar ekliyorsa
                            // yeni bir test senaryosu oluştur
                            scenario.test_cases = [{
                                title: `${scenario.title} Test`,
                                steps: updatedData.steps,
                                expected_results: updatedData.expected_results
                            }];
                        }

                        // Senaryo seçim menüsündeki başlığı güncelle
                        const optionElement = scenarioSelect.querySelector(`option[value="${currentScenarioIndex}"]`);
                        if (optionElement) {
                            optionElement.textContent = updatedData.title;
                        }

                        // Update the original data
                        originalScenarioData = JSON.parse(JSON.stringify(scenario));

                        // Remove success alert after 3 seconds
                        setTimeout(() => {
                            successAlert.remove();
                        }, 3000);
                    } else {
                        // Update failed
                        const errorAlert = document.createElement('div');
                        errorAlert.className = 'alert alert-danger mt-3';
                        errorAlert.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Hata: ${data.error || 'Güncelleme başarısız oldu'}`;
                        playgroundContainer.appendChild(errorAlert);

                        // Remove error alert after 5 seconds
                        setTimeout(() => {
                            errorAlert.remove();
                        }, 5000);
                    }
                })
                .catch(error => {
                    // Remove loading overlay
                    loadingOverlay.remove();

                    // Show error message
                    const errorAlert = document.createElement('div');
                    errorAlert.className = 'alert alert-danger mt-3';
                    errorAlert.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Sunucu hatası! Lütfen daha sonra tekrar deneyin.';
                    playgroundContainer.appendChild(errorAlert);

                    console.error('Error updating playground:', error);

                    // Remove error alert after 5 seconds
                    setTimeout(() => {
                        errorAlert.remove();
                    }, 5000);
                });
        });
    }
}

/**
 * Bir kodu düzenlenebilir hale getirir
 * @param {HTMLElement} codeElement - Düzenlenebilir hale getirilecek kod elementi
 */
function makeEditable(codeElement) {
    if (!codeElement) return;

    codeElement.setAttribute('contenteditable', 'true');
    codeElement.setAttribute('spellcheck', 'false');

    // Düzenleme sırasında syntax highlighting'i korumak için
    codeElement.addEventListener('blur', function () {
        if (typeof Prism !== 'undefined') {
            Prism.highlightElement(codeElement);
        }
    });

    // Tab tuşunun normal çalışmasını sağla
    codeElement.addEventListener('keydown', function (e) {
        if (e.key === 'Tab') {
            e.preventDefault();

            // Seçili metin varsa, her satırın başına tab ekle
            if (window.getSelection) {
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const selectedText = range.toString();

                    // Seçili metin varsa ve içinde satır sonu varsa
                    if (selectedText && selectedText.includes('\n')) {
                        const lines = selectedText.split('\n');
                        const indentedText = lines.map(line => '    ' + line).join('\n');

                        // Seçili metni değiştir
                        document.execCommand('insertText', false, indentedText);
                        return;
                    }
                }
            }

            // Seçili metin yoksa veya tek satırsa, sadece 4 boşluk ekle
            document.execCommand('insertText', false, '    ');
        }
    });

    // AI destekli otomatik tamamlama
    codeElement.addEventListener('keyup', function (e) {
        // Sadece belirli tuşlarda AI destekli tamamlama devreye girsin
        if (e.key === '.' || e.key === ' ' || e.key === '\n') {
            const currentText = codeElement.textContent;
            const lastLine = currentText.split('\n').pop();

            // Satır sonunda durduysa ve satır belli bir uzunluktaysa
            if (lastLine.length > 10 && (lastLine.endsWith('.') || lastLine.endsWith(' '))) {
                // Bu noktada gerçek bir uygulamada AI API'sine istek atılabilir
                // Ancak bu örnek için sadece basit bir tamamlama gösteriyoruz

                // Burada gerçek bir AI ile tamamlama yapılabilir
                // Örneğin, eğer senaryo adı içinde "login" geçiyorsa
                if (currentText.toLowerCase().includes('login') || currentText.toLowerCase().includes('giriş')) {
                    setTimeout(() => {
                        const suggestion = "Kullanıcı adı ve şifre alanlarını doldur ve giriş butonuna tıkla.";
                        showSuggestion(codeElement, suggestion);
                    }, 300);
                }
                // Eğer senaryo adı içinde "search" veya "ara" geçiyorsa
                else if (currentText.toLowerCase().includes('search') || currentText.toLowerCase().includes('ara')) {
                    setTimeout(() => {
                        const suggestion = "Arama kutusuna metin yaz ve ara butonuna tıkla.";
                        showSuggestion(codeElement, suggestion);
                    }, 300);
                }
            }
        }
    });
}

/**
 * Kullanıcıya bir öneri gösterir
 * @param {HTMLElement} element - Önerinin gösterileceği element
 * @param {string} suggestion - Öneri metni
 */
function showSuggestion(element, suggestion) {
    // Öneri görüntüleme elementini oluştur
    let suggestionEl = document.getElementById('ai-suggestion');
    if (!suggestionEl) {
        suggestionEl = document.createElement('div');
        suggestionEl.id = 'ai-suggestion';
        suggestionEl.className = 'ai-suggestion-popup';
        suggestionEl.innerHTML = `
            <div class="suggestion-content">
                <i class="fas fa-robot me-2"></i>
                <span class="suggestion-text"></span>
            </div>
            <div class="suggestion-actions">
                <button class="btn btn-sm btn-primary accept-suggestion">
                    <i class="fas fa-check me-1"></i>Kabul Et
                </button>
                <button class="btn btn-sm btn-outline-secondary dismiss-suggestion">
                    <i class="fas fa-times me-1"></i>Reddet
                </button>
            </div>
        `;
        document.body.appendChild(suggestionEl);

        // Öneriyi kabul et
        suggestionEl.querySelector('.accept-suggestion').addEventListener('click', function () {
            const suggestionText = suggestionEl.querySelector('.suggestion-text').textContent;
            if (element) {
                // Öneriyi ekle
                element.textContent += suggestionText;
                if (typeof Prism !== 'undefined') {
                    Prism.highlightElement(element);
                }
            }
            suggestionEl.style.display = 'none';
        });

        // Öneriyi reddet
        suggestionEl.querySelector('.dismiss-suggestion').addEventListener('click', function () {
            suggestionEl.style.display = 'none';
        });
    }

    // Öneri metnini ayarla
    suggestionEl.querySelector('.suggestion-text').textContent = suggestion;

    // Öneriyi göster
    suggestionEl.style.display = 'block';

    // Öneriyi element yanına konumlandır
    const rect = element.getBoundingClientRect();
    suggestionEl.style.top = `${rect.bottom + window.scrollY + 10}px`;
    suggestionEl.style.left = `${rect.left + window.scrollX}px`;

    // 5 saniye sonra kaybol
    setTimeout(() => {
        if (suggestionEl.style.display === 'block') {
            suggestionEl.style.display = 'none';
        }
    }, 5000);
}

/**
 * Gets test scenarios data from the global variable or hidden element on the page
 * @returns {Object} The parsed test scenarios data
 */
function getTestScenariosData() {
    // Önce global değişkeni kontrol et
    if (window.testScenariosData) {
        return window.testScenariosData;
    }

    // Sonra gizli elemandan veri almayı dene
    const scenariosDataElement = document.getElementById('scenariosData');
    if (!scenariosDataElement) {
        // Sayfadaki script değişkenlerini kontrol et
        const scriptElements = document.querySelectorAll('script');
        for (let script of scriptElements) {
            if (script.textContent.includes('window.testScenariosData')) {
                // Eğer bulunursa, global değişken zaten tanımlanmış demektir
                return window.testScenariosData || { scenarios: [] };
            }
        }

        // Sayfa içerisindeki JSON veriyi kontrol et
        const jsonContainers = document.querySelectorAll('[data-scenario-json]');
        if (jsonContainers.length > 0) {
            try {
                const data = JSON.parse(jsonContainers[0].getAttribute('data-scenario-json'));
                window.testScenariosData = data;
                return data;
            } catch (e) {
                console.error('Error parsing JSON from data attribute:', e);
            }
        }

        // Hiçbir veri bulunamadıysa boş bir nesne döndür
        console.warn('Test scenarios data not found on page, using empty data');
        return { scenarios: [] };
    }

    try {
        const data = JSON.parse(scenariosDataElement.textContent);
        window.testScenariosData = data; // Store in global for other functions
        return data;
    } catch (e) {
        console.error('Error parsing scenarios data:', e);
        return { scenarios: [] };
    }
}