#!/usr/bin/env python
# coding: utf-8

# In[1]:


from flask import Flask, render_template, request, redirect, session, url_for
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


# In[2]:


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
        elif item_type == "embed":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Embed": item[i][item_type]["url"],
            }
        elif item_type == "bookmark":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "Bookmark": item[i][item_type]["url"],
            }
        elif item_type == "link_preview":
            block = {
                "Id": item[i]["id"],
                "Type": item_type,
                "HasChildren": item[i]["has_children"],
                "LinkPreview": item[i][item_type]["url"],
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


# In[ ]:


app = Flask(__name__)
app.secret_key = "tekitou"  # os.urandom(32)などが良い。が、herokuで安定しないとのコメントあり。
labellist={ 'Home':'/','Blog':'/blog','Wishlist':'https://pushy-kitty-07b.notion.site/PC-3a8f8fc1fdb243649a2bbb1cbcb41f11',}
# 何も描かないとGETしか受け付けない。ブログならそれでOK
# https://shigeblog221.com/python-flask4/
@app.route("/")
def index():
    return render_template("index.html",labellist=labellist)

@app.route("/blog", methods=["GET", "POST"])
def blog():
    #if len(posts)>10:
        #post_list=posts[:10]
    #else:
        #post_list=posts
    return render_template("blog.html",labellist=labellist,posts=posts,tags=tags_set,tagname=0)

@app.route("/blog/<Slug>", methods=["GET", "POST"])
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


if __name__ == "__main__":
    app.run()


# In[ ]:




