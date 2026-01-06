#!/bin/bash
# =============================================================================
# LOTOFÁCIL - Script Automatizado
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NUM_CONCURSOS=${1:-100}
OUTPUT_DIR="resultados_$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$OUTPUT_DIR/RELATORIO.md"

echo "=============================================================================="
echo "LOTOFÁCIL - AUTOMAÇÃO COMPLETA"
echo "=============================================================================="
echo "Concursos a analisar: $NUM_CONCURSOS"
echo ""

mkdir -p "$OUTPUT_DIR"

# ETAPA 1: Popular cache
echo "[1/5] Buscando sorteios..."
if [ ! -f "lotofacil_cache.json" ] || [ $(cat lotofacil_cache.json 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0) -lt "$NUM_CONCURSOS" ]; then
    python3 verificar_sorteios.py tickets_20_15_cov14_grasp.txt "$NUM_CONCURSOS" > /dev/null 2>&1 || true
fi

# ETAPA 2: Análise
echo "[2/5] Analisando estatísticas..."
python3 analisar_lotofacil.py "$NUM_CONCURSOS" > "$OUTPUT_DIR/analise_estatistica.txt" 2>&1

# ETAPA 3: Buscar universo
echo "[3/5] Buscando universo ideal..."
python3 buscar_universo_ideal.py "$NUM_CONCURSOS" > "$OUTPUT_DIR/busca_universo.txt" 2>&1

# Extrair universo
UNIVERSO=$(grep -A1 "Comando para gerar fechamento:" "$OUTPUT_DIR/busca_universo.txt" 2>/dev/null | tail -1 | grep -oP '(?<=--universe ")[^"]+' || echo "")
if [ -z "$UNIVERSO" ]; then
    UNIVERSO=$(grep -A1 "^Comando:$" "$OUTPUT_DIR/busca_universo.txt" 2>/dev/null | tail -1 | grep -oP '(?<=--universe ")[^"]+' || echo "1,2,3,4,5,7,8,9,10,11,13,14,15,17,18,19,20,21,23,25")
fi

# ETAPA 4: Gerar fechamento
echo "[4/5] Gerando fechamento..."
python3 fechamento_lotofacil.py --universe "$UNIVERSO" --out "$OUTPUT_DIR/tickets.txt" --verify > "$OUTPUT_DIR/fechamento.txt" 2>&1

# ETAPA 5: Simular
echo "[5/5] Simulando resultados..."
python3 verificar_sorteios.py "$OUTPUT_DIR/tickets.txt" "$NUM_CONCURSOS" > "$OUTPUT_DIR/simulacao.txt" 2>&1

# =============================================================================
# GERAR RELATÓRIO MARKDOWN
# =============================================================================
echo ""
echo "Gerando relatório..."

TOTAL_JOGOS=$(wc -l < "$OUTPUT_DIR/tickets.txt")
CUSTO_CONCURSO=$(echo "$TOTAL_JOGOS * 3.50" | bc)
CUSTO_TOTAL=$(echo "$CUSTO_CONCURSO * $NUM_CONCURSOS" | bc)

# Extrair estatísticas
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

# Universo formatado
UNIVERSO_ARRAY=(${UNIVERSO//,/ })
UNIVERSO_FORMATADO=""
for num in "${UNIVERSO_ARRAY[@]}"; do
    UNIVERSO_FORMATADO="$UNIVERSO_FORMATADO $(printf '%02d' $num)"
done

cat > "$REPORT_FILE" << EOF
# 🎯 Relatório Lotofácil

**Data:** $(date '+%d/%m/%Y %H:%M')  
**Concursos analisados:** $NUM_CONCURSOS

---

## 📊 Resumo Financeiro

| Métrica | Valor |
|---------|-------|
| 💰 Ganho Total | $GANHO_TOTAL |
| 💸 Custo Total | R$ $(printf "%'.2f" $CUSTO_TOTAL | sed 's/\./,/g; s/,/./g; s/\(.*\)\./\1,/') |
| 📈 Lucro/Prejuízo | $LUCRO |
| 🔄 Retorno | $RETORNO |
| 📊 Ganho Médio/Concurso | $GANHO_MEDIO |

---

## 🎲 Distribuição de Acertos

| Acertos | Ocorrências | Prêmio Unitário |
|---------|-------------|-----------------|
| 🏆 15 | $AC15 | R$ 2.000.000,00 |
| 🥇 14 | $AC14 | R$ 1.800,00 |
| 🥈 13 | $AC13 | R$ 30,00 |
| 🥉 12 | $AC12 | R$ 12,00 |
| ✓ 11 | $AC11 | R$ 6,00 |

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
| \`simulacao.txt\` | Resultado detalhado da simulação |
| \`analise_estatistica.txt\` | Análise de frequência e padrões |
| \`busca_universo.txt\` | Log da busca do universo ideal |

---

## 💡 Custo para Jogar

| Período | Custo |
|---------|-------|
| Por concurso | R$ $(printf "%'.2f" $CUSTO_CONCURSO | sed 's/\./,/g; s/,/./g; s/\(.*\)\./\1,/') |
| Por semana (~6 concursos) | R$ $(printf "%'.2f" $(echo "$CUSTO_CONCURSO * 6" | bc) | sed 's/\./,/g; s/,/./g; s/\(.*\)\./\1,/') |
| Por mês (~26 concursos) | R$ $(printf "%'.2f" $(echo "$CUSTO_CONCURSO * 26" | bc) | sed 's/\./,/g; s/,/./g; s/\(.*\)\./\1,/') |

---

*Gerado automaticamente por \`executar.sh\`*
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
echo ""

