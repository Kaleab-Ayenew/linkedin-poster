import requests
from dotenv import load_dotenv
import openai
import config
from newspaper import Article
import os
import io
import json
from datetime import datetime


def get_ln_header():
    now = datetime.now()

    # Format the date to 'YYYYMM'
    version = "202301"

    headers = {
        'LinkedIn-Version': version,
        'X-Restli-Protocol-Version': '2.0.0'
    }
    return headers


def post_to_telegram(content):
    bot_token = config.GENAI_BOT_TOKEN
    channel_uname = config.GENAI_CHANNEL_USERNAME
    # url = f"https://api.telegram.org/bot{bot_token}/sendphoto"
    url = f"https://api.telegram.org/bot{bot_token}/sendmessage"

    # data = {
    #     "chat_id": channel_uname,
    #     "caption": content.get("main_text"),
    #     "photo": content.get("image")
    # }
    data = {
        "chat_id": channel_uname,
        "text": content.get("main_text"),

    }

    print(data)
    rsp = requests.post(url=url, data=data)
    print(rsp.json())


def get_article_content(url):
    article = Article(url)
    article.download()
    article.parse()
    article_data = {
        "main_text": article.text,
        "top_image": article.top_image,
        "title": article.title,
        "url": article.url
    }
    return article_data


def ask_chatgpt(system_prompt, user_prompt):
    openai.api_key = config.OPENAI_API_KEY

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[

            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    response = completion.choices[0].message.get("content")

    return response


def get_prompt(one_liner, article_text):
    system_prompt = f"You are a master tech, startup, and finance journalist, an expert at summerizing articles into crispy short form LinkedIn posts, with catchy dramatic hooks. You have mastered the skill of short form content so much that you can summerize each paragraph, into a single concise, and crispy sentence. You are not generic with your hooks, but you surprise your audience everytime. Your hooks are never longer than a single line. Add 3 relevant hashtags to each LinkedIn post. {one_liner}"
    user_prompt = f"Convert the following report into a LinkedIn post: {article_text}"
    prompts = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
    return prompts


def create_cache(data_id):
    print(f"Creating cache for {data_id}")
    with open("cache.json", "r") as file:
        content = file.read()
        file.close()

    cache_data = json.loads(content)

    cache_data.update({data_id: {}})

    with open("cache.json", "w") as file:
        text_cache = json.dumps(cache_data)
        file.write(text_cache)
        file.close()


def update_cache(data_id, property, value):

    with open("cache.json", "r") as file:
        content = file.read()
        file.close()

    cache_data = json.loads(content)
    current_data = cache_data.get(data_id)
    current_data.update({property: value})
    cache_data.update({data_id: current_data})

    with open("cache.json", "w") as file:
        text_cache = json.dumps(cache_data)
        file.write(text_cache)
        file.close()


def org_post_to_linkedin_text(text_content):
    post_url = "https://api.linkedin.com/rest/posts"
    post_json = {
        "author": f"urn:li:organization:{config.STARTIST_PAGE_ID}",
        "commentary": text_content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    headers = get_ln_header()
    headers.update({"Authorization": f"Bearer {config.POSTIST_ACCESS_TOKEN}"})
    print("[*] Creating text post...")  # Creating text post log
    rsp = requests.post(url=post_url, headers=headers, json=post_json)
    print(rsp.content)


def org_create_linkedin_image_asset():
    post_url = "https://api.linkedin.com/rest/images?action=initializeUpload"
    post_json = {
        "initializeUploadRequest": {
            "owner": f"urn:li:organization:{config.STARTIST_PAGE_ID}"
        }
    }
    headers = get_ln_header()
    headers.update({"Authorization": f"Bearer {config.POSTIST_ACCESS_TOKEN}"})
    print("[*] Creating image asset...")
    rsp = requests.post(url=post_url, json=post_json, headers=headers)
    json_rsp = rsp.json()
    print(json_rsp)

    asset_urn = json_rsp.get("value").get("image")
    upload_url = json_rsp.get("value").get("uploadUrl")

    return {"asset_urn": asset_urn, "upload_url": upload_url}


def org_upload_linkedin_image(upload_url, image_binary):
    headers = get_ln_header()
    headers.update({"Authorization": f"Bearer {config.POSTIST_ACCESS_TOKEN}"})
    print("[*] Uploading image...")
    rsp = requests.put(url=upload_url, data=image_binary, headers=headers)
    print("[*] Image Upload Status:", rsp.status_code)
    print(rsp.content)
    if rsp.status_code == 201:
        return True
    else:
        return False


def org_create_image_post(text_content, asset_urn):
    post_json = {
        "author": f"urn:li:organization:{config.STARTIST_PAGE_ID}",
        "commentary": text_content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "content": {
            "media": {
                "altText": "Post Image",
                "id": asset_urn
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    post_url = "https://api.linkedin.com/rest/posts"
    headers = get_ln_header()
    headers.update({"Authorization": f"Bearer {config.POSTIST_ACCESS_TOKEN}"})
    print("[*] Creating image post...")
    rsp = requests.post(url=post_url, json=post_json, headers=headers)
    print("[*] Create post status: ", rsp.status_code)
    if rsp.status_code == 201:
        print("Post Created Succesfully!")
    else:
        raise ValueError("Failed to create post")


def org_post_to_linkedin_image(text_content, image_url):
    image_asset_data = org_create_linkedin_image_asset()
    image_binary = get_image_content(image_url)

    upload_url = image_asset_data.get("upload_url")
    image_asset_urn = image_asset_data.get("asset_urn")
    upload_ok = org_upload_linkedin_image(
        upload_url=upload_url, image_binary=image_binary)

    if upload_ok:
        org_create_image_post(text_content=text_content,
                              asset_urn=image_asset_urn)
    else:
        raise ValueError("Failed to upload image")


def post_to_linkedin_text(text_content):
    post_json = {
        "author": f"urn:li:person:{config.POSTIN_KALISH_AYISH_URN}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text_content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {config.POSTIN_ACCESS_TOKEN}"}

    rsp = requests.post(url=post_url, headers=headers, json=post_json)


def create_linkedin_image_asset():
    post_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    post_json = {
        "registerUploadRequest": {
            "recipes": [
                "urn:li:digitalmediaRecipe:feedshare-image"
            ],
            "owner": f"urn:li:person:{config.POSTIN_KALISH_AYISH_URN}",
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    post_headers = {
        "Authorization": f"Bearer {config.POSTIN_ACCESS_TOKEN}"
    }

    rsp = requests.post(url=post_url, json=post_json, headers=post_headers)
    json_rsp = rsp.json()

    asset_urn = json_rsp.get("value").get("asset")
    upload_url = json_rsp.get("value").get("uploadMechanism").get(
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest").get("uploadUrl")
    print(upload_url)

    return {"asset_urn": asset_urn, "upload_url": upload_url}


def upload_linkedin_image(upload_url, image_binary):
    headers = {"Authorization": f"Bearer {config.POSTIN_ACCESS_TOKEN}"}
    rsp = requests.post(url=upload_url, data=image_binary, headers=headers)
    print(rsp.status_code)
    if rsp.status_code == 201:
        return True
    else:
        return False


def get_image_content(image_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    rsp = requests.get(url=image_url, headers=headers)
    image = rsp.content
    return image


def create_image_post(text_content, asset_urn):
    post_json = {
        "author": f"urn:li:person:{config.POSTIN_KALISH_AYISH_URN}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text_content
                },
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": "Post Image"
                        },
                        "media": asset_urn,
                        "title": {
                            "text": "Post Image"
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {config.POSTIN_ACCESS_TOKEN}"}
    rsp = requests.post(url=post_url, json=post_json, headers=headers)
    print(rsp.json(), rsp.status_code)
    if rsp.status_code == 201:
        return rsp.json().get("id")
    else:
        raise ValueError("Failed to create post")


def post_to_linkedin_image(text_content, image_url):
    image_asset_data = create_linkedin_image_asset()
    image_binary = get_image_content(image_url)

    upload_url = image_asset_data.get("upload_url")
    image_asset_urn = image_asset_data.get("asset_urn")
    upload_ok = upload_linkedin_image(
        upload_url=upload_url, image_binary=image_binary)

    if upload_ok:
        create_image_post(text_content=text_content, asset_urn=image_asset_urn)
    else:
        raise ValueError("Failed to upload image")


def register_used_link(site_url, link):
    with open("posted_links.json", "r") as f:
        link_data = json.load(f)
        f.close()
    if link_data.get(site_url):
        link_data.get(site_url).append(link)
    else:
        link_data.update({site_url: [link]})

    with open("posted_links.json", "w") as f:
        json.dump(link_data, f)
        f.close()


def is_link_used(site_url, link):

    with open("posted_links.json", "r") as f:
        link_data = json.load(f)
        f.close()

    if link_data.get(site_url):
        return link in link_data.get(site_url)

    return False
