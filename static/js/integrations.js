/**
 * Test Otomasyonu Entegrasyonları - Doctest Test Scenario Generator
 * 
 * Bu dosya popüler test otomasyon araçları için entegrasyon seçenekleri sunar
 * Dokunmadan genel test araçlarına erişim sağlar
 */

document.addEventListener('DOMContentLoaded', function () {
    // Modal element referanslarını al
    const integrationModals = {
        selenium: document.getElementById('seleniumModal'),
        cypress: document.getElementById('cypressModal'),
        playwright: document.getElementById('playwrightModal'),
        appium: document.getElementById('appiumModal'),
        cucumber: document.getElementById('cucumberModal'),
        all: document.getElementById('allIntegrationsModal')
    };

    // Modal nesnelerini sakla
    const modalInstances = {};

    // Tüm modalları başlat ve konsolda bildir
    Object.keys(integrationModals).forEach(key => {
        if (integrationModals[key]) {
            try {
                modalInstances[key] = new bootstrap.Modal(integrationModals[key]);
                console.log('Modal initialized:', integrationModals[key].id);
            } catch (e) {
                console.error('Error initializing modal:', integrationModals[key].id, e);
            }
        } else {
            console.warn('Modal not pre-initialized:', '#' + key + 'Modal');
        }
    });

    // Entegrasyon düğmelerine tıklama olayları ekle
    document.querySelectorAll('.integration-btn').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const target = this.getAttribute('data-target');

            if (modalInstances[target]) {
                try {
                    modalInstances[target].show();
                    console.log('Custom modal açıldı:', '#' + target + 'Modal');
                } catch (error) {
                    console.error('Error showing modal:', error);
                }
            } else {
                // Eğer modal başlatılmadıysa, manuel olarak göster
                const modalElement = document.querySelector('#' + target + 'Modal');
                if (modalElement) {
                    try {
                        const modalObj = new bootstrap.Modal(modalElement);
                        modalObj.show();
                        console.log('Manual modal shown:', '#' + target + 'Modal');
                    } catch (error) {
                        console.error('Manual modal error:', error);
                    }
                } else {
                    console.error('Modal not found:', '#' + target + 'Modal');
                }
            }
        });
    });

    // Senaryo dönüştürme fonksiyonları
    window.convertToSelenium = function (scenarioData) {
        // Selenium formatında Python kodu oluştur
        const code = generateSeleniumCode(scenarioData);
        document.getElementById('seleniumCodeOutput').textContent = code;
    };

    window.convertToCypress = function (scenarioData) {
        // Cypress formatında JavaScript kodu oluştur
        const code = generateCypressCode(scenarioData);
        document.getElementById('cypressCodeOutput').textContent = code;
    };

    window.convertToPlaywright = function (scenarioData) {
        // Playwright formatında JavaScript kodu oluştur
        const code = generatePlaywrightCode(scenarioData);
        document.getElementById('playwrightCodeOutput').textContent = code;
    };

    // Varsayılan kod örnekleri (veri transfer edilebilir)
    function generateSeleniumCode(data) {
        return `from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import unittest

class TestScenario(unittest.TestCase):
    
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.driver.get("https://example.com")
    
    def test_scenario_1(self):
        """${data?.scenarios?.[0]?.description || 'Test senaryosu açıklaması buraya gelecek'}"""
        # Login işlemi
        username_field = self.driver.find_element(By.ID, "username")
        password_field = self.driver.find_element(By.ID, "password")
        
        username_field.send_keys("testuser")
        password_field.send_keys("password123")
        
        login_button = self.driver.find_element(By.ID, "login-button")
        login_button.click()
        
        # Başarılı giriş kontrolü
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "welcome-message"))
        )
        
        # Test senaryosunun gerçekleştirilmesi
        # ...test adımları burada olacak...
    
    def tearDown(self):
        self.driver.quit()

if __name__ == "__main__":
    unittest.main()`;
    }

    function generateCypressCode(data) {
        return `// ${data?.scenarios?.[0]?.description || 'Test senaryosu açıklaması buraya gelecek'}
describe('Test Scenario', () => {
  beforeEach(() => {
    cy.visit('https://example.com')
    
    // Login işlemi
    cy.get('#username').type('testuser')
    cy.get('#password').type('password123')
    cy.get('#login-button').click()
    
    // Başarılı giriş kontrolü
    cy.get('.welcome-message').should('be.visible')
  })
  
  it('should perform the test scenario successfully', () => {
    // Test senaryosunun gerçekleştirilmesi
    // ...test adımları burada olacak...
    
    // Örnek adımlar
    cy.get('.menu-item').first().click()
    cy.get('.product-list').should('have.length.gt', 0)
    
    // Form işlemleri
    cy.get('input[name="search"]').type('test product')
    cy.get('button[type="submit"]').click()
    
    // Sonuç kontrolü
    cy.get('.results').should('contain', 'test product')
  })
})`;
    }

    function generatePlaywrightCode(data) {
        return `const { test, expect } = require('@playwright/test');

// ${data?.scenarios?.[0]?.description || 'Test senaryosu açıklaması buraya gelecek'}
test('test scenario execution', async ({ page }) => {
  await page.goto('https://example.com');
  
  // Login işlemi
  await page.fill('#username', 'testuser');
  await page.fill('#password', 'password123');
  await page.click('#login-button');
  
  // Başarılı giriş kontrolü
  await expect(page.locator('.welcome-message')).toBeVisible();
  
  // Test senaryosunun gerçekleştirilmesi
  // ...test adımları burada olacak...
  
  // Örnek adımlar
  await page.click('.menu-item:first-child');
  const productCount = await page.locator('.product-list').count();
  expect(productCount).toBeGreaterThan(0);
  
  // Form işlemleri
  await page.fill('input[name="search"]', 'test product');
  await page.click('button[type="submit"]');
  
  // Sonuç kontrolü
  await expect(page.locator('.results')).toContainText('test product');
});`;
    }
});