/**
 * Analitik Sayfası JavaScript
 * 
 * Bu dosya, analitik sayfasındaki interaktif özellikleri yönetir:
 * - Grafik oluşturma ve güncelleme
 * - Filtreleme işlevleri
 * - Özel sorgu işlemleri
 * - Animasyonlar ve geçişler
 */

// Sayfa yüklendiğinde çalışacak ana fonksiyon
document.addEventListener('DOMContentLoaded', function() {
    // Grafikleri başlat
    initCharts();
    
    // Filtreleme işlevlerini ayarla
    setupFilters();
    
    // Sorgu editörünü hazırla
    setupQueryEditor();
    
    // Animasyon efektlerini ekle
    setupAnimationEffects();
    
    // Ek istatistik kartlarını ayarla
    setupStatCards();
});

/**
 * Grafikleri başlatır
 */
function initCharts() {
    // Kategori dağılımı grafiği
    if (document.getElementById('categoryChart')) {
        createCategoryChart();
    }
    
    // Karmaşıklık grafiği
    if (document.getElementById('complexityChart')) {
        createComplexityChart();
    }
    
    // Kapsama grafiği
    if (document.getElementById('coverageChart')) {
        createCoverageChart();
    }
    
    // Zaman içinde senaryo sayısı grafiği
    if (document.getElementById('scenariosTimeChart')) {
        createScenariosTimeChart();
    }
}

/**
 * Kategori dağılımı için pasta grafiği oluşturur
 */
function createCategoryChart() {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    // Eğer veri varsa grafiği oluştur
    if (window.analyticsData && window.analyticsData.categoryDistribution) {
        const data = window.analyticsData.categoryDistribution;
        const labels = Object.keys(data);
        const values = Object.values(data);
        
        // Özel renkler
        const colors = [
            'rgba(18, 110, 130, 0.7)',
            'rgba(242, 183, 5, 0.7)',
            'rgba(255, 62, 95, 0.7)',
            'rgba(10, 35, 66, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)'
        ];
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 12
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18, 21, 30, 0.9)',
                        titleColor: 'rgba(255, 255, 255, 0.9)',
                        bodyColor: 'rgba(255, 255, 255, 0.8)',
                        borderColor: 'rgba(18, 110, 130, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        font: {
                            family: 'Inter, sans-serif'
                        }
                    }
                },
                cutout: '65%',
                animation: {
                    animateScale: true,
                    animateRotate: true
                }
            }
        });
    } else {
        // Veri yoksa boş bir mesaj göster
        ctx.canvas.style.display = 'none';
        const noDataMsg = document.createElement('div');
        noDataMsg.className = 'text-center text-muted py-4';
        noDataMsg.innerHTML = '<i class="fas fa-chart-pie me-2"></i> Bu grafik için veri bulunmuyor.';
        ctx.canvas.parentNode.appendChild(noDataMsg);
    }
}

/**
 * Karmaşıklık dağılımı için çubuk grafiği oluşturur
 */
function createComplexityChart() {
    const ctx = document.getElementById('complexityChart').getContext('2d');
    
    // Eğer veri varsa grafiği oluştur
    if (window.analyticsData && window.analyticsData.complexityDistribution) {
        const data = window.analyticsData.complexityDistribution;
        const labels = Object.keys(data);
        const values = Object.values(data);
        
        // Özel renkler
        const colors = {
            'Basit': 'rgba(75, 192, 192, 0.7)',
            'Orta': 'rgba(242, 183, 5, 0.7)',
            'Karmaşık': 'rgba(255, 62, 95, 0.7)'
        };
        
        const bgColors = labels.map(label => colors[label] || 'rgba(18, 110, 130, 0.7)');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Senaryo Sayısı',
                    data: values,
                    backgroundColor: bgColors,
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18, 21, 30, 0.9)',
                        titleColor: 'rgba(255, 255, 255, 0.9)',
                        bodyColor: 'rgba(255, 255, 255, 0.8)',
                        borderColor: 'rgba(18, 110, 130, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                return `Senaryo: ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false,
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.7)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.7)',
                            precision: 0
                        }
                    }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                }
            }
        });
    } else {
        // Veri yoksa boş bir mesaj göster
        ctx.canvas.style.display = 'none';
        const noDataMsg = document.createElement('div');
        noDataMsg.className = 'text-center text-muted py-4';
        noDataMsg.innerHTML = '<i class="fas fa-chart-bar me-2"></i> Bu grafik için veri bulunmuyor.';
        ctx.canvas.parentNode.appendChild(noDataMsg);
    }
}

/**
 * Kapsama skoru için gösterge grafiği oluşturur (basitleştirilmiş versiyon)
 */
function createCoverageChart() {
    const ctx = document.getElementById('coverageChart').getContext('2d');
    
    // Eğer veri varsa grafiği oluştur
    if (window.analyticsData && window.analyticsData.coverageScore !== undefined) {
        const coverageScore = window.analyticsData.coverageScore;
        
        // Gauge yerine doughnut tipi kullanıyoruz (daha yaygın destekleniyor)
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [coverageScore, 100 - coverageScore],
                    backgroundColor: [
                        getGradientColor(ctx, coverageScore),
                        'rgba(40, 40, 40, 0.2)'
                    ],
                    borderWidth: 0,
                    cutout: '80%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                circumference: 180,
                rotation: 270,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            },
            plugins: [{
                id: 'coverageText',
                afterDraw: (chart) => {
                    const width = chart.width;
                    const height = chart.height;
                    const ctx = chart.ctx;
                    
                    ctx.restore();
                    ctx.font = 'bold 24px Inter, sans-serif';
                    ctx.textBaseline = 'middle';
                    ctx.textAlign = 'center';
                    ctx.fillStyle = '#ffffff';
                    
                    const text = `${coverageScore.toFixed(1)}%`;
                    const textX = width / 2;
                    const textY = height - (height / 3);
                    
                    ctx.fillText(text, textX, textY);
                    
                    // Alt mesaj
                    ctx.font = '14px Inter, sans-serif';
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
                    ctx.fillText('Test Kapsamı', textX, textY + 30);
                    
                    ctx.save();
                }
            }]
        });
    } else {
        // Veri yoksa boş bir mesaj göster
        ctx.canvas.style.display = 'none';
        const noDataMsg = document.createElement('div');
        noDataMsg.className = 'text-center text-muted py-4';
        noDataMsg.innerHTML = '<i class="fas fa-tachometer-alt me-2"></i> Kapsama skoru verileri bulunmuyor.';
        ctx.canvas.parentNode.appendChild(noDataMsg);
    }
}

/**
 * Skor bazlı gradient renk oluşturur
 */
function getGradientColor(ctx, score) {
    let gradient;
    
    if (score < 40) {
        // Düşük skor - kırmızı/turuncu
        gradient = ctx.createLinearGradient(0, 0, 200, 0);
        gradient.addColorStop(0, 'rgba(255, 62, 95, 0.8)');
        gradient.addColorStop(1, 'rgba(255, 159, 64, 0.8)');
    } else if (score < 70) {
        // Orta skor - turuncu/sarı
        gradient = ctx.createLinearGradient(0, 0, 200, 0);
        gradient.addColorStop(0, 'rgba(255, 159, 64, 0.8)');
        gradient.addColorStop(1, 'rgba(242, 183, 5, 0.8)');
    } else {
        // Yüksek skor - sarı/yeşil
        gradient = ctx.createLinearGradient(0, 0, 200, 0);
        gradient.addColorStop(0, 'rgba(242, 183, 5, 0.8)');
        gradient.addColorStop(1, 'rgba(75, 192, 140, 0.8)');
    }
    
    return gradient;
}

/**
 * Zaman içinde senaryo sayısını gösteren çizgi grafiği oluşturur
 */
function createScenariosTimeChart() {
    const ctx = document.getElementById('scenariosTimeChart').getContext('2d');
    
    // Eğer veri varsa grafiği oluştur
    if (window.analyticsData && window.analyticsData.timeData) {
        const timeData = window.analyticsData.timeData;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeData.labels,
                datasets: [{
                    label: 'Oluşturulan Senaryolar',
                    data: timeData.scenarios,
                    backgroundColor: 'rgba(18, 110, 130, 0.2)',
                    borderColor: 'rgba(18, 110, 130, 0.8)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointBackgroundColor: 'rgba(242, 183, 5, 0.8)',
                    pointBorderColor: 'rgba(255, 255, 255, 0.8)',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }, {
                    label: 'Test Durumları',
                    data: timeData.testCases,
                    backgroundColor: 'rgba(255, 62, 95, 0.1)',
                    borderColor: 'rgba(255, 62, 95, 0.7)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointBackgroundColor: 'rgba(255, 62, 95, 0.8)',
                    pointBorderColor: 'rgba(255, 255, 255, 0.8)',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 12
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(18, 21, 30, 0.9)',
                        titleColor: 'rgba(255, 255, 255, 0.9)',
                        bodyColor: 'rgba(255, 255, 255, 0.8)',
                        borderColor: 'rgba(18, 110, 130, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.7)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.7)',
                            precision: 0
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    } else {
        // Veri yoksa boş bir mesaj göster
        ctx.canvas.style.display = 'none';
        const noDataMsg = document.createElement('div');
        noDataMsg.className = 'text-center text-muted py-4';
        noDataMsg.innerHTML = '<i class="fas fa-chart-line me-2"></i> Zaman serisi verileri bulunmuyor.';
        ctx.canvas.parentNode.appendChild(noDataMsg);
    }
}

/**
 * Filtreleme işlevlerini ayarlar
 */
function setupFilters() {
    // Kategori filtresi
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', updateFilters);
    }
    
    // Öncelik filtresi
    const priorityFilter = document.getElementById('priorityFilter');
    if (priorityFilter) {
        priorityFilter.addEventListener('change', updateFilters);
    }
    
    // Tarih aralığı filtresi
    const dateRangeFilter = document.getElementById('dateRangeFilter');
    if (dateRangeFilter) {
        dateRangeFilter.addEventListener('change', updateFilters);
    }
    
    // Filtre uygulandığında tüm tabloları güncelle
    function updateFilters() {
        // Filtre değerlerini al
        const category = categoryFilter ? categoryFilter.value : '';
        const priority = priorityFilter ? priorityFilter.value : '';
        const dateRange = dateRangeFilter ? dateRangeFilter.value : '';
        
        console.log("Filtreler: ", "Kategori:", category, "Öncelik:", priority, "Tarih Aralığı:", dateRange);
        
        // AJAX ile filtrelenmiş verileri getir
        // Bu bölüm şu an için pasif, burada sadece konsola filtre değerlerini yazdırıyoruz
        // Gerçek implementasyonda sunucuya istek gönderilerek filtrelenmiş veriler alınacaktır
        
        // Filtre durumunu göster
        updateFilterStatus(category, priority, dateRange);
    }
    
    // Filtre durumunu gösterir
    function updateFilterStatus(category, priority, dateRange) {
        const filterStatus = document.getElementById('filterStatus');
        if (filterStatus) {
            let filterText = '';
            
            if (category) filterText += '<span class="badge bg-info me-2">Kategori: ' + category + '</span>';
            if (priority) filterText += '<span class="badge bg-warning me-2">Öncelik: ' + priority + '</span>';
            if (dateRange) filterText += '<span class="badge bg-secondary me-2">Tarih: ' + dateRange + '</span>';
            
            if (filterText) {
                filterStatus.innerHTML = '<div class="mt-2">Aktif Filtreler: ' + filterText + '</div>';
                filterStatus.style.display = 'block';
            } else {
                filterStatus.style.display = 'none';
            }
        }
    }
}

/**
 * SQL sorgu editörünü hazırlar
 */
function setupQueryEditor() {
    const queryForm = document.getElementById('queryForm');
    const queryEditor = document.getElementById('queryEditor');
    
    if (queryForm && queryEditor) {
        // Editör yüksekliğini otomatik ayarla
        queryEditor.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Form gönderildiğinde
        queryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const queryText = queryEditor.value.trim();
            if (!queryText) {
                alert('Lütfen bir SQL sorgusu girin.');
                return;
            }
            
            // Sorguyu çalıştır (normalde AJAX ile yapılır)
            console.log('SQL Sorgusu çalıştırılıyor:', queryText);
            
            // Sorgu sonuçlarını göster
            const resultContainer = document.getElementById('queryResultContainer');
            
            // Yükleniyor animasyonu
            resultContainer.innerHTML = 
                '<div class="text-center py-4">' +
                    '<div class="spinner-border text-primary" role="status">' +
                        '<span class="visually-hidden">Yükleniyor...</span>' +
                    '</div>' +
                    '<p class="mt-2 text-muted">Sorgu çalıştırılıyor...</p>' +
                '</div>';
            
            // Normalde burada AJAX ile sorgu sonuçları alınır ve gösterilir
            // Bu örnek için sadece birkaç saniye bekletiyoruz
            setTimeout(function() {
                resultContainer.innerHTML = 
                    '<div class="query-result-title">' +
                        '<i class="fas fa-table"></i>' +
                        'Sorgu Sonuçları' +
                    '</div>' +
                    '<div class="alert analytics-alert analytics-alert-info">' +
                        '<div class="d-flex">' +
                            '<div class="alert-icon">' +
                                '<i class="fas fa-info-circle"></i>' +
                            '</div>' +
                            '<div class="ms-3">' +
                                '<h6 class="alert-heading">Demo Modu</h6>' +
                                '<p class="mb-0">Bu demo sürümünde gerçek sorgu çalıştırılmıyor. Gerçek bir uygulamada, bu bölüm veritabanından gelen sonuçları gösterecektir.</p>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
            }, 1500);
        });
    }
}

/**
 * İstatistik kartlarını ayarlar
 */
function setupStatCards() {
    // İstatistik kartlarında sayı animasyonu için
    const statValues = document.querySelectorAll('.stat-value');
    
    statValues.forEach(statValue => {
        const finalValue = parseInt(statValue.textContent.replace(/\D/g, ''), 10);
        
        if (!isNaN(finalValue) && finalValue > 0) {
            let startValue = 0;
            const duration = 1500;
            const frameDuration = 1000 / 60; // 60fps
            const totalFrames = Math.round(duration / frameDuration);
            let frame = 0;
            
            function animate() {
                frame++;
                const progress = frame / totalFrames;
                const currentValue = Math.floor(progress * finalValue);
                
                statValue.textContent = currentValue;
                
                if (frame < totalFrames) {
                    requestAnimationFrame(animate);
                } else {
                    statValue.textContent = finalValue;
                }
            }
            
            animate();
        }
    });
}

/**
 * Animasyon efektlerini ayarlar
 */
function setupAnimationEffects() {
    // Bölümler için animasyon ekle
    animateElements('.analytics-card', 'fadeInUp', 0.1);
    animateElements('.stat-box', 'fadeInUp', 0.05);
    
    // Analitik kutularına hover efekti
    const analyticCards = document.querySelectorAll('.analytics-card');
    analyticCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.25)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.2)';
        });
    });
    
    // Stat kutularına hover efekti
    const statBoxes = document.querySelectorAll('.stat-box');
    statBoxes.forEach(box => {
        box.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
            this.style.borderColor = 'rgba(18, 110, 130, 0.5)';
        });
        
        box.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.borderColor = 'rgba(255, 255, 255, 0.08)';
        });
    });
}

/**
 * Belirli bir seçiciye sahip tüm öğelere animasyon ekler
 */
function animateElements(selector, animationClass, delay) {
    const elements = document.querySelectorAll(selector);
    elements.forEach((element, index) => {
        element.classList.add(animationClass);
        element.style.animationDelay = (index * delay) + 's';
    });
}