import os
from openai import OpenAI
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

llm = init_chat_model(
    "openai:gpt-4.1"
)


class State(TypedDict):
    graph_state: str


def node_1(state):
    print("---Node 1---")
    return {"graph_state": state['graph_state'] +" I am"}

def node_2(state):
    print("---Node 2---")
    return {"graph_state": state['graph_state'] +" happy!"}


