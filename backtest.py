#!/usr/bin/env python3
"""
Backtest Realista para apostas na Lotofácil.
Simula a evolução do capital ao longo do tempo,
considerando apostas reais mês a mês.
"""

import json
import os
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

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


def carregar_jogos(arquivo: str) -> List[set]:
    jogos = []
    with open(arquivo, 'r') as f:
        for linha in f:
            match = re.match(r'Jogo\s+\d+:\s*(.+)', linha.strip())
            if match:
                numeros = [int(n.strip()) for n in match.group(1).split(',')]
                jogos.append(set(numeros))
    return jogos


def extrair_mes_ano(data_str: str) -> str:
    """Extrai mês/ano de uma data no formato DD/MM/YYYY."""
    try:
        partes = data_str.split('/')
        return f"{partes[1]}/{partes[2]}"
    except:
        return "00/0000"


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def gerar_grafico_ascii(dados: List[Tuple[str, float]], largura: int = 50) -> str:
    """Gera um gráfico ASCII da evolução do patrimônio."""
    if not dados:
        return ""
    
    valores = [v for _, v in dados]
    min_val = min(valores)
    max_val = max(valores)
    
    if max_val == min_val:
        max_val = min_val + 1
    
    linhas = []
    linhas.append("Evolução do Patrimônio:")
    linhas.append("-" * (largura + 20))
    
    for mes, valor in dados:
        # Normalizar para 0-largura
        if valor >= 0:
            pos = int((valor - min_val) / (max_val - min_val) * largura)
            zero_pos = int((0 - min_val) / (max_val - min_val) * largura) if min_val < 0 else 0
            
            if valor >= 0 and min_val < 0:
                barra = " " * zero_pos + "▓" * (pos - zero_pos)
            else:
                barra = "▓" * pos
        else:
            zero_pos = int((0 - min_val) / (max_val - min_val) * largura)
            pos = int((valor - min_val) / (max_val - min_val) * largura)
            barra = " " * pos + "░" * (zero_pos - pos)
        
        status = "+" if valor >= 0 else "-"
        linhas.append(f"{mes} |{barra:<{largura}}| {status}{formatar_moeda(abs(valor))}")
    
    linhas.append("-" * (largura + 20))
    return "\n".join(linhas)


