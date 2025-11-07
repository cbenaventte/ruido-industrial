# Arquitectura del Sistema

## Diagrama de Componentes

```
┌────────────────────────────────────────────────────────────┐
│                     CAPA DE INGESTA                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Sensor 001  │  │  Sensor 002  │  │  Sensor 00N  │      │
│  │  (Simulado)  │  │  (Simulado)  │  │  (Simulado)  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                            │                               │
│                    ┌───────▼────────┐                      │
│                    │  Kafka Topic   │                      │
│                    │ acoustic-raw   │                      │
│                    └───────┬────────┘                      │
└────────────────────────────┼───────────── ─────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────┐
│                CAPA DE PROCESAMIENTO                      │
│                    ┌───────▼────────┐                     │
│                    │ Stream         │                     │
│                    │ Processor      │                     │
│                    │ (Kafka Consumer)│                    │
│                    └───────┬────────┘                     │
│                            │                              │
│         ┌──────────────────┼──────────────────┐           │
│         │                  │                  │           │
│  ┌──────▼──────┐  ┌────────▼────────┐  ┌─────▼─────┐      │
│  │ DS594 Calc  │  │ ML Anomaly      │  │  Alerting │      │
│  │             │  │ Detection       │  │  Engine   │      │
│  └──────┬──────┘  └────────┬────────┘  └─────┬─────┘      │
└─────────┼───────────────────┼─────────────────┼───────────┘
          │                   │                 │
┌─────────┼───────────────────┼─────────────────┼────────────┐
│                 CAPA DE ALMACENAMIENTO                     │
│  ┌──────▼──────┐      ┌────▼─────┐      ┌───▼──────┐       │
│  │  InfluxDB   │      │PostgreSQL│      │  Files   │       │
│  │ (Time-series)│     │(Relacional)│    │  (CSV)   │       │
│  └──────┬──────┘      └────┬─────┘      └───┬──────┘       │
└─────────┼──────────────────┼────────────────┼──────────────┘
          │                  │                │
┌─────────┼──────────────────┼────────────────┼──────────────┐
│              CAPA DE VISUALIZACIÓN                         │
│  ┌──────▼──────┐      ┌────▼─────┐                         │
│  │   Grafana   │      │Streamlit │                         │
│  │(Monitoring) │      │(Analysis)│                         │
│  └─────────────┘      └──────────┘                         │
└────────────────────────────────────────────────────────────┘
```

## Flujo de Datos

1. **Sensores simulados** generan datos acústicos cada 5 segundos
2. **Kafka** recibe y almacena eventos en topic
3. **Stream Processor** consume eventos y:
   - Calcula métricas DS 594
   - Detecta anomalías con ML
   - Genera alertas
4. **Almacenamiento**:
   - InfluxDB: Métricas temporales
   - PostgreSQL: Alertas y configuración
5. **Visualización**:
   - Grafana: Monitoreo 24/7
   - Streamlit: Análisis interactivo

## Tecnologías

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| Streaming | Apache Kafka | Message broker |
| Processing | Python + PyFlink | Stream processing |
| TSDB | InfluxDB 2.7 | Time-series storage |
| RDBMS | PostgreSQL 15 | Relational data |
| Monitoring | Grafana 10 | Real-time dashboards |
| Analysis | Streamlit | Interactive analytics |
| ML | scikit-learn | Anomaly detection |