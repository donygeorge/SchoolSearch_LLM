import chainlit as cl
import openai
import json
import re
from datetime import datetime
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from chainlit.step import Step as cl_Step

from config.config_llm import config, model_kwargs
from prompts import BASE_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT, LLM_FUNCTIONS, USER_MEMORY_CHECK_PROMPT
from config.config_app import config_area

from rag_pipeline import get_query_engine, get_schools_with_data, get_sources
from map_functions import get_travel_time, get_travel_time_based_on_arrival_time, get_travel_time_based_on_departure_time

from helpers.memory_helper import get_formatted_memories, save_memories
from dotenv import load_dotenv
load_dotenv()

# Initialize the OpenAI async client
client = wrap_openai(openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"]))

@traceable
async def query_rag(client, message_history, message, school):
    conversation_context = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in message_history[-5:] if msg['role'] != 'system'
    ])
    rag_query = f"{conversation_context}\nUser: {message}"
    print("RAG query: " + rag_query)

    query_engine = get_query_engine(school)
    rag_response = query_engine.query(rag_query)
    rag_context = str(rag_response)
    
    # Extract sources from the response
    sources = get_sources(rag_response.source_nodes)
    
    print("RAG reply: " + rag_context)
    
    return rag_context, sources


@traceable
async def check_rag(client, message_history, message):
    rag_check_message_history = message_history.copy()
    rag_prompt = RAG_SYSTEM_PROMPT.format(schools_with_data=get_schools_with_data())
    rag_prompt_message = {"role": "system", "content": rag_prompt}
    if rag_check_message_history and rag_check_message_history[0]["role"] == "system":
        # Replace the existing system message
        rag_check_message_history[0] = rag_prompt_message
    else:
        # Insert a new system message at the beginning
        rag_check_message_history.insert(0, rag_prompt_message)

    # Add the user's message to the message history
    rag_check_message_history.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        messages=rag_check_message_history,
        **model_kwargs)
    
    updated_message_history = message_history.copy()
    used_rag = False
    try:
        response_json = json.loads(response.choices[0].message.content)
        print("Rag check reponse: " + str(response_json))
        if response_json.get("fetch_school_data", False):
            rag_messages = response_json.get("rag_messages", [])
            print("Rag message: " + str(rag_messages))
            rag_replies = []
            for rag_message_item in rag_messages:
                rag_message = rag_message_item["question"]
                school = rag_message_item["school"]
                temporary_message_history = message_history.copy()
                temporary_message_history.append({"role": "system", "Updated question to query:": rag_message})
                rag_reply, rag_sources = await query_rag(client, temporary_message_history, rag_message, school)
                
                # Format the sources information
                sources_info = "\n".join([
                    f"Source {i+1}: {source['metadata'].get('source', 'Unknown')} "
                    f"Type: {source['metadata'].get('type', 'Unknown')}, "
                    f"Relevance: {source['score']:.2f})"
                    for i, source in enumerate(rag_sources)
                ])
                
                updated_message_history.append({
                    "role": "assistant", 
                    "content": f"COntext:\n{rag_reply}\n\nQuestion:\n{rag_message}\n\nSources:\n{sources_info}"
                })
                used_rag = True
    except json.JSONDecodeError:
        pass
    
    return updated_message_history, used_rag

async def add_system_tooltip(message):
    system_message = f'<span class="system-message">{message}</span>'
    await cl.Message(content=system_message, author="System").send()

@traceable
async def check_memories(message_history, message):
    memories_message_history = message_history.copy()
    memories = get_formatted_memories()
    system_prompt = USER_MEMORY_CHECK_PROMPT.format(current_user_memories=memories)


    memories_prompt_message = {"role": "system", "content": system_prompt}
    if memories_message_history and memories_message_history[0]["role"] == "system":
        # Replace the existing system message
        memories_message_history[0] = memories_prompt_message
    else:
        # Insert a new system message at the beginning
        memories_message_history.insert(0, memories_prompt_message)

    # Add the user's message to the message history
    memories_message_history.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        messages=memories_message_history,
        **model_kwargs)
    
    try:
        response_json = json.loads(response.choices[0].message.content)
        print("Memory check reponse: " + str(response_json))
        if response_json.get("update_needed", False):
            updated_memories = response_json.get("memories", [])
            print("Updated memories: " + str(updated_memories))
            save_memories(updated_memories)
            return True
        else:
            print("No memory update needed")
    except json.JSONDecodeError as e:
        print("Memory update error: " + str(e))
        pass

    return False


@traceable
async def generate_response(client, message_history):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(
        messages=message_history, 
        tools=LLM_FUNCTIONS,
        tool_choice="auto",
        stream=True, 
        **model_kwargs)

    full_response = ""
    is_tool_call = False
    tool_calls = []
    current_tool_call_index = None
    current_tool_call = None
    
    # print("Message history: " + str(message_history))
    
    async for part in stream:
        delta = part.choices[0].delta
        
        if delta.content:
            await response_message.stream_token(delta.content)
            full_response += delta.content

        if delta.tool_calls:
            is_tool_call = True
            print("Tool calls: " + str(delta.tool_calls))
            for tool_call in delta.tool_calls:
                if tool_call.index is not current_tool_call_index:  # A new tool call is starting
                    if current_tool_call:
                        tool_calls.append(current_tool_call)
                    current_tool_call = {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments or ""
                    }
                    current_tool_call_index = tool_call.index
                    print("Current tool call: " + str(current_tool_call_index))
                else:
                    if tool_call.function and tool_call.function.arguments:
                        current_tool_call["arguments"] += tool_call.function.arguments
                    elif tool_call.function and tool_call.function.name:
                        current_tool_call["names"] += tool_call.function.name

    if current_tool_call:
        tool_calls.append(current_tool_call)

    print("Tool calls: " + str(tool_calls))
    await response_message.update()
    return response_message, full_response, message_history, is_tool_call, tool_calls


@traceable
@cl.on_chat_start
def on_chat_start():    
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = BASE_SYSTEM_PROMPT.format(
        config_area=config_area,
        current_date=current_date,
        user_information=get_formatted_memories(),
        schools_with_data=get_schools_with_data())
    message_history = [{"role": "system", "content": system_prompt}]
    cl.user_session.set("message_history", message_history)
    
    
@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Key dates and events",
            message="What the key admission deadlines and events for Harker school?",
            icon="/public/calendar.svg",
            ),
        cl.Starter(
            label="School values and ideologies",
            message="Tell me about the core values and ideologies of Harker school?",
            icon="/public/ideas.svg",
            ),
        cl.Starter(
            label="School costs",
            message="What is the annual cost of sending my kid to Harker school in kindergarden?",
            icon="/public/cost.svg",
            ),
        cl.Starter(
            label="Commute time to school",
            message="How long will it take me to commute to Harker school from my house in the morning?",
            icon="/public/time.svg",
            )
        ]

@traceable
@cl.on_message
async def on_message(message: cl.Message):
    # Maintain an array of messages in the user session
    message_history = cl.user_session.get("message_history", [])
    print("Chat interface: message received:" + message.content)
    
    #  Check if we need to update memories
    memory_updated = await check_memories(message_history, message.content)
    if memory_updated:
        await add_system_tooltip('Memory updated')

    # Check if we need to fetch additional data and q
    await add_system_tooltip('Querying RAG for additional data...')
    message_history, used_rag = await check_rag(client, message_history, message.content)
    if used_rag:
        await add_system_tooltip('Loading additional data from RAG')
    else:
        await add_system_tooltip('No additional data found in RAG')

    # Add the user's message to the message history
    message_history.append({"role": "user", "content": message.content})
    
    while True:
        # Generate a response
        response_message, full_response, updated_message_history, is_tool_call, tool_call_data = await generate_response(client, message_history)
        
        print("Is tool call: " + str(is_tool_call))
        # print("Tool call data: " + str(tool_call_data))
        
        if not is_tool_call:
            break
        
        for tool_call in tool_call_data:
            print("Tool call: " + str(tool_call))            
            function_name = tool_call["name"]
            function_args = json.loads(tool_call["arguments"])
            
            if function_name is None:
                continue
            
            print("Function name: " + function_name)
            print("Function args: " + str(function_args))
            
            used_map_function = False
            if function_name == "get_travel_time":
                result = get_travel_time(**function_args)
                used_map_function = True
            elif function_name == "get_travel_time_based_on_arrival_time":
                result = get_travel_time_based_on_arrival_time(**function_args)
                used_map_function = True
            elif function_name == "get_travel_time_based_on_departure_time":
                result = get_travel_time_based_on_departure_time(**function_args)
                used_map_function = True
            else:
                result = "Unknown function"
                
            if used_map_function:
                await add_system_tooltip('Made an external API call to get travel time')

            system_message = {
                "role": "system",
                "content": f"Function '{function_name}' was called with arguments {function_args}. The result is:\n{result}"
            }
            updated_message_history.append(system_message)
        
        message_history = updated_message_history    
    
    # Record the AI's response in the history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)


if __name__ == "__main__":
    cl.main()