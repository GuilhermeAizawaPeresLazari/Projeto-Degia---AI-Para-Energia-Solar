# Machine Learning

Esta pasta será usada na próxima etapa.

Fluxo planejado:

1. OpenDSS gera cenários elétricos.
2. Resultados são transformados em dataset.
3. Python/Pandas realiza limpeza e preparação.
4. Treinar:
   - Regressão Linear
   - Random Forest
   - XGBoost
5. Comparar:
   - MAE
   - RMSE
   - R²
6. Salvar modelo treinado.
7. Integrar modelo ao FastAPI.

Variável-alvo planejada:

`tensao_resultado_pu`

Entradas candidatas:

- potencia_fv_kwp
- geracao_fv_kw
- irradiancia_w_m2
- carga_kw
- hora
- no_rede
- fator_potencia
- tensao_inicial_pu
