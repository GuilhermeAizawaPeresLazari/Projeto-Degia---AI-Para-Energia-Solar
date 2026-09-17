# OpenDSS

Esta pasta será usada para o modelo elétrico.

Próximos passos:

1. Carregar o IEEE 13-Bus.
2. Validar fluxo de potência base.
3. Adicionar geração fotovoltaica.
4. Variar:
   - potência FV
   - carga
   - irradiância
   - ponto da rede
   - fator de potência
5. Extrair tensão em pu.
6. Exportar resultados.
7. Alimentar o dataset do Machine Learning.

O resultado do OpenDSS poderá depois ser persistido na tabela `cenario`
com:

`origem_resultado = 'OPENDSS'`
