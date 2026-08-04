"""
AO3 百合(F/F)作品元数据抓取器
只抓元数据不抓正文；带延迟，遵守礼貌抓取原则
"""
import json
import re
import time
import requests
from bs4 import BeautifulSoup

BASE = "https://archiveofourown.org"
# F/F 分类 + 中文 + 按点赞数(kudos)排序，可自行修改筛选条件
SEARCH_URL = (
    BASE + "/works?"
    "work_search%5Bsort_column%5D=kudos_count"
    "&work_search%5Bcategory_ids%5D%5B%5D=116"   # F/F 分类
    "&work_search%5Blanguage_id%5D=zh"            # 中文；删掉这行则抓所有语言
    "&commit=Sort+and+Filter"
    "&tag_id=F%2FF"
)

HEADERS = {"User-Agent": "YuriIndexBot/1.0 (personal fan-index project; contact: your-email@example.com)"}
PAGES = 5          # 抓前 5 页（每页 20 部），别设太大
DELAY = 6          # 每页间隔 6 秒，务必保留

def parse_number(text):
    if not text:
        return 0
    text = text.replace(",", "").strip()
    m = re.search(r"[\d.]+", text)
    return int(float(m.group())) if m else 0

def scrape():
    works = []
    for page in range(1, PAGES + 1):
        print(f"抓取第 {page} 页...")
        r = requests.get(f"{SEARCH_URL}&page={page}", headers=HEADERS, timeout=30)
        if r.status_code == 429:
            print("被限流，等待 5 分钟...")
            time.sleep(300)
            continue
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for li in soup.select("li.work.blurb"):
            try:
                title_a = li.select_one("h4.heading a")
                author_a = li.select_one("h4.heading a[rel=author]")
                fandom = li.select_one("h5.fandoms a")
                summary = li.select_one("blockquote.summary")
                words = parse_number((li.select_one("dd.words") or {}).get_text("") if li.select_one("dd.words") else "")
                kudos = parse_number(li.select_one("dd.kudos").get_text()) if li.select_one("dd.kudos") else 0
                date = li.select_one("p.datetime")
                chapters = li.select_one("dd.chapters").get_text() if li.select_one("dd.chapters") else "1/1"
                done = chapters.split("/")[0] == chapters.split("/")[1]
                tags = [t.get_text() for t in li.select("li.freeforms a")][:5]
                cps = [t.get_text() for t in li.select("li.relationships a")][:2]

                works.append({
                    "title": title_a.get_text(strip=True),
                    "author": author_a.get_text(strip=True) if author_a else "匿名",
                    "url": BASE + title_a["href"],
                    "fandom": fandom.get_text(strip=True) if fandom else "未知",
                    "cp": " / ".join(cps),
                    "platform": "AO3",
                    "status": "完结" if done else "连载中",
                    "words": words,
                    "tags": tags,
                    "summary": summary.get_text(strip=True)[:200] if summary else "",
                    "score": round(min(10, 7 + kudos / 500), 1),  # 用 kudos 估算评分
                    "heat": kudos,
                    "updated": date.get_text(strip=True) if date else "",
                })
            except Exception as e:
                print("跳过一条：", e)

        time.sleep(DELAY)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(works, f, ensure_ascii=False, indent=2)
    print(f"完成，共 {len(works)} 部作品 → data.json")

if __name__ == "__main__":
    scrape()
