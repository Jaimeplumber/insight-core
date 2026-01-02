from app.enrichment.pipeline import run_pipeline
from app.core import logger

def main():
    vertical = "protein"
    logger.info(f"Starting pipeline test for vertical: {vertical}")
    
    filtered_posts = run_pipeline(vertical)
    
    logger.info(f"Pipeline test completed. {len(filtered_posts)} posts returned:")
    for p in filtered_posts:
        logger.info(f" - [{p.date}] {p.text}")

if __name__ == "__main__":
    main()
