import os
import json
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_with_deepseek(document_text):
    """
    Generate test scenarios using DeepSeek API
    
    Args:
        document_text (str): Text extracted from the document
        
    Returns:
        dict: Structured test scenarios and use cases
    """
    # Get API key from environment
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DeepSeek API key not found. Please set the DEEPSEEK_API_KEY environment variable.")
    
    # Get API endpoint from environment with default fallback
    api_endpoint = os.environ.get("DEEPSEEK_API_ENDPOINT", "https://api.deepseek.com/v1/chat/completions")
    
    # Get model name from environment with default fallback
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    
    try:
        # Prepare the prompt for DeepSeek
        system_prompt = """
        You are a test scenario and use case generation expert. Analyze the provided document and 
        generate comprehensive test scenarios and use cases. Follow these guidelines:
        
        1. Identify key functionality described in the document
        2. Create test scenarios that cover both happy path and edge cases
        3. For each scenario, provide multiple test cases with clear steps and expected results
        4. Ensure your output follows this JSON structure:
        {
            "summary": "Brief overview of the document and identified scenarios",
            "scenarios": [
                {
                    "title": "Scenario name",
                    "description": "Detailed description of the scenario",
                    "test_cases": [
                        {
                            "title": "Test case title",
                            "steps": "Numbered steps to execute the test",
                            "expected_results": "Expected outcomes of the test"
                        }
                    ]
                }
            ]
        }
        
        Be thorough, detailed, and ensure your response is in valid JSON format.
        """
        
        user_message = f"Generate test scenarios and use cases from the following document:\n\n{document_text}"
        
        # Make API call
        logger.info(f"Sending request to DeepSeek API using model: {model}...")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(api_endpoint, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Extract the generated text
        if 'choices' in result and len(result['choices']) > 0 and 'message' in result['choices'][0]:
            message = result['choices'][0]['message']
            if 'content' in message:
                generated_text = message['content']
            else:
                logger.error("No content found in DeepSeek API response message")
                raise Exception("No content found in DeepSeek API response")
        else:
            logger.error(f"Unexpected DeepSeek API response format: {result}")
            raise Exception("Unexpected DeepSeek API response format")
        
        # Parse the JSON from the generated text
        try:
            # First, try to parse it directly
            json_result = json.loads(generated_text)
            logger.info("Successfully parsed DeepSeek response as JSON")
            return json_result
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract the JSON part
            logger.warning("Failed to parse DeepSeek response directly as JSON. Attempting to extract JSON part...")
            
            # Try to find JSON within the text (between curly braces)
            import re
            json_match = re.search(r'({[\s\S]*})', generated_text)
            
            if json_match:
                try:
                    json_part = json_match.group(1)
                    json_result = json.loads(json_part)
                    logger.info("Successfully extracted and parsed JSON from DeepSeek response")
                    return json_result
                except json.JSONDecodeError:
                    logger.error("Failed to parse extracted JSON from DeepSeek response")
            
            # If we can't extract valid JSON, format it using the helper function
            from utils.ai_service import format_test_scenarios
            return format_test_scenarios(generated_text)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to DeepSeek API: {str(e)}")
        raise Exception(f"Failed to connect to DeepSeek API: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating test scenarios with DeepSeek: {str(e)}")
        raise Exception(f"Failed to generate test scenarios with DeepSeek: {str(e)}")
