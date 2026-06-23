# Coletor de Preços com Selenium

Script de automação que abre um site de livros, lê o título e o preço de cada livro e salva tudo num arquivo CSV. A ideia foi praticar automação de navegador (web scraping) com Selenium.

Usei o [books.toscrape.com](https://books.toscrape.com/), um site feito de propósito pra praticar scraping. Escolhi ele em vez de uma loja real porque é estável, não bloqueia robôs e é liberado pra esse uso, então o projeto sempre funciona quando alguém for testar.

## Como funciona

O Selenium abre um Chrome de verdade e controla ele pelo Python. O script:

- acessa o site;
- encontra todos os blocos de livro da página;
- pega o título e o preço de cada um;
- salva o resultado em `precos.csv`.

Tem uma pausa proposital entre cada item (com `time.sleep`) só pra dar pra acompanhar o processo no terminal enquanto roda.

## Como rodar

Precisa ter o Google Chrome instalado. Depois:

```bash
pip install selenium
python coletor_precos.py
```

O Chrome vai abrir sozinho, os livros aparecem um a um no terminal, e no final o script mostra o caminho completo onde o `precos.csv` foi salvo.

Na primeira execução o Selenium baixa o driver do Chrome automaticamente, então pode demorar uns segundos a mais.

## Possíveis próximos passos

- Percorrer todas as páginas do site (hoje pega só a primeira).
- Trocar o site alvo por outro.
- Agendar pra rodar sozinho de tempos em tempos.
