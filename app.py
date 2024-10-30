from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import numpy as np
import joblib
import requests
from tensorflow.keras.models import load_model
import os
from datetime import datetime, timedelta

app = FastAPI()

# Variáveis de configuração
cidade = "Rio de Janeiro"
api_key = "af14a5d98cd1cc1fc38ce560697d2727"
tempo_atualizacao_clima = timedelta(minutes=10)
dados_clima_cache = None
ultima_atualizacao_clima = datetime.min

# Carregar todos os modelos ao iniciar o aplicativo
modelos_scalers_cache = {}

# Função para carregar o modelo (adicionada)
def carregar_modelo(joblib_path, keras_path):
    if os.path.exists(keras_path):
        return load_model(keras_path)
    elif os.path.exists(joblib_path):
        return joblib.load(joblib_path)
    else:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")

def carregar_modelos_scalers(chiller_num):
    if chiller_num not in modelos_scalers_cache:
        pathProd = f'ModelsDeploy/chiller{chiller_num}/'
        modelos_scalers_cache[chiller_num] = {
            'corrente': (carregar_modelo(f'{pathProd}ur_correnteMotor/model.pkl', f'{pathProd}ur_correnteMotor/model.h5'), joblib.load(f'{pathProd}ur_correnteMotor/scaler.pkl')),
            'ligados': (carregar_modelo(f'{pathProd}Fancoil_ligado_%/model.pkl', f'{pathProd}Fancoil_ligado_%/model.h5'), joblib.load(f'{pathProd}Fancoil_ligado_%/scaler.pkl')),
            'vag': (carregar_modelo(f'{pathProd}VAG_Aberta_%/model.pkl', f'{pathProd}VAG_Aberta_%/model.h5'), joblib.load(f'{pathProd}VAG_Aberta_%/scaler.pkl')),
            'deltaAC': (carregar_modelo(f'{pathProd}delta_AC/model.pkl', f'{pathProd}delta_AC/model.h5'), joblib.load(f'{pathProd}delta_AC/scaler.pkl')),
            'TR': (carregar_modelo(f'{pathProd}TR/model.pkl', f'{pathProd}TR/model.h5'), joblib.load(f'{pathProd}TR/scaler.pkl')),
            'KWH': (carregar_modelo(f'{pathProd}ur_kwh/model.pkl', f'{pathProd}ur_kwh/model.h5'), joblib.load(f'{pathProd}ur_kwh/scaler.pkl')),
            'torre3': (carregar_modelo(f'{pathProd}Torre_3/model.pkl', f'{pathProd}Torre_3/model.h5'), joblib.load(f'{pathProd}Torre_3/scaler.pkl'))
        }
    return modelos_scalers_cache[chiller_num]

# Função para obter e atualizar dados climáticos
def obter_dados_climaticos():
    global dados_clima_cache, ultima_atualizacao_clima
    if datetime.now() - ultima_atualizacao_clima > tempo_atualizacao_clima:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric"
            resposta = requests.get(url)
            resposta.raise_for_status()
            dados_clima = resposta.json()
            dados_clima_cache = (
                dados_clima['main']['pressure'],
                dados_clima['main']['humidity'],
                dados_clima['main']['temp']
            )
            ultima_atualizacao_clima = datetime.now()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Erro ao obter dados climáticos: {e}")
    return dados_clima_cache

# Classe de entrada
class PrevisaoInput(BaseModel):
    ur_temp_saida: float
    chiller: int  # 1 ou 2 para especificar o chiller desejado

# Classe de saída com campos adicionais
class PrevisaoOutput(BaseModel):
    corrente: float
    vag: float
    ligados: float
    delta_ac: float
    tr: float
    kwh: float
    torre: float
    temperatura: float
    pressao: float
    umidade: float
    horario_comercial: int
    fim_de_semana: int
    data_hora: str  # Campo para data e hora

# Função para verificar se é final de semana e horário comercial
def verificar_data_horario():
    data_hora = datetime.now()
    return 1 if data_hora.weekday() >= 5 else 0, 1 if 8 <= data_hora.hour < 17 else 0

# Função de previsão com base nos scalers e modelos
def calcular_previsoes(scaler, model, *args):
    input_data = np.array([args])
    input_data_scaled = scaler.transform(input_data)
    return model.predict(input_data_scaled).flatten()[0]

# Endpoint único para previsões dos Chillers 1 e 2
@app.post("/previsao/chiller", response_model=PrevisaoOutput)
async def previsao_chiller(dados: PrevisaoInput):
    try:
        if dados.chiller not in [1, 2]:
            raise HTTPException(status_code=400, detail="Chiller inválido. Escolha 1 ou 2.")

        modelos_scalers = carregar_modelos_scalers(dados.chiller)
        pressao, umidade, temperatura = obter_dados_climaticos()
        fim_de_semana, horario_comercial = verificar_data_horario()

        previsaoLigados = calcular_previsoes(modelos_scalers['ligados'][1], modelos_scalers['ligados'][0], pressao, temperatura, umidade, fim_de_semana, horario_comercial)
        previsaoVAG = calcular_previsoes(modelos_scalers['vag'][1], modelos_scalers['vag'][0], pressao, temperatura, umidade, fim_de_semana, horario_comercial, previsaoLigados)
        previsaodeltaAC = calcular_previsoes(modelos_scalers['deltaAC'][1], modelos_scalers['deltaAC'][0], pressao, temperatura, umidade, dados.ur_temp_saida, previsaoVAG, previsaoLigados)
        previsaoTorre3 = calcular_previsoes(modelos_scalers['torre3'][1], modelos_scalers['torre3'][0], pressao, temperatura, umidade, previsaodeltaAC, previsaoVAG)
        previsaoTR = calcular_previsoes(modelos_scalers['TR'][1], modelos_scalers['TR'][0], pressao, temperatura, umidade, previsaodeltaAC, previsaoVAG, dados.ur_temp_saida, fim_de_semana, horario_comercial, previsaoLigados, previsaoTorre3)
        previsaoKWH = calcular_previsoes(modelos_scalers['KWH'][1], modelos_scalers['KWH'][0], pressao, temperatura, umidade, previsaodeltaAC, previsaoTR, dados.ur_temp_saida, previsaoVAG, previsaoTorre3, previsaoLigados)
        previsaoCorrente = calcular_previsoes(modelos_scalers['corrente'][1], modelos_scalers['corrente'][0], pressao, temperatura, umidade, dados.ur_temp_saida, previsaoTR, previsaodeltaAC, previsaoVAG, previsaoLigados, previsaoKWH, previsaoTorre3)

        data_hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return PrevisaoOutput(
            corrente=previsaoCorrente,
            vag=previsaoVAG,
            ligados=previsaoLigados,
            delta_ac=previsaodeltaAC,
            tr=previsaoTR,
            kwh=previsaoKWH,
            torre=previsaoTorre3,
            temperatura=temperatura,
            pressao=pressao,
            umidade=umidade,
            horario_comercial=horario_comercial,
            fim_de_semana=fim_de_semana,
            data_hora=data_hora_atual
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Hello, Render!"}