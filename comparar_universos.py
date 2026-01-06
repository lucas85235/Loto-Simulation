#!/usr/bin/env python3
"""
Comparador de Múltiplos Universos para Lotofácil.
Testa vários universos em paralelo e faz ranking de desempenho.
"""

import json
import os
import random
import itertools
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed

CACHE_FILE = os.path.join(os.path.dirname(__file__), "lotofacil_cache.json")
CUSTO_JOGO = 3.50

PREMIOS = {
    11: 6.00,
    12: 12.00,
    13: 30.00,
    14: 1800.00,
    15: 2000000.00
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


def gerar_universo_aleatorio(tamanho: int = 20) -> Set[int]:
    """Gera um universo aleatório de N números."""
    return set(random.sample(range(1, 26), tamanho))


def gerar_universo_baseado_frequencia(sorteios: Dict[int, Sorteio], tamanho: int = 20) -> Set[int]:
    """Gera universo baseado nos números mais frequentes."""
    freq = {}
    for s in sorteios.values():
        for d in s.dezenas:
            freq[d] = freq.get(d, 0) + 1
    
    ordenados = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return set(num for num, _ in ordenados[:tamanho])


def gerar_universo_balanceado() -> Set[int]:
    """Gera universo com distribuição equilibrada de baixos/altos e pares/ímpares."""
    baixos = list(range(1, 13))  # 1-12
    altos = list(range(13, 26))  # 13-25
    
    # 8 baixos, 12 altos
    universo = set(random.sample(baixos, 8) + random.sample(altos, 12))
    return universo


def gerar_universos_candidatos(sorteios: Dict[int, Sorteio], quantidade: int = 10) -> List[Set[int]]:
    """Gera lista de universos candidatos para testar."""
    universos = []
    
    # 1. Baseado em frequência
    universos.append(gerar_universo_baseado_frequencia(sorteios, 20))
    
    # 2-4. Baseados em sorteios recentes
    numeros_recentes = sorted(sorteios.keys(), reverse=True)[:5]
    for num in numeros_recentes[:3]:
        sorteio = sorteios[num]
        # Adiciona 5 números mais frequentes fora do sorteio
        freq_universo = gerar_universo_baseado_frequencia(sorteios, 25)
        extras = freq_universo - sorteio.dezenas
        universo = sorteio.dezenas | set(list(extras)[:5])
        universos.append(universo)
    
    # 5+. Aleatórios e balanceados
    while len(universos) < quantidade:
        if random.random() < 0.5:
            universos.append(gerar_universo_balanceado())
        else:
            universos.append(gerar_universo_aleatorio(20))
    
    return universos[:quantidade]


def calcular_fechamento_size(universo: Set[int]) -> int:
    """Estima o número de jogos necessários para um universo."""
    n = len(universo)
    k = n - 15  # Complemento
    
    # Estimativa baseada na fórmula do set cover
    # C(n, k) / (1 + k*(n-k))
    from math import comb
    total_complements = comb(n, k)
    coverage_per_game = 1 + k * (n - k)
    
    # Greedy consegue aproximadamente ln(n) vezes o ótimo
    estimated = int(total_complements / coverage_per_game * 1.5)
    return estimated


def avaliar_universo(universo: Set[int], sorteios: Dict[int, Sorteio]) -> Dict:
    """Avalia o desempenho de um universo contra os sorteios."""
    resultados = {
        "universo": sorted(universo),
        "tamanho": len(universo),
        "jogos_estimados": calcular_fechamento_size(universo),
        "max_acertos": 0,
        "count_15": 0,
        "count_14": 0,
        "count_13": 0,
        "count_12": 0,
        "count_11": 0,
        "total_acertos": 0,
        "ganho_potencial": 0.0,
    }
    
    custo_estimado = resultados["jogos_estimados"] * CUSTO_JOGO
    
    for sorteio in sorteios.values():
        acertos = len(universo & sorteio.dezenas)
        resultados["total_acertos"] += acertos
        resultados["max_acertos"] = max(resultados["max_acertos"], acertos)
        
        if acertos == 15:
            resultados["count_15"] += 1
            resultados["ganho_potencial"] += sorteio.premios.get(15, PREMIOS[15])
        elif acertos == 14:
            resultados["count_14"] += 1
            resultados["ganho_potencial"] += sorteio.premios.get(14, PREMIOS[14])
        elif acertos == 13:
            resultados["count_13"] += 1
            resultados["ganho_potencial"] += sorteio.premios.get(13, PREMIOS[13])
        elif acertos == 12:
            resultados["count_12"] += 1
            resultados["ganho_potencial"] += sorteio.premios.get(12, PREMIOS[12])
        elif acertos == 11:
            resultados["count_11"] += 1
            resultados["ganho_potencial"] += sorteio.premios.get(11, PREMIOS[11])
    
    resultados["custo_estimado_por_concurso"] = custo_estimado
    resultados["custo_total_estimado"] = custo_estimado * len(sorteios)
    resultados["lucro_potencial"] = resultados["ganho_potencial"] - resultados["custo_total_estimado"]
    resultados["roi"] = (resultados["ganho_potencial"] / resultados["custo_total_estimado"] * 100) if resultados["custo_total_estimado"] > 0 else 0
    
    # Score composto
    resultados["score"] = (
        resultados["count_15"] * 10000 +
        resultados["count_14"] * 100 +
        resultados["count_13"] * 10 +
        resultados["count_12"] * 1 +
        resultados["roi"]
    )
    
    return resultados


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def main():
    import sys
    
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    num_concursos = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    print("=" * 80)
    print("COMPARADOR DE MÚLTIPLOS UNIVERSOS - LOTOFÁCIL")
    print("=" * 80)
    
    cache = carregar_cache()
    if not cache:
        print("Erro: Cache vazio. Execute verificar_sorteios.py primeiro.")
        return
    
    # Limitar concursos
    numeros = sorted(cache.keys(), reverse=True)[:num_concursos]
    sorteios = {n: cache[n] for n in numeros}
    
    print(f"\nConcursos analisados: {len(sorteios)}")
    print(f"Universos a testar: {quantidade}")
    
    # Gerar universos
    print("\nGerando universos candidatos...")
    universos = gerar_universos_candidatos(sorteios, quantidade)
    
    # Avaliar cada universo
    print("Avaliando universos...")
    resultados = []
    
    for i, universo in enumerate(universos):
        resultado = avaliar_universo(universo, sorteios)
        resultado["id"] = i + 1
        resultados.append(resultado)
        print(f"  Universo {i+1}: max={resultado['max_acertos']}, 15ac={resultado['count_15']}, 14ac={resultado['count_14']}")
    
    # Ordenar por score
    resultados.sort(key=lambda x: x["score"], reverse=True)
    
    # Ranking
    print("\n" + "=" * 80)
    print("RANKING DE UNIVERSOS")
    print("=" * 80)
    
    print(f"\n{'#':<3} {'Max':<5} {'15ac':<5} {'14ac':<6} {'13ac':<6} {'Jogos':<8} {'ROI':<10} {'Lucro Potencial':<20}")
    print("-" * 80)
    
    for i, r in enumerate(resultados):
        print(f"{i+1:<3} {r['max_acertos']:<5} {r['count_15']:<5} {r['count_14']:<6} {r['count_13']:<6} ~{r['jogos_estimados']:<7} {r['roi']:.1f}%{'':<6} {formatar_moeda(r['lucro_potencial']):<20}")
    
    # Melhor universo
    melhor = resultados[0]
    
    print("\n" + "=" * 80)
    print("🏆 MELHOR UNIVERSO")
    print("=" * 80)
    
    print(f"\nNúmeros: {','.join(map(str, melhor['universo']))}")
    print(f"\nEstatísticas:")
    print(f"  Máximo de acertos: {melhor['max_acertos']}")
    print(f"  Sorteios com 15: {melhor['count_15']}")
    print(f"  Sorteios com 14: {melhor['count_14']}")
    print(f"  Sorteios com 13: {melhor['count_13']}")
    print(f"  Jogos estimados: ~{melhor['jogos_estimados']}")
    print(f"  Ganho potencial: {formatar_moeda(melhor['ganho_potencial'])}")
    print(f"  Custo estimado: {formatar_moeda(melhor['custo_total_estimado'])}")
    print(f"  Lucro potencial: {formatar_moeda(melhor['lucro_potencial'])}")
    print(f"  ROI: {melhor['roi']:.1f}%")
    
    print(f"\nComando para usar este universo:")
    print(f'python3 fechamento_lotofacil.py --universe "{",".join(map(str, melhor["universo"]))}" --out tickets_melhor.txt')
    
    # Top 3
    if len(resultados) >= 3:
        print("\n" + "=" * 80)
        print("TOP 3 UNIVERSOS")
        print("=" * 80)
        
        for i, r in enumerate(resultados[:3]):
            print(f"\n#{i+1}: {','.join(map(str, r['universo']))}")
            print(f"    Max: {r['max_acertos']}, 15ac: {r['count_15']}, 14ac: {r['count_14']}, ROI: {r['roi']:.1f}%")


if __name__ == "__main__":
    main()
