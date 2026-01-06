#!/bin/bash
# =============================================================================
# LOTOFÁCIL - Script Automatizado Completo
# =============================================================================

set -e
export LC_NUMERIC=C  # Fix printf locale issues

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NUM_CONCURSOS=${1:-100}
CAPITAL=${2:-10000}
OUTPUT_DIR="resultados_$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$OUTPUT_DIR/RELATORIO.md"

echo "=============================================================================="
echo "LOTOFÁCIL - AUTOMAÇÃO COMPLETA"
echo "=============================================================================="
echo "Concursos a analisar: $NUM_CONCURSOS"
echo "Capital para backtest: R$ $CAPITAL"
echo ""

mkdir -p "$OUTPUT_DIR"

# ETAPA 1: Popular cache
echo "[1/8] Buscando sorteios..."
if [ ! -f "lotofacil_cache.json" ] || [ $(cat lotofacil_cache.json 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0) -lt "$NUM_CONCURSOS" ]; then
    python3 verificar_sorteios.py tickets_20_15_cov14_grasp.txt "$NUM_CONCURSOS" > /dev/null 2>&1 || true
fi

# ETAPA 2: Análise estatística
echo "[2/8] Analisando estatísticas..."
python3 analisar_lotofacil.py "$NUM_CONCURSOS" > "$OUTPUT_DIR/analise_estatistica.txt" 2>&1

# ETAPA 3: Comparar universos
echo "[3/8] Comparando universos..."
python3 comparar_universos.py 5 "$NUM_CONCURSOS" > "$OUTPUT_DIR/comparar_universos.txt" 2>&1

# ETAPA 4: Buscar universo ideal
echo "[4/8] Buscando universo ideal..."
python3 buscar_universo_ideal.py "$NUM_CONCURSOS" > "$OUTPUT_DIR/busca_universo.txt" 2>&1

# Extrair universo
UNIVERSO=$(grep -A1 "Comando para gerar fechamento:" "$OUTPUT_DIR/busca_universo.txt" 2>/dev/null | tail -1 | grep -oP '(?<=--universe ")[^"]+' || echo "")
if [ -z "$UNIVERSO" ]; then
    UNIVERSO=$(grep -A1 "^Comando:$" "$OUTPUT_DIR/busca_universo.txt" 2>/dev/null | tail -1 | grep -oP '(?<=--universe ")[^"]+' || echo "1,2,3,4,5,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25")
fi

# ETAPA 5: Gerar fechamento
echo "[5/8] Gerando fechamento..."
python3 fechamento_lotofacil.py --universe "$UNIVERSO" --out "$OUTPUT_DIR/tickets.txt" --verify > "$OUTPUT_DIR/fechamento.txt" 2>&1

# ETAPA 6: Simular resultados
echo "[6/8] Simulando resultados..."
python3 verificar_sorteios.py "$OUTPUT_DIR/tickets.txt" "$NUM_CONCURSOS" > "$OUTPUT_DIR/simulacao.txt" 2>&1

# ETAPA 7: Análise de risco
echo "[7/8] Calculando métricas de risco..."
python3 analise_risco.py "$OUTPUT_DIR/tickets.txt" "$NUM_CONCURSOS" > "$OUTPUT_DIR/analise_risco.txt" 2>&1

# ETAPA 8: Backtest
echo "[8/8] Executando backtest..."
python3 backtest.py "$OUTPUT_DIR/tickets.txt" "$CAPITAL" "$NUM_CONCURSOS" > "$OUTPUT_DIR/backtest.txt" 2>&1

# =============================================================================
# GERAR RELATÓRIO MARKDOWN
# =============================================================================
echo ""
echo "Gerando relatório..."

TOTAL_JOGOS=$(wc -l < "$OUTPUT_DIR/tickets.txt")
CUSTO_CONCURSO=$(echo "$TOTAL_JOGOS * 3.50" | bc)
CUSTO_TOTAL=$(echo "$CUSTO_CONCURSO * $NUM_CONCURSOS" | bc)

# Extrair estatísticas da simulação
GANHO_TOTAL=$(grep "TOTAL DE GANHOS:" "$OUTPUT_DIR/simulacao.txt" | grep -oP 'R\$ [\d.,]+' | head -1 || echo "R$ 0,00")
LUCRO=$(grep "LUCRO/PREJUÍZO:" "$OUTPUT_DIR/simulacao.txt" | grep -oP 'R\$ -?[\d.,]+' | head -1 || echo "R$ 0,00")
RETORNO=$(grep "Retorno sobre investimento:" "$OUTPUT_DIR/simulacao.txt" | grep -oP '[\d.,]+%' | head -1 || echo "0%")
GANHO_MEDIO=$(grep "Ganho médio por concurso:" "$OUTPUT_DIR/simulacao.txt" | grep -oP 'R\$ [\d.,]+' | head -1 || echo "R$ 0,00")

# Extrair acertos
AC15=$(grep "^15 " "$OUTPUT_DIR/simulacao.txt" | awk '{print $2}' || echo "0")
AC14=$(grep "^14 " "$OUTPUT_DIR/simulacao.txt" | awk '{print $2}' || echo "0")
AC13=$(grep "^13 " "$OUTPUT_DIR/simulacao.txt" | awk '{print $2}' || echo "0")
AC12=$(grep "^12 " "$OUTPUT_DIR/simulacao.txt" | awk '{print $2}' || echo "0")
AC11=$(grep "^11 " "$OUTPUT_DIR/simulacao.txt" | awk '{print $2}' || echo "0")

# Extrair métricas de risco
PROB_PREJUIZO=$(grep "Por concurso:" "$OUTPUT_DIR/analise_risco.txt" | grep -oP '[\d.]+%' | head -1 || echo "N/A")
DRAWDOWN=$(grep "Máximo:" "$OUTPUT_DIR/analise_risco.txt" | grep -oP 'R\$ [\d.,]+' | head -1 || echo "N/A")
SHARPE=$(grep "Valor:" "$OUTPUT_DIR/analise_risco.txt" | head -1 | grep -oP '[\d.]+' | head -1 || echo "N/A")
SEQ_PREJUIZO=$(grep "Maior sequência de prejuízo:" "$OUTPUT_DIR/analise_risco.txt" | grep -oP '\d+' || echo "N/A")

# Extrair backtest
PATRIMONIO_FINAL=$(grep "Valor:" "$OUTPUT_DIR/backtest.txt" | head -1 | grep -oP 'R\$ [\d.,]+' || echo "N/A")
ROI_BACKTEST=$(grep "ROI:" "$OUTPUT_DIR/backtest.txt" | grep -oP '-?[\d.]+%' | head -1 || echo "N/A")

# Universo formatado
UNIVERSO_ARRAY=(${UNIVERSO//,/ })
UNIVERSO_FORMATADO=""
for num in "${UNIVERSO_ARRAY[@]}"; do
    UNIVERSO_FORMATADO="$UNIVERSO_FORMATADO $(printf '%02d' $num)"
done

# Formatar números em BR
fmt_br() {
    printf "%.2f" $1 | sed 's/\./,/'
}

cat > "$REPORT_FILE" << EOF
# 🎯 Relatório Lotofácil

**Data:** $(date '+%d/%m/%Y %H:%M')  
**Concursos analisados:** $NUM_CONCURSOS

---

## 📊 Resumo Financeiro

| Métrica | Valor |
|---------|-------|
| 💰 Ganho Total | $GANHO_TOTAL |
| 💸 Custo Total | R\$ $(fmt_br $CUSTO_TOTAL) |
| 📈 Lucro/Prejuízo | $LUCRO |
| 🔄 Retorno | $RETORNO |
| 📊 Ganho Médio/Concurso | $GANHO_MEDIO |

---

## 🎲 Distribuição de Acertos

| Acertos | Ocorrências | Prêmio Unitário |
|---------|-------------|-----------------|
| 🏆 15 | $AC15 | R\$ 2.000.000,00 |
| 🥇 14 | $AC14 | R\$ 1.800,00 |
| 🥈 13 | $AC13 | R\$ 30,00 |
| 🥉 12 | $AC12 | R\$ 12,00 |
| ✓ 11 | $AC11 | R\$ 6,00 |

---

## ⚠️ Análise de Risco

| Métrica | Valor |
|---------|-------|
| Probabilidade de prejuízo | $PROB_PREJUIZO |
| Drawdown máximo | $DRAWDOWN |
| Sharpe Ratio | $SHARPE |
| Maior sequência de prejuízo | $SEQ_PREJUIZO concursos |

---

## 💼 Backtest (Capital: R\$ $(fmt_br $CAPITAL))

| Métrica | Valor |
|---------|-------|
| Capital inicial | R\$ $(fmt_br $CAPITAL) |
| Patrimônio final | $PATRIMONIO_FINAL |
| ROI | $ROI_BACKTEST |

---

## 🎯 Universo Utilizado

**20 números:**
\`\`\`
$UNIVERSO_FORMATADO
\`\`\`

**Comando:**
\`\`\`bash
python3 fechamento_lotofacil.py --universe "$UNIVERSO" --out tickets.txt
\`\`\`

---

## 📁 Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| \`tickets.txt\` | $TOTAL_JOGOS jogos para apostar |
| \`simulacao.txt\` | Resultado da simulação |
| \`analise_risco.txt\` | Métricas de risco |
| \`backtest.txt\` | Simulação de capital |
| \`comparar_universos.txt\` | Ranking de universos |
| \`analise_estatistica.txt\` | Frequência e padrões |

---

## 💡 Custo para Jogar

| Período | Custo |
|---------|-------|
| Por concurso | R\$ $(fmt_br $CUSTO_CONCURSO) |
| Por semana (~6) | R\$ $(fmt_br $(echo "$CUSTO_CONCURSO * 6" | bc)) |
| Por mês (~26) | R\$ $(fmt_br $(echo "$CUSTO_CONCURSO * 26" | bc)) |

---

*Gerado por \`./executar.sh $NUM_CONCURSOS $CAPITAL\`*
EOF

echo ""
echo "=============================================================================="
echo "✅ CONCLUÍDO!"
echo "=============================================================================="
echo ""
echo "📁 Arquivos em: $OUTPUT_DIR/"
echo "📄 Relatório:   $REPORT_FILE"
echo "🎫 Jogos:       $OUTPUT_DIR/tickets.txt ($TOTAL_JOGOS jogos)"
echo ""
echo "📊 Resumo: $GANHO_TOTAL de ganho | $LUCRO de lucro | $RETORNO retorno"
echo "⚠️  Risco: $PROB_PREJUIZO prob. prejuízo | Drawdown: $DRAWDOWN"
echo ""


