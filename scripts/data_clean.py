import os
import json
import random
import requests
from tqdm import tqdm
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


question_list = [
    "从文章中总结可以提问的问题，要求提出的问题必须能在文章中找到对应的答案。返回结果以<问题，答案>对的形式呈现。",
]


def send_request(requests_template, system_prompt=None, user_prompt=None):
    url = "http://localhost:9091/v1/chat/completions"
    requests_template["messages"][0]["content"] = system_prompt
    requests_template["messages"][1]["content"] = user_prompt
    payload = requests_template
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def process_data(d, title2data, f, lock):
    if d["title"] in title2data:
        return
    else:
        logger.info(d["title"])
        strategy = d["title"] + "\n\n" + d["content"]
        system_prompt = """
        你是一个文档总结机器人，你的任务是从一篇文档中总结可以提问的问题，要求提出的问题必须能在文章中找到对应的答案。返回结果以<问题，答案>对的形式呈现。
        ===strategy content start===
        {{{content}}}
        ===strategy content end===
        """
        user_prompt = """
        {{{question}}}
        """
        sys_prompt = system_prompt.format(content=strategy)
        user_prompt = user_prompt.format(question=random.choice(question_list))
        requests_template = {
            "model": "",
            "messages": [
                {"role": "system", "content": ""},
                {"role": "user", "content": ""},
            ],
            "temperature": 1,
            "top_p": 1,
            "n": 1,
            "max_tokens": 1024,
            "stop": "string",
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "stream": False,
        }
        if len(sys_prompt) + len(user_prompt) > 2500:
            requests_template["model"] = "gpt-3.5-turbo-16k"
        else:
            requests_template["model"] = "gpt-3.5-turbo"
        response = send_request(requests_template, sys_prompt, user_prompt)
        title2data[d["title"]] = {
            "title": d["title"],
            "sys_prompt": sys_prompt,
            "user_prompt": user_prompt,
            "response": response,
        }
        with lock:
            f.write(json.dumps(title2data[d["title"]], ensure_ascii=False) + "\n")


if __name__ == "__main__":
    with open("./cookbook.jsonl", "r") as f:
        data = []
        for d in f.readlines():
            data.append(json.loads(d))

        title2data = {}
        if os.path.exists("./cookbook_processed_20230917.jsonl"):
            with open("./cookbook_processed_20230917.jsonl", "r") as f:
                for d in f.readlines():
                    d = json.loads(d)
                    title2data[d["title"]] = d

        lock = Lock()

        with open("./cookbook_processed_20230917.jsonl", "a") as f:
            with ThreadPoolExecutor(max_workers=4) as executor:
                for d in tqdm(data):
                    executor.submit(process_data, d, title2data, f, lock)
