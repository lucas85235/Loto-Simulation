#!/usr/bin/env python3
"""
Busca o universo ideal que teria acertado o prêmio máximo (15 acertos)
em algum dos últimos X concursos.

Estratégia:
1. Carrega os sorteios do cache
2. Para cada sorteio, as 15 dezenas sorteadas são um candidato perfeito
3. Busca o melhor universo de 20 números que maximize os acertos em múltiplos sorteios
"""

import json
import os
import itertools
import random
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from collections import Counter

CACHE_FILE = os.path.join(os.path.dirname(__file__), "lotofacil_cache.json")


@dataclass
class Sorteio:
    numero: int
    data: str
    dezenas: set


def carregar_sorteios() -> List[Sorteio]:
    """Carrega sorteios do cache."""
    if not os.path.exists(CACHE_FILE):
        print("Cache não encontrado. Execute primeiro:")
        print("  python3 verificar_sorteios.py tickets.txt 100")
        return []
    
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sorteios = []
    for v in data.values():
        sorteios.append(Sorteio(
            numero=v["numero"],
            data=v["data"],
            dezenas=set(v["dezenas"])
        ))
    
    sorteios.sort(key=lambda x: x.numero, reverse=True)
    return sorteios


def verificar_acertos(universo: Set[int], sorteio: Sorteio) -> int:
    """Verifica quantos acertos teríamos se jogássemos o universo inteiro."""
    return len(universo & sorteio.dezenas)


def encontrar_universo_perfeito(sorteios: List[Sorteio], tamanho_universo: int = 20) -> Tuple[Set[int], int, Sorteio]:
    """
    Encontra um universo que contém um sorteio inteiro (15 acertos garantidos).
    Retorna (universo, acertos, sorteio_acertado)
    """
    print(f"\n{'='*80}")
    print(f"BUSCANDO UNIVERSO PERFEITO (que contenha 15 números de algum sorteio)")
    print(f"{'='*80}")
    
    for sorteio in sorteios:
        # Um universo que contém as 15 dezenas do sorteio
        # Precisamos adicionar mais 5 números para completar 20
        dezenas_sorteio = sorteio.dezenas
        numeros_fora = set(range(1, 26)) - dezenas_sorteio
        
        # Escolher os 5 números mais frequentes fora do sorteio
        freq = Counter()
        for s in sorteios:
            freq.update(s.dezenas)
        
        melhores_extras = sorted(numeros_fora, key=lambda x: freq.get(x, 0), reverse=True)[:5]
        
        universo = dezenas_sorteio | set(melhores_extras)
        
        # Verificar acertos neste sorteio
        acertos = verificar_acertos(universo, sorteio)
        
        if acertos == 15:
            print(f"\n✅ ENCONTRADO! Universo que acerta 15 no concurso {sorteio.numero}")
            return universo, 15, sorteio
    
    return set(), 0, None


def buscar_melhor_universo_genetico(sorteios: List[Sorteio], 
                                      tamanho_universo: int = 20,
                                      populacao: int = 100,
                                      geracoes: int = 500,
                                      alvo_acertos: int = 15) -> Tuple[Set[int], Dict]:
    """
    Usa algoritmo genético para encontrar o melhor universo.
    """
    print(f"\n{'='*80}")
    print(f"ALGORITMO GENÉTICO - Buscando universo com {alvo_acertos} acertos")
    print(f"{'='*80}")
    print(f"População: {populacao}, Gerações: {geracoes}")
    
    todos_numeros = list(range(1, 26))
    
    def criar_individuo():
        return set(random.sample(todos_numeros, tamanho_universo))
    
    def avaliar(universo: Set[int]) -> Tuple[int, int, int]:
        """Retorna (max_acertos, total_14+, total_acertos)"""
        max_ac = 0
        count_14_plus = 0
        total = 0
        for s in sorteios:
            ac = len(universo & s.dezenas)
            max_ac = max(max_ac, ac)
            if ac >= 14:
                count_14_plus += 1
            total += ac
        return (max_ac, count_14_plus, total)
    
    def crossover(pai1: Set[int], pai2: Set[int]) -> Set[int]:
        uniao = list(pai1 | pai2)
        return set(random.sample(uniao, min(tamanho_universo, len(uniao))))
    
    def mutacao(ind: Set[int], taxa: float = 0.1) -> Set[int]:
        ind = set(ind)
        for _ in range(int(tamanho_universo * taxa)):
            if random.random() < 0.5 and len(ind) > 0:
                # Remover um número
                ind.discard(random.choice(list(ind)))
            # Adicionar um número
            disponiveis = set(todos_numeros) - ind
            if disponiveis and len(ind) < tamanho_universo:
                ind.add(random.choice(list(disponiveis)))
        
        # Garantir tamanho correto
        while len(ind) < tamanho_universo:
            disponiveis = set(todos_numeros) - ind
            if disponiveis:
                ind.add(random.choice(list(disponiveis)))
        while len(ind) > tamanho_universo:
            ind.discard(random.choice(list(ind)))
        
        return ind
    
    # Inicializar população
    pop = [criar_individuo() for _ in range(populacao)]
    
    # Adicionar indivíduos baseados nos sorteios (elite inicial)
    for s in sorteios[:10]:
        extras = set(random.sample(list(set(range(1, 26)) - s.dezenas), 5))
        pop.append(s.dezenas | extras)
    
    melhor_global = None
    melhor_score_global = (0, 0, 0)
    
    for geracao in range(geracoes):
        # Avaliar
        avaliados = [(ind, avaliar(ind)) for ind in pop]
        avaliados.sort(key=lambda x: x[1], reverse=True)
        
        melhor_ind, melhor_score = avaliados[0]
        
        if melhor_score > melhor_score_global:
            melhor_score_global = melhor_score
            melhor_global = melhor_ind
            
            max_ac, count_14, total = melhor_score
            print(f"Geração {geracao:3d}: Max={max_ac}, 14+={count_14}, Total={total}")
            
            if max_ac >= alvo_acertos:
                print(f"\n🎯 ALVO ATINGIDO na geração {geracao}!")
                break
        
        # Seleção (elitismo + torneio)
        elite = [ind for ind, _ in avaliados[:populacao // 5]]
        
        nova_pop = list(elite)
        
        while len(nova_pop) < populacao:
            # Torneio
            competidores = random.sample(avaliados[:populacao // 2], 3)
            pai1 = max(competidores, key=lambda x: x[1])[0]
            competidores = random.sample(avaliados[:populacao // 2], 3)
            pai2 = max(competidores, key=lambda x: x[1])[0]
            
            filho = crossover(pai1, pai2)
            filho = mutacao(filho)
            nova_pop.append(filho)
        
        pop = nova_pop
    
    # Encontrar em qual sorteio deu o máximo
    resultados = {}
    for s in sorteios:
        ac = len(melhor_global & s.dezenas)
        if ac >= 14:
            resultados[s.numero] = {"acertos": ac, "data": s.data, "dezenas": s.dezenas}
    
    return melhor_global, resultados


def main():
    import sys
    
    print("=" * 80)
    print("BUSCADOR DE UNIVERSO IDEAL - LOTOFÁCIL")
    print("=" * 80)
    
    sorteios = carregar_sorteios()
    if not sorteios:
        return
    
    num_concursos = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    sorteios = sorteios[:num_concursos]
    
    print(f"\nAnalisando {len(sorteios)} concursos")
    print(f"Do concurso {sorteios[-1].numero} ao {sorteios[0].numero}")
    
    # Método 1: Universo perfeito (contém um sorteio inteiro)
    universo_perfeito, acertos, sorteio = encontrar_universo_perfeito(sorteios)
    
    if acertos == 15:
        print(f"\n{'='*80}")
        print("UNIVERSO PERFEITO ENCONTRADO!")
        print(f"{'='*80}")
        print(f"\nConcurso: {sorteio.numero} ({sorteio.data})")
        print(f"Dezenas sorteadas: {sorted(sorteio.dezenas)}")
        print(f"\nUniverso de 20 números: {sorted(universo_perfeito)}")
        print(f"\nComando para gerar fechamento:")
        print(f'python3 fechamento_lotofacil.py --universe "{",".join(map(str, sorted(universo_perfeito)))}" --out tickets_perfeito.txt')
        
        # Verificar desempenho em outros sorteios
        print(f"\nDesempenho nos outros sorteios:")
        acertos_dist = Counter()
        for s in sorteios:
            ac = len(universo_perfeito & s.dezenas)
            acertos_dist[ac] += 1
        
        for ac in sorted(acertos_dist.keys(), reverse=True):
            print(f"  {ac} acertos: {acertos_dist[ac]} sorteios")
    
    # Método 2: Algoritmo genético para maximizar acertos
    print("\n" + "=" * 80)
    print("BUSCANDO UNIVERSO OTIMIZADO (Algoritmo Genético)")
    print("=" * 80)
    
    melhor_universo, resultados = buscar_melhor_universo_genetico(
        sorteios, 
        tamanho_universo=20,
        populacao=200,
        geracoes=1000,
        alvo_acertos=15
    )
    
    print(f"\n{'='*80}")
    print("MELHOR UNIVERSO ENCONTRADO")
    print(f"{'='*80}")
    
    print(f"\nUniverso: {sorted(melhor_universo)}")
    print(f"\nComando:")
    print(f'python3 fechamento_lotofacil.py --universe "{",".join(map(str, sorted(melhor_universo)))}" --out tickets_otimizado.txt')
    
    if resultados:
        print(f"\nSorteios com 14+ acertos:")
        for num, info in sorted(resultados.items(), key=lambda x: x[1]["acertos"], reverse=True):
            print(f"  Concurso {num} ({info['data']}): {info['acertos']} acertos")
            print(f"    Dezenas: {sorted(info['dezenas'])}")
    
    # Estatísticas finais
    print(f"\n{'='*80}")
    print("ESTATÍSTICAS DO UNIVERSO OTIMIZADO")
    print(f"{'='*80}")
    
    acertos_dist = Counter()
    for s in sorteios:
        ac = len(melhor_universo & s.dezenas)
        acertos_dist[ac] += 1
    
    print("\nDistribuição de acertos:")
    for ac in sorted(acertos_dist.keys(), reverse=True):
        pct = (acertos_dist[ac] / len(sorteios)) * 100
        print(f"  {ac} acertos: {acertos_dist[ac]} sorteios ({pct:.1f}%)")
    
    # Melhor caso
    max_ac = max(acertos_dist.keys())
    if max_ac >= 14:
        print(f"\n🏆 MÁXIMO ATINGIDO: {max_ac} acertos!")
        if max_ac == 15:
            print("🎉 JACKPOT! Este universo teria ganho o prêmio máximo!")
    else:
        print(f"\n⚠️  Melhor resultado: {max_ac} acertos")
        print("   Nenhum universo de 20 números contém um sorteio inteiro neste período.")


if __name__ == "__main__":
    main()