def main():
    import sys
    
    arquivo_jogos = sys.argv[1] if len(sys.argv) > 1 else "tickets.txt"
    capital_inicial = float(sys.argv[2]) if len(sys.argv) > 2 else 10000.0
    num_concursos = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    
    print("=" * 80)
    print("BACKTEST REALISTA - LOTOFÁCIL")
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
    
    # Ordenar concursos do mais antigo para o mais recente
    numeros = sorted(cache.keys(), reverse=True)[:num_concursos]
    numeros = list(reversed(numeros))  # Do mais antigo para o mais recente
    
    custo_por_concurso = len(jogos) * CUSTO_JOGO
    
    print(f"\nCapital inicial: {formatar_moeda(capital_inicial)}")
    print(f"Jogos por concurso: {len(jogos)}")
    print(f"Custo por concurso: {formatar_moeda(custo_por_concurso)}")
    print(f"Concursos a simular: {len(numeros)}")
    
    # Simular
    patrimonio = capital_inicial
    historico = []
    historico_mensal = {}
    
    total_investido = 0.0
    total_ganho = 0.0
    
    concursos_sem_capital = 0
    
    print("\n" + "=" * 80)
    print("SIMULAÇÃO CONCURSO A CONCURSO")
    print("=" * 80)
    print(f"\n{'Concurso':<12} {'Data':<12} {'Custo':<15} {'Ganho':<15} {'Lucro':<15} {'Patrimônio':<18}")
    print("-" * 90)
    
    for i, num in enumerate(numeros):
        sorteio = cache[num]
        mes_ano = extrair_mes_ano(sorteio.data)
        
        # Verificar se tem capital
        if patrimonio < custo_por_concurso:
            concursos_sem_capital += 1
            if concursos_sem_capital == 1:
                print(f"\n⚠️  CAPITAL INSUFICIENTE no concurso {num}!")
                print(f"    Patrimônio: {formatar_moeda(patrimonio)}")
                print(f"    Custo necessário: {formatar_moeda(custo_por_concurso)}")
            continue
        
        # Apostar
        patrimonio -= custo_por_concurso
        total_investido += custo_por_concurso
        
        # Calcular ganhos
        ganho = 0.0
        for jogo in jogos:
            acertos = len(jogo & sorteio.dezenas)
            if acertos >= 11:
                premio = sorteio.premios.get(acertos, PREMIOS.get(acertos, 0))
                ganho += premio
        
        patrimonio += ganho
        total_ganho += ganho
        lucro = ganho - custo_por_concurso
        
        # Registrar
        historico.append({
            "concurso": num,
            "data": sorteio.data,
            "custo": custo_por_concurso,
            "ganho": ganho,
            "lucro": lucro,
            "patrimonio": patrimonio
        })
        
        # Acumular mensal
        if mes_ano not in historico_mensal:
            historico_mensal[mes_ano] = {"investido": 0, "ganho": 0, "concursos": 0}
        historico_mensal[mes_ano]["investido"] += custo_por_concurso
        historico_mensal[mes_ano]["ganho"] += ganho
        historico_mensal[mes_ano]["concursos"] += 1
        
        # Mostrar a cada 10 concursos ou se houver grande prêmio
        if i % 10 == 0 or ganho > 1000:
            status = "🏆" if ganho > 1000 else ("✅" if lucro > 0 else "❌")
            print(f"{num:<12} {sorteio.data:<12} {formatar_moeda(custo_por_concurso):<15} {formatar_moeda(ganho):<15} {formatar_moeda(lucro):<15} {formatar_moeda(patrimonio):<18} {status}")
    
    if concursos_sem_capital > 0:
        print(f"\n⚠️  {concursos_sem_capital} concursos pulados por falta de capital.")
    
    # Resumo mensal
    print("\n" + "=" * 80)
    print("RESUMO MENSAL")
    print("=" * 80)
    print(f"\n{'Mês/Ano':<10} {'Concursos':<12} {'Investido':<18} {'Ganho':<18} {'Lucro':<18}")
    print("-" * 80)
    
    grafico_dados = []
    patrimonio_acumulado = capital_inicial
    
    for mes in sorted(historico_mensal.keys(), key=lambda x: (x.split('/')[1], x.split('/')[0])):
        dados = historico_mensal[mes]
        lucro_mes = dados["ganho"] - dados["investido"]
        patrimonio_acumulado += lucro_mes
        
        status = "✅" if lucro_mes > 0 else "❌"
        print(f"{mes:<10} {dados['concursos']:<12} {formatar_moeda(dados['investido']):<18} {formatar_moeda(dados['ganho']):<18} {formatar_moeda(lucro_mes):<18} {status}")
        
        grafico_dados.append((mes, patrimonio_acumulado - capital_inicial))
    
    print("-" * 80)
    
    # Gráfico
    print("\n" + "=" * 80)
    print("EVOLUÇÃO DO PATRIMÔNIO")
    print("=" * 80)
    print()
    print(gerar_grafico_ascii(grafico_dados))
    
    # Resumo final
    print("\n" + "=" * 80)
    print("RESULTADO FINAL")
    print("=" * 80)
    
    lucro_total = total_ganho - total_investido
    
    print(f"\n📊 INVESTIMENTO:")
    print(f"   Capital inicial: {formatar_moeda(capital_inicial)}")
    print(f"   Total investido: {formatar_moeda(total_investido)}")
    
    print(f"\n💰 RETORNO:")
    print(f"   Total ganho: {formatar_moeda(total_ganho)}")
    print(f"   Lucro/Prejuízo: {formatar_moeda(lucro_total)}")
    
    print(f"\n📈 PATRIMÔNIO FINAL:")
    print(f"   Valor: {formatar_moeda(patrimonio)}")
    print(f"   Variação: {((patrimonio / capital_inicial) - 1) * 100:+.1f}%")
    
    if patrimonio > capital_inicial:
        print(f"\n✅ SUCESSO! Patrimônio cresceu {formatar_moeda(patrimonio - capital_inicial)}")
    elif patrimonio == 0:
        print(f"\n💀 FALÊNCIA! Capital zerado.")
    else:
        print(f"\n❌ PREJUÍZO! Perdeu {formatar_moeda(capital_inicial - patrimonio)}")
    
    # Estatísticas
    if historico:
        concursos_lucro = sum(1 for h in historico if h["lucro"] > 0)
        taxa_acerto = (concursos_lucro / len(historico)) * 100
        print(f"\n📋 ESTATÍSTICAS:")
        print(f"   Concursos jogados: {len(historico)}")
        print(f"   Concursos com lucro: {concursos_lucro} ({taxa_acerto:.1f}%)")
        print(f"   ROI: {((patrimonio / capital_inicial) - 1) * 100:.1f}%")


if __name__ == "__main__":
    main()
