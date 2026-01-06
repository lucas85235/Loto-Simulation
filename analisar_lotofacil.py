#!/usr/bin/env python3
"""
Análise estatística dos concursos da Lotofácil.
Gera insights e sugere universos baseados em dados históricos.
"""

import json
import os
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter
import itertools

CACHE_FILE = os.path.join(os.path.dirname(__file__), "lotofacil_cache.json")


@dataclass
class Sorteio:
    numero: int
    data: str
    dezenas: set


def carregar_sorteios() -> List[Sorteio]:
    """Carrega sorteios do cache."""
    if not os.path.exists(CACHE_FILE):
        print("Cache não encontrado. Execute primeiro o verificar_sorteios.py para popular o cache.")
        return []
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sorteios = []
        for k, v in data.items():
            sorteios.append(Sorteio(
                numero=v["numero"],
                data=v["data"],
                dezenas=set(v["dezenas"])
            ))
        
        # Ordenar do mais recente para o mais antigo
        sorteios.sort(key=lambda x: x.numero, reverse=True)
        return sorteios
    except Exception as e:
        print(f"Erro ao carregar cache: {e}")
        return []


def formatar_porcentagem(valor: float) -> str:
    return f"{valor:.1f}%"


def analisar_frequencia(sorteios: List[Sorteio]) -> Dict[int, int]:
    """Conta frequência de cada número."""
    freq = Counter()
    for s in sorteios:
        freq.update(s.dezenas)
    return dict(freq)


def analisar_pares_impares(sorteios: List[Sorteio]) -> Dict[str, int]:
    """Analisa distribuição de pares/ímpares."""
    dist = Counter()
    for s in sorteios:
        pares = sum(1 for d in s.dezenas if d % 2 == 0)
        impares = 15 - pares
        dist[f"{pares}P/{impares}I"] += 1
    return dict(dist)


def analisar_baixos_altos(sorteios: List[Sorteio]) -> Dict[str, int]:
    """Analisa distribuição baixos (1-12) / altos (13-25)."""
    dist = Counter()
    for s in sorteios:
        baixos = sum(1 for d in s.dezenas if d <= 12)
        altos = 15 - baixos
        dist[f"{baixos}B/{altos}A"] += 1
    return dict(dist)


def analisar_sequencias(sorteios: List[Sorteio]) -> Dict[int, int]:
    """Conta sequências consecutivas nos sorteios."""
    seq_counts = Counter()
    for s in sorteios:
        nums = sorted(s.dezenas)
        seq_len = 1
        max_seq = 1
        for i in range(1, len(nums)):
            if nums[i] == nums[i-1] + 1:
                seq_len += 1
                max_seq = max(max_seq, seq_len)
            else:
                seq_len = 1
        seq_counts[max_seq] += 1
    return dict(seq_counts)


def analisar_soma(sorteios: List[Sorteio]) -> Tuple[float, int, int, Dict[str, int]]:
    """Analisa soma das dezenas."""
    somas = [sum(s.dezenas) for s in sorteios]
    media = sum(somas) / len(somas)
    minimo = min(somas)
    maximo = max(somas)
    
    # Distribuição por faixas
    faixas = Counter()
    for soma in somas:
        if soma < 170:
            faixas["< 170"] += 1
        elif soma < 190:
            faixas["170-189"] += 1
        elif soma < 210:
            faixas["190-209"] += 1
        elif soma < 230:
            faixas["210-229"] += 1
        else:
            faixas[">= 230"] += 1
    
    return media, minimo, maximo, dict(faixas)


def analisar_repeticoes(sorteios: List[Sorteio]) -> Dict[int, int]:
    """Analisa quantos números se repetem entre concursos consecutivos."""
    rep_counts = Counter()
    for i in range(len(sorteios) - 1):
        atual = sorteios[i].dezenas
        anterior = sorteios[i + 1].dezenas
        repeticoes = len(atual & anterior)
        rep_counts[repeticoes] += 1
    return dict(rep_counts)


def analisar_atrasos(sorteios: List[Sorteio]) -> Dict[int, int]:
    """Calcula há quantos concursos cada número não sai."""
    ultimo_aparecimento = {i: -1 for i in range(1, 26)}
    
    for idx, s in enumerate(sorteios):
        for d in s.dezenas:
            if ultimo_aparecimento[d] == -1:
                ultimo_aparecimento[d] = idx
    
    # Converter para atraso
    atrasos = {}
    for num, idx in ultimo_aparecimento.items():
        if idx == -1:
            atrasos[num] = len(sorteios)  # Nunca apareceu
        else:
            atrasos[num] = idx
    
    return atrasos


def gerar_universo_frequencia(freq: Dict[int, int], tamanho: int = 20) -> List[int]:
    """Gera universo com os números mais frequentes."""
    ordenados = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return sorted([num for num, _ in ordenados[:tamanho]])


def gerar_universo_equilibrado(freq: Dict[int, int], atrasos: Dict[int, int]) -> List[int]:
    """Gera universo equilibrado entre frequência e atraso."""
    # Score = frequência normalizada + (inverso do atraso normalizado)
    max_freq = max(freq.values())
    max_atraso = max(atrasos.values()) if max(atrasos.values()) > 0 else 1
    
    scores = {}
    for num in range(1, 26):
        freq_norm = freq.get(num, 0) / max_freq
        atraso_norm = atrasos.get(num, 0) / max_atraso
        # Números com alto atraso ganham bônus (prestes a sair)
        scores[num] = freq_norm * 0.6 + atraso_norm * 0.4
    
    ordenados = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted([num for num, _ in ordenados[:20]])


def gerar_universo_balanceado(freq: Dict[int, int]) -> List[int]:
    """Gera universo balanceado entre baixos/altos e pares/ímpares."""
    # Separar em grupos
    baixos = [(n, freq.get(n, 0)) for n in range(1, 13)]
    altos = [(n, freq.get(n, 0)) for n in range(13, 26)]
    
    # Ordenar por frequência
    baixos.sort(key=lambda x: x[1], reverse=True)
    altos.sort(key=lambda x: x[1], reverse=True)
    
    # Pegar proporcionalmente (8 baixos, 12 altos - proporção típica)
    universo = [n for n, _ in baixos[:8]] + [n for n, _ in altos[:12]]
    return sorted(universo)


def main():
    import sys
    
    print("=" * 80)
    print("ANÁLISE ESTATÍSTICA DA LOTOFÁCIL")
    print("=" * 80)
    
    sorteios = carregar_sorteios()
    if not sorteios:
        print("\nNenhum sorteio encontrado. Execute primeiro:")
        print("  python3 verificar_sorteios.py tickets.txt 100")
        return
    
    # Limitar análise se especificado
    num_concursos = int(sys.argv[1]) if len(sys.argv) > 1 else len(sorteios)
    sorteios = sorteios[:num_concursos]
    
    print(f"\nAnalisando {len(sorteios)} concursos")
    print(f"Do concurso {sorteios[-1].numero} ao {sorteios[0].numero}")
    
    # 1. Frequência
    print("\n" + "=" * 80)
    print("1. FREQUÊNCIA DOS NÚMEROS")
    print("=" * 80)
    
    freq = analisar_frequencia(sorteios)
    total_sorteios = len(sorteios)
    
    print("\nNúmero | Freq | % | Gráfico")
    print("-" * 50)
    
    for num in range(1, 26):
        f = freq.get(num, 0)
        pct = (f / total_sorteios) * 100
        bar = "█" * int(pct / 2)
        print(f"  {num:2d}   | {f:4d} | {pct:5.1f}% | {bar}")
    
    # Top 5 mais frequentes
    top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"\nTOP 5 mais frequentes: {', '.join(f'{n}({f})' for n, f in top5)}")
    
    # Top 5 menos frequentes
    bottom5 = sorted(freq.items(), key=lambda x: x[1])[:5]
    print(f"TOP 5 menos frequentes: {', '.join(f'{n}({f})' for n, f in bottom5)}")
    
    # 2. Atrasos
    print("\n" + "=" * 80)
    print("2. ATRASOS (concursos sem aparecer)")
    print("=" * 80)
    
    atrasos = analisar_atrasos(sorteios)
    
    atrasados = [(n, a) for n, a in atrasos.items() if a > 0]
    atrasados.sort(key=lambda x: x[1], reverse=True)
    
    print("\nNúmeros mais atrasados:")
    for num, atraso in atrasados[:10]:
        print(f"  {num:2d}: {atraso} concursos sem sair")
    
    # 3. Pares/Ímpares
    print("\n" + "=" * 80)
    print("3. DISTRIBUIÇÃO PARES/ÍMPARES")
    print("=" * 80)
    
    pi = analisar_pares_impares(sorteios)
    pi_sorted = sorted(pi.items(), key=lambda x: x[1], reverse=True)
    
    print("\nDistribuição | Ocorrências | %")
    print("-" * 40)
    for dist, count in pi_sorted:
        pct = (count / total_sorteios) * 100
        print(f"    {dist}    |    {count:4d}     | {pct:5.1f}%")
    
    # 4. Baixos/Altos
    print("\n" + "=" * 80)
    print("4. DISTRIBUIÇÃO BAIXOS(1-12)/ALTOS(13-25)")
    print("=" * 80)
    
    ba = analisar_baixos_altos(sorteios)
    ba_sorted = sorted(ba.items(), key=lambda x: x[1], reverse=True)
    
    print("\nDistribuição | Ocorrências | %")
    print("-" * 40)
    for dist, count in ba_sorted:
        pct = (count / total_sorteios) * 100
        print(f"    {dist}    |    {count:4d}     | {pct:5.1f}%")
    
    # 5. Soma
    print("\n" + "=" * 80)
    print("5. SOMA DAS DEZENAS")
    print("=" * 80)
    
    media_soma, min_soma, max_soma, faixas_soma = analisar_soma(sorteios)
    
    print(f"\nMédia: {media_soma:.1f}")
    print(f"Mínima: {min_soma}")
    print(f"Máxima: {max_soma}")
    
    print("\nDistribuição por faixas:")
    for faixa, count in sorted(faixas_soma.items()):
        pct = (count / total_sorteios) * 100
        print(f"  {faixa}: {count} ({pct:.1f}%)")
    
    # 6. Sequências
    print("\n" + "=" * 80)
    print("6. SEQUÊNCIAS CONSECUTIVAS (maior sequência no sorteio)")
    print("=" * 80)
    
    seqs = analisar_sequencias(sorteios)
    
    for seq_len, count in sorted(seqs.items()):
        pct = (count / total_sorteios) * 100
        print(f"  {seq_len} consecutivos: {count} sorteios ({pct:.1f}%)")
    
    # 7. Repetições entre concursos
    print("\n" + "=" * 80)
    print("7. REPETIÇÕES ENTRE CONCURSOS CONSECUTIVOS")
    print("=" * 80)
    
    reps = analisar_repeticoes(sorteios)
    
    for num_rep, count in sorted(reps.items()):
        pct = (count / (total_sorteios - 1)) * 100 if total_sorteios > 1 else 0
        print(f"  {num_rep} repetições: {count} vezes ({pct:.1f}%)")
    
    # 8. Universos sugeridos
    print("\n" + "=" * 80)
    print("8. UNIVERSOS SUGERIDOS (20 números)")
    print("=" * 80)
    
    # Universo por frequência
    univ_freq = gerar_universo_frequencia(freq, 20)
    print(f"\n📊 UNIVERSO POR FREQUÊNCIA (mais sorteados):")
    print(f"   {','.join(map(str, univ_freq))}")
    
    # Universo equilibrado
    univ_equil = gerar_universo_equilibrado(freq, atrasos)
    print(f"\n⚖️  UNIVERSO EQUILIBRADO (frequência + atraso):")
    print(f"   {','.join(map(str, univ_equil))}")
    
    # Universo balanceado
    univ_bal = gerar_universo_balanceado(freq)
    print(f"\n🎯 UNIVERSO BALANCEADO (proporção baixos/altos):")
    print(f"   {','.join(map(str, univ_bal))}")
    
    # 9. Comandos prontos
    print("\n" + "=" * 80)
    print("9. COMANDOS PRONTOS PARA USAR")
    print("=" * 80)
    
    print(f"\n# Gerar fechamento com universo por frequência:")
    print(f'python3 fechamento_lotofacil.py --universe "{",".join(map(str, univ_freq))}" --out tickets_frequencia.txt')
    
    print(f"\n# Gerar fechamento com universo equilibrado:")
    print(f'python3 fechamento_lotofacil.py --universe "{",".join(map(str, univ_equil))}" --out tickets_equilibrado.txt')
    
    print(f"\n# Gerar fechamento com universo balanceado:")
    print(f'python3 fechamento_lotofacil.py --universe "{",".join(map(str, univ_bal))}" --out tickets_balanceado.txt')
    
    # 10. Insights finais
    print("\n" + "=" * 80)
    print("10. INSIGHTS")
    print("=" * 80)
    
    # Média de pares
    total_pares = sum(int(k.split('P')[0]) * v for k, v in pi.items())
    media_pares = total_pares / total_sorteios
    print(f"\n• Média de números PARES por sorteio: {media_pares:.1f}")
    print(f"• Média de números ÍMPARES por sorteio: {15 - media_pares:.1f}")
    
    # Média de baixos
    total_baixos = sum(int(k.split('B')[0]) * v for k, v in ba.items())
    media_baixos = total_baixos / total_sorteios
    print(f"• Média de números BAIXOS (1-12): {media_baixos:.1f}")
    print(f"• Média de números ALTOS (13-25): {15 - media_baixos:.1f}")
    
    # Números "quentes" (alta frequência + baixo atraso)
    quentes = []
    for n in range(1, 26):
        if freq.get(n, 0) > total_sorteios * 0.6 and atrasos.get(n, 0) <= 2:
            quentes.append(n)
    if quentes:
        print(f"\n🔥 Números QUENTES (frequentes + saíram recente): {quentes}")
    
    # Números "frios" (baixa frequência + alto atraso)
    frios = []
    for n in range(1, 26):
        if freq.get(n, 0) < total_sorteios * 0.5 and atrasos.get(n, 0) >= 3:
            frios.append(n)
    if frios:
        print(f"❄️  Números FRIOS (infrequentes + atrasados): {frios}")
    
    # Números "prestes a sair" (frequentes mas atrasados)
    prestes = []
    for n in range(1, 26):
        if freq.get(n, 0) > total_sorteios * 0.55 and atrasos.get(n, 0) >= 2:
            prestes.append((n, atrasos[n]))
    if prestes:
        prestes.sort(key=lambda x: x[1], reverse=True)
        print(f"⏰ Números provavelmente PRESTES A SAIR: {[n for n, _ in prestes]}")


if __name__ == "__main__":
    main()
