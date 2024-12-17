# main.py

import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from pydantic import BaseModel
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

openai.api_key = os.getenv("OPENAI_API_KEY")

class QueryRequest(BaseModel):
    query: str

async def generate_cypher_query(user_query, schema_description):
    prompt = f"""
You are an assistant that converts natural language queries into Cypher queries for a Neo4j graph database.

Graph Schema
The graph has the following schema:

{schema_description}

Task
Convert the following user query into an accurate Cypher query that strictly adheres to the given schema.

Special Case for Service Bulletins (SB)
All user queries will be related to Service Bulletins (SB). Therefore, every Cypher query must:
1. Retrieve all properties of the specified Service Bulletin (SB).
2. Retrieve all properties of the aircraft nodes connected to the Service Bulletin (SB).
   - If the user specifies a specific aircraft, include only that aircraft. If not specified, include all aircraft connected to this SB.
3. Retrieve all other Service Bulletins (SBs) connected to the same aircraft(s) as the current SB.
   - If the user specifies an aircraft, include SBs related to that aircraft. If not, include all SBs connected to any of the aircraft associated with this SB.
4. Retrieve all properties of the Part nodes connected to the Service Bulletin (SB) via the REQUIRES_PART relationship, including the quantity_required.
5. Provide results in a format that facilitates optimizing maintenance schedules and identifying opportunities to group Service Bulletins (SBs) together to minimize downtime.

Important:
- Ensure that the Cypher query uses correct syntax for relationships, including the correct use of '-' and '->' or '<-'.
- When chaining relationships, ensure that each node and relationship is properly connected.
- **When accessing properties of relationships, you must assign a variable to the relationship in the MATCH clause.**
- **Example:**
  - To access the 'quantity_required' property of the REQUIRES_PART relationship:
    - Correct: MATCH (sb)-[r:REQUIRES_PART]->(p:Part) RETURN r.quantity_required
    - Incorrect: RETURN RELATIONSHIP().quantity_required

Input and Output
Input: User Query
Output: Corresponding Cypher Query

Input
User Query: "{user_query}"

Output
Cypher Query:

"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
        ]
    )
    
    cypher_query = response.choices[0].message.content
    print("Generated Cypher Query:\n", cypher_query)
    cypher_query = cypher_query.replace("```cypher", "").replace("```", "").strip()
    
    if cypher_query.startswith('"') and cypher_query.endswith('"'):
        cypher_query = cypher_query[1:-1]
    elif cypher_query.startswith("'") and cypher_query.endswith("'"):
        cypher_query = cypher_query[1:-1]
    
    cypher_query = re.sub(r'^Cypher Query:\s*', '', cypher_query, flags=re.IGNORECASE)
    
    return cypher_query


async def generate_final_answer(user_query, results):
    prompt = f"""
You are an assistant that helps answer user questions based on data retrieved from a database.

User Query: "{user_query}"

Database Results: {results}

Task:
- Provide a clear and insightful answer to the user's question based on the database results.
- Avoid simply listing the data; instead, analyze the information to provide meaningful insights and actionable recommendations.
- Consider whether parts are available or not for the implementation of the Service Bulletins (SBs), and include that in your recommendations.
- Highlight any mandatory Service Bulletins (SBs) in **red** to emphasize their importance.
- Suggest maintenance optimizations by identifying opportunities to group Service Bulletins (SBs) for connected aircraft, focusing on minimizing downtime and costs.
- You have to help the user plan the implementation of the SBs; otherwise, it's no use, so you must plan.
- Include a button in your response that says "View Part Information". This button should be enclosed within a <button id="check-part-availability">View Part Information</button> tag.

Guidelines for Answer:
1. **Key Findings**
   - Synthesize the key insights from the database results, focusing on what is most relevant to the user query.
   - Highlight critical information such as upcoming compliance deadlines, urgency, and impacts on operations without listing raw data.
   - Mention whether the required parts are available or if there are any lead times to consider.

2. **Recommendations**
   - Provide concise, actionable recommendations to optimize maintenance schedules.
   - Identify opportunities to group Service Bulletins for the same aircraft or across multiple aircraft to reduce downtime.
   - Focus on clear and practical steps the user can take based on the analysis.
   - Take into account the availability of parts when making recommendations.

3. **Context and Alignment**
   - Briefly explain how the findings and recommendations align with the user's query, ensuring the response is logical and actionable.

Formatting:
- Use HTML formatting for clarity and visual appeal.
- Mandatory Service Bulletins (SBs) should be highlighted in **red** to indicate priority.
- Keep recommendations concise but impactful, while the explanation of findings can include more detailed context as needed.
- Include the Part information in a separate section at the end of the response, enclosed within a <div id="part-info">...</div>.
- The "Check Part Availability" button should be interactive and enclosed within <button id="check-part-availability">Check Part Availability</button>.

Respond in HTML format. Do not include the ```html or the closing ```. Focus on clarity and relevance. Must ensure correct formatting.

Today's Date: 18th November, 2024

Answer:

"""
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
        ]
    )
    return response.choices[0].message.content

@app.post("/query")
async def process_query(request: Request):
    data = await request.json()
    user_query = data.get("query")

    schema_description = """
Nodes:
- ServiceBulletin
    - Properties:
        - docnumber (String)
        - required_man_hours (Integer)
        - description (String)
        - urgency_level (String) ["High", "Medium", "Low"]
        - applicability (List of Strings)
        - is_mandatory (Boolean)
        - compliance_deadline (Date or Null)
        - expected_mtbf_increase (Integer)
        - expected_operational_cost_reduction (Integer)
        - expected_downtime (Integer)
- Aircraft
    - Properties:
        - name (String)
        - mean_time_between_failures (Integer)
        - unexpected_removal_time (Integer)
        - service_interruptions (Integer)
        - downtime_from_maintenance (Integer)
        - time_on_wing (Integer)
        - age (Integer)
        - operational_cost_per_hour (Integer)
        - current_status (String) ["In Service", "Scheduled for Maintenance", "Under Maintenance"]
        - next_scheduled_maintenance (Date)
- Part
    - Properties:
        - part_number (String)
        - name (String)
        - price (Integer)
        - availability (Boolean)
        - lead_time (Integer)

Relationships:
- (sb:ServiceBulletin)-[:APPLICABLE_TO]->(a:Aircraft)
- (sb:ServiceBulletin)-[:REQUIRES_PART {quantity_required}]->(p:Part)

"""

    cypher_query = await generate_cypher_query(user_query, schema_description)

    try:
        with driver.session() as session:
            result = session.run(cypher_query)
            records = [record.data() for record in result]

        results_text = str(records)
        final_answer = await generate_final_answer(user_query, results_text)

        return {"answer": final_answer}
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        return {"answer": error_message}
