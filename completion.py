from openai import OpenAI

client = OpenAI()
import os
import yaml

config = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MODEL_ENGINE = config["model_engine"]


def get_completion(messages):
    response = client.chat.completions.create(model=MODEL_ENGINE,
    messages=messages)
    return response