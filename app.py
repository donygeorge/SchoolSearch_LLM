import chainlit as cl
import openai
import json
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from config_llm import config, model_kwargs
from prompts import BASE_SYSTEM_PROMPT, RAG_SYSTEM_PROMPT
from config_app import config_area

from rag_pipeline import get_query_engine

from dotenv import load_dotenv
load_dotenv()

# Initialize the OpenAI async client
client = wrap_openai(openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"]))

# Initialize the query engine
query_engine = get_query_engine()

@traceable
async def query_rag(client, message_history, message):
    conversation_context = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in message_history[-5:] if msg['role'] != 'system'
    ])
    rag_query = f"{conversation_context}\nUser: {message.content}"

    rag_response = query_engine.query(rag_query)
    rag_context = str(rag_response)
    print("RAG context: " + rag_context)
    
    # Append RAG context and user message to message history
    message_history.append({"role": "user", "content": f"Context: {rag_context}\n\nQuestion: {message.content}"})
    
    return message_history


@traceable
async def check_for_additional_data(client, message_history, message):
    updated_message_history = message_history.copy()
    rag_prompt_message = {"role": "system", "content": RAG_SYSTEM_PROMPT}
    if updated_message_history and updated_message_history[0]["role"] == "system":
        # Replace the existing system message
        updated_message_history[0] = rag_prompt_message
    else:
        # Insert a new system message at the beginning
        updated_message_history.insert(0, rag_prompt_message)

    response = await client.chat.completions.create(
        messages=updated_message_history,
        **model_kwargs)
    try:
        response_json = json.loads(response.choices[0].message.content)
        print("Rag check reponse: " + str(response_json))
        if response_json.get("fetch_school_data", False):
            message_history = await query_rag(client, message_history, message)
            return message_history
    except json.JSONDecodeError:
        pass
    
    return message_history

@traceable
@cl.on_chat_start
def on_chat_start():    
    system_prompt = BASE_SYSTEM_PROMPT.format(config_area=config_area)
    message_history = [{"role": "system", "content": system_prompt}]
    cl.user_session.set("message_history", message_history)

@traceable
@cl.on_message
async def on_message(message: cl.Message):
    # Maintain an array of messages in the user session
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    print("Chat interface: message received:" + message.content)
    
    # Check if we need to fetch additional data and q
    message_history = await check_for_additional_data(client, message_history, message)
        
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(
        messages=message_history,
        stream=True, **model_kwargs
    )
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    await response_message.update()

    # Record the AI's response in the history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)


if __name__ == "__main__":
    cl.main()