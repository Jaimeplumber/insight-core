import json
import re

# Ruta al archivo original (scrapeado)
INPUT_FILE = "../../posts.json"
# Ruta para guardar el archivo limpio
OUTPUT_FILE = "clean_posts.json"

def clean_text(text):
    """Limpia el texto eliminando espacios extra y caracteres no deseados."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # elimina caracteres no ASCII
    return text

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = []
    seen_titles = set()

    for post in data:
        title = clean_text(post.get("title", ""))
        author = post.get("author", "")
        score = post.get("score", 0)
        comments = post.get("comments", 0)

        # Filtra posts irrelevantes o duplicados
        if not title or title.lower() in seen_titles:
            continue
        if len(title) < 10 or len(title) > 200:  # elimina títulos muy cortos o largos
            continue

        seen_titles.add(title.lower())
        cleaned.append({
            "title": title,
            "author": author,
            "score": score,
            "comments": comments
        })

    print(f"✅ Posts procesados: {len(data)}")
    print(f"✅ Posts limpios: {len(cleaned)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"✅ Archivo limpio guardado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
