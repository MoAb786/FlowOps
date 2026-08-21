import json
from ai_client import generate_with_fallback


def assess_risk(parsed_data: dict, domain: str) -> dict:
    """
    Uses AI to assess the risk of a parsed request.

    Main model: Groq
    Fallback: Gemini
    Final fallback: HIGH risk + human review
    """

    # If parser itself says clarification is needed,
    # don't send it for automatic approval.
    if parsed_data.get("needs_human_clarification", False):
        return {
            "risk_level": "HIGH",
            "risk_score": 10,
            "reasons": [
                "The request contains missing, unclear, or ambiguous information."
            ]
        }

    prompt = f"""
You are FlowOps, an intelligent risk assessment and routing engine for an
automation system.

Your responsibility is to evaluate the operational risk of a structured request
and assign an appropriate risk level.

You are NOT responsible for parsing natural language.

The request has already been parsed into structured data.

CURRENT DOMAIN:
{domain}

STRUCTURED REQUEST:
{json.dumps(parsed_data, indent=2)}

==================================================
YOUR TASK
==================================================

Evaluate the request as a whole and determine its operational risk.

You must consider the COMBINATION of factors rather than using one fixed rule.

Do NOT use simplistic rules such as:

- "quantity above 5 is always high risk"
- "all electronic items are normal"
- "all expensive items are automatically high risk"

The risk depends on context.

For example:

5 LEDs and 5 oscilloscopes should NOT automatically receive the same risk
assessment.

Similarly:

3 Arduino boards may be a normal request in one situation, while requesting
many Raspberry Pis or several expensive instruments may deserve greater review.

Use general real-world knowledge about the nature of the items.

Do not require a manually hardcoded database of every possible laboratory item.

==================================================
RISK FACTORS
==================================================

For the "lab" domain, consider the following factors.

1. ITEM VALUE

Consider whether the item is generally:

- inexpensive
- moderately valuable
- expensive
- highly specialized

Examples of considerations:

- common resistors and LEDs are generally low value
- development boards may have moderate value
- specialized instruments may have higher value

Do not invent exact prices.

Use general understanding rather than exact cost estimates.

--------------------------------------------------

2. QUANTITY RELATIVE TO THE ITEM

Evaluate quantity relative to the specific item.

The same quantity can represent very different levels of risk.

Examples:

- 5 LEDs may be routine
- 5 oscilloscopes may be unusual
- 3 Arduino boards may be reasonable
- 50 Arduino boards may require review

Do NOT evaluate quantity in isolation.

--------------------------------------------------

3. SAFETY AND HAZARD

Consider whether the requested item may involve:

- electrical hazards
- high voltage
- high current
- lasers or intense optical sources
- chemicals
- heat
- mechanical hazards
- radiation
- other safety-sensitive handling

Safety-sensitive items should generally receive increased risk.

However, do not exaggerate risk without reason.

--------------------------------------------------

4. SPECIALIZATION AND REPLACEMENT DIFFICULTY

Consider whether the item is:

- a common consumable
- easily replaceable
- specialized
- difficult or expensive to replace
- sensitive or fragile equipment

--------------------------------------------------

5. OPERATIONAL CRITICALITY

Consider whether issuing the item could affect laboratory operations.

Examples may include:

- essential instruments
- shared equipment
- limited specialized resources

Do not assume exact inventory levels.

Instead, evaluate general operational significance.

--------------------------------------------------

6. COMBINED REQUEST RISK

Evaluate all items together.

Several individually low-risk items may collectively create a larger concern.

A mixed request containing common components and expensive equipment should be
evaluated based on the overall request.

Do not simply calculate risk using total quantity.

--------------------------------------------------

7. REQUEST CONTEXT

Use the event type and available structured information.

A return request may generally have different operational implications from an
issue request.

However, still consider safety and handling where relevant.

Do not invent user history, inventory information, permissions, prices, or
laboratory policies that were not provided.

==================================================
RISK LEVELS
==================================================

Assign one of the following levels.

NORMAL

Use NORMAL when the request appears to be:

- routine
- low operational risk
- composed of common or low-value items
- in a reasonable quantity
- without meaningful safety concerns

Examples may include a reasonable number of:

- LEDs
- resistors
- capacitors
- breadboards
- common electronic components

These are examples only, not a fixed whitelist.

--------------------------------------------------

MEDIUM

Use MEDIUM when the request contains factors such as:

- moderately valuable equipment
- specialized equipment
- an unusually large quantity
- equipment requiring more careful handling
- meaningful operational impact

MEDIUM means the request deserves review but does not clearly represent a
high-risk situation.

--------------------------------------------------

HIGH

Use HIGH when the request contains significant concerns such as:

- expensive or highly specialized equipment
- a large quantity of valuable equipment
- hazardous or safety-sensitive items
- potentially critical laboratory equipment
- a combination of factors that creates substantial operational risk
- missing or ambiguous information that prevents safe automated assessment

If the request cannot be safely assessed because important information is
unclear, prefer HIGH as a safe routing decision.

==================================================
RISK SCORE
==================================================

Assign a risk_score from 0 to 10.

Use this range:

0 to 3 → NORMAL

4 to 6 → MEDIUM

7 to 10 → HIGH

The score and risk_level MUST agree.

Examples:

NORMAL:
risk_score between 0 and 3

MEDIUM:
risk_score between 4 and 6

HIGH:
risk_score between 7 and 10

==================================================
IMPORTANT REASONING RULES
==================================================

1. Do not rely on a hardcoded inventory database.

Use general real-world understanding of the requested items.

2. Do not invent exact:

- prices
- stock quantities
- laboratory policies
- permissions
- budgets

3. Evaluate item type and quantity together.

4. Do not classify an item only because of its name.

Consider:

- value
- specialization
- quantity
- safety
- operational importance
- combined request

5. The assessment should be general enough to work for different laboratories.

Different laboratories may have different inventories, but you should still
provide a reasonable general risk assessment.

6. The purpose of HIGH and MEDIUM classification is not to reject the request.

It is to route the request to the appropriate approval stage.

7. Human involvement should mainly occur at the approval stage.

Your output helps decide whether the request can proceed automatically or
requires additional approval.

==================================================
OUTPUT FORMAT
==================================================

Return ONLY ONE valid JSON object in exactly this format:

{{
    "risk_level": "NORMAL",
    "risk_score": 0,
    "reasons": [
        "Short specific reason based on the request",
        "Another relevant reason if necessary"
    ]
}}

Rules:

- risk_level must be exactly NORMAL, MEDIUM, or HIGH
- risk_score must be an integer from 0 to 10
- risk_score must match the selected risk_level range
- reasons must explain the actual factors used
- do not invent unavailable facts
- keep reasons concise and relevant

Do NOT return:

- markdown
- code fences
- explanations outside JSON
- comments
- additional text

Return only valid JSON.
"""

    try:
        # This will use:
        # 1. Groq main model
        # 2. Gemini fallback if Groq fails
        result_content = generate_with_fallback(prompt)

        # Convert AI response into Python dictionary
        risk_data = json.loads(result_content)

        return risk_data

    except Exception as e:
        print(f"Error during AI risk assessment: {e}")

        # Final safety fallback
        return {
            "risk_level": "HIGH",
            "risk_score": 10,
            "reasons": [
                "Risk assessment system encountered an error.",
                "Request sent for human review as a safety fallback."
            ],
            "error": str(e)
        }


def route_request(parsed_data: dict, domain: str):
    risk_data = assess_risk(parsed_data, domain)

    risk_level = risk_data.get("risk_level", "HIGH").upper()

    if risk_level == "NORMAL":
        approver = "system"

    elif risk_level == "MEDIUM":
        approver = "operator"

    else:
        risk_level = "HIGH"
        approver = "operator"

    return risk_level, approver


# ---------------------------------------------------------
# TESTING
# ---------------------------------------------------------

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
                        "name": "resistor",
                        "quantity": 10
                    },
                    {
                        "name": "capacitor",
                        "quantity": 5
                    },
                    {
                        "name": "breadboard",
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
                        "name": "Raspberry Pi",
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
                        "name": "oscilloscope",
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
                        "quantity": 50
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
                        "name": "high power laser",
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
                        "name": "concentrated acid",
                        "quantity": 3
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
                        "name": "Raspberry Pi",
                        "quantity": 4
                    },
                    {
                        "name": "oscilloscope",
                        "quantity": 2
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
                        "name": "equipment",
                        "quantity": None
                    }
                ],
                "needs_human_clarification": True
            }
        }
    ]

    for test in test_cases:

        print("\n" + "=" * 60)
        print("TEST:", test["name"])

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