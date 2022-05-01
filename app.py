#!/usr/bin/env python
# coding: utf-8

# In[1]:


from flask import Flask, render_template, request, redirect, session, url_for,send_from_directory
import os
from dotenv import load_dotenv
from pprint import pprint
from notion_client import Client
# .envファイルの内容を読み込みます
load_dotenv()

# os.environを用いて環境変数を表示させます
DATABASE_ID=os.environ['DATABASE_ID']
NOTION_API_SECRET=os.environ['NOTION_API_SECRET']

notion = Client(auth=NOTION_API_SECRET)
db = notion.databases.query(
    **{
        'database_id' : DATABASE_ID  # データベースID
       }
)
    
posts=[]
tags=[]
for i in range(len(db["results"])):
    prop=db["results"][i]["properties"]
    excerpt=prop["Excerpt"]["rich_text"]
    ogimege=prop["OGImage"]["files"]
    if prop["Published"]["checkbox"]:
        post = {
            "PageId": db["results"][i]["id"],
            "Title": prop["Page"]["title"][0]["plain_text"],
            "Slug": prop["Slug"]["rich_text"][0]["plain_text"],
            "Date": prop["Date"]["date"]["start"],
            "LastEditedTime": db["results"][i]["last_edited_time"][:10],
            "Tags": list(map(lambda x:x["name"] ,prop["Tags"]["multi_select"])),
            "Excerpt":excerpt[0]["plain_text"] if len(excerpt)> 0 else "",
            "OGImage":ogimege[0]["file"]["url"] if len(ogimege)> 0 else None,
            "Rank": prop["Rank"]["number"]}
        tags.extend(post["Tags"])
        posts.append(post)
tags_set=list(set(tags))


# In[3]:


import requests
from bs4 import BeautifulSoup


headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    }
def get_title(html):
    """Scrape page title."""
    title = None
    if type(html.title)==str:
        title = html.title.string
    elif html.find("meta", property="og:title"):
        title = html.find("meta", property="og:title").get('content')
    elif html.find("meta", property="twitter:title"):
        title = html.find("meta", property="twitter:title").get('content')
    elif html.find("h1"):
        title = html.find("h1").string
    return title


def get_description(html):
    """Scrape page description."""
    description = None
    if html.find("meta", property="description"):
        description = html.find("meta", property="description").get('content')
    elif html.find("meta", property="og:description"):
        description = html.find("meta", property="og:description").get('content')
    elif html.find("meta", property="twitter:description"):
        description = html.find("meta", property="twitter:description").get('content')
    elif html.find("p"):
        description = html.find("p").contents
    return description


def get_image(html):
    """Scrape share image."""
    image = None
    if html.find("meta", property="image"):
        image = html.find("meta", property="image").get('content')
    elif html.find("meta", property="og:image"):
        image = html.find("meta", property="og:image").get('content')
    elif html.find("meta", property="twitter:image"):
        image = html.find("meta", property="twitter:image").get('content')
    elif html.find("img", src=True):
        image = html.find("img").get('src')
    return image

def generate_preview(url):
    req = requests.get(url, headers)
    html = BeautifulSoup(req.content, 'html.parser')
    meta_data = {
       'title': get_title(html),
       'description': get_description(html),
       'image': get_image(html),
    }
    return meta_data


def make_page(p):
    item = notion.blocks.children.list(block_id=posts[p]["PageId"])["results"]
    blocks = []
    pprint(item)
    for i in range(len(item)):
        item_type = item[i]["type"]
        if (
            item_type
            in [
                "paragraph",
                "heading_1",
                "heading_2",
                "heading_3",
                "bulleted_list_item",
                "numbered_list_item",
            ]
            and len(item[i][item_type]["text"]) > 0
        ):
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "RichTexts": item[i][item_type],
            }
        elif item_type == "image":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Caption": item[i]["image"]["caption"],
                "Image": item[i]["image"]["file"]["url"]
                if item[i]["image"]["type"] == "file"
                else item[i]["image"]["external"]["url"],
            }
        elif item_type == "code":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Caption": item[i][item_type]["caption"],
                "Text": item[i][item_type],
                "Language": item[i]["code"]["language"],
            }
        elif item_type == "quote":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Quote": item[i][item_type],
            }
        elif item_type == "callout":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "RichTexts": item[i][item_type],
                "Icon": item[i][item_type]["icon"]["emoji"],
            }

        elif item_type in ["link_preview","bookmark","embed"]:
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Url":item[i][item_type]["url"],
                "LinkPreview": generate_preview(item[i][item_type]["url"]),
            }
        elif item_type == "table":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Table": {
                    "TableWidth": item[i][item_type]["table_width"],
                    "HasColumnHeader": item[i][item_type]["has_column_header"],
                    "HasRowHeader": item[i][item_type]["has_row_header"],
                    "Rows": [],
                },
            }
        elif item_type == "table_row":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "TableRow": item[i][item_type]["cells"],
            }
        else:
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "RichTexts":{"text":[{"plain_text":""}]}#空白行にしたいので追加
            }
        blocks.append(block)
    return blocks

def makesitemap():
    import xml.etree.ElementTree as ET

    urls = [
        "https://flasknotionblog.herokuapp.com/",
        "https://flasknotionblog.herokuapp.com/top"
    ]
    for p in range(len(posts)):
        urls.append("https://flasknotionblog.herokuapp.com/"+posts[p]["Slug"])
    urlset = ET.Element('urlset')
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ET.ElementTree(element=urlset)

    for u in range(len(urls)):
        url=urls[u]
        url_element = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url_element, 'loc')
        loc.text = url
        lastmod = ET.SubElement(url_element, 'lastmod')
        if u<2:
            lastmod.text = "2022-04-01"
        else:
            lastmod.text = posts[u-2]["LastEditedTime"]


    tree.write('static/sitemap.xml', encoding='utf-8', xml_declaration=True)
#makesitemap()


# In[4]:


app = Flask(__name__, static_folder='static')
app.secret_key = "tekitou"  # os.urandom(32)などが良い。が、herokuで安定しないとのコメントあり。
labellist={ 'Home':'/top','Blog':'/','Wishlist':'https://pushy-kitty-07b.notion.site/PC-3a8f8fc1fdb243649a2bbb1cbcb41f11',}
# 何も描かないとGETしか受け付けない。ブログならそれでOK
# https://shigeblog221.com/python-flask4/
@app.route("/top")
def index():
    return render_template("index.html",labellist=labellist,tags=tags_set)

@app.route("/", methods=["GET", "POST"])
def blog():
    #if len(posts)>10:
        #post_list=posts[:10]
    #else:
        #post_list=posts
    return render_template("blog.html",labellist=labellist,posts=posts,tags=tags_set,tagname=0)

@app.route("/<Slug>", methods=["GET", "POST"])
def page(Slug):
    for p in range(len(posts)):
        if posts[p]["Slug"]==Slug:
            page_num=p
            break
    blocks=make_page(page_num)
    pprint(blocks)
    return render_template("slug.html",labellist=labellist,post=posts[p],blocks=blocks,tags=tags_set)

@app.route("/tag/<Tag>", methods=["GET", "POST"])
def tagpage(Tag):
    tag_page=[]
    for p in range(len(posts)):
        if Tag in posts[p]["Tags"]:
            tag_page.append(posts[p])
    return render_template("blog.html",labellist=labellist,posts=tag_page,tags=tags_set,tagname=Tag)

@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == "__main__":
    app.run()


# In[ ]:




