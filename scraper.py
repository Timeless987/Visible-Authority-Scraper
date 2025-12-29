import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.thevisibleauthority.com"
BLOG_URL = BASE_URL + "/blog"

def pobierz_strone(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    response = requests.get(url, headers=headers)
    return response.text

def znajdz_linki_artykulow(html):
    soup = BeautifulSoup(html, 'html.parser')
    linki = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/blog/' in href and href != '/blog' and 'page/' not in href:
            pelny_link = href if href.startswith('http') else BASE_URL + href
            if pelny_link not in linki:
                linki.append(pelny_link)
    return linki

def pobierz_tresc_artykulu(url):
    try:
        html = pobierz_strone(url)
        soup = BeautifulSoup(html, 'html.parser')
        tytul = soup.find('h1')
        tytul_tekst = tytul.get_text(strip=True) if tytul else "Brak tytulu"
        artykul = soup.find('article') or soup.find('div', class_='post-body')
        if not artykul:
            for div in soup.find_all('div'):
                if len(div.get_text()) > 1000:
                    artykul = div
                    break
        if artykul:
            for tag in artykul.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            tresc = artykul.get_text(separator='\n', strip=True)
        else:
            tresc = "Nie udalo sie pobrac tresci"
        return tytul_tekst, tresc
    except Exception as e:
        return "Blad", f"Nie udalo sie pobrac: {e}"

def main():
    print("=" * 50)
    print("SCRAPER BLOGA THE VISIBLE AUTHORITY")
    print("=" * 50)
    wszystkie_linki = []
    print("\n[1/3] Szukam artykulow...")
    html = pobierz_strone(BLOG_URL)
    wszystkie_linki.extend(znajdz_linki_artykulow(html))
    print(f"  Strona 1 - znaleziono {len(wszystkie_linki)} artykulow")
    for numer_strony in range(2, 16):
        url_strony = f"{BLOG_URL}/page/{numer_strony}"
        try:
            html = pobierz_strone(url_strony)
            nowe_linki = znajdz_linki_artykulow(html)
            if not nowe_linki:
                print(f"  Strona {numer_strony} - brak artykulow, koncze szukanie")
                break
            wszystkie_linki.extend(nowe_linki)
            print(f"  Strona {numer_strony} - znaleziono {len(nowe_linki)} nowych")
            time.sleep(0.5)
        except:
            break
    wszystkie_linki = list(set(wszystkie_linki))
    print(f"\n  RAZEM: {len(wszystkie_linki)} unikalnych artykulow")
    print("\n[2/3] Pobieram tresc artykulow...")
    wyniki = []
    for i, link in enumerate(wszystkie_linki, 1):
        print(f"  [{i}/{len(wszystkie_linki)}] {link[:60]}...")
        tytul, tresc = pobierz_tresc_artykulu(link)
        wyniki.append({'url': link, 'tytul': tytul, 'tresc': tresc})
        time.sleep(1)
    print("\n[3/3] Zapisuje do pliku...")
    with open('visible_authority_blog.md', 'w', encoding='utf-8') as f:
        f.write("# The Visible Authority - Blog Archive\n\n")
        f.write(f"Pobrano {len(wyniki)} artykulow\n\n")
        f.write("=" * 80 + "\n\n")
        for artykul in wyniki:
            f.write(f"## {artykul['tytul']}\n\n")
            f.write(f"Zrodlo: {artykul['url']}\n\n")
            f.write(artykul['tresc'])
            f.write("\n\n" + "=" * 80 + "\n\n")
    print("\n" + "=" * 50)
    print("GOTOWE!")
    print("Plik zapisany jako: visible_authority_blog.md")
    print("=" * 50)

if __name__ == "__main__":
    main()
