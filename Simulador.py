"""
Simulador.py - Rotina principal do simulador (TR1 - UnB)

Como executar:

    streamlit run Simulador.py

Cada mensagem do chat percorre o caminho da Figura 1 do enunciado:

    Thread transmissora (TX):  aplicação -> enlace -> física --+
                                                               |
                                            meio de comunicação (ruído)
                                                               |
    Thread receptora (RX):     aplicação <- enlace <- física <-+

As duas threads guardam a saída de cada etapa em dicionários, e a interface
gráfica (InterfaceGUI.py) mostra esses dicionários na tela.
"""

import queue
import random
import threading
import time

import CamadaEnlace
import CamadaFisica
import InterfaceGUI


# Aviso que a thread transmissora coloca no meio quando não há mais quadros
FIM_DA_TRANSMISSAO = None


# =============================================================================
# Camada de aplicação: conversão entre texto e bits
# =============================================================================

def adaptar_texto(texto):
    """Troca por '?' os caracteres que não cabem em 8 bits (emojis, por exemplo)."""
    adaptado = ''
    for caractere in texto:
        if ord(caractere) <= 255:
            adaptado += caractere
        else:
            adaptado += '?'
    return adaptado


def texto_para_bits(texto):
    """Codificador em bits: cada caractere vira os 8 bits do seu código na tabela ASCII."""
    bits = ''
    for caractere in texto:
        bits += format(ord(caractere), '08b')
    return bits


def bits_para_texto(bits):
    """Conversor de bits em texto: cada grupo de 8 bits volta a ser um caractere."""
    texto = ''
    quantidade_de_bytes = len(bits) // 8
    for numero_do_byte in range(quantidade_de_bytes):
        inicio = numero_do_byte * 8
        byte = bits[inicio:inicio + 8]
        texto += chr(int(byte, 2))
    return texto


def dividir_em_pedacos(texto, tamanho_maximo):
    """Corta o texto em pedaços de no máximo `tamanho_maximo` caracteres (1 pedaço = 1 quadro)."""
    pedacos = []
    for inicio in range(0, len(texto), tamanho_maximo):
        pedacos.append(texto[inicio:inicio + tamanho_maximo])
    return pedacos


# =============================================================================
# Transmissor, meio de comunicação e receptor (para um quadro)
# =============================================================================

def transmitir_quadro(texto, config):
    """Lado transmissor: leva um pedaço de texto da aplicação até o sinal elétrico."""
    amplitude = config['amplitude']
    portadora = config['modulacao_por_portadora']

    # Camada de aplicação
    bits_da_aplicacao = texto_para_bits(texto)

    # Camada de enlace: primeiro enquadra, depois anexa o código de erro
    quadro = CamadaEnlace.enquadrar(bits_da_aplicacao, config['enquadramento'])
    quadro_com_edc = CamadaEnlace.adicionar_edc(quadro, config['edc'], config['tamanho_do_checksum'])

    # Camada física
    if portadora == CamadaFisica.SEM_PORTADORA:
        # transmissão em banda base: o sinal do codificador vai direto para o meio
        sinal_banda_base = CamadaFisica.codificar_banda_base(
            quadro_com_edc, config['modulacao_digital'], amplitude)
        sinal_modulado = []
        sinal_transmitido = sinal_banda_base
    else:
        # com portadora: o codificador banda base gera o NRZ que alimenta o modulador
        sinal_banda_base = CamadaFisica.codificar_nrz_polar(quadro_com_edc, amplitude)
        sinal_modulado = CamadaFisica.modular(
            sinal_banda_base, portadora, amplitude, config['frequencia'])
        sinal_transmitido = sinal_modulado

    return {
        'texto': texto,
        'bits_da_aplicacao': bits_da_aplicacao,
        'quadro': quadro,
        'quadro_com_edc': quadro_com_edc,
        'sinal_banda_base': sinal_banda_base,
        'sinal_modulado': sinal_modulado,
        'sinal_transmitido': sinal_transmitido,
    }


def meio_de_comunicacao(sinal, quantidade_de_bits, config, fila_do_receptor):
    """Leva o sinal do transmissor até o receptor, somando ruído no caminho.

    O ruído é somado à tensão (em volts) de cada amostra e vem de uma variável
    aleatória gaussiana n(média, desvio padrão).

    O receptor também é avisado de quantos bits o quadro tem, porque o 8PSK e o
    32-QAM completam o último símbolo com zeros que não fazem parte do quadro.
    """
    sinal_com_ruido = []
    for tensao in sinal:
        ruido = random.gauss(config['media_do_ruido'], config['desvio_do_ruido'])
        sinal_com_ruido.append(tensao + ruido)
    fila_do_receptor.put((sinal_com_ruido, quantidade_de_bits))


def receber_quadro(sinal_recebido, quantidade_de_bits, config):
    """Lado receptor: leva o sinal que chegou do meio de volta até o texto."""
    amplitude = config['amplitude']
    portadora = config['modulacao_por_portadora']

    # Camada física
    if portadora == CamadaFisica.SEM_PORTADORA:
        sinal_banda_base = sinal_recebido
        bits_recebidos = CamadaFisica.decodificar_banda_base(
            sinal_banda_base, config['modulacao_digital'], amplitude)
    else:
        # o demodulador devolve um sinal NRZ, que o decodificador banda base lê
        sinal_banda_base = CamadaFisica.demodular(
            sinal_recebido, portadora, amplitude, config['frequencia'])
        bits_recebidos = CamadaFisica.decodificar_nrz_polar(sinal_banda_base)

    # descarta os zeros usados para completar o último símbolo
    bits_recebidos = bits_recebidos[:quantidade_de_bits]

    # Camada de enlace: primeiro confere o código de erro, depois desenquadra
    quadro, erro_detectado, bits_corrigidos = CamadaEnlace.verificar_edc(
        bits_recebidos, config['edc'], config['tamanho_do_checksum'])
    bits_da_aplicacao, aviso_do_enquadramento = CamadaEnlace.desenquadrar(
        quadro, config['enquadramento'])

    # Camada de aplicação
    texto = bits_para_texto(bits_da_aplicacao)

    return {
        'sinal_recebido': sinal_recebido,
        'sinal_banda_base': sinal_banda_base,
        'bits_recebidos': bits_recebidos,
        'quadro': quadro,
        'erro_detectado': erro_detectado,
        'bits_corrigidos': bits_corrigidos,
        'aviso_do_enquadramento': aviso_do_enquadramento,
        'bits_da_aplicacao': bits_da_aplicacao,
        'texto': texto,
    }


# =============================================================================
# Threads TX e RX
# =============================================================================

def thread_transmissora(texto, config, fila_do_receptor, quadros_tx):
    """Thread TX: divide a mensagem em quadros e envia um de cada vez pelo meio."""
    try:
        for pedaco in dividir_em_pedacos(texto, config['tamanho_maximo_do_quadro']):
            saida = transmitir_quadro(pedaco, config)
            quadros_tx.append(saida)
            quantidade_de_bits = len(saida['quadro_com_edc'])
            meio_de_comunicacao(saida['sinal_transmitido'], quantidade_de_bits,
                                config, fila_do_receptor)
    finally:
        # mesmo se algo der errado, avisa o receptor para ele não esperar para sempre
        fila_do_receptor.put(FIM_DA_TRANSMISSAO)


def thread_receptora(config, fila_do_receptor, quadros_rx):
    """Thread RX: espera os sinais chegarem do meio e processa cada um."""
    while True:
        chegada = fila_do_receptor.get()
        if chegada is FIM_DA_TRANSMISSAO:
            break
        sinal_recebido, quantidade_de_bits = chegada
        saida = receber_quadro(sinal_recebido, quantidade_de_bits, config)
        quadros_rx.append(saida)


def enviar_mensagem(remetente, texto, config):
    """Simula o envio de uma mensagem do chat de uma estação para a outra.

    Quem escreve a mensagem é o transmissor e a outra estação é o receptor.
    Devolve um dicionário com tudo o que a interface precisa mostrar.
    """
    if remetente == 'A':
        destinatario = 'B'
    else:
        destinatario = 'A'

    texto = adaptar_texto(texto)
    fila_do_receptor = queue.Queue()
    quadros_tx = []
    quadros_rx = []

    transmissora = threading.Thread(
        target=thread_transmissora, args=(texto, config, fila_do_receptor, quadros_tx))
    receptora = threading.Thread(
        target=thread_receptora, args=(config, fila_do_receptor, quadros_rx))
    receptora.start()
    transmissora.start()
    transmissora.join()
    receptora.join()

    # a mensagem recebida é a junção do texto de todos os quadros
    texto_recebido = ''
    for quadro in quadros_rx:
        texto_recebido += quadro['texto']

    return {
        'remetente': remetente,
        'destinatario': destinatario,
        'horario': time.strftime('%H:%M:%S'),
        'config': config,
        'texto_enviado': texto,
        'texto_recebido': texto_recebido,
        'quadros_tx': quadros_tx,
        'quadros_rx': quadros_rx,
    }


# =============================================================================
# Rotina principal
# =============================================================================

def main():
    """Desenha a tela, simula as mensagens que acabaram de ser digitadas e mostra o resultado."""
    if not InterfaceGUI.executando_no_streamlit():
        print('Este simulador usa interface gráfica. Execute com:  streamlit run Simulador.py')
        return

    InterfaceGUI.preparar_pagina()
    config = InterfaceGUI.desenhar_configuracao()
    historico = InterfaceGUI.obter_historico()

    areas_das_conversas, mensagens_digitadas = InterfaceGUI.desenhar_chat(historico)
    for remetente, texto in mensagens_digitadas:
        mensagem = enviar_mensagem(remetente, texto, config)
        historico.append(mensagem)

    InterfaceGUI.mostrar_conversas(areas_das_conversas, historico)
    InterfaceGUI.mostrar_detalhes(historico)


if __name__ == '__main__':
    main()
