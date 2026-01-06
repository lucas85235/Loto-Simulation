#!/usr/bin/env python3
"""
Análise de Risco para apostas na Lotofácil.
Calcula métricas de risco como probabilidade de prejuízo, drawdown, VaR, etc.
"""

import json
import os
import math
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter
import re

CACHE_FILE = os.path.join(os.path.dirname(__file__), "lotofacil_cache.json")
CUSTO_JOGO = 3.50

# Valores médios típicos (baseados em histórico real)
PREMIOS = {
    11: 6.00,        # Fixo
    12: 12.00,       # Fixo
    13: 30.00,       # Fixo
    14: 1400.00,     # Média histórica ~R$ 1.400
    15: 1200000.00   # Média histórica ~R$ 1.200.000 (geralmente rateado)
}



@dataclass
class Sorteio:
    numero: int
    data: str
    dezenas: set
    premios: Dict[int, float]


def carregar_cache() -> Dict[int, Sorteio]:
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, 'r') as f:
        data = json.load(f)
    sorteios = {}
    for k, v in data.items():
        premios = {int(pk): pv for pk, pv in v.get("premios", {}).items()}
        if not premios:
            premios = PREMIOS.copy()
        sorteios[int(k)] = Sorteio(
            numero=v["numero"],
            data=v["data"],
            dezenas=set(v["dezenas"]),
            premios=premios
        )
    return sorteios


def carregar_jogos(arquivo: str) -> List[set]:
    jogos = []
    with open(arquivo, 'r') as f:
        for linha in f:
            match = re.match(r'Jogo\s+\d+:\s*(.+)', linha.strip())
            if match:
                numeros = [int(n.strip()) for n in match.group(1).split(',')]
                jogos.append(set(numeros))
    return jogos


def calcular_ganhos_por_concurso(jogos: List[set], sorteios: Dict[int, Sorteio]) -> Dict[int, float]:
    """Retorna o ganho total em cada concurso."""
    ganhos = {}
    for num, sorteio in sorteios.items():
        ganho_concurso = 0.0
        for jogo in jogos:
            acertos = len(jogo & sorteio.dezenas)
            if acertos >= 11:
                premio = sorteio.premios.get(acertos, PREMIOS.get(acertos, 0))
                ganho_concurso += premio
        ganhos[num] = ganho_concurso
    return ganhos


def calcular_lucros_por_concurso(ganhos: Dict[int, float], custo_por_concurso: float) -> Dict[int, float]:
    """Retorna o lucro (ganho - custo) por concurso."""
    return {num: ganho - custo_por_concurso for num, ganho in ganhos.items()}


def calcular_drawdown(lucros: List[float]) -> Tuple[float, int]:
    """Calcula o drawdown máximo (maior sequência de prejuízo acumulado)."""
    if not lucros:
        return 0.0, 0
    
    pico = 0.0
    patrimonio = 0.0
    max_drawdown = 0.0
    drawdown_concursos = 0
    current_dd_concursos = 0
    
    for lucro in lucros:
        patrimonio += lucro
        if patrimonio > pico:
            pico = patrimonio
            current_dd_concursos = 0
        
        drawdown = pico - patrimonio
        if drawdown > 0:
            current_dd_concursos += 1
        
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            drawdown_concursos = current_dd_concursos
    
    return max_drawdown, drawdown_concursos


def calcular_var(lucros: List[float], percentil: float = 5) -> float:
    """Calcula o Value at Risk (pior perda esperada no percentil dado)."""
    if not lucros:
        return 0.0
    ordenados = sorted(lucros)
    idx = int(len(ordenados) * percentil / 100)
    return ordenados[idx]


def calcular_sharpe_ratio(lucros: List[float]) -> float:
    """Calcula uma versão adaptada do Sharpe Ratio."""
    if len(lucros) < 2:
        return 0.0
    
    media = sum(lucros) / len(lucros)
    variancia = sum((l - media) ** 2 for l in lucros) / len(lucros)
    desvio = math.sqrt(variancia)
    
    if desvio == 0:
        return 0.0
    
    return media / desvio


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def main():
    import sys
    
    arquivo_jogos = sys.argv[1] if len(sys.argv) > 1 else "tickets.txt"
    num_concursos = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    print("=" * 80)
    print("ANÁLISE DE RISCO - LOTOFÁCIL")
    print("=" * 80)
    
    # Carregar dados
    jogos = carregar_jogos(arquivo_jogos)
    if not jogos:
        print(f"Erro: Nenhum jogo encontrado em {arquivo_jogos}")
        return
    
    cache = carregar_cache()
    if not cache:
        print("Erro: Cache vazio. Execute verificar_sorteios.py primeiro.")
        return
    
    # Limitar concursos
    numeros = sorted(cache.keys(), reverse=True)[:num_concursos]
    sorteios = {n: cache[n] for n in numeros}
    
    print(f"\nJogos analisados: {len(jogos)}")
    print(f"Concursos analisados: {len(sorteios)}")
    
    # Calcular custos e ganhos
    custo_por_concurso = len(jogos) * CUSTO_JOGO
    ganhos = calcular_ganhos_por_concurso(jogos, sorteios)
    lucros = calcular_lucros_por_concurso(ganhos, custo_por_concurso)
    
    # Lista ordenada de lucros
    lucros_lista = [lucros[n] for n in sorted(lucros.keys())]
    
    # Métricas básicas
    total_ganhos = sum(ganhos.values())
    total_custo = custo_por_concurso * len(sorteios)
    total_lucro = total_ganhos - total_custo
    
    # Estatísticas de lucro por concurso
    media_lucro = sum(lucros_lista) / len(lucros_lista)
    variancia = sum((l - media_lucro) ** 2 for l in lucros_lista) / len(lucros_lista)
    desvio_padrao = math.sqrt(variancia)
    
    # Probabilidade de prejuízo
    concursos_prejuizo = sum(1 for l in lucros_lista if l < 0)
    prob_prejuizo = (concursos_prejuizo / len(lucros_lista)) * 100
    
    # Melhor e pior concurso
    melhor_concurso = max(lucros.items(), key=lambda x: x[1])
    pior_concurso = min(lucros.items(), key=lambda x: x[1])
    
    # Drawdown
    max_drawdown, dd_concursos = calcular_drawdown(lucros_lista)
    
    # VaR
    var_5 = calcular_var(lucros_lista, 5)
    var_1 = calcular_var(lucros_lista, 1)
    
    # Sharpe Ratio
    sharpe = calcular_sharpe_ratio(lucros_lista)
    
    # Sequências
    sequencia_prejuizo = 0
    max_sequencia_prejuizo = 0
    sequencia_lucro = 0
    max_sequencia_lucro = 0
    
    for l in lucros_lista:
        if l < 0:
            sequencia_prejuizo += 1
            max_sequencia_prejuizo = max(max_sequencia_prejuizo, sequencia_prejuizo)
            sequencia_lucro = 0
        else:
            sequencia_lucro += 1
            max_sequencia_lucro = max(max_sequencia_lucro, sequencia_lucro)
            sequencia_prejuizo = 0
    
    # Resultados
    print("\n" + "=" * 80)
    print("RESUMO FINANCEIRO")
    print("=" * 80)
    print(f"\nCusto por concurso: {formatar_moeda(custo_por_concurso)}")
    print(f"Custo total ({len(sorteios)} concursos): {formatar_moeda(total_custo)}")
    print(f"Ganho total: {formatar_moeda(total_ganhos)}")
    print(f"Lucro total: {formatar_moeda(total_lucro)}")
    
    print("\n" + "=" * 80)
    print("MÉTRICAS DE RISCO")
    print("=" * 80)
    
    print(f"\n📊 ESTATÍSTICAS POR CONCURSO:")
    print(f"   Lucro médio: {formatar_moeda(media_lucro)}")
    print(f"   Desvio padrão: {formatar_moeda(desvio_padrao)}")
    print(f"   Coef. de variação: {(desvio_padrao/abs(media_lucro)*100) if media_lucro != 0 else 0:.1f}%")
    
    print(f"\n⚠️  PROBABILIDADE DE PREJUÍZO:")
    print(f"   Por concurso: {prob_prejuizo:.1f}% ({concursos_prejuizo}/{len(lucros_lista)})")
    
    print(f"\n📉 DRAWDOWN:")
    print(f"   Máximo: {formatar_moeda(max_drawdown)}")
    print(f"   Duração: {dd_concursos} concursos")
    
    print(f"\n🎲 VALUE AT RISK (VaR):")
    print(f"   VaR 5%: {formatar_moeda(var_5)} (95% dos concursos: lucro > este valor)")
    print(f"   VaR 1%: {formatar_moeda(var_1)} (99% dos concursos: lucro > este valor)")
    
    print(f"\n📈 SHARPE RATIO:")
    print(f"   Valor: {sharpe:.3f}")
    if sharpe > 1:
        print("   Interpretação: Excelente relação retorno/risco")
    elif sharpe > 0.5:
        print("   Interpretação: Bom retorno ajustado ao risco")
    elif sharpe > 0:
        print("   Interpretação: Retorno positivo, risco moderado")
    else:
        print("   Interpretação: Risco supera o retorno esperado")
    
    print(f"\n🏆 EXTREMOS:")
    print(f"   Melhor concurso: {melhor_concurso[0]} ({formatar_moeda(melhor_concurso[1])})")
    print(f"   Pior concurso: {pior_concurso[0]} ({formatar_moeda(pior_concurso[1])})")
    
    print(f"\n🔄 SEQUÊNCIAS:")
    print(f"   Maior sequência de prejuízo: {max_sequencia_prejuizo} concursos")
    print(f"   Maior sequência de lucro: {max_sequencia_lucro} concursos")
    
    # Simulação de cenários
    print("\n" + "=" * 80)
    print("SIMULAÇÃO DE CENÁRIOS")
    print("=" * 80)
    
    meses = [1, 3, 6, 12]
    concursos_por_mes = 26  # ~6 por semana
    
    print("\nProjeção baseada nos dados históricos:")
    print("-" * 60)
    print(f"{'Período':<15} {'Custo':<18} {'Ganho Médio':<18} {'Lucro Médio':<18}")
    print("-" * 60)
    
    for m in meses:
        n_conc = m * concursos_por_mes
        custo_periodo = custo_por_concurso * n_conc
        ganho_periodo = (total_ganhos / len(sorteios)) * n_conc
        lucro_periodo = ganho_periodo - custo_periodo
        
        periodo = f"{m} mês" if m == 1 else f"{m} meses"
        print(f"{periodo:<15} {formatar_moeda(custo_periodo):<18} {formatar_moeda(ganho_periodo):<18} {formatar_moeda(lucro_periodo):<18}")
    
    print("-" * 60)
    
    # Resumo final
    print("\n" + "=" * 80)
    print("CONCLUSÃO")
    print("=" * 80)
    
    if total_lucro > 0:
        print(f"\n✅ Resultado POSITIVO no período analisado.")
        print(f"   Para cada R$ 1 investido, retornou R$ {(total_ganhos/total_custo):.2f}")
    else:
        print(f"\n❌ Resultado NEGATIVO no período analisado.")
        print(f"   Para cada R$ 1 investido, retornou R$ {(total_ganhos/total_custo):.2f}")
    
    print(f"\n⚠️  AVISO: {prob_prejuizo:.0f}% dos concursos resultam em prejuízo.")
    print(f"   Prepare-se para sequências de até {max_sequencia_prejuizo} concursos no vermelho.")


if __name__ == "__main__":
    main()
