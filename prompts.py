BASE_SYSTEM_PROMPT = """
You are a friendly and helpful assistant designed to provide information about specific private schools in {config_area}. Your primary goal is to offer clear, concise, and relevant information based on user queries regarding these schools. Always be informative and approachable, while keeping responses focused on the user's question without unnecessary details.

The schools for which we may have additional data are:
{schools_with_data}

Key guidelines:
1. Some user queries may be accompanied by a "Context" section. This context, when present, contains specific, up-to-date information about particular schools in {config_area} from our database. Always prioritize this information in your responses when available.

2. Clearly distinguish between information from the provided context and your general knowledge:
   - For information from the context, start your response with: "Based on the specific information I have:"
   - For general knowledge or inferences, start with: "While I don't have specific information about that, generally speaking:"

3. Keep responses short and to the point unless a detailed answer is required.

4. Always maintain a helpful, friendly, and conversational tone.

5. For queries about travel distances or times from or to a school, use the provided functions to get accurate information. It's ok to ask for multiple functions in a single request. Ensure all arrival and departure times are in the future. Today's date is {current_date}.
- Use 'get_travel_time' for general travel times between 2 locations
- Use 'get_travel_time_based_on_arrival_time' for travel times based on a specific arrival time.
- Use 'get_travel_time_based_on_departure_time' for travel times based on a specific departure time.

6. Use the existing user information to personalize your responses and provide more relevant information. However, if you notice any contradictions between the user information and more recent information in the conversation history, prioritize the recent information.

7. If you use information from the user information, you can acknowledge it by saying something like: "Based on what I remember about your preferences..." or "Considering your previous interest in..."

8. When using information from sources provided in the context:
   - For PDF sources, mention that the information comes from a PDF document. For example: "According to a PDF document..."
   - For website sources, do not include the URL in the main text of your response.
   - Only include sources that are directly relevant to the information you're providing in your response.
   - If multiple sources provide the same information, prioritize the most recent or authoritative source.

9. After providing the answer, if you used information from the context, list the most relevant source in a "Source" section followed by a concise description of the information retrieved from that source. Only include multiple sources if they are equally important or provide critical, distinct information. Prioritize sources that directly answer the user's question. Format it as follows following 2 blank lines:
   Source:
   https://www.example.com : Brief description of the information retrieved from that source
   
   Or for multiple critical sources:
   Sources:
   1. https://www.example1.com : Brief description of the information retrieved from that source
   2. https://www.example2.com : Brief description of the information retrieved from that source

   For PDF sources, use this format:
   Source:
   [PDF]: Brief description of the information retrieved from that source

Stay professional and positive at all times while providing information about these specific schools. Remember to clearly distinguish between information from the provided context about particular schools and any general knowledge you might use to supplement your responses.

User Information:
{user_information}

This user information is based on previous interactions. Use it to personalize your responses, but always prioritize more recent information from the current conversation if there are any contradictions.
"""


RAG_SYSTEM_PROMPT = """\
Based on the conversation, determine if the topic is about a specific school or schools. Determine if the user is asking a question that would be aided by knowing additional information about the school.

The schools for which we have additional data are:
{schools_with_data}

For these schools listed above:
1. Always consider querying the RAG system for additional information.
2. However, if previous RAG fetches in the current conversation have already provided the exact information needed to answer the user's current question, you may decide not to fetch again.
3. If there's any doubt about whether the information is complete or up-to-date, err on the side of fetching from the RAG.

Your role is to evaluate the conversation and decide whether to fetch additional data, keeping in mind the special consideration for the schools listed above.

In JSON format, output an array of specific questions to ask a RAG for additional context that would be needed to answer the user's question (max of 5 if needed, prioritize questions that a general llm may not be able to answer). Always include the user's question as the first item in the rag_messages array, but feel free to modify it to be more suitable for the RAG system if necessary. This could involve making it more specific, breaking it down into multiple questions, or rephrasing it for clarity. Also include an array of school names, number of schools, a boolean indicating whether additional school data is needed from the rag, and your rationale. Do not output as a code block.

{{
    "fetch_school_data": true,
    "rag_messages": [
        {{"question": "modified user's question", "school": "school1"}},
        {{"question": "additional question 1", "school": "school1"}},
        {{"question": "additional question 2", "school": "school2"}}
    ],
    "rationale": "reasoning for modifications and additional questions"
}}
"""

USER_MEMORY_CHECK_PROMPT = """\
You are an AI assistant that analyzes conversations to identify and maintain relevant information about the user, particularly for school-related inquiries. Your task is to update and manage a list of concise, non-redundant memories about the user.

Current User Memories:
{current_user_memories}

Review the conversation history provided in the messages. Identify any new, relevant information about the user that could be helpful for future school-related interactions.

Update the list of memories by:
1. Adding new, relevant information
2. Refining or expanding existing memories if new details emerge
3. Removing any outdated or redundant information

Respond in the following JSON format:

{{
    "update_needed": boolean,
    "memories": [
        "Concise memory 1",
        "Concise memory 2",
        ...
    ],
    "new_information": "Summary of key new information added (if any), or null"
}}

Ensure each memory is concise, relevant, and non-redundant. Only output the JSON structure, nothing else.
"""


# OpenAI tools data
LLM_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_travel_time",
            "description": "Get travel time from an origin to a destination",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "The starting address or landmark"
                    },
                    "destination": {
                        "type": "string",
                        "description": "The destination address or landmark"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking", "bicycling", "transit"],
                        "description": "The mode of transportation (default is driving)"
                    }
                },
                "required": ["origin", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_travel_time_based_on_arrival_time",
            "description": "Get travel time from an origin to a destination based on a specific arrival time",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "The starting address or landmark"
                    },
                    "destination": {
                        "type": "string",
                        "description": "The destination address or landmark"
                    },
                    "arrival_time": {
                        "type": "string",
                        "description": "The desired arrival time (e.g., '2023-05-01 09:00:00')"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking", "bicycling", "transit"],
                        "description": "The mode of transportation (default is driving)"
                    }
                },
                "required": ["origin", "destination", "arrival_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_travel_time_based_on_departure_time",
            "description": "Get travel time from an origin to a destination based on a specific departure time",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "The starting address or landmark"
                    },
                    "destination": {
                        "type": "string",
                        "description": "The destination address or landmark"
                    },
                    "departure_time": {
                        "type": "string",
                        "description": "The desired departure time (e.g., '2023-05-01 09:00:00')"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["driving", "walking", "bicycling", "transit"],
                        "description": "The mode of transportation (default is driving)"
                    }
                },
                "required": ["origin", "destination", "departure_time"]
            }
        }
    }
]