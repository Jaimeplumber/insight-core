import json
from openai import OpenAI

INPUT_FILE = "clean_posts.json"
OUTPUT_FILE = "../scraper/ai_analyzed_posts.json"

client = OpenAI(api_key="TU_API_KEY_AQUI")  # o usa variables de entorno

def analyze_post(title, author, score, comments):
    prompt = f"""
    Analiza este post de Reddit:
    Título: "{title}"
    - Autor: {author}
    - Score: {score}
    - Comentarios: {comments}

    Devuelve en formato JSON:
    {{
        "categoria": "tema principal (ej: humor, política, relaciones, etc)",
        "sentimiento": "positivo/neutral/negativo",
        "resumen": "breve resumen del post"
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.choices[0].message.content)

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    results = []
    for post in posts[:50]:  # procesa los primeros 50 (ajústalo)
        analysis = analyze_post(post["title"], post["author"], post["score"], post["comments"])
        post.update(analysis)
        results.append(post)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"✅ Posts analizados con IA guardados en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()