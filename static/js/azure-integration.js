/**
 * Azure OpenAI integration for Document Test Scenario Generator
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Azure model selection
    setupAzureModelSelection();
});

/**
 * Sets up Azure model selection functionality
 */
function setupAzureModelSelection() {
    const azureOption = document.getElementById('azure');
    const azureModelSection = document.getElementById('azureModelSection');
    
    if (azureOption && azureModelSection) {
        // Check initial state
        if (azureOption.checked) {
            azureModelSection.classList.remove('d-none');
        }
        
        // Add change event for Azure option
        azureOption.addEventListener('change', function() {
            if (this.checked) {
                azureModelSection.classList.remove('d-none');
            } else {
                azureModelSection.classList.add('d-none');
            }
        });
        
        // Hide Azure model section when any other AI model is selected
        const otherAIOptions = document.querySelectorAll('input[name="ai_model"]:not(#azure)');
        otherAIOptions.forEach(option => {
            option.addEventListener('change', function() {
                if (this.checked) {
                    azureModelSection.classList.add('d-none');
                }
            });
        });
    }
}
