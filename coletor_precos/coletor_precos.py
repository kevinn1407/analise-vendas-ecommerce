import csv
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By

PAUSA = 1

navegador = webdriver.Chrome()

navegador.get("https://books.toscrape.com/")
time.sleep(2)

livros = navegador.find_elements(By.CLASS_NAME, "product_pod")

dados = []
for livro in livros:
    titulo = livro.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("title")
    preco = livro.find_element(By.CLASS_NAME, "price_color").text
    dados.append([titulo, preco])
    print(titulo, "-", preco)
    time.sleep(2)

with open("precos.csv", "w", newline="", encoding="utf-8") as arquivo:
    escritor = csv.writer(arquivo)
    escritor.writerow(["titulo", "preco"])
    escritor.writerows(dados)

print(f"\nPronto! {len(dados)} livros salvos.")
print(f"Arquivo salvo em: {Path('precos.csv').resolve()}")

navegador.quit()