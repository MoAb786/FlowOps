import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

print("Looking for .env at:", ENV_PATH)

load_dotenv(ENV_PATH)

api_key = os.getenv("GEMINI_API_KEY")

print("API key found:", bool(api_key))
# Initialize Gemini client
client = genai.Client(api_key=api_key)

class Item(BaseModel):
    name: str | None = None
    quantity: int | None = Field(default=None, ge=1)


class LabRequest(BaseModel):
    event_type: str | None = None
    items: list[Item] = Field(default_factory=list)
    needs_human_clarification: bool = False

def parse_request(raw_text: str, domain: str) -> dict:
    """
    Uses Gemini to parse the raw text into a structured JSON 
    matching the domain schema.
    """
    schema_path = f"schemas/{domain}.json"
    if not os.path.exists(schema_path):
        return {"needs_human_clarification": True, "raw": raw_text, "error": f"Unknown domain schema: {domain}"}
    
    with open(schema_path, "r") as f:
        schema = json.load(f)

    # Use Gemini to extract JSON matching the schema
    prompt = f"""
    You are FlowOps, an intelligent request-parsing assistant.

    Your job is to convert a user's natural-language request into accurate,
    structured JSON that can be safely processed by an automation system.

    You can work across multiple domains. Adapt your understanding and
    terminology based on the provided domain.

    CURRENT DOMAIN: {domain}

    DOMAIN ROLE:
    - If the domain is "lab", act as an intelligent lab management assistant.
    Understand requests related to issuing, returning, borrowing, or managing
    laboratory components and equipment.

    - If the domain is "restaurant", act as an intelligent restaurant assistant,
    waiter, or manager. Understand requests related to orders, cancellations,
    tables, and restaurant operations.

    Your task is to analyze the user's request and extract only the information
    that is explicitly stated or can be unambiguously understood from the request.

    Return a JSON object that follows this schema:

    {json.dumps(schema, indent=2)}

    STRICT EXTRACTION RULES:

    1. NEVER invent, assume, or guess information that the user did not provide.

    2. If required information is missing, unclear, ambiguous, or cannot be
    confidently determined, use null where the schema allows it.

    3. If the request requires additional information before it can be safely
    processed, set:
    "needs_human_clarification": true

    4. If all required information is clear and sufficient, set:
    "needs_human_clarification": false

    5. Correctly identify the appropriate event_type from the allowed values
    in the provided schema.

    6. Support multiple items. If the user requests multiple components,
    equipment items, or products, include every item separately in the
    "items" array.

    7. Preserve quantities exactly as stated by the user. Do not change,
    estimate, or invent quantities.

    8. If an item is mentioned but its quantity is missing, check if the request
    uses singular articles ("a", "an") or clearly implies a single item (e.g. "one"). 
    If so, set the quantity to 1. Otherwise, if the quantity is completely unknown
    or ambiguous, use null and request clarification.

    9. If the user's request does not make sense for the current domain,
    do not attempt to force it into the schema. Set
    "needs_human_clarification": true.

    10. Interpret natural, informal, abbreviated, or conversational language
        correctly, but do not infer information beyond what is reasonably clear.

    OUTPUT RULES:

    - Return ONLY one valid JSON object.
    - Do NOT return markdown.
    - Do NOT use ```json or code fences.
    - Do NOT include explanations, comments, reasoning, or additional text.
    - Ensure the output can be parsed directly using json.loads().

    USER REQUEST:
    "{raw_text}"
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction="You are a helpful assistant that outputs strictly in JSON.",
                temperature=0,
            )
        )
        
        result_content = response.text
        parsed_json = json.loads(result_content)
        return parsed_json
        
    except Exception as e:
        print(f"Error parsing with Gemini: {e}")
        return {"needs_human_clarification": True, "raw": raw_text, "error": str(e)}

if __name__ == "__main__":

    test_requests = [
        "I need 2 Arduino Uno boards",
        "I need 2 Arduino Uno boards and 3 breadboards",
        "I need an Arduino Uno",
        "I am returning 5 LEDs",
        "I need some equipment"
    ]

    for request in test_requests:
        print("\n" + "=" * 50)
        print("USER REQUEST:")
        print(request)

        result = parse_request(request, "lab")

        print("\nPARSED RESULT:")
        print(json.dumps(result, indent=4))