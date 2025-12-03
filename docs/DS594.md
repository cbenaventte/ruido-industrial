## 🎯 Fundamentos Acústicos DS 594
**Autor:** Carlos Benavente – Experto en Acústica y Data Engineering
### Marco Normativo

El **Decreto Supremo 594** (Chile) establece las condiciones sanitarias y ambientales básicas en los lugares de trabajo. El **Artículo 75** regula específicamente la exposición ocupacional a ruido con criterios basados en la norma internacional **ISO 1999**.

### Parámetros Normativos Clave

#### 1. Límite de Exposición Diaria (LED)

```
Nivel máximo: 85 dB(A) para 8 horas de exposición continua
```

**Fundamento acústico**: La exposición a niveles de presión sonora superiores a 85 dB(A) durante períodos prolongados puede causar **Pérdida Auditiva Inducida por Ruido (PAIR)**, una enfermedad profesional irreversible..

#### 2. Factor de Intercambio (Exchange Rate)

```
Factor: 3 dB
Regla: Por cada 3 dB de aumento, el tiempo permitido se reduce a la mitad
```

**Tabla oficial DS 594**:

| Nivel dB(A) | Tiempo Permitido |
|-------------|------------------|
| 85          | 8 horas          |
| 88          | 4 horas          |
| 91          | 2 horas          |
| 94          | 1 hora           |
| 97          | 30 minutos       |
| 100         | 15 minutos       |

**Fórmula matemática**:

```
T(L) = 8 × 2^((85 - L) / 3)

donde:
  T = Tiempo permitido (horas)
  L = Nivel de presión sonora LAeq (dB)
```

#### 3. Dosis de Ruido

La **dosis** representa el porcentaje de exposición permitida consumido durante la jornada:

```
Dosis (%) = Σ(Ti / TPi) × 100

donde:
  Ti  = Tiempo real de exposición al nivel i
  TPi = Tiempo permitido para el nivel i según DS 594
```

**Criterio de cumplimiento**:
- ✅ Dosis ≤ 100% → Cumple
- ❌ Dosis > 100% → Excede exposición permitida → Obligatorio actuar

**Ejemplo práctico**:

```python
# Exposición mixta durante jornada de 8 horas
# 6 horas a 86 dB + 2 horas a 90 dB

T_permitido_86 = 8 × 2^((85-86)/3) = 6.35 horas
T_permitido_90 = 8 × 2^((85-90)/3) = 2.52 horas

Dosis = (6/6.35 + 2/2.52) × 100 = 173.9%

# Resultado: EXCEDE el límite (requiere acción inmediata)
```

#### 4. Nivel de Exposición Diaria (Lex,8h)

El **Lex,8h** representa el nivel sonoro equivalente al que estaría expuesto un trabajador durante **8 horas completas**, aunque la exposición real haya sido de duración variable.

```
Lex,8h = 10 × log₁₀( Σ(10^(LAeq,i/10) × ti) / 8 )

donde:
  `LAeq,i` = nivel equivalente del intervalo i
  `ti`     = duración del intervalo i (en horas)
  `8`      = jornada de referencia (horas)
```

**Interpretación física**: 
- 4 horas a 91 dB(A) → Lex,8h = **88 dB(A)**
- Significa: *"Esa exposición de 4 horas equivale energéticamente a estar 8 horas completas expuesto a 88 dB(A)"*

**Ejemplo de cálculo**:
```python
energía_total = 10^(91/10) × 4 horas
Lex,8h = 10 × log₁₀(energía_total / 8) = 88.0 dB(A)

#### 5. Nivel de Presión Sonora Peak

```
Límite absoluto: 140 dB(C)
```

Representa el **nivel instantáneo máximo** permitido. Niveles superiores pueden causar **trauma acústico agudo** (daño inmediato al oído interno).

#### 6. Nivel de Acción

```
Nivel de acción: 82 dB(A)
```

**Propósito**: Umbral preventivo que obliga a:
- Implementar medidas de control
- Proveer EPP (Equipos de Protección Personal)
- Realizar vigilancia médica (audiometrías)

---



### Componentes Principales

#### 1. **Producer (sensor_simulator.py)**

**Responsabilidad**: Simular sensores acústicos industriales generando datos sintéticos realistas.

**Características técnicas**:
- Frecuencia de muestreo: 5 segundos (ajustable)
- Generación de espectro de octavas (125 Hz - 8 kHz)
- Inyección de anomalías controladas (2% probabilidad):
  - Spikes: Picks súbitos (+8 a +15 dB)
  - Drift: Deriva gradual (+3 a +8 dB)
  - Off-hours: Actividad fuera de horario
- Publicación a Kafka topic: `acoustic-raw-data`

**Parámetros acústicos generados**:
```python
{
    "LAeq": 86.2,           # Nivel equivalente continuo
    "LPeak": 98.5,          # Nivel peak instantáneo
    "L10": 89.2,            # Nivel superado 10% del tiempo
    "L90": 81.3,            # Nivel superado 90% del tiempo
    "espectro_octavas": [   # Niveles por banda de octava
        85.2, 87.1, 88.5, 89.0, 87.8, 85.6, 82.1
    ],
    "frecuencia_dominante": 2000  # Hz
}
```

#### 2. **Consumer (stream_processor_v2.py)**

**Responsabilidad**: Procesamiento en tiempo real y cálculos normativos DS 594.

**Pipeline de procesamiento**:

```
Mensaje Kafka
    │
    ▼
1. Validación de datos
    │
    ▼
2. Buffer temporal (ventana 8h)
    │
    ▼
3. Cálculo de métricas DS 594
    │   ├─ Dosis acumulada
    │   ├─ Lex,8h normalizado
    │   └─ Tiempo permitido restante
    │
    ▼
4. Detección de anomalías (ML)
    │   └─ Isolation Forest
    │
    ▼
5. Evaluación de cumplimiento
    │   ├─ Dosis > 100%? → Alerta CRÍTICA
    │   ├─ Lex,8h > 85 dB? → Alerta ALTA
    │   └─ LPeak > 140 dB? → Alerta CRÍTICA
    │
    ▼
6. Persistencia dual
    │   ├─ InfluxDB (métricas en tiempo real)
    │   └─ PostgreSQL (alertas, eventos, reportes)
```

**Implementación de Cálculos DS 594**:

```python
class DS594Calculator:
    """Cálculos 100% conformes con DS 594"""
    
    LIMITE_8H = 85.0        # dB(A)
    NIVEL_ACCION = 82.0     # dB(A)
    PEAK_MAXIMO = 140.0     # dB(C)
    FACTOR_CAMBIO = 3.0     # dB
    
    @staticmethod
    def calculate_permitted_time(level_db: float) -> float:
        """
        Tiempo permitido según DS 594
        T(L) = 8 × 2^((85 - L) / 3)
        """
        permitted = 8.0 * (2 ** ((85.0 - level_db) / 3.0))
        return permitted if permitted < 100000 else float('inf')
    
    @staticmethod
    def calculate_dose(levels_db: List[float], 
                      durations_hours: List[float]) -> float:
        """
        Dosis = Σ(Ti / TPi) × 100%
        """
        total_dose = 0.0
        for level, duration in zip(levels_db, durations_hours):
            permitted = DS594Calculator.calculate_permitted_time(level)
            if permitted > 0 and permitted != float('inf'):
                total_dose += (duration / permitted) * 100
        return round(total_dose, 2)
    
    @staticmethod
    def calculate_lex8h(measurements: List[Dict], 
                       sample_duration_seconds: float) -> float:
        """
        Lex,8h = 10 × log10((1/8) × Σ(10^(LAeq_i/10) × ti))
        """
        T0 = 8.0  # Jornada de referencia
        total_energy = 0.0
        
        for i in range(1, len(measurements)):
            m_prev, m_curr = measurements[i-1], measurements[i]
            level = m_curr['metrics']['LAeq']
            
            # Calcular duración real entre mediciones
            t_prev = datetime.fromisoformat(m_prev['timestamp'][:-1])
            t_curr = datetime.fromisoformat(m_curr['timestamp'][:-1])
            duration_hours = (t_curr - t_prev).total_seconds() / 3600.0
            
            energy = (10 ** (level / 10)) * duration_hours
            total_energy += energy
        
        lex8h = 10 * np.log10(total_energy / T0)
        return round(lex8h, 1)
```

#### 3. **Detección de Anomalías con Machine Learning**

**Algoritmo**: Isolation Forest (scikit-learn)

**Fundamento**: Detecta patrones atípicos en la exposición acústica que podrían indicar:
- Mal funcionamiento de maquinaria
- Eventos no planificados
- Errores de medición
- Cambios en procesos productivos

**Features extraídos**:
```python
features = [
    LAeq,                           # Nivel equivalente
    LPeak,                          # Nivel peak
    L10,                            # Percentil 10%
    L90,                            # Percentil 90%
    max(espectro_octavas),         # Banda más energética
    std(espectro_octavas)          # Variabilidad espectral
]
```

**Configuración**:
```python
model = IsolationForest(
    contamination=0.05,     # 5% de datos esperados como anomalías
    n_estimators=100,       # Número de árboles de decisión
    random_state=42
)
```

**Niveles de confianza**:
- **High** (score < -0.5): Anomalía muy probable → Investigar inmediatamente
- **Medium** (score < -0.3): Posible anomalía → Monitorear
- **Low** (score ≥ -0.3): Probablemente normal

---

## 🔬 Implementación Técnica DS 594

### Desafíos Técnicos Resueltos

#### 1. **Ventanas Temporales Móviles**

**Problema**: DS 594 exige evaluar exposición sobre jornadas de 8 horas, pero los datos llegan cada 5 segundos.

**Solución implementada**:

```python
class StreamProcessor:
    def __init__(self):
        # Buffer de 8 horas por sensor
        # 8h × 3600s/h ÷ 5s = 5,760 muestras
        self.sensor_buffers = defaultdict(lambda: deque(maxlen=5760))
        
    def _prune_old_data(self, sensor_id: str):
        """Mantiene solo datos de últimas 8 horas"""
        buffer = self.sensor_buffers[sensor_id]
        cutoff = datetime.utcnow() - timedelta(hours=8)
        
        while buffer and datetime.fromisoformat(
            buffer[0]['timestamp'][:-1]
        ) < cutoff:
            buffer.popleft()
```

**Ventaja**: Permite cálculo continuo de dosis sin necesidad de esperar fin de jornada.

#### 2. **Reset Diario de Jornada**

**Problema**: La dosis debe reiniciarse al inicio de cada jornada laboral.

**Solución**:

```python
def _prune_old_data(self, sensor_id: str):
    today = datetime.utcnow().date()
    
    # Reset a medianoche
    if today != self.last_reset:
        print(f"🔄 Reset diario - Nueva jornada: {today}")
        self.last_reset = today
        
        # Limpiar todos los buffers
        for buf in self.sensor_buffers.values():
            buf.clear()
```

#### 3. **Cálculo con Timestamps Reales**

**Problema**: No se puede asumir intervalos fijos entre mediciones (pueden haber interrupciones).

**Solución**:

```python
def calculate_dose_from_measurements(measurements: List[Dict]) -> float:
    total_dose = 0.0
    
    for i in range(1, len(measurements)):
        m_prev, m_curr = measurements[i-1], measurements[i]
        level = m_curr['metrics']['LAeq']
        
        # Duración REAL entre mediciones
        t_prev = datetime.fromisoformat(m_prev['timestamp'][:-1])
        t_curr = datetime.fromisoformat(m_curr['timestamp'][:-1])
        duration_hours = (t_curr - t_prev).total_seconds() / 3600.0
        
        permitted = get_permitted_time(level)
        if permitted > 0:
            total_dose += (duration_hours / permitted) * 100
    
    return round(total_dose, 2)
```

**Ventaja**: Maneja correctamente paradas de producción, desconexiones temporales, etc.

#### 4. **Normalización Lex,8h**

**Problema**: Diferentes duraciones de exposición deben normalizarse a 8 horas de referencia.

**Solución**:

```python
def calculate_lex8h(measurements: List[Dict]) -> float:
    """
    Normaliza cualquier exposición a nivel equivalente de 8 horas
    """
    T0 = 8.0  # Jornada de referencia DS 594
    total_energy = 0.0
    
    for i in range(1, len(measurements)):
        # ... calcular duration_hours (ver código arriba)
        
        # Acumular energía sonora
        energy = (10 ** (level / 10)) * duration_hours
        total_energy += energy
    
    # Normalizar a 8 horas
    lex8h = 10 * np.log10(total_energy / T0)
    return round(lex8h, 1)
```

**Ejemplo**:
```python
# 4 horas a 91 dB
energy = 10^(91/10) × 4 = 5.04×10^9
Lex,8h = 10 × log10(5.04×10^9 / 8) = 88 dB(A)

# Interpretación: "4h a 91 dB ≡ 8h a 88 dB"
```

