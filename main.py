import json
import os
import random
import re
import time

import markdown
import undetected_chromedriver as uc
from dotenv import load_dotenv
from openai import OpenAI
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()


def random_delay(min_delay=2, max_delay=5):
    delay = random.uniform(min_delay, max_delay)
    print(f"Waiting {delay:.2f} seconds")
    time.sleep(delay)


def clean_text(input):
    driver.find_elements(By.TAG_NAME, "iframe")
    return re.sub(r"\s+", " ", input)


if __name__ == "__main__":

    url = input("URL (https://www.leboncoin.fr/recherche...) ")

    if not url:
        print("URL is empty")
        exit()

    chrome_options = Options()

    # chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    driver = uc.Chrome(headless=False, options=chrome_options)

    driver.set_window_size(411, 731)

    wait = WebDriverWait(driver, 30)

    driver.get("https://www.leboncoin.fr")

    consent_button_element = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "[class=didomi-continue-without-agreeing]")
        )
    )

    random_delay()
    consent_button_element.click()

    gimii_button_element = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "[class=gimii_root__NNJEc] button")
        )
    )
    random_delay()
    gimii_button_element.click()

    random_delay()

    announcements = []

    driver.get(url)

    announcement_link_elements = wait.until(
        EC.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                'ul[data-test-id=listing-column] a[aria-label="Voir l’annonce"]',
            )
        )
    )

    random_delay()

    urls = [
        link_element.get_attribute("href")
        for link_element in announcement_link_elements
    ]

    for url in urls:

        driver.get(url)

        script_element = wait.until(
            EC.presence_of_element_located(
                (
                    By.ID,
                    "__NEXT_DATA__",
                )
            )
        )

        random_delay()

        script_content = script_element.get_attribute("textContent")

        data = json.loads(script_content)

        ad = data["props"]["pageProps"]["ad"]

        attributes = [
            {"attribute": a.get("key_label"), "value": a.get("value_label")}
            for a in ad["attributes"][1:14]
        ]

        announcements.append(
            {
                "url": ad["url"],
                "subject": ad["subject"],
                "body": clean_text(ad["body"]),
                "price": ad["price"][0],
                "images": ad["images"]["urls_large"],
                "attributes": attributes,
            }
        )

        print(url)

    print("Saving results to data.json")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(announcements, f, indent=4, ensure_ascii=False)

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    messages = [
        {
            "role": "system",
            "content": """
            Tu es un expert automobile spécialisé dans les véhicules d’occasion, avec une connaissance approfondie des tendances du marché, des prix moyens, et des facteurs qui influencent la valeur d’un véhicule (état, équipements, kilométrage, fiabilité, etc.).

            Ta mission est d’analyser des annonces de voiture d’occasion et d’évaluer leurs rapport qualité/prix en te basant sur les données disponibles, afin de déterminer si le prix demandé est justifié, compétitif ou surévalué.

            Instructions :

            Analyse complète de l’annonce :

            Examine toutes les données disponibles : modèle, année, kilométrage, version, équipements, boîte, finition, motorisation, etc.

            Tiens compte des options et équipements spécifiques listés dans le corps de l’annonce.

            Évaluation du prix de marché :

            Estime la valeur moyenne actuelle sur le marché pour un modèle équivalent (même version, même motorisation, état et kilométrage proche).

            Compare cette valeur à celle demandée dans l’annonce.

            Analyse critique et notation :

            Fournis une analyse textuelle claire, professionnelle et objective qui explique :

            Pourquoi le prix est justifié ou non.

            Ce qui valorise ou dévalorise le véhicule dans cette annonce.

            S’il s’agit d’une bonne affaire, d’un prix correct ou d’un prix élevé.

            Termine par une note sur 10 représentant le rapport qualité/prix, où :

            10/10 = excellente affaire
            5/10 = prix conforme au marché
            1/10 = prix très surévalué

            Si possible, base-toi également sur des données de marché récentes ou des tendances de sites spécialisés (La Centrale, Leboncoin, AutoScout24…) pour affiner ton estimation.
            """,
        },
        {"role": "user", "content": []},
    ]

    for i, ad in enumerate(announcements, 1):
        messages[1]["content"].append(
            {
                "type": "text",
                "text": (
                    f"URL: {ad['url']}\n"
                    f"Titre: {ad['subject']}\n"
                    f"Prix: {ad['price']}\n"
                    f"Description: {ad['body']}\n"
                    f"Attributs: {ad['attributes']}\n"
                ),
            }
        )

    print("Starting GPT call...")

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )

    print("Saving results to output.html")

    html = markdown.markdown(completion.choices[0].message.content)

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html)
