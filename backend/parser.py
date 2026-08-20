import json
import os
from groq import Groq

# Initialize Groq client
# It will automatically pick up GROQ_API_KEY from the environment
client = Groq()

def parse_request(raw_text: str, domain: str) -> dict:
    """
    Uses Groq to parse the raw text into a structured JSON 
    matching the domain schema.
    """
    current_dir = os.path.dirname(__file__)
    schema_path = os.path.join(current_dir, "schemas", f"{domain}.json")
    if not os.path.exists(schema_path):
        return {"needs_human_clarification": True, "raw": raw_text, "error": f"Unknown domain schema: {domain}"}
    
    with open(schema_path, "r") as f:
        schema = json.load(f)

    # Use Groq to extract JSON matching the schema
    prompt = f"""
    You are an AI assistant parsing user requests into structured data.
    Domain: {domain}
    
    Please extract the relevant details from the user's request and output a valid JSON object matching this schema:
    {json.dumps(schema, indent=2)}
    
    If the request is ambiguous, lacks details, or doesn't make sense for the domain, set "needs_human_clarification" to true.
    Return ONLY the raw JSON object, without any markdown formatting or explanations.
    
    User Request: "{raw_text}"
    """
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs strictly in JSON."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-120b", # Defaulting to a supported fast model
            response_format={"type": "json_object"},
            temperature=0,
        )
        
        result_content = response.choices[0].message.content
        parsed_json = json.loads(result_content)
        return parsed_json
        
    except Exception as e:
        print(f"Error parsing with Groq: {e}")
        return {"needs_human_clarification": True, "raw": raw_text, "error": str(e)}
