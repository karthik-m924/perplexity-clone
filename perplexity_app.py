import anthropic
import os
import urllib3
from dotenv import load_dotenv
from ddgs import DDGS
import streamlit as st

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(dotenv_path=r"C:\Users\619188\agent_project\.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ---- TOOL FUNCTION ----
def web_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        return results
    except Exception as e:
        return []

# ---- TOOL DEFINITION ----
tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information. Use this for any question that needs up to date information from the internet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up"
                }
            },
            "required": ["query"]
        }
    }
]

# ---- AGENT LOOP ----
def run_agent(user_message, messages):
    sources = []
    
    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            tools=tools,
            messages=messages,
            system="You are an AI assistant for Indian IT corporate employees. When searching, prioritize Indian sources, Indian regulations, and Indian context."
        )

        if response.stop_reason == "end_turn":
            final_answer = response.content[0].text
            return final_answer, sources

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    query = block.input["query"]
                    print(f"Searching: {query}")
                    
                    search_results = web_search(query)
                    
                    # Save sources for UI display
                    for r in search_results:
                        sources.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "body": r.get("body", "")
                        })
                    
                    # Format results for Claude
                    formatted = ""
                    for i, r in enumerate(search_results):
                        formatted += f"\nSource {i+1}: {r.get('title', '')}\n"
                        formatted += f"URL: {r.get('href', '')}\n"
                        formatted += f"Content: {r.get('body', '')}\n"
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": formatted
                    })

            messages.append({
                "role": "user",
                "content": tool_results
            })

# ---- STREAMLIT UI ----
st.set_page_config(page_title="Perplexity Clone", page_icon="🔍", layout="wide")

st.title("🔍 Search AI")
st.caption("Ask anything — I'll search the web and answer with sources")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for chat in st.session_state.chat_history:
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])
        if chat.get("sources"):
            with st.expander(f"📚 Sources ({len(chat['sources'])})"):
                for s in chat["sources"]:
                    st.markdown(f"**[{s['title']}]({s['url']})**")
                    st.caption(s["body"][:150] + "...")
                    st.divider()

# Chat input
user_input = st.chat_input("Ask anything...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching the web..."):
            answer, sources = run_agent(user_input, st.session_state.messages)
        st.markdown(answer)
        if sources:
            with st.expander(f"📚 Sources ({len(sources)})"):
                for s in sources:
                    st.markdown(f"**[{s['title']}]({s['url']})**")
                    st.caption(s["body"][:150] + "...")
                    st.divider()

    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": answer,
        "sources": sources
    })
    st.session_state.messages.append({"role": "assistant", "content": answer})