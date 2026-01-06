# Lotofácil - Fechamento e Simulação

Scripts para gerar fechamentos da Lotofácil com garantia de 14 acertos e simular resultados.

## Scripts Disponíveis

| Script | Descrição |
|--------|-----------|
| `fechamento_lotofacil.py` | Gera jogos com garantia de 14 acertos |
| `verificar_sorteios.py` | Simula jogos contra sorteios reais |
| `analisar_lotofacil.py` | Análise estatística e sugestão de universos |
| `buscar_universo_ideal.py` | Busca universo ideal via algoritmo genético |
| `analise_risco.py` | **NOVO!** Métricas de risco (VaR, Sharpe, Drawdown) |
| `backtest.py` | **NOVO!** Simulação realista de capital |
| `comparar_universos.py` | **NOVO!** Ranking de múltiplos universos |
| `executar.sh` | Automação completa do fluxo |


---

## 0. Análise Estatística (NOVO!)

### Analisar todos os concursos em cache
```bash
python3 analisar_lotofacil.py
```

### Analisar apenas os últimos 50 concursos
```bash
python3 analisar_lotofacil.py 50
```

**Fornece:**
- Frequência de cada número
- Atrasos (concursos sem aparecer)
- Distribuição pares/ímpares
- Distribuição baixos/altos
- Soma das dezenas
- Sequências consecutivas
- Repetições entre concursos
- **3 universos sugeridos** (frequência, equilibrado, balanceado)
- Números quentes/frios
- Comandos prontos para usar

---


## 1. Gerar Fechamentos

### Universo de 20 números (padrão original)
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25" \
  --out tickets_20_numeros.txt \
  --verify
```
**Resultado esperado:** ~330 jogos

### Universo de 21 números
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,6,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25" \
  --out tickets_21_numeros.txt \
  --verify
```
**Resultado esperado:** ~1428 jogos

### Universo de 22 números
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,18,19,20,21,23,25" \
  --out tickets_22_numeros.txt \
  --verify
```
**Resultado esperado:** ~4000+ jogos

### Limitar quantidade de jogos
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25" \
  --max-games 200 \
  --out tickets_limitado.txt
```

---

## 2. Simular Resultados

### Simular últimos 10 concursos (padrão)
```bash
python3 verificar_sorteios.py tickets_20_numeros.txt
```

### Simular últimos 50 concursos
```bash
python3 verificar_sorteios.py tickets_20_numeros.txt 50
```

### Simular últimos 100 concursos
```bash
python3 verificar_sorteios.py tickets_20_numeros.txt 100
```

### Simular últimos 200 concursos
```bash
python3 verificar_sorteios.py tickets_20_numeros.txt 200
```

---

## 3. Comparar Diferentes Universos

### Testar universo de 20 números
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25" \
  --out test_20.txt
python3 verificar_sorteios.py test_20.txt 100
```

### Testar universo de 21 números
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,6,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25" \
  --out test_21.txt
python3 verificar_sorteios.py test_21.txt 100
```

---

## 4. Exemplos de Universos Personalizados

### Números baixos (1-15) + alguns altos
```bash
python3 fechamento_lotofacil.py \
  --universe "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,20,21,22,23,25" \
  --out universo_baixos.txt
```

### Números ímpares predominantes
```bash
python3 fechamento_lotofacil.py \
  --universe "1,3,5,7,9,11,13,15,17,19,21,23,25,2,4,6,8,10,12,14" \
  --out universo_impares.txt
```

### Baseado em frequência histórica
```bash
# Pesquise os 20 números mais frequentes e use-os
python3 fechamento_lotofacil.py \
  --universe "SEUS_20_NUMEROS_AQUI" \
  --out universo_frequentes.txt
```

---

## 5. Análise Rápida

### Ver informações de um fechamento
```bash
head -5 tickets_20_numeros.txt   # Primeiros 5 jogos
wc -l tickets_20_numeros.txt     # Total de jogos
```

### Calcular custo
```bash
# Custo = quantidade_jogos * R$ 3,50
echo "Custo por concurso: R$ $(echo "$(wc -l < tickets_20_numeros.txt) * 3.50" | bc)"
```

---

## 6. Cache de Sorteios

Os resultados dos sorteios são salvos em `lotofacil_cache.json` para evitar requisições repetidas à API.

### Limpar cache (forçar busca nova)
```bash
rm lotofacil_cache.json
```

### Ver conteúdo do cache
```bash
cat lotofacil_cache.json | python3 -m json.tool | head -50
```

---

## Tabela de Prêmios (Referência)

| Acertos | Prêmio Típico |
|---------|---------------|
| 11 | R$ 6,00 |
| 12 | R$ 12,00 |
| 13 | R$ 30,00 |
| 14 | R$ 1.800,00 |
| 15 | R$ 2.000.000,00+ |

---

## Resumo de Custos por Universo

| Universo | Jogos | Custo/Concurso |
|----------|-------|----------------|
| 20 números | ~330 | R$ 1.155,00 |
| 21 números | ~1.428 | R$ 4.998,00 |
| 22 números | ~4.000+ | R$ 14.000,00+ |

---

## Dicas

1. **Universo menor = menos jogos = menor custo**, mas menor cobertura
2. **Simule com muitos concursos** (100+) para ter uma média mais realista
3. **O retorno típico é ~25-35%** do investimento (prejuízo esperado)
4. **Use o cache** para acelerar simulações repetidas
