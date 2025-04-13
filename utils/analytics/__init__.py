"""
Analytics module for the test scenario application.
"""

from utils.analytics.coverage_analyzer import analyze_scenarios

# Generate scenario analytics using enhanced algorithms
def generate_scenario_analytics(scenario_data, document_length=0):
    """
    Generates analytics for the given scenario data
    
    Args:
        scenario_data: The scenario data to analyze
        document_length: The length of the document that generated the scenarios
        
    Returns:
        dict: Analytics data including category and complexity distributions
    """
    return analyze_scenarios(scenario_data, doc_content_length=document_length)