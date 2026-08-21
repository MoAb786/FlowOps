import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types


# -------------------------------------------------
# ENVIRONMENT SETUP
# -------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")


# Initialize Gemini client
client = genai.Client(api_key=api_key)


def route_request(parsed_data: dict, domain: str):
    """
    Evaluates the risk of a parsed request and determines
    whether it can be automatically approved or requires
    human approval.
    """

    # ---------------------------------------------
    # 1. Handle clarification cases immediately
    # ---------------------------------------------

    if parsed_data.get("needs_human_clarification"):

        risk_details = {
            "risk_level": "HIGH",
            "risk_score": 10,
            "reasons": [
                "The request contains missing, unclear, or ambiguous information."
            ]
        }

        return "HIGH", "operator", risk_details


    # ---------------------------------------------
    # 2. Currently focus on Lab domain
    # ---------------------------------------------

    if domain != "lab":

        risk_details = {
            "risk_level": "MEDIUM",
            "risk_score": 5,
            "reasons": [
                f"Automatic risk assessment is not yet configured for the '{domain}' domain."
            ]
        }

        return "MEDIUM", "operator", risk_details


    # ---------------------------------------------
    # 3. Ask Gemini to assess the request
    # ---------------------------------------------

    prompt = f"""
You are the risk assessment engine for FlowOps, an automated
laboratory management system.

Your task is to evaluate the operational risk of the following
laboratory request.

REQUEST DATA:

{json.dumps(parsed_data, indent=2)}

Evaluate the request based on the COMBINATION of the following factors:

1. ITEM VALUE
   Consider whether the requested item is generally inexpensive,
   moderately valuable, expensive, or highly valuable.

2. QUANTITY
   Evaluate the requested quantity relative to the type of item.

   A quantity that is normal for cheap consumables may be unusual
   for expensive or specialized equipment.

   Examples:
   - 5 LEDs is generally normal.
   - 5 oscilloscopes may represent significant risk.
   - A few resistors may be routine.
   - Multiple expensive instruments may require approval.

3. SAFETY AND HAZARD

   Consider whether the item may involve:

   - high voltage
   - high current
   - lasers
   - chemicals
   - heat
   - radiation
   - batteries
   - hazardous materials
   - specialized safety procedures

4. SPECIALIZATION

   Consider whether the equipment requires:

   - special training
   - careful handling
   - calibration
   - controlled storage
   - restricted access

5. OPERATIONAL IMPACT

   Consider whether issuing the requested item could:

   - significantly affect laboratory availability
   - remove critical equipment from other users
   - create a significant financial impact
   - create an unusual or excessive request pattern

IMPORTANT RULES:

- Do NOT assume the lab has a specific inventory system.
- Do NOT invent information about stock availability.
- Use general real-world knowledge about common laboratory equipment.
- Evaluate the COMBINATION of item type and quantity.
- Do not judge quantity in isolation.

For example:

- 10 LEDs may be low risk.
- 10 oscilloscopes may be high risk.
- 1 oscilloscope may be medium risk.
- 1 hazardous chemical may require high risk assessment.
- Multiple Raspberry Pi boards may become higher risk depending
  on the quantity.
- Common low-cost components are generally lower risk unless
  requested in an unusually large quantity.

RISK SCORING:

0-3 = NORMAL
4-6 = MEDIUM
7-10 = HIGH

OUTPUT REQUIREMENTS:

Return ONLY valid JSON in this exact format:

{{
    "risk_score": 0,
    "risk_level": "NORMAL",
    "reasons": [
        "reason 1",
        "reason 2"
    ]
}}

RULES FOR OUTPUT:

- risk_score must be an integer from 0 to 10.
- risk_level must be exactly one of:
  NORMAL, MEDIUM, HIGH
- Give 1 to 4 concise reasons.
- Do not include markdown.
- Do not include explanations outside the JSON.
- Do not invent laboratory-specific inventory information.
"""


    try:

        response = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=prompt,

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                temperature=0

            )

        )


        # ---------------------------------------------
        # 4. Parse Gemini response
        # ---------------------------------------------

        risk_details = json.loads(response.text)

        risk_score = risk_details.get("risk_score", 10)
        risk_level = risk_details.get("risk_level", "HIGH").upper()


        # ---------------------------------------------
        # 5. Safety validation
        # ---------------------------------------------

        if risk_level not in ["NORMAL", "MEDIUM", "HIGH"]:

            risk_level = "HIGH"

            risk_details["risk_level"] = "HIGH"

            risk_details["reasons"].append(
                "Invalid risk level returned by AI. Sent for human review."
            )


        if not isinstance(risk_score, int):

            risk_score = 10

            risk_details["risk_score"] = 10


        if risk_score < 0 or risk_score > 10:

            risk_score = 10

            risk_details["risk_score"] = 10

            risk_level = "HIGH"

            risk_details["risk_level"] = "HIGH"


        # ---------------------------------------------
        # 6. Decide approver
        # ---------------------------------------------

        if risk_level == "NORMAL":

            approver = "system"

        else:

            approver = "operator"


        return risk_level, approver, risk_details


    # ---------------------------------------------
    # 7. Fail safely
    # ---------------------------------------------

    except Exception as e:

        print(f"Error during Gemini risk assessment: {e}")

        risk_details = {
            "risk_level": "HIGH",
            "risk_score": 10,
            "reasons": [
                "Risk assessment system encountered an error.",
                "Request sent for human review as a safety fallback."
            ],
            "error": str(e)
        }

        return "HIGH", "operator", risk_details



# =================================================
# TESTING
# =================================================

if __name__ == "__main__":

    test_cases = [

        {
            "name": "Normal - common components",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "LED",
                        "quantity": 5
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Normal - multiple basic components",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "Resistor",
                        "quantity": 20
                    },
                    {
                        "name": "Breadboard",
                        "quantity": 2
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Medium - single specialized equipment",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "Oscilloscope",
                        "quantity": 1
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "High - multiple expensive instruments",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "Oscilloscope",
                        "quantity": 5
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Quantity stress test",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "Arduino Uno",
                        "quantity": 100
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Safety-related equipment",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "High power laser",
                        "quantity": 2
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Hazardous item",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "Lithium battery pack",
                        "quantity": 10
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Mixed request",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "LED",
                        "quantity": 10
                    },
                    {
                        "name": "Oscilloscope",
                        "quantity": 3
                    }
                ],
                "needs_human_clarification": False
            }
        },


        {
            "name": "Ambiguous request",
            "data": {
                "event_type": "issue component",
                "items": [
                    {
                        "name": "Arduino Uno",
                        "quantity": None
                    }
                ],
                "needs_human_clarification": True
            }
        }

    ]


    for test in test_cases:

        print("\n" + "=" * 60)

        print(f"TEST: {test['name']}")

        risk_level, approver, risk_details = route_request(
            test["data"],
            "lab"
        )

        print("\nRISK LEVEL:")
        print(risk_level)

        print("\nAPPROVER:")
        print(approver)

        print("\nRISK DETAILS:")
        print(json.dumps(risk_details, indent=4))