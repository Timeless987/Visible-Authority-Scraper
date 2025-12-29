import requests
from bs4 import BeautifulSoup
import time
import re

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
        if '/blog/' in href and href != '/blog' and 'page/' not in href and 'author/' not in href:
            pelny_link = href if href.startswith('http') else BASE_URL + href
            if pelny_link not in linki:
                linki.append(pelny_link)
    return linki

def pobierz_tresc_artykulu(url):
    try:
        html = pobierz_strone(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Tytuł - H1
        tytul_tag = soup.find('h1')
        tytul = tytul_tag.get_text(strip=True) if tytul_tag else "Brak tytulu"
        
        # Autor i data
        autor = ""
        data = ""
        
        # Szukamy autora (link z /author/)
        autor_link = soup.find('a', href=re.compile(r'/author/'))
        if autor_link:
            autor = autor_link.get_text(strip=True)
        
        # Usuwamy elementy których nie chcemy
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'iframe']):
            tag.decompose()
        
        # Usuwamy menu nawigacyjne
        for nav in soup.find_all(['nav', 'ul']):
            if nav.find('a', href='/about') or nav.find('a', href=re.compile(r'about')):
                nav.decompose()
        
        # Usuwamy sekcję "Further Reading"
        for heading in soup.find_all(['h2', 'h3']):
            if 'Further Reading' in heading.get_text():
                # Usuń wszystko od tego headinga do końca
                for sibling in heading.find_next_siblings():
                    sibling.decompose()
                heading.decompose()
                break
        
        # Usuwamy formularz newslettera i bio autora na końcu
        for div in soup.find_all('div'):
            text = div.get_text()
            if 'Subscribe to our newsletter' in text and len(text) < 500:
                div.decompose()
            if 'Share this article' in text and len(text) < 200:
                div.decompose()
        
        # Usuwamy sekcje z info o firmie (footer content)
        for div in soup.find_all('div'):
            text = div.get_text()
            if 'TVA & Partners BV' in text:
                div.decompose()
            if 'Jan Verbertlei 37' in text:
                div.decompose()
        
        # Szukamy głównej treści - wszystko między H1 a "Further Reading" lub footer
        tresc_czesci = []
        
        if tytul_tag:
            # Zbieramy tekst z paragrafów, nagłówków i list po H1
            for element in tytul_tag.find_all_next(['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote']):
                # Sprawdzamy czy to nie jest część footera lub menu
                parent_classes = ' '.join(element.parent.get('class', []))
                if 'footer' in parent_classes.lower() or 'menu' in parent_classes.lower():
                    continue
                
                tekst = element.get_text(strip=True)
                
                # Pomijamy krótkie elementy które wyglądają na nawigację
                if len(tekst) < 20 and element.name not in ['h2', 'h3', 'h4']:
                    continue
                
                # Pomijamy jeśli to menu
                if tekst in ['About us', 'Insights', 'Contact', 'About Us']:
                    continue
                
                # Pomijamy bio autora (zwykle na końcu)
                if "extensive career in the consulting" in tekst:
                    break
                
                # Pomijamy "Share this article"
                if tekst.startswith('Share this article'):
                    break
                    
                # Pomijamy "Further Reading"
                if 'Further Reading' in tekst:
                    break
                
                # Formatujemy nagłówki
                if element.name in ['h2', 'h3', 'h4']:
                    tresc_czesci.append(f"\n### {tekst}\n")
                elif element.name in ['ul', 'ol']:
                    # Formatujemy listy
                    for li in element.find_all('li'):
                        li_text = li.get_text(strip=True)
                        if li_text:
                            tresc_czesci.append(f"• {li_text}")
                elif element.name == 'blockquote':
                    tresc_czesci.append(f"\n> {tekst}\n")
                else:
                    tresc_czesci.append(tekst)
        
        tresc = '\n\n'.join(tresc_czesci)
        
        # Czyszczenie - usuwamy wielokrotne puste linie
        tresc = re.sub(r'\n{3,}', '\n\n', tresc)
        
        return tytul, autor, tresc
        
    except Exception as e:
        return "Blad", "", f"Nie udalo sie pobrac: {e}"

def main():
    print("=" * 60)
    print("SCRAPER BLOGA THE VISIBLE AUTHORITY - WERSJA 2.0")
    print("=" * 60)
    
    wszystkie_linki = []
    
    print("\n[1/3] Szukam artykulow...")
    
    # Strona główna bloga
    html = pobierz_strone(BLOG_URL)
    wszystkie_linki.extend(znajdz_linki_artykulow(html))
    print(f"  Strona 1 - znaleziono {len(wszystkie_linki)} artykulow")
    
    # Kolejne strony
    for numer_strony in range(2, 20):
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
    
    # Usuwamy duplikaty
    wszystkie_linki = list(set(wszystkie_linki))
    print(f"\n  RAZEM: {len(wszystkie_linki)} unikalnych artykulow")
    
    # Pobieramy treść
    print("\n[2/3] Pobieram pelna tresc artykulow...")
    
    wyniki = []
    for i, link in enumerate(wszystkie_linki, 1):
        print(f"  [{i}/{len(wszystkie_linki)}] Pobieram: {link.split('/')[-1][:50]}...")
        tytul, autor, tresc = pobierz_tresc_artykulu(link)
        
        # Sprawdzamy czy mamy treść
        if len(tresc) > 200:
            wyniki.append({
                'url': link,
                'tytul': tytul,
                'autor': autor,
                'tresc': tresc
            })
            print(f"             OK - {len(tresc)} znakow")
        else:
            print(f"             UWAGA - malo tresci ({len(tresc)} znakow)")
            wyniki.append({
                'url': link,
                'tytul': tytul,
                'autor': autor,
                'tresc': tresc if tresc else "Nie udalo sie pobrac tresci"
            })
        
        time.sleep(1)
    
    # Zapisujemy do pliku
    print("\n[3/3] Zapisuje do pliku...")
    
    with open('visible_authority_blog_FULL.md', 'w', encoding='utf-8') as f:
        f.write("# The Visible Authority - Pelna Baza Wiedzy\n\n")
        f.write(f"Pobrano {len(wyniki)} artykulow\n")
        f.write(f"Zrodlo: https://www.thevisibleauthority.com/blog\n\n")
        f.write("=" * 80 + "\n\n")
        
        for artykul in wyniki:
            f.write(f"## {artykul['tytul']}\n\n")
            if artykul['autor']:
                f.write(f"**Autor:** {artykul['autor']}\n")
            f.write(f"**Zrodlo:** {artykul['url']}\n\n")
            f.write("---\n\n")
            f.write(artykul['tresc'])
            f.write("\n\n" + "=" * 80 + "\n\n")
    
    # Statystyki
    total_chars = sum(len(a['tresc']) for a in wyniki)
    avg_chars = total_chars // len(wyniki) if wyniki else 0
    
    print("\n" + "=" * 60)
    print("GOTOWE!")
    print("=" * 60)
    print(f"Plik: visible_authority_blog_FULL.md")
    print(f"Artykulow: {len(wyniki)}")
    print(f"Laczna liczba znakow: {total_chars:,}")
    print(f"Srednia na artykul: {avg_chars:,} znakow")
    print("=" * 60)

if __name__ == "__main__":
    main()
