/**
 * Doctest Test Senaryo Üreteci - Otomasyon JS Dosyası
 * Test otomasyonu kod üretim işlevlerini içerir
 */

/**
 * Sets up the test automation functionality
 */
function setupTestAutomation() {
    const automationScenarioSelect = document.getElementById('automationScenarioSelect');
    const automationFormatSelect = document.getElementById('automationFormatSelect');
    const automationResult = document.getElementById('automationResult');
    const automationCode = document.getElementById('automationCode');
    const generateBtn = document.getElementById('generateAutomationBtn');
    const copyBtn = document.getElementById('copyAutomationBtn');

    if (!automationScenarioSelect || !automationFormatSelect) return;

    // Load test scenarios data from the page
    const testScenariosData = getTestScenariosData();

    // Generate automation code
    if (generateBtn) {
        generateBtn.addEventListener('click', function () {
            const scenarioIndex = automationScenarioSelect.value;
            const format = automationFormatSelect.value;

            if (!scenarioIndex || !format) {
                // Show error
                const errorAlert = document.createElement('div');
                errorAlert.className = 'alert alert-warning mb-3';
                errorAlert.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Lütfen tüm seçenekleri doldurun.';
                const cardBody = generateBtn.closest('.card-body');
                if (cardBody) {
                    const existingAlerts = cardBody.querySelectorAll('.alert-warning');
                    existingAlerts.forEach(alert => alert.remove());
                    cardBody.prepend(errorAlert);
                }

                // Hide error after 3 seconds
                setTimeout(() => {
                    errorAlert.remove();
                }, 3000);

                return;
            }

            // Show loading message
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'alert alert-info mb-3';
            loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Otomasyon kodu oluşturuluyor...';
            const cardBody = generateBtn.closest('.card-body');
            if (cardBody) {
                const existingAlerts = cardBody.querySelectorAll('.alert');
                existingAlerts.forEach(alert => alert.remove());
                cardBody.prepend(loadingIndicator);
            }

            // Yapay zeka modeli kullanarak API üzerinden kod oluştur
            // Add fallback ID if testScenariosData.id doesn't exist
            const scenarioSetId = testScenariosData.id || 'latest';
            console.log('Using scenario set ID:', scenarioSetId, 'scenarioIndex:', scenarioIndex, 'format:', format);

            fetch('/api/generate_automation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    scenario_set_id: scenarioSetId,
                    scenario_index: scenarioIndex,
                    format: format
                })
            })
                .then(response => response.json())
                .then(data => {
                    // Remove loading indicator
                    loadingIndicator.remove();

                    if (data.success) {
                        // Display generated code
                        automationCode.textContent = data.code;
                        automationResult.classList.remove('d-none');

                        // Set language for syntax highlighting
                        automationCode.className = `language-${data.language}`;

                        // Highlight code if Prism.js is available
                        if (typeof Prism !== 'undefined') {
                            Prism.highlightElement(automationCode);
                        }

                        // Show success message
                        const successMsg = document.createElement('div');
                        successMsg.className = 'alert alert-success mb-3';
                        successMsg.innerHTML = '<i class="fas fa-check-circle me-2"></i>Kod başarıyla oluşturuldu!';
                        cardBody.prepend(successMsg);

                        // Hide success message after 3 seconds
                        setTimeout(() => {
                            successMsg.remove();
                        }, 3000);
                    } else {
                        // Show error message
                        const errorMsg = document.createElement('div');
                        errorMsg.className = 'alert alert-danger mb-3';
                        errorMsg.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Hata: ${data.error || 'Kod oluşturulamadı'}`;
                        cardBody.prepend(errorMsg);

                        // Hide error message after 5 seconds
                        setTimeout(() => {
                            errorMsg.remove();
                        }, 5000);
                    }
                })
                .catch(error => {
                    // Remove loading indicator
                    loadingIndicator.remove();

                    // Show error message
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'alert alert-danger mb-3';
                    errorMsg.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Sunucu hatası! Lütfen daha sonra tekrar deneyin.';
                    cardBody.prepend(errorMsg);

                    console.error('Otomasyon kodu üretim hatası:', error);

                    // Hide error message after 5 seconds
                    setTimeout(() => {
                        errorMsg.remove();
                    }, 5000);
                });
        });
    }

    // Copy automation code
    if (copyBtn) {
        copyBtn.addEventListener('click', function () {
            const code = automationCode.textContent;

            // Copy to clipboard
            navigator.clipboard.writeText(code).then(() => {
                // Show success message
                const successMsg = document.createElement('div');
                successMsg.className = 'copy-success-message';
                successMsg.innerHTML = '<i class="fas fa-check-circle me-1"></i>Kopyalandı!';
                this.appendChild(successMsg);

                // Hide success message after 2 seconds
                setTimeout(() => {
                    successMsg.remove();
                }, 2000);
            }).catch(err => {
                console.error('Kopyalama hatası:', err);

                // Alternatif kopyalama yöntemi
                const textarea = document.createElement('textarea');
                textarea.value = code;
                textarea.style.position = 'fixed';
                textarea.style.opacity = 0;
                document.body.appendChild(textarea);
                textarea.select();

                try {
                    document.execCommand('copy');
                    // Başarı mesajı göster
                    const successMsg = document.createElement('div');
                    successMsg.className = 'copy-success-message';
                    successMsg.innerHTML = '<i class="fas fa-check-circle me-1"></i>Kopyalandı!';
                    this.appendChild(successMsg);

                    setTimeout(() => {
                        successMsg.remove();
                    }, 2000);
                } catch (e) {
                    console.error('Alternatif kopyalama başarısız:', e);
                }

                document.body.removeChild(textarea);
            });
        });
    }
}

/**
 * Generates automation code for the given scenario and format
 * @param {Object} scenario - The scenario object
 * @param {Object} testCase - The test case object
 * @param {string} format - The automation format
 * @returns {string} - The generated code
 */
function generateAutomationCode(scenario, testCase, format) {
    const scenarioTitle = scenario.title || 'Adsız Senaryo';
    const testTitle = testCase.title || 'Adsız Test Vakası';
    const steps = testCase.steps || '';
    const expectedResults = testCase.expected_results || '';

    switch (format) {
        case 'selenium-java':
            return generateSeleniumJava(scenarioTitle, testTitle, steps, expectedResults);
        case 'selenium-python':
            return generateSeleniumPython(scenarioTitle, testTitle, steps, expectedResults);
        case 'cypress':
            return generateCypress(scenarioTitle, testTitle, steps, expectedResults);
        case 'playwright':
            return generatePlaywright(scenarioTitle, testTitle, steps, expectedResults);
        case 'appium':
            return generateAppium(scenarioTitle, testTitle, steps, expectedResults);
        case 'restassured':
            return generateRestAssured(scenarioTitle, testTitle, steps, expectedResults);
        case 'cucumber':
            return generateCucumber(scenarioTitle, testTitle, steps, expectedResults);
        default:
            return '// Format seçilmedi';
    }
}

/**
 * Gets the language for syntax highlighting based on the format
 * @param {string} format - The automation format
 * @returns {string} - The language for syntax highlighting
 */
function getLanguageFromFormat(format) {
    switch (format) {
        case 'selenium-java':
        case 'restassured':
            return 'java';
        case 'selenium-python':
        case 'playwright-python':
            return 'python';
        case 'cypress':
        case 'playwright':
            return 'javascript';
        case 'cucumber':
            return 'gherkin';
        default:
            return 'clike';
    }
}

/**
 * Generates Selenium Java code
 */
function generateSeleniumJava(scenarioTitle, testTitle, steps, expectedResults) {
    // Convert steps to code statements
    const parsedSteps = parseStepsToCode(steps, 'java');

    return `import org.junit.Test;
import org.junit.Before;
import org.junit.After;
import static org.junit.Assert.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;

/**
 * ${scenarioTitle}
 */
public class ${formatNameForClass(testTitle)}Test {
    private WebDriver driver;
    private WebDriverWait wait;
    
    @Before
    public void setUp() {
        // Driver kurulumu
        driver = new ChromeDriver();
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        driver.manage().window().maximize();
    }
    
    @Test
    public void ${formatNameForMethod(testTitle)}() {
        // Test senaryosu: ${scenarioTitle}
        // Test vakası: ${testTitle}
        
${parsedSteps}
        
        // Beklenen sonuçlar:
        // ${expectedResults.replace(/\n/g, '\n        // ')}
    }
    
    @After
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}`;
}

/**
 * Generates Selenium Python code
 */
function generateSeleniumPython(scenarioTitle, testTitle, steps, expectedResults) {
    // Convert steps to code statements
    const parsedSteps = parseStepsToCode(steps, 'python');

    return `import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ${formatNameForClass(testTitle)}Test(unittest.TestCase):
    """${scenarioTitle}"""
    
    def setUp(self):
        # Driver kurulumu
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
    
    def test_${formatNameForMethod(testTitle)}(self):
        """${testTitle}"""
        driver = self.driver
        wait = self.wait
        
${parsedSteps}
        
        # Beklenen sonuçlar:
        # ${expectedResults.replace(/\n/g, '\n        # ')}
    
    def tearDown(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    unittest.main()`;
}

/**
 * Generates Cypress code
 */
function generateCypress(scenarioTitle, testTitle, steps, expectedResults) {
    // Convert steps to code statements
    const parsedSteps = parseStepsToCode(steps, 'javascript');

    return `// ${scenarioTitle}
// ${testTitle}

describe('${scenarioTitle}', () => {
    beforeEach(() => {
        // Site ziyareti
        cy.visit('/')
    })
    
    it('${testTitle}', () => {
${parsedSteps}
        
        // Beklenen sonuçlar:
        // ${expectedResults.replace(/\n/g, '\n        // ')}
    })
})`;
}

/**
 * Generates Playwright code
 */
function generatePlaywright(scenarioTitle, testTitle, steps, expectedResults) {
    // Convert steps to code statements
    const parsedSteps = parseStepsToCode(steps, 'javascript');

    return `// ${scenarioTitle}
// ${testTitle}
const { test, expect } = require('@playwright/test');

test.describe('${scenarioTitle}', () => {
    test('${testTitle}', async ({ page }) => {
        // Test vakası: ${testTitle}
        
${parsedSteps}
        
        // Beklenen sonuçlar:
        // ${expectedResults.replace(/\n/g, '\n        // ')}
    });
});`;
}

/**
 * Generates Appium code
 */
function generateAppium(scenarioTitle, testTitle, steps, expectedResults) {
    // Convert steps to code statements
    const parsedSteps = parseStepsToCode(steps, 'java');

    return `import io.appium.java_client.AppiumDriver;
import io.appium.java_client.MobileElement;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.remote.MobileCapabilityType;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.openqa.selenium.By;
import org.openqa.selenium.remote.DesiredCapabilities;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.net.URL;
import java.time.Duration;

/**
 * ${scenarioTitle}
 */
public class ${formatNameForClass(testTitle)}Test {
    private AppiumDriver<MobileElement> driver;
    private WebDriverWait wait;
    
    @Before
    public void setUp() throws Exception {
        DesiredCapabilities capabilities = new DesiredCapabilities();
        capabilities.setCapability(MobileCapabilityType.PLATFORM_NAME, "Android");
        capabilities.setCapability(MobileCapabilityType.DEVICE_NAME, "Android Device");
        capabilities.setCapability(MobileCapabilityType.APP, "/path/to/your/app.apk");
        
        driver = new AndroidDriver<>(new URL("http://127.0.0.1:4723/wd/hub"), capabilities);
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }
    
    @Test
    public void ${formatNameForMethod(testTitle)}() {
        // Test senaryosu: ${scenarioTitle}
        // Test vakası: ${testTitle}
        
${parsedSteps}
        
        // Beklenen sonuçlar:
        // ${expectedResults.replace(/\n/g, '\n        // ')}
    }
    
    @After
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}`;
}

/**
 * Generates REST Assured code
 */
function generateRestAssured(scenarioTitle, testTitle, steps, expectedResults) {
    // Convert steps to code statements
    const parsedSteps = parseStepsToCode(steps, 'java');

    return `import org.junit.Test;
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;
import io.restassured.response.Response;
import org.junit.Before;

/**
 * ${scenarioTitle}
 */
public class ${formatNameForClass(testTitle)}Test {
    
    @Before
    public void setUp() {
        // API temel URL'si
        baseURI = "https://api.example.com";
    }
    
    @Test
    public void ${formatNameForMethod(testTitle)}() {
        // Test senaryosu: ${scenarioTitle}
        // Test vakası: ${testTitle}
        
${parsedSteps}
        
        // Beklenen sonuçlar:
        // ${expectedResults.replace(/\n/g, '\n        // ')}
    }
}`;
}

/**
 * Generates Cucumber Gherkin code
 */
function generateCucumber(scenarioTitle, testTitle, steps, expectedResults) {
    // Parse steps to Given/When/Then format
    const stepsArray = steps.split('\n').filter(step => step.trim() !== '');
    let gherkinSteps = '';

    if (stepsArray.length > 0) {
        gherkinSteps += '  Given ' + stepsArray[0] + '\n';

        for (let i = 1; i < stepsArray.length; i++) {
            if (i === stepsArray.length - 1) {
                gherkinSteps += '  Then ' + stepsArray[i] + '\n';
            } else {
                gherkinSteps += '  When ' + stepsArray[i] + '\n';
            }
        }
    }

    // Add expected results
    const resultsArray = expectedResults.split('\n').filter(result => result.trim() !== '');
    resultsArray.forEach(result => {
        gherkinSteps += '  And ' + result + '\n';
    });

    return `# ${scenarioTitle}
Feature: ${scenarioTitle}

Scenario: ${testTitle}
${gherkinSteps}`;
}

/**
 * Formats a name to be used as a class name
 * @param {string} name - The original name
 * @returns {string} - The formatted class name
 */
function formatNameForClass(name) {
    return name
        .replace(/[^a-zA-Z0-9]/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('');
}

/**
 * Formats a name to be used as a method name
 * @param {string} name - The original name
 * @returns {string} - The formatted method name
 */
function formatNameForMethod(name) {
    const className = formatNameForClass(name);
    return className.charAt(0).toLowerCase() + className.slice(1);
}

/**
 * Parses natural language steps to code statements
 * @param {string} steps - The natural language steps
 * @param {string} language - The programming language (java, python, javascript)
 * @returns {string} - The parsed code statements
 */
function parseStepsToCode(steps, language) {
    const stepsArray = steps.split('\n').filter(step => step.trim() !== '');
    let code = '';

    // Basic parsing based on common patterns
    stepsArray.forEach(step => {
        const trimmedStep = step.trim();

        // Add step as comment
        if (language === 'python') {
            code += `        # ${trimmedStep}\n`;
        } else {
            code += `        // ${trimmedStep}\n`;
        }

        // Simple heuristic-based code generation
        if (/^(açıl|aç|git|ziyaret|başlat)/i.test(trimmedStep)) {
            // Navigation actions
            if (language === 'java') {
                code += '        driver.get("https://example.com");\n\n';
            } else if (language === 'python') {
                code += '        driver.get("https://example.com")\n\n';
            } else if (language === 'javascript') {
                code += '        cy.visit("https://example.com")\n\n';
            }
        } else if (/^(tıkla|bas|seç)/i.test(trimmedStep)) {
            // Click actions
            if (language === 'java') {
                code += '        WebElement element = wait.until(ExpectedConditions.elementToBeClickable(By.id("element-id")));\n';
                code += '        element.click();\n\n';
            } else if (language === 'python') {
                code += '        element = wait.until(EC.element_to_be_clickable((By.ID, "element-id")))\n';
                code += '        element.click()\n\n';
            } else if (language === 'javascript') {
                code += '        cy.get("#element-id").click()\n\n';
            }
        } else if (/^(yaz|gir|doldur)/i.test(trimmedStep)) {
            // Input actions
            if (language === 'java') {
                code += '        WebElement inputField = wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("input-field")));\n';
                code += '        inputField.sendKeys("örnek metin");\n\n';
            } else if (language === 'python') {
                code += '        input_field = wait.until(EC.visibility_of_element_located((By.ID, "input-field")))\n';
                code += '        input_field.send_keys("örnek metin")\n\n';
            } else if (language === 'javascript') {
                code += '        cy.get("#input-field").type("örnek metin")\n\n';
            }
        } else if (/^(bekle|dur)/i.test(trimmedStep)) {
            // Wait actions
            if (language === 'java') {
                code += '        Thread.sleep(1000); // 1 saniye bekle\n\n';
            } else if (language === 'python') {
                code += '        import time\n';
                code += '        time.sleep(1) # 1 saniye bekle\n\n';
            } else if (language === 'javascript') {
                code += '        cy.wait(1000) // 1 saniye bekle\n\n';
            }
        } else if (/^(kontrol|doğrula|eşleş)/i.test(trimmedStep)) {
            // Assertion actions
            if (language === 'java') {
                code += '        WebElement resultElement = wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("result")));\n';
                code += '        assertEquals("Beklenen Sonuç", resultElement.getText());\n\n';
            } else if (language === 'python') {
                code += '        result_element = wait.until(EC.visibility_of_element_located((By.ID, "result")))\n';
                code += '        self.assertEqual("Beklenen Sonuç", result_element.text)\n\n';
            } else if (language === 'javascript') {
                code += '        cy.get("#result").should("have.text", "Beklenen Sonuç")\n\n';
            }
        } else {
            // Generic action
            if (language === 'java') {
                code += '        // İlgili kodu buraya ekleyin\n\n';
            } else if (language === 'python') {
                code += '        # İlgili kodu buraya ekleyin\n\n';
            } else if (language === 'javascript') {
                code += '        // İlgili kodu buraya ekleyin\n\n';
            }
        }
    });

    return code;
}