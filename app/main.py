import os
import openai
import random
import json
import time

from dotenv import load_dotenv
import newspaper

import config
import utils
import data


# one_liner = "Make every sentence its own line, and use two new lines as separators between each line." if random.randint(
#     0, 1) == 1 else ""


def main_task(website):
    source_url = website
    source = newspaper.build(source_url, memoize_articles=False)
    print(source.size())
    for article in source.articles[:10]:
        print("here")

        if utils.is_link_used(source_url, article.url):
            print(f"[-] Link already used - {article.url}")
            continue
        try:
            # utils.create_cache(article.url)
            article_data = utils.get_article_content(article.url)
            one_liner = "Make every paragraph only one sentence long."
            article_text = article_data.get('main_text')
            # utils.update_cache(article.url, "article_text", article_text)
            prompts = utils.get_prompt(one_liner, article_text)

            system_prompt = prompts.get("system_prompt")
            user_prompt = prompts.get("user_prompt")

            response = utils.ask_chatgpt(system_prompt, user_prompt)
            # utils.update_cache(article.url, "response", response)
            print(response)

            tg_post = {
                "main_text": response + f"\n\n{article_data.get('url')}\n\n{article_data.get('top_image')}",
                "image": article_data.get("top_image")
            }
            utils.post_to_telegram(tg_post)
            # utils.org_post_to_linkedin_text(response)

            if article_data.get("top_image"):
                utils.org_post_to_linkedin_image(
                    text_content=response, image_url=article_data.get("top_image"))
            # else:
            #     utils.post_to_linkedin_text(response)

            utils.register_used_link(source_url, article.url)
        except openai.error.InvalidRequestError:
            continue
        time.sleep(60*10)


if __name__ == "__main__":
    mode = ["random", "all", "manual"]
    current_mode = mode[1]
    web_sites = data.sites

    if current_mode == "random":
        selected_website = random.choice(web_sites)
        main_task(selected_website)

    elif current_mode == "all":
        print("Running app loop...")
        while True:
            for site in web_sites:

                main_task(site)
            time.sleep(60*60*3)

    elif current_mode == "manual":
        selected_website = "https://disrupt-africa.com/"
        main_task(selected_website)
