/**
 * Doctest Test Senaryo Üreteci - Editör JS Dosyası
 * Düzenlenebilir içerik işlevlerini içerir
 */

/**
 * Sets up editable content functionality for the test scenarios
 */
function setupEditableContent() {
    // Find all elements with the 'editable' class
    const editableElements = document.querySelectorAll('.editable');

    if (editableElements.length === 0) {
        return; // No editable elements found
    }

    // Düzenlenebilir öğelere tıklama işlevlerini ekle
    editableElements.forEach(element => {
        // Veri özelliklerini kontrol et
        const field = element.dataset.field;
        const scenarioIndex = element.dataset.scenarioIndex;
        const testcaseIndex = element.dataset.testcaseIndex;

        // Edit özelliğini (kalem) oluştur
        const editIcon = document.createElement('div');
        editIcon.className = 'edit-icon';
        editIcon.innerHTML = '<i class="fas fa-edit"></i>';
        editIcon.style.display = 'none';

        // Düzenleme fonksiyonunu tanımla
        element.addEventListener('click', function (event) {
            // Eğer zaten düzenleme modundaysa işlem yapma
            if (this.classList.contains('editing')) {
                return;
            }

            // Orijinal içerik verilerini sakla
            const originalText = this.textContent.trim();
            const originalContent = this.innerHTML;

            // Düzenleme arayüzünü oluştur
            const editor = document.createElement('div');
            editor.className = 'editor-container';

            // Textarea oluştur
            const textarea = document.createElement('textarea');
            textarea.className = 'editor-textarea';
            textarea.value = originalText;
            textarea.placeholder = 'İçeriği buraya girin...';

            // Toolbar oluştur
            const toolbar = document.createElement('div');
            toolbar.className = 'editor-toolbar';

            // Mesaj alanını oluştur
            const message = document.createElement('div');
            message.className = 'editor-message';
            message.innerHTML = '<i class="fas fa-info-circle me-1"></i> Değişikliklerinizi kaydedin veya iptal edin';

            // Butonları oluştur
            const buttons = document.createElement('div');
            buttons.className = 'editor-buttons';

            // İptal butonu
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-sm btn-outline-secondary';
            cancelBtn.innerHTML = '<i class="fas fa-times me-1"></i>İptal';
            cancelBtn.type = 'button';

            // Kaydet butonu
            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn btn-sm btn-success';
            saveBtn.innerHTML = '<i class="fas fa-check me-1"></i>Kaydet';
            saveBtn.type = 'button';

            // Butonları ekle
            buttons.appendChild(cancelBtn);
            buttons.appendChild(saveBtn);
            toolbar.appendChild(message);
            toolbar.appendChild(buttons);

            // Editörü oluştur
            editor.appendChild(textarea);
            editor.appendChild(toolbar);

            // İçeriği temizle ve editörü ekle
            this.innerHTML = '';
            this.appendChild(editor);
            this.classList.add('editing');

            // Textarea'ya odaklan
            textarea.focus();

            // Kaydet butonu işlevi
            const saveHandler = (e) => {
                e.preventDefault();
                e.stopPropagation();

                const newText = textarea.value;

                // Mesaj alanını güncelle
                message.innerHTML = '<i class="fas fa-sync-alt fa-spin me-1"></i> Kaydediliyor...';

                // Veritabanına kaydetmek için API'ye istek gönder
                const documentId = this.dataset.documentId;

                console.log("Document ID:", documentId);

                // API için veri hazırla
                const updateData = {
                    scenario_set_id: documentId,
                    field: field,
                    value: newText,
                    scenario_index: scenarioIndex,
                    test_case_index: testcaseIndex
                };

                console.log("Sending update data:", JSON.stringify(updateData));

                // API'ye istek gönder
                fetch('/api/update_scenario', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData)
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // API isteği başarılı oldu

                            // Editörü kaldır
                            editor.remove();

                            // İçeriği güncelle
                            this.textContent = newText;
                            this.classList.remove('editing');

                            // Bildirim göster
                            const notification = document.createElement('div');
                            notification.className = 'alert alert-success py-2 px-3';
                            notification.innerHTML = '<i class="fas fa-check-circle me-2"></i>Değişiklikler başarıyla kaydedildi!';
                            this.appendChild(notification);

                            // Yerel veriyi de güncelle
                            if (window.testScenariosData) {
                                if (field === 'summary') {
                                    window.testScenariosData.summary = newText;
                                } else if (scenarioIndex !== undefined) {
                                    try {
                                        const scIndex = parseInt(scenarioIndex);
                                        if (testcaseIndex !== undefined) {
                                            const tcIndex = parseInt(testcaseIndex);
                                            window.testScenariosData.scenarios[scIndex].test_cases[tcIndex][field] = newText;
                                        } else {
                                            window.testScenariosData.scenarios[scIndex][field] = newText;
                                        }
                                    } catch (e) {
                                        console.error('Error updating scenario data:', e);
                                    }
                                }
                            }

                            // 2 saniye sonra bildirimi kaldır
                            setTimeout(() => {
                                if (notification && notification.parentNode) {
                                    notification.remove();
                                }
                            }, 2000);

                            console.log(`Updated content for ${field} in scenario ${scenarioIndex || 'undefined'}${testcaseIndex ? ', test case ' + testcaseIndex : ''}`);
                        } else {
                            // Hata olduğunda mesaj göster
                            const notification = document.createElement('div');
                            notification.className = 'alert alert-danger py-2 px-3';
                            notification.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Hata: ${data.error || 'Bilinmeyen hata'}`;

                            // Editörü kaldır
                            editor.remove();

                            // Orijinal içeriği geri yükle ve bildirimi ekle
                            this.innerHTML = originalContent;
                            this.classList.remove('editing');
                            this.appendChild(notification);

                            console.error('Error saving to database:', data.error);

                            // 3 saniye sonra bildirimi kaldır
                            setTimeout(() => {
                                if (notification && notification.parentNode) {
                                    notification.remove();
                                }
                            }, 3000);
                        }
                    })
                    .catch(error => {
                        console.error('API request failed:', error);

                        // Hata mesajı göster
                        const notification = document.createElement('div');
                        notification.className = 'alert alert-danger py-2 px-3';
                        notification.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Sunucu hatası! Değişiklikler kaydedilemedi.';

                        // Editörü kaldır
                        editor.remove();

                        // Orijinal içeriği geri yükle ve bildirimi ekle
                        this.innerHTML = originalContent;
                        this.classList.remove('editing');
                        this.appendChild(notification);

                        // 3 saniye sonra bildirimi kaldır
                        setTimeout(() => {
                            if (notification && notification.parentNode) {
                                notification.remove();
                            }
                        }, 3000);
                    });
            };

            // İptal butonu işlevi
            const cancelHandler = (e) => {
                e.preventDefault();
                e.stopPropagation();

                // Editörü kaldır
                editor.remove();

                // Orijinal içeriği geri yükle
                this.innerHTML = originalContent;
                this.classList.remove('editing');

                // Bildirim ekle
                const notification = document.createElement('div');
                notification.className = 'alert alert-info py-2 px-3';
                notification.innerHTML = '<i class="fas fa-info-circle me-2"></i>Değişiklikler iptal edildi';
                this.appendChild(notification);

                // 2 saniye sonra bildirimi kaldır
                setTimeout(() => {
                    if (notification && notification.parentNode) {
                        notification.remove();
                    }
                }, 2000);
            };

            // Butonlara tek seferlik olay dinleyicileri ekle
            saveBtn.addEventListener('click', saveHandler);
            cancelBtn.addEventListener('click', cancelHandler);

            // Enter ve Escape tuş olaylarını ele al
            textarea.addEventListener('keydown', function (e) {
                // Ctrl+Enter ile kaydet
                if (e.key === 'Enter' && e.ctrlKey) {
                    saveHandler(e);
                }

                // Escape ile iptal et
                if (e.key === 'Escape') {
                    cancelHandler(e);
                }
            });

            // Dışarı tıklanması engellenir
            event.stopPropagation();
        });
    });
}