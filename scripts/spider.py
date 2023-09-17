# 狼人杀数据下载
import json
import time
import requests
from bs4 import BeautifulSoup

base_url = "https://www.langrensha.net/api/article/list"
params = {
    "articleType": 0,
    "sourceType": 0,
    "count": 20,
}

page_url = "https://www.langrensha.net/strategy/"


def fetch_page_content(page_number):
    params["page"] = page_number
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    return response.json()


def download_article_list():
    with open("./article_list.jsonl", "w") as fw:
        for page_num in range(1, 65):
            print(f"Fetching page {page_num} ...")
            article_list = fetch_page_content(page_num)
            fw.write(json.dumps(article_list, ensure_ascii=False) + "\n ")
    print("Complete download.")


def download_page(id, title, url: str):
    print(f"downloading article {id} {title} ...")
    url = url.replace("pc/strategy/", "")
    with open(f"./html_page/{id}_{title}.html", "w") as fw:
        response = requests.get(f"{page_url}{url}")
        fw.write(response.text)
    print(f"Complete download article {id} {title}.")


def download_all_page():
    with open("./article_list.jsonl", "r") as fr:
        for line in fr:
            article_list = json.loads(line)
            for article in article_list["records"]:
                download_page(article["articleId"], article["title"], article["url"])
                time.sleep(1)


def parse_article_page(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("h1", class_="content-title").get_text()
    description_editor = (
        soup.find("div", class_="description").find_all("span")[0].get_text()
    )
    description_date = (
        soup.find("div", class_="description").find_all("span")[1].get_text()
    )
    content = soup.find("div", class_="content").get_text()
    result = {
        "title": title,
        "description_editor": description_editor,
        "description_date": description_date,
        "content": content.strip(),
    }
    return result


def clean_all_html():
    import os

    data = []
    for file in os.listdir("./html_page"):
        if file.endswith(".html"):
            with open(f"./html_page/{file}", "r") as fr:
                html = fr.read()
            result = parse_article_page(html)
            data.append(result)
    with open("./cookbook.jsonl", "w") as fw:
        for item in data:
            fw.write(json.dumps(item, ensure_ascii=False) + "\n")
    print("Complete clean html.")


if __name__ == "__main__":
    # download_article_list()
    # download_all_page()
    # parse_article_page(open("./html_page/984_狼人杀两个预言家对跳怎么办？.html").read())
    clean_all_html()
