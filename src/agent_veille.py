import smtplib
from email.mime.text import MIMEText
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from mistralai.client import Mistral
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

KEYWORDS = [
    "LLM", "agent IA", "Mistral", "Google ADK", "Gemini", "Claude", "IA générative",
    "agent conversationnel", "intelligence artificielle", "modèle de langage",
    "large language model", "AI agent", "chatbot", "deep learning", "neural network",
    "transformer", "NLP", "machine learning", "IA", "AI", "automation", "robot",
    "algorithme", "data science", "apprentissage automatique", "GPT", "BERT",
    "vector embeddings", "fine-tuning", "inference", "deploy", "API IA", "cyber", "cybersecurite",
    "Windows", "Linux"
]

# URL corrigée : la vraie page "toute l'actualité"
LE_MONDE_INFO_URL = "https://www.lemondeinformatique.fr/actualites/toute-l-actualite.html"


def fetch_le_monde_informatique():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(LE_MONDE_INFO_URL, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    # Sélecteur corrigé : les titres sont dans des <h2> contenant un <a>
    for h2 in soup.select("h2"):
        a_tag = h2.find("a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        link = a_tag.get("href", "")
        # Compléter les liens relatifs
        if link.startswith("/"):
            link = "https://www.lemondeinformatique.fr" + link
        if title and any(keyword.lower() in title.lower() for keyword in KEYWORDS):
            articles.append({"title": title, "url": link, "source": "Le Monde Informatique"})
    return articles


def fetch_newsapi(query="LLM OR agent IA OR intelligence artificielle"):
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={query}&language=fr&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    )
    response = requests.get(url, timeout=10)
    data = response.json()

    articles = []
    for item in data.get("articles", []):
        title = item.get("title") or ""
        description = item.get("description") or ""
        if any(
            keyword.lower() in title.lower() or keyword.lower() in description.lower()
            for keyword in KEYWORDS
        ):
            articles.append({
                "title": title,
                "url": item["url"],
                "source": item["source"]["name"],
                "description": description,
            })
    return articles


def summarize_with_mistral(text):
    prompt = (
        "Résume cet article en 2-3 phrases en français. "
        "Focus sur les points clés pour un expert en IA :\n\n" + text
    )
    with Mistral(api_key=MISTRAL_API_KEY) as client:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )
    return response.choices[0].message.content


def generate_report(articles):
    report = f"# Veille Tech : LLM & Agents IA - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for article in articles:
        try:
            if "lemondeinformatique" in article["url"]:
                content = f"Titre : {article['title']}. Source : Le Monde Informatique."
            else:
                content = article.get("description") or article["title"]
            summary = summarize_with_mistral(content)
            report += (
                f"### [{article['title']}]({article['url']})\n"
                f"*Source : {article['source']}*\n"
                f"**Résumé :** {summary}\n\n---\n\n"
            )
        except Exception as e:
            report += f"### [Erreur] {article['title']} : {str(e)}\n\n"
    return report


def send_mail(report_text):
    msg = MIMEText(report_text.replace("###", "").replace("---", "---\n"), "plain", "utf-8")
    msg["Subject"] = f"Veille Tech IA - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = os.getenv("MAIL_FROM")
    msg["To"] = os.getenv("MAIL_TO")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("MAIL_FROM"), os.getenv("MAIL_PASSWORD"))
            server.send_message(msg)
        print("Mail envoyé !")
    except Exception as e:
        print(f"Erreur envoi mail : {e}")


if __name__ == "__main__":
    print("Récupération des articles...")
    lemonde_articles = fetch_le_monde_informatique()
    print(f"Trouvé {len(lemonde_articles)} articles sur Le Monde Informatique.")
    all_articles = lemonde_articles
    if not all_articles:
        print("Aucun article trouvé. Vérifie tes clés API et ta connexion.")
    else:
        report = generate_report(all_articles)
        filename = f"veille_llm_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Rapport généré : {filename}")
        send_mail(report)
