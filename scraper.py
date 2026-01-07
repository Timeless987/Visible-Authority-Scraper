import requests
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://www.thevisibleauthority.com"
BLOG_URL = BASE_URL + "/blog"

def pobierz_strone(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.encoding = 'utf-8'
    return response.text

def znajdz_linki_artykulow(html):
    soup = BeautifulSoup(html, 'html.parser')
    linki = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/blog/' in href and href != '/blog' and 'page/' not in href and 'author/' not in href and '#' not in href:
            pelny_link = href if href.startswith('http') else BASE_URL + href
            if pelny_link not in linki and 'tag/' not in pelny_link:
                linki.append(pelny_link)
    return linki

def wyczysc_tekst(tekst):
    """Czyści tekst z nadmiarowych białych znaków"""
    tekst = re.sub(r'\n\s*\n\s*\n+', '\n\n', tekst)
    tekst = re.sub(r' +', ' ', tekst)
    return tekst.strip()

def pobierz_tresc_artykulu(url):
    try:
        html = pobierz_strone(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Tytuł - H1
        tytul_tag = soup.find('h1')
        tytul = tytul_tag.get_text(strip=True) if tytul_tag else "Brak tytulu"
        
        # Autor
        autor = ""
        autor_link = soup.find('a', href=re.compile(r'/blog/author/'))
        if autor_link:
            autor = autor_link.get_text(strip=True)
        
        # Data
        data = ""
        # Szukamy daty w formacie "DD Month YYYY"
        text_content = soup.get_text()
        data_match = re.search(r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', text_content)
        if data_match:
            data = data_match.group(0)
        
        # Usuwamy elementy których nie chcemy przed ekstrakcją
        for element in soup.find_all(['script', 'style', 'nav', 'iframe', 'noscript']):
            element.decompose()
        
        # Usuwamy header i footer
        for element in soup.find_all(['header', 'footer']):
            element.decompose()
        
        # Usuwamy menu nawigacyjne
        for nav in soup.find_all('nav'):
            nav.decompose()
        for ul in soup.find_all('ul'):
            if ul.find('a', href='/about') or ul.find('a', string=re.compile('About', re.I)):
                # Sprawdź czy to menu (krótkie linki)
                links = ul.find_all('a')
                if len(links) <= 5 and all(len(l.get_text(strip=True)) < 30 for l in links):
                    ul.decompose()
        
        # Zbieramy treść artykułu
        tresc_czesci = []
        zbieraj = False
        
        # Znajdź wszystkie elementy tekstowe
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'blockquote']):
            tekst = element.get_text(strip=True)
            
            # Zaczynamy zbierać po H1
            if element.name == 'h1':
                zbieraj = True
                continue
            
            if not zbieraj:
                continue
            
            # Kończymy na "Further Reading" lub podobnych
            if element.name in ['h2', 'h3'] and any(x in tekst for x in ['Further Reading', 'Share this article', 'Info', 'Menu', 'Connect with us']):
                break
            
            # Pomijamy bio autora
            if "extensive career in the consulting" in tekst:
                break
            
            # Pomijamy krótkie teksty które wyglądają na nawigację
            if len(tekst) < 15 and element.name == 'p':
                continue
            
            # Pomijamy puste elementy
            if not tekst:
                continue
            
            # Pomijamy elementy nawigacyjne
            if tekst in ['About us', 'Insights', 'Contact', 'About Us', 'Read more', 'Read More']:
                continue
            
            # Pomijamy info o firmie
            if 'TVA & Partners' in tekst or 'Jan Verbertlei' in tekst or 'Copyright' in tekst:
                break
            
            # Formatujemy nagłówki
            if element.name == 'h2':
                tresc_czesci.append(f"\n## {tekst}\n")
            elif element.name == 'h3':
                tresc_czesci.append(f"\n### {tekst}\n")
            elif element.name == 'h4':
                tresc_czesci.append(f"\n#### {tekst}\n")
            elif element.name in ['ul', 'ol']:
                # Formatujemy listy
                for li in element.find_all('li', recursive=False):
                    li_text = li.get_text(strip=True)
                    if li_text and len(li_text) > 5:
                        tresc_czesci.append(f"• {li_text}")
            elif element.name == 'blockquote':
                tresc_czesci.append(f"\n> {tekst}\n")
            else:
                # Paragraf - sprawdź czy to nie "Recommended reading"
                if tekst.startswith('Recommended reading:'):
                    # Zachowaj ale oznacz
                    tresc_czesci.append(f"\n*{tekst}*\n")
                else:
                    tresc_czesci.append(tekst)
        
        tresc = '\n\n'.join(tresc_czesci)
        tresc = wyczysc_tekst(tresc)
        
        return tytul, autor, data, tresc
        
    except Exception as e:
        return "Błąd", "", "", f"Nie udało się pobrać: {e}"

def main():
    print("=" * 60)
    print("SCRAPER BLOGA THE VISIBLE AUTHORITY")
    print("=" * 60)
    
    wszystkie_linki = []
    
    print("\n[1/3] Szukam artykułów...")
    
    # Strona główna bloga
    html = pobierz_strone(BLOG_URL)
    wszystkie_linki.extend(znajdz_linki_artykulow(html))
    print(f"  Strona 1 - znaleziono {len(wszystkie_linki)} artykułów")
    
    # Kolejne strony
    for numer_strony in range(2, 25):
        url_strony = f"{BLOG_URL}/page/{numer_strony}"
        try:
            html = pobierz_strone(url_strony)
            nowe_linki = znajdz_linki_artykulow(html)
            if not nowe_linki:
                print(f"  Strona {numer_strony} - brak artykułów, kończę szukanie")
                break
            wszystkie_linki.extend(nowe_linki)
            print(f"  Strona {numer_strony} - znaleziono {len(nowe_linki)} nowych")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Strona {numer_strony} - błąd: {e}")
            break
    
    # Usuwamy duplikaty zachowując kolejność
    unikalne_linki = []
    for link in wszystkie_linki:
        if link not in unikalne_linki:
            unikalne_linki.append(link)
    wszystkie_linki = unikalne_linki
    
    print(f"\n  RAZEM: {len(wszystkie_linki)} unikalnych artykułów")
    
    # Pobieramy treść
    print("\n[2/3] Pobieram pełną treść artykułów...")
    
    wyniki = []
    for i, link in enumerate(wszystkie_linki, 1):
        slug = link.split('/')[-1][:40]
        print(f"  [{i}/{len(wszystkie_linki)}] {slug}...")
        
        tytul, autor, data, tresc = pobierz_tresc_artykulu(link)
        
        wyniki.append({
            'url': link,
            'tytul': tytul,
            'autor': autor,
            'data': data,
            'tresc': tresc
        })
        
        status = f"OK - {len(tresc)} znaków" if len(tresc) > 500 else f"UWAGA - tylko {len(tresc)} znaków"
        print(f"       {status}")
        
        time.sleep(1)  # Pauza między requestami
    
    # Zapisujemy do pliku
    print("\n[3/3] Zapisuję do pliku...")
    
    with open('visible_authority_blog.md', 'w', encoding='utf-8') as f:
        f.write("# The Visible Authority - Pełna Baza Artykułów\n\n")
        f.write(f"**Pobrano:** {len(wyniki)} artykułów\n")
        f.write(f"**Źródło:** https://www.thevisibleauthority.com/blog\n\n")
        f.write("=" * 80 + "\n\n")
        
        for artykul in wyniki:
            f.write(f"# {artykul['tytul']}\n\n")
            if artykul['autor']:
                f.write(f"**Autor:** {artykul['autor']}\n")
            if artykul['data']:
                f.write(f"**Data:** {artykul['data']}\n")
            f.write(f"**Link:** {artykul['url']}\n\n")
            f.write("---\n\n")
            f.write(artykul['tresc'])
            f.write("\n\n" + "=" * 80 + "\n\n")
    
    # Statystyki
    total_chars = sum(len(a['tresc']) for a in wyniki)
    avg_chars = total_chars // len(wyniki) if wyniki else 0
    
    print("\n" + "=" * 60)
    print("GOTOWE!")
    print("=" * 60)
    print(f"Plik: visible_authority_blog.md")
    print(f"Artykułów: {len(wyniki)}")
    print(f"Łączna liczba znaków: {total_chars:,}")
    print(f"Średnia na artykuł: {avg_chars:,} znaków")
    print("=" * 60)

if __name__ == "__main__":
    main()
