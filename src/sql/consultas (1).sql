-- Consultas do projeto de analise de vendas
-- Banco: vendas.db (gerado pelo carregar_sqlite.py)


-- faturamento por mes
SELECT
    c.ano_mes,
    ROUND(SUM(f.valor_liquido), 2) AS faturamento
FROM fato_vendas f
JOIN dim_calendario c ON f.data_pedido = c.data
GROUP BY c.ano_mes
ORDER BY c.ano_mes;


-- top 10 produtos por faturamento
SELECT
    p.titulo,
    p.categoria,
    ROUND(SUM(f.valor_liquido), 2) AS faturamento,
    SUM(f.quantidade)              AS unidades
FROM fato_vendas f
JOIN dim_produtos p ON f.produto_id = p.produto_id
GROUP BY p.produto_id, p.titulo, p.categoria
ORDER BY faturamento DESC
LIMIT 10;


-- quanto cada categoria pesa no total
-- (o SUM(...) OVER () pega o total geral sem precisar de subquery)
SELECT
    p.categoria,
    ROUND(SUM(f.valor_liquido), 2) AS faturamento,
    ROUND(
        100.0 * SUM(f.valor_liquido) / SUM(SUM(f.valor_liquido)) OVER (),
        2
    ) AS pct_do_total
FROM fato_vendas f
JOIN dim_produtos p ON f.produto_id = p.produto_id
GROUP BY p.categoria
ORDER BY faturamento DESC;


-- ranking dos produtos dentro de cada categoria
WITH vendas_produto AS (
    SELECT
        p.categoria,
        p.titulo,
        SUM(f.valor_liquido) AS faturamento
    FROM fato_vendas f
    JOIN dim_produtos p ON f.produto_id = p.produto_id
    GROUP BY p.produto_id, p.categoria, p.titulo
)
SELECT
    categoria,
    titulo,
    ROUND(faturamento, 2) AS faturamento,
    RANK() OVER (PARTITION BY categoria ORDER BY faturamento DESC) AS posicao
FROM vendas_produto
ORDER BY categoria, posicao;


-- media movel de 3 meses do faturamento
WITH fat_mes AS (
    SELECT
        c.ano_mes,
        SUM(f.valor_liquido) AS faturamento
    FROM fato_vendas f
    JOIN dim_calendario c ON f.data_pedido = c.data
    GROUP BY c.ano_mes
)
SELECT
    ano_mes,
    ROUND(faturamento, 2) AS faturamento,
    ROUND(
        AVG(faturamento) OVER (
            ORDER BY ano_mes
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS media_movel_3m
FROM fat_mes
ORDER BY ano_mes;


-- ticket medio por faixa etaria
SELECT
    cl.faixa_etaria,
    COUNT(DISTINCT f.pedido_id) AS pedidos,
    ROUND(SUM(f.valor_liquido) * 1.0 / COUNT(DISTINCT f.pedido_id), 2)
        AS ticket_medio
FROM fato_vendas f
JOIN dim_clientes cl ON f.cliente_id = cl.cliente_id
GROUP BY cl.faixa_etaria
ORDER BY ticket_medio DESC;


-- pedidos apontando pra cliente que nao existe (checagem de integridade)
SELECT
    f.pedido_id,
    f.cliente_id,
    ROUND(SUM(f.valor_liquido), 2) AS valor_pedido
FROM fato_vendas f
LEFT JOIN dim_clientes cl ON f.cliente_id = cl.cliente_id
WHERE cl.cliente_id IS NULL
GROUP BY f.pedido_id, f.cliente_id
ORDER BY valor_pedido DESC;
