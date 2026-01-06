#!/usr/bin/env python3
"""
Script para verificar jogos da Lotofácil contra os últimos sorteios.
Calcula acertos, prêmios e média de ganhos.
Salva resultados em cache local para evitar requisições repetidas.
"""

import requests
import re
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


CACHE_FILE = os.path.join(os.path.dirname(__file__), "lotofacil_cache.json")
CUSTO_JOGO_15 = 3.50  # Custo de um jogo de 15 números


# Valores médios típicos de prêmios da Lotofácil
PREMIOS_TIPICOS = {
    11: 6.00,
    12: 12.00,
    13: 30.00,
    14: 900.00,
    15: 700000.00
}


@dataclass
class Sorteio:
    numero: int
    data: str
    dezenas: set
    premios: Dict[int, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "numero": self.numero,
            "data": self.data,
            "dezenas": list(self.dezenas),
            "premios": self.premios
        }
    
    @staticmethod
    def from_dict(d: dict) -> "Sorteio":
        return Sorteio(
            numero=d["numero"],
            data=d["data"],
            dezenas=set(d["dezenas"]),
            premios={int(k): v for k, v in d["premios"].items()}
        )


@dataclass
class Jogo:
    numero: int
    dezenas: set


def carregar_cache() -> Dict[int, Sorteio]:
    """Carrega o cache de sorteios do arquivo JSON."""
    if not os.path.exists(CACHE_FILE):
        return {}
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {int(k): Sorteio.from_dict(v) for k, v in data.items()}
    except Exception as e:
        print(f"Aviso: Erro ao carregar cache: {e}")
        return {}


def salvar_cache(cache: Dict[int, Sorteio]):
    """Salva o cache de sorteios no arquivo JSON."""
    try:
        data = {str(k): v.to_dict() for k, v in cache.items()}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Aviso: Erro ao salvar cache: {e}")


def carregar_jogos(arquivo: str) -> List[Jogo]:
    """Carrega jogos do arquivo txt."""
    jogos = []
    with open(arquivo, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            
            match = re.match(r'Jogo\s+(\d+):\s*(.+)', linha)
            if match:
                num = int(match.group(1))
                numeros = [int(n.strip()) for n in match.group(2).split(',')]
                jogos.append(Jogo(numero=num, dezenas=set(numeros)))
    
    return jogos


def buscar_sorteio_api(numero: int) -> Optional[Sorteio]:
    """Busca um sorteio específico da API."""
    try:
        url = f"https://loteriascaixa-api.herokuapp.com/api/lotofacil/{numero}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        dados = response.json()
        
        dezenas = set(int(d) for d in dados['dezenas'])
        data = dados.get('data', 'N/A')
        
        premios = {}
        if 'premiacoes' in dados:
            for premiacao in dados['premiacoes']:
                acertos = premiacao.get('acertos', 0)
                if acertos < 11:
                    continue
                valor = premiacao.get('valorPremio', 0)
                if isinstance(valor, str):
                    valor = float(valor.replace('.', '').replace(',', '.'))
                if valor > 0:
                    premios[acertos] = valor
        
        if not premios:
            premios = PREMIOS_TIPICOS.copy()
        
        return Sorteio(numero=numero, data=data, dezenas=dezenas, premios=premios)
        
    except Exception as e:
        print(f"Erro ao buscar sorteio {numero}: {e}")
        return None


def buscar_ultimo_numero() -> Optional[int]:
    """Busca o número do último sorteio."""
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/latest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()['concurso']
    except Exception as e:
        print(f"Erro ao buscar último sorteio: {e}")
        return None


def buscar_ultimos_sorteios(quantidade: int = 10) -> List[Sorteio]:
    """Busca os últimos sorteios, usando cache quando disponível."""
    cache = carregar_cache()
    sorteios = []
    cache_atualizado = False
    
    ultimo_numero = buscar_ultimo_numero()
    if ultimo_numero is None:
        # Usa o maior número do cache
        if cache:
            ultimo_numero = max(cache.keys())
            print(f"Usando cache. Último sorteio em cache: {ultimo_numero}")
        else:
            print("Não foi possível obter sorteios.")
            return []
    
    for i in range(quantidade):
        numero = ultimo_numero - i
        
        if numero in cache:
            sorteios.append(cache[numero])
        else:
            sorteio = buscar_sorteio_api(numero)
            if sorteio:
                sorteios.append(sorteio)
                cache[numero] = sorteio
                cache_atualizado = True
    
    if cache_atualizado:
        salvar_cache(cache)
        print(f"[cache] Atualizado com {len(cache)} sorteios salvos")
    else:
        print(f"[cache] Usando {len(sorteios)} sorteios do cache")
    
    return sorteios


def verificar_acertos(jogo: Jogo, sorteio: Sorteio) -> int:
    """Retorna quantidade de acertos entre o jogo e o sorteio."""
    return len(jogo.dezenas & sorteio.dezenas)


def calcular_premio(acertos: int, sorteio: Sorteio) -> float:
    """Calcula o prêmio baseado nos acertos."""
    if acertos < 11:
        return 0.0
    return sorteio.premios.get(acertos, PREMIOS_TIPICOS.get(acertos, 0.0))


def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def calcular_meses_de_sorteios(sorteios: List[Sorteio]) -> int:
    """Calcula quantos meses distintos os sorteios abrangem."""
    meses = set()
    for sorteio in sorteios:
        try:
            # Formato esperado: DD/MM/YYYY
            partes = sorteio.data.split('/')
            if len(partes) == 3:
                mes_ano = f"{partes[1]}/{partes[2]}"
                meses.add(mes_ano)
        except:
            pass
    return max(1, len(meses))


def main():
    import sys
    
    arquivo_jogos = sys.argv[1] if len(sys.argv) > 1 else "tickets_20_15_cov14_grasp.txt"
    num_sorteios = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print("=" * 80)
    print("VERIFICADOR DE JOGOS LOTOFÁCIL")
    print("=" * 80)
    print(f"\nCarregando jogos de: {arquivo_jogos}")
    
    jogos = carregar_jogos(arquivo_jogos)
    print(f"Total de jogos carregados: {len(jogos)}")
    
    print(f"\nBuscando os últimos {num_sorteios} sorteios...")
    sorteios = buscar_ultimos_sorteios(num_sorteios)
    
    if not sorteios:
        print("Não foi possível buscar os sorteios. Verifique sua conexão.")
        return
    
    print(f"Sorteios encontrados: {len(sorteios)}")
    
    # Calcular meses abrangidos
    num_meses = calcular_meses_de_sorteios(sorteios)
    
    print("\n" + "-" * 80)
    print("SORTEIOS ANALISADOS:")
    print("-" * 80)
    for sorteio in sorteios:
        dezenas_str = ', '.join(f"{d:02d}" for d in sorted(sorteio.dezenas))
        premios_str = " | ".join(f"{a}ac={formatar_moeda(v)}" for a, v in sorted(sorteio.premios.items()) if a >= 11)
        print(f"Concurso {sorteio.numero} ({sorteio.data}): {dezenas_str}")
        print(f"  Prêmios: {premios_str}")
    
    print("\n" + "=" * 80)
    print("ANÁLISE DOS JOGOS")
    print("=" * 80)
    
    total_ganhos = 0.0
    jogos_com_premio = 0
    detalhes_por_jogo = []
    acertos_geral = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
    ganhos_por_faixa = {11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0}
    
    for jogo in jogos:
        ganho_jogo = 0.0
        resultados_jogo = []
        
        for sorteio in sorteios:
            acertos = verificar_acertos(jogo, sorteio)
            
            if acertos >= 11:
                premio = calcular_premio(acertos, sorteio)
                acertos_geral[acertos] += 1
                ganhos_por_faixa[acertos] += premio
                resultados_jogo.append((sorteio.numero, acertos, premio))
                ganho_jogo += premio
        
        if ganho_jogo > 0:
            jogos_com_premio += 1
            total_ganhos += ganho_jogo
            detalhes_por_jogo.append((jogo, resultados_jogo, ganho_jogo))
    
    print("\nJOGOS COM PRÊMIOS (11+ acertos):")
    print("-" * 80)
    
    if not detalhes_por_jogo:
        print("Nenhum jogo teve 11+ acertos nos últimos sorteios.")
    else:
        detalhes_por_jogo.sort(key=lambda x: x[2], reverse=True)
        
        print(f"\nTop 20 jogos com maior retorno:")
        for jogo, resultados, ganho_total in detalhes_por_jogo[:20]:
            dezenas_str = ', '.join(f"{d:02d}" for d in sorted(jogo.dezenas))
            print(f"\nJogo {jogo.numero:03d}: {dezenas_str}")
            print(f"  Ganho total: {formatar_moeda(ganho_total)}")
            for concurso, acertos, premio in resultados:
                print(f"    • Concurso {concurso}: {acertos} acertos = {formatar_moeda(premio)}")
    
    print("\n" + "=" * 80)
    print("RESUMO GERAL")
    print("=" * 80)
    
    print(f"\nTotal de jogos analisados: {len(jogos)}")
    print(f"Total de sorteios verificados: {len(sorteios)}")
    print(f"Período abrangido: {num_meses} mês(es)")
    print(f"Jogos com 11+ acertos: {jogos_com_premio}")
    
    print("\nDistribuição de acertos (todos os jogos x todos os sorteios):")
    print("-" * 50)
    print(f"{'Acertos':<10} {'Ocorrências':<15} {'Ganho Total':<20}")
    print("-" * 50)
    for acertos in [11, 12, 13, 14, 15]:
        count = acertos_geral[acertos]
        ganho = ganhos_por_faixa[acertos]
        print(f"{acertos:<10} {count:<15} {formatar_moeda(ganho):<20}")
    print("-" * 50)
    
    print(f"\nTOTAL DE GANHOS: {formatar_moeda(total_ganhos)}")
    
    if jogos_com_premio > 0:
        media_por_jogo_premiado = total_ganhos / jogos_com_premio
        print(f"Média por jogo premiado: {formatar_moeda(media_por_jogo_premiado)}")
    
    media_por_jogo = total_ganhos / len(jogos) if jogos else 0
    print(f"Média por jogo (todos): {formatar_moeda(media_por_jogo)}")
    
    # Análise Financeira - custo por concurso
    custo_por_jogo = CUSTO_JOGO_15
    custo_por_concurso = len(jogos) * custo_por_jogo
    num_concursos = len(sorteios)
    custo_total = custo_por_concurso * num_concursos
    lucro = total_ganhos - custo_total
    
    print(f"\n" + "=" * 80)
    print("ANÁLISE FINANCEIRA")
    print("=" * 80)
    print(f"\nCusto por jogo (15 números): {formatar_moeda(custo_por_jogo)}")
    print(f"Quantidade de jogos: {len(jogos)}")
    print(f"Custo por concurso: {formatar_moeda(custo_por_concurso)}")
    print(f"Concursos simulados: {num_concursos}")
    print(f"Custo total ({num_concursos} concursos): {formatar_moeda(custo_total)}")
    print("-" * 50)
    print(f"Ganho total: {formatar_moeda(total_ganhos)}")
    print(f"LUCRO/PREJUÍZO: {formatar_moeda(lucro)}")
    
    if custo_total > 0:
        retorno = (total_ganhos / custo_total) * 100
        print(f"Retorno sobre investimento: {retorno:.2f}%")
    
    # Médias por concurso
    if num_concursos > 0:
        ganho_medio_por_concurso = total_ganhos / num_concursos
        custo_medio_por_concurso = custo_por_concurso
        lucro_medio_por_concurso = (total_ganhos - custo_total) / num_concursos
        print(f"\n--- MÉDIAS POR CONCURSO ---")
        print(f"Ganho médio por concurso: {formatar_moeda(ganho_medio_por_concurso)}")
        print(f"Custo por concurso: {formatar_moeda(custo_medio_por_concurso)}")
        print(f"Lucro médio por concurso: {formatar_moeda(lucro_medio_por_concurso)}")


if __name__ == "__main__":
    main()
