# Arquitetura DEGIA — MVP 0.3

```text
Projeto
├── Localização
│   ├── UF
│   ├── Município
│   └── Concessionária
├── Dados FV
│   ├── Potência instalada
│   ├── Carga local
│   ├── Tensão de referência
│   └── Fator de potência
└── Rede simulada
    ├── IEEE 13-Bus
    └── Nó de referência

Projeto
   ↓
Cenários operacionais
   ├── geração FV
   ├── carga
   ├── irradiância automática por localidade
   ├── nó herdado da rede simulada
   └── fator de potência herdado do projeto
   ↓
OpenDSS (próxima etapa)
   ↓
tensão / resultados
   ↓
PostgreSQL
   ↓
Dashboard
   ↓
Machine Learning (etapa posterior)
```

## Regra importante

- A **irradiância** é dependente da localidade e, no MVP 0.3, pode ser consultada automaticamente.
- O **nó** é um elemento do modelo elétrico simulado, portanto não é deduzido apenas pela UF/município.
- O **fator de potência** é configuração do projeto/inversor, e não característica geográfica.
- O campo **hora** foi retirado da interface e do modelo de API desta versão.
