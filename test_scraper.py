from scraper.scraper_biobio import scrap_news_article
import csv

def main():
    with open("Crawler/biobiochile.csv", "r", newline = "", encoding = "utf-8") as f:
        reader = csv.reader(f)
        lista_url = [linea[0] for linea in reader if linea]

    for index, url in enumerate(lista_url, start = 1):
        doc = scrap_news_article(url, validate = True)
        if (isinstance(doc, dict)):
            print(f"Url {index} scrappeada exitosamente")
        else:
            print(f"Error al scrappear la url n° {index}") 
            break           


if __name__ == "__main__":
    main()