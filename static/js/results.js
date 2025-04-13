/**
 * Test Senaryoları Sonuç Sayfası JavaScript
 * 
 * Bu dosya, sonuçlar sayfasındaki interaktif özellikleri yönetir:
 * - Kopyalama işlevleri
 * - Panel genişletme/daraltma
 * - Paylaşım özellikleri
 * - Modül iletişimi
 * - Toast bildirimleri
 */

// Sayfa yüklendiğinde çalışacak ana fonksiyon
document.addEventListener('DOMContentLoaded', function() {
    // Toast bildirimi örneği
    const copyToast = new bootstrap.Toast(document.getElementById('copyToast'));
    
    // Kopyalama fonksiyonları
    setupCopyFunctions(copyToast);
    
    // Genişlet/Daralt butonları
    setupAccordionControls();
    
    // Paylaşım modal butonları
    setupModalActions(copyToast);
    
    // Animasyon efektleri
    setupAnimationEffects();
    
    // Hızlı erişim ve modal işlevleri
    setupQuickActions();
});

/**
 * Kopyalama işlevlerini ayarlar
 */
function setupCopyFunctions(copyToast) {
    // Özeti kopyala
    const copyAllBtn = document.getElementById('copyAllBtn');
    if (copyAllBtn) {
        copyAllBtn.addEventListener('click', function() {
            const summaryContent = document.querySelector('.summary-content').innerText;
            copyToClipboard(summaryContent, copyToast);
        });
    }
    
    // Tüm senaryoları kopyala
    const copyAllScenarios = document.getElementById('copyAllScenarios');
    if (copyAllScenarios) {
        copyAllScenarios.addEventListener('click', function() {
            const scenarioElements = document.querySelectorAll('.scenario-accordion .accordion-item');
            let allScenariosText = '';
            
            scenarioElements.forEach((scenario, index) => {
                const title = scenario.querySelector('.scenario-title').innerText;
                const description = scenario.querySelector('.scenario-description').innerText;
                
                allScenariosText += `Senaryo ${index + 1}: ${title}\n`;
                allScenariosText += `Açıklama: ${description}\n\n`;
                
                const testCases = scenario.querySelectorAll('.test-case-card');
                testCases.forEach((testCase, testIndex) => {
                    const testTitle = testCase.querySelector('.test-case-title').innerText;
                    const steps = testCase.querySelector('[data-field="steps"]')?.innerText || '';
                    const expectedResults = testCase.querySelector('[data-field="expected_results"]')?.innerText || '';
                    
                    allScenariosText += `  Test ${testIndex + 1}: ${testTitle}\n`;
                    allScenariosText += `  Adımlar: ${steps}\n`;
                    allScenariosText += `  Beklenen Sonuçlar: ${expectedResults}\n\n`;
                });
                
                allScenariosText += '-----------------------------------\n\n';
            });
            
            copyToClipboard(allScenariosText, copyToast);
        });
    }
    
    // Doküman içeriğini kopyala
    const copyDocumentContent = document.getElementById('copyDocumentContent');
    if (copyDocumentContent) {
        copyDocumentContent.addEventListener('click', function() {
            const documentText = document.querySelector('.document-content').innerText;
            copyToClipboard(documentText, copyToast);
        });
    }
}

/**
 * Metni panoya kopyala ve bildirimi göster
 */
function copyToClipboard(text, toast) {
    navigator.clipboard.writeText(text)
        .then(() => {
            // Toast göster
            toast.show();
        })
        .catch(err => {
            console.error('Panoya kopyalama başarısız:', err);
            alert('Panoya kopyalama başarısız: ' + err);
        });
}

/**
 * Akordeon kontrollerini ayarlar
 */
function setupAccordionControls() {
    const expandAllBtn = document.getElementById('expandAllBtn');
    const collapseAllBtn = document.getElementById('collapseAllBtn');
    
    if (expandAllBtn) {
        expandAllBtn.addEventListener('click', function() {
            const accordionItems = document.querySelectorAll('.accordion-collapse');
            accordionItems.forEach(item => {
                const bsCollapse = new bootstrap.Collapse(item, { toggle: false });
                bsCollapse.show();
            });
        });
    }
    
    if (collapseAllBtn) {
        collapseAllBtn.addEventListener('click', function() {
            const accordionItems = document.querySelectorAll('.accordion-collapse');
            accordionItems.forEach(item => {
                const bsCollapse = new bootstrap.Collapse(item, { toggle: false });
                bsCollapse.hide();
            });
        });
    }
}

/**
 * Modal işlemlerini ayarlar
 */
function setupModalActions(copyToast) {
    // JSON olarak dışa aktar - Modal içinden
    const modalExportJson = document.getElementById('modal-export-json');
    if (modalExportJson) {
        modalExportJson.addEventListener('click', function() {
            document.getElementById('export-json').click();
            const shareModal = bootstrap.Modal.getInstance(document.getElementById('shareModal'));
            shareModal.hide();
        });
    }
    
    // Metin olarak dışa aktar - Modal içinden
    const modalExportText = document.getElementById('modal-export-text');
    if (modalExportText) {
        modalExportText.addEventListener('click', function() {
            document.getElementById('export-text').click();
            const shareModal = bootstrap.Modal.getInstance(document.getElementById('shareModal'));
            shareModal.hide();
        });
    }
    
    // Yazdır - Modal içinden
    const modalExportPrint = document.getElementById('modal-export-print');
    if (modalExportPrint) {
        modalExportPrint.addEventListener('click', function() {
            window.print();
            const shareModal = bootstrap.Modal.getInstance(document.getElementById('shareModal'));
            shareModal.hide();
        });
    }
    
    // Bağlantıyı kopyala - Modal içinden
    const modalCopyLink = document.getElementById('modal-copy-link');
    if (modalCopyLink) {
        modalCopyLink.addEventListener('click', function() {
            const linkInput = document.getElementById('shareLink');
            copyToClipboard(linkInput.value, copyToast);
        });
    }
}

/**
 * Animasyon efektlerini ayarlar
 */
function setupAnimationEffects() {
    // Accordion öğeleri için hover efekti
    const accordionItems = document.querySelectorAll('.accordion-item');
    accordionItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Test kartları için hover efekti
    const testCards = document.querySelectorAll('.test-case-card');
    testCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
            this.style.transition = 'transform 0.3s ease';
            this.style.borderColor = 'rgba(18, 110, 130, 0.3)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.borderColor = 'rgba(255, 255, 255, 0.08)';
        });
    });
}

/**
 * Hızlı erişim özelliklerini ayarlar
 */
function setupQuickActions() {
    // Yazdırma butonu
    const printButton = document.getElementById('print-scenarios');
    if (printButton) {
        printButton.addEventListener('click', function() {
            window.print();
        });
    }
}

// Bağlantı kopyalaması için ana sayfa butonu
document.addEventListener('DOMContentLoaded', function() {
    const copyLinkBtn = document.getElementById('copy-link');
    if (copyLinkBtn) {
        copyLinkBtn.addEventListener('click', function() {
            const copyToast = new bootstrap.Toast(document.getElementById('copyToast'));
            copyToClipboard(window.location.href, copyToast);
        });
    }
});