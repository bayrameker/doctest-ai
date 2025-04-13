"""
Analytics functions for test scenarios.
"""
import json
from collections import Counter, defaultdict

def categorize_scenarios(scenarios):
    """
    Analyze and categorize test scenarios.
    
    Args:
        scenarios (list): List of scenario dictionaries
        
    Returns:
        dict: Category distribution data
    """
    categories = Counter()
    
    for scenario in scenarios:
        # Get category - use a default if not present
        category = scenario.get('category', 'Functional')
        categories[category] += 1
    
    # Convert to a format suitable for charts
    result = {
        'labels': list(categories.keys()),
        'data': list(categories.values())
    }
    
    return result

def analyze_complexity(scenarios):
    """
    Analyze the complexity distribution of scenarios.
    
    Args:
        scenarios (list): List of scenario dictionaries
        
    Returns:
        dict: Complexity distribution data
    """
    # Initialize complexity counters
    complexity = {
        'Simple': 0,
        'Medium': 0,
        'Complex': 0
    }
    
    for scenario in scenarios:
        test_cases = scenario.get('test_cases', [])
        num_test_cases = len(test_cases)
        
        # Determine complexity based on number of test cases
        if num_test_cases <= 2:
            complexity['Simple'] += 1
        elif num_test_cases <= 5:
            complexity['Medium'] += 1
        else:
            complexity['Complex'] += 1
    
    # Convert to a format suitable for charts
    result = {
        'labels': list(complexity.keys()),
        'data': list(complexity.values())
    }
    
    return result

def calculate_coverage_score(scenarios):
    """
    Calculate an estimated coverage score based on test cases.
    
    Args:
        scenarios (list): List of scenario dictionaries
        
    Returns:
        float: Coverage score (0-100%)
    """
    if not scenarios:
        return 0.0
        
    # Count types of test cases
    test_types = defaultdict(int)
    total_test_cases = 0
    
    for scenario in scenarios:
        test_cases = scenario.get('test_cases', [])
        for test_case in test_cases:
            test_type = test_case.get('type', 'normal')
            test_types[test_type] += 1
            total_test_cases += 1
    
    # Calculate coverage - give bonuses for edge, error and conditional test cases
    base_coverage = min(100, total_test_cases * 5)  # Base coverage
    
    error_bonus = min(15, test_types.get('error', 0) * 3)
    edge_bonus = min(10, test_types.get('edge', 0) * 2)
    conditional_bonus = min(5, test_types.get('conditional', 0))
    
    coverage = min(100, base_coverage + error_bonus + edge_bonus + conditional_bonus)
    
    return float(coverage)

def generate_scenario_analytics(scenarios_data):
    """
    Generate comprehensive analytics for test scenarios.
    
    Args:
        scenarios_data (dict): Full scenarios data returned by AI
        
    Returns:
        dict: Analytics data for the scenarios
    """
    scenarios = scenarios_data.get('scenarios', [])
    
    # Calculate number of test cases
    total_test_cases = sum(len(scenario.get('test_cases', [])) for scenario in scenarios)
    
    analytics = {
        'total_scenarios': len(scenarios),
        'total_test_cases': total_test_cases,
        'category_distribution': categorize_scenarios(scenarios),
        'complexity_distribution': analyze_complexity(scenarios),
        'coverage_score': calculate_coverage_score(scenarios)
    }
    
    return analytics