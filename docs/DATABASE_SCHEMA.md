# 🗄️ Esquema de Base de Datos - PostgreSQL

## 📐 Diagrama Entidad-Relación

```
┌────────────────────────────────────────────────────────────────────┐
│                          SCHEMA: config                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────┐         ┌──────────────────────┐         │
│  │   config.sensors     │         │   config.zones       │         │
│  ├──────────────────────┤         ├──────────────────────┤         │
│  │ PK sensor_id         │         │ PK zone_id           │         │
│  │    zona              │◄────────┤    zone_name         │         │
│  │    descripcion       │         │    zone_type         │         │
│  │    lat, lon          │         │    custom_limit_laeq │         │
│  │    baseline_db       │         │    max_workers       │         │
│  │    is_active         │         └──────────────────────┘         │
│  │    status            │                                          │
│  │    metadata (JSONB)  │         ┌──────────────────────┐         │
│  └──────┬───────────────┘         │ config.ds594_limits  │         │
│         │                         ├──────────────────────┤         │
│         │                         │ PK id                │         │
│         │                         │    zona              │         │
│         │                         │    limit_type        │         │
│         │                         │    limit_value       │         │
│         │                         │    duration_hours    │         │
│         │                         └──────────────────────┘         │
│         │                                                          │
│         │                         ┌──────────────────────┐         │
│         │                         │   config.users       │         │
│         │                         ├──────────────────────┤         │
│         │                         │ PK id                │         │
│         │                         │    username          │         │
│         │                         │    email             │         │
│         │                         │    password_hash     │         │
│         │                         │    role              │         │
│         │                         │    is_active         │         │
│         │                         └──────────────────────┘         │
└─────────┼──────────────────────────────────────────────────────────┘
          │
          │ FK
          │
┌─────────┼─────────────────────────────────────────────────────────┐
│         │               SCHEMA: monitoring                        │
├─────────┼─────────────────────────────────────────────────────────┤
│         │                                                         │
│  ┌──────▼───────────────┐         ┌──────────────────────┐        │
│  │ monitoring.alerts    │         │ monitoring.events    │        │
│  ├──────────────────────┤         ├──────────────────────┤        │
│  │ PK id                │         │ PK id                │        │
│  │ FK sensor_id         │         │ FK sensor_id         │        │
│  │    timestamp         │         │    event_type        │        │
│  │    zona              │         │    description       │        │
│  │    alert_type        │         │    timestamp         │        │
│  │    severity          │         │    metadata (JSONB)  │        │
│  │    level_db          │         └──────────────────────┘        │
│  │    peak_db           │                                         │
│  │    message           │         ┌─────────────────────┐         │
│  │    acknowledged      │         │ monitoring.         │         │
│  │    acknowledged_by   │         │ maintenance_events  │         │
│  │    acknowledged_at   │         ├─────────────────────┤         │
│  └──────────────────────┘         │ PK id                         │
│                                   │ FK sensor_id         │        │
│                                   │    event_type        │        │
│                                   │    scheduled_at      │        │
│                                   │    status            │        │
│                                   └──────────────────────┘        │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                        SCHEMA: reporting                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐                                         │
│  │ reporting.           │                                         │
│  │ daily_reports        │                                         │
│  ├──────────────────────┤                                         │
│  │ PK id                │                                         │
│  │    report_date       │                                         │
│  │ FK sensor_id         │                                         │
│  │    zona              │                                         │
│  │    avg_LAeq          │                                         │
│  │    max_LAeq          │                                         │
│  │    max_LPeak         │                                         │
│  │    total_dose_%      │                                         │
│  │    ds594_violations  │                                         │
│  │    anomalies_count   │                                         │
│  │    operating_hours   │                                         │
│  └──────────────────────┘                                         │
│         │                                                         │
│         │ Aggregated by                                           │
│         │                                                         │
│  ┌──────▼───────────────┐                                         │
│  │ VIEW: v_daily_       │                                         │
│  │ zone_summary         │                                         │
│  ├──────────────────────┤                                         │
│  │ report_date          │                                         │
│  │ zona                 │                                         │
│  │ sensors_count        │                                         │
│  │ avg_LAeq             │                                         │
│  │ total_violations     │                                         │
│  └──────────────────────┘                                         │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                            VISTAS                                 │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • monitoring.v_active_alerts                                     │
│    └─ Alertas no reconocidas con información del sensor           │
│                                                                   │
│  • reporting.v_daily_zone_summary                                 │
│    └─ Resumen diario agregado por zona                            │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 📋 Tablas Principales

### **1. config.sensors** - Configuración de Sensores

Almacena la información maestra de cada sensor acústico.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **sensor_id** 🔑 | VARCHAR(50) | Identificador único del sensor |
| zona | VARCHAR(100) | Zona/área donde está instalado |
| descripcion | TEXT | Descripción detallada |
| lat, lon | NUMERIC | Coordenadas geográficas |
| floor | INTEGER | Piso del edificio |
| building | VARCHAR(50) | Edificio |
| **baseline_db** | NUMERIC(5,1) | Nivel de ruido base esperado |
| alert_threshold_db | NUMERIC(5,1) | Umbral para generar alertas |
| is_active | BOOLEAN | Si el sensor está operativo |
| status | VARCHAR(20) | operational, maintenance, offline, error |
| installed_at | TIMESTAMPTZ | Fecha de instalación |
| last_calibration | TIMESTAMPTZ | Última calibración |
| metadata | JSONB | Datos adicionales flexibles |

**Índices:**
- `idx_sensors_zona` en (zona)
- `idx_sensors_status` en (status)
- `idx_sensors_active` en (is_active)

**Ejemplo de datos:**
```sql
sensor_id: 'SENSOR_001'
zona: 'Sala_Compresores'
baseline_db: 88.0
status: 'operational'
metadata: {"manufacturer": "Bruel & Kjaer", "model": "Type 2250"}
```

---

### **2. monitoring.alerts** - Registro de Alertas

Almacena todas las alertas generadas por el sistema.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **id** 🔑 | SERIAL | ID autoincremental |
| timestamp | TIMESTAMPTZ | Cuándo ocurrió la alerta |
| **sensor_id** 🔗 | VARCHAR(50) | Sensor que generó la alerta |
| zona | VARCHAR(100) | Zona del sensor |
| **alert_type** | VARCHAR(50) | DS594_EXCEEDED, PEAK_EXCEEDED, ANOMALY_DETECTED, SENSOR_OFFLINE |
| **severity** | VARCHAR(20) | critical, high, medium, low, info |
| level_db | NUMERIC(5,1) | Nivel de ruido que causó la alerta |
| peak_db | NUMERIC(5,1) | Nivel peak si aplica |
| message | TEXT | Mensaje descriptivo |
| acknowledged | BOOLEAN | Si fue reconocida por operador |
| acknowledged_by | VARCHAR(100) | Quién la reconoció |
| acknowledged_at | TIMESTAMPTZ | Cuándo fue reconocida |

**Índices:**
- `idx_alerts_timestamp` en (timestamp DESC)
- `idx_alerts_sensor_id` en (sensor_id)
- `idx_alerts_severity` en (severity)
- `idx_alerts_acknowledged` en (acknowledged)

**Tipos de alertas:**
```
DS594_EXCEEDED      → Excede límite de 85 dB(A)
PEAK_EXCEEDED       → Peak > 140 dB(C)
ANOMALY_DETECTED    → ML detectó patrón anómalo
SENSOR_OFFLINE      → Sensor no responde
```

**Ejemplo de registro:**
```sql
id: 12345
timestamp: '2024-11-04 14:30:15-03'
sensor_id: 'SENSOR_003'
alert_type: 'DS594_EXCEEDED'
severity: 'high'
level_db: 93.2
message: 'Nivel LAeq de 93.2 dB(A) excede límite DS 594 de 85 dB(A)'
acknowledged: false
```

---

### **3. monitoring.events** - Log de Eventos

Registro de eventos operacionales del sistema (no alertas).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **id** 🔑 | SERIAL | ID autoincremental |
| event_type | VARCHAR(50) | calibration, maintenance, system_restart, config_change |
| sensor_id | VARCHAR(50) | Sensor relacionado (opcional) |
| description | TEXT | Descripción del evento |
| timestamp | TIMESTAMPTZ | Cuándo ocurrió |
| metadata | JSONB | Información adicional |
| performed_by | VARCHAR(100) | Usuario que ejecutó la acción |

**Ejemplo:**
```sql
event_type: 'calibration'
sensor_id: 'SENSOR_001'
description: 'Calibración anual completada'
performed_by: 'juan.perez@empresa.cl'
metadata: {"calibration_factor": 1.0023, "previous": 1.0000}
```

---

### **4. reporting.daily_reports** - Reportes Diarios Agregados

Agregaciones diarias de métricas por sensor.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **id** 🔑 | SERIAL | ID autoincremental |
| **report_date** | DATE | Fecha del reporte |
| **sensor_id** 🔗 | VARCHAR(50) | Sensor |
| zona | VARCHAR(100) | Zona |
| avg_LAeq | NUMERIC(5,1) | Promedio LAeq del día |
| max_LAeq | NUMERIC(5,1) | Máximo LAeq |
| max_LPeak | NUMERIC(5,1) | Peak máximo |
| total_dose_percent | NUMERIC(7,2) | Dosis de ruido acumulada |
| ds594_violations_count | INTEGER | Cantidad de violaciones |
| anomalies_count | INTEGER | Cantidad de anomalías |
| operating_hours | NUMERIC(5,2) | Horas operativas |

**UNIQUE constraint:** (report_date, sensor_id)

**Uso:** Generación de reportes mensuales y análisis de tendencias.

---

### **5. config.ds594_limits** - Límites Normativos

Límites configurables según DS 594, pueden personalizarse por zona.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **id** 🔑 | SERIAL | ID autoincremental |
| zona | VARCHAR(100) | Zona específica (NULL = todas) |
| limit_type | VARCHAR(50) | continuo_8h, peak_max, accion |
| limit_value | NUMERIC(5,1) | Valor del límite en dB |
| duration_hours | NUMERIC(5,2) | Duración permitida |
| description | TEXT | Descripción del límite |

**UNIQUE constraint:** (zona, limit_type)

**Ejemplo:**
```sql
zona: NULL (aplica a todas)
limit_type: 'continuo_8h'
limit_value: 85.0
duration_hours: 8.0
description: 'Límite continuo para 8 horas según DS 594 Art. 75'
```

---

### **6. config.zones** - Zonas de la Planta

Información sobre áreas/zonas de la planta industrial.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **zone_id** 🔑 | SERIAL | ID autoincremental |
| zone_name | VARCHAR(100) | Nombre único |
| zone_type | VARCHAR(50) | produccion, mantenimiento, oficinas, almacen |
| description | TEXT | Descripción |
| custom_limit_laeq | NUMERIC(5,1) | Límite personalizado |
| max_workers | INTEGER | Cantidad máxima de trabajadores |
| shift_type | VARCHAR(50) | continuo, rotativo, diurno |

---

### **7. config.users** - Usuarios del Sistema

Autenticación y permisos.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **id** 🔑 | SERIAL | ID autoincremental |
| username | VARCHAR(50) | Nombre de usuario único |
| email | VARCHAR(100) | Email único |
| password_hash | VARCHAR(255) | Hash bcrypt de contraseña |
| role | VARCHAR(20) | admin, engineer, operator, viewer, analyst |
| is_active | BOOLEAN | Si está activo |
| last_login | TIMESTAMPTZ | Último login |

**Roles:**
- `admin`: Control total
- `engineer`: Configuración y análisis
- `operator`: Reconocer alertas
- `viewer`: Solo lectura
- `analyst`: Reportes y analytics

---

## 📊 Vistas (Views)

### **monitoring.v_active_alerts**

Vista de alertas activas con información enriquecida del sensor.

```sql
SELECT 
    a.id,
    a.timestamp,
    a.sensor_id,
    s.zona,
    s.descripcion as sensor_description,
    a.alert_type,
    a.severity,
    a.level_db,
    a.peak_db,
    a.message,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - a.timestamp))/3600 as hours_since_alert
FROM monitoring.alerts a
LEFT JOIN config.sensors s ON a.sensor_id = s.sensor_id
WHERE a.acknowledged = FALSE
ORDER BY a.timestamp DESC;
```

**Uso:** Dashboard de alertas pendientes.

---

### **reporting.v_daily_zone_summary**

Resumen diario agregado por zona.

```sql
SELECT 
    report_date,
    zona,
    COUNT(DISTINCT sensor_id) as sensors_count,
    ROUND(AVG(avg_LAeq), 1) as avg_LAeq,
    ROUND(MAX(max_LAeq), 1) as max_LAeq,
    SUM(ds594_violations_count) as total_violations,
    SUM(anomalies_count) as total_anomalies
FROM reporting.daily_reports
GROUP BY report_date, zona
ORDER BY report_date DESC, zona;
```

**Uso:** Reportes ejecutivos y análisis de tendencias por zona.

---

## 🔧 Funciones Útiles

### **cleanup_old_alerts(days_to_keep INTEGER)**

Limpia alertas antiguas que ya fueron reconocidas.

```sql
SELECT cleanup_old_alerts(90); -- Elimina alertas reconocidas > 90 días
```

**Retorna:** Cantidad de registros eliminados.

---

## 📏 Convenciones y Estándares

### **Nomenclatura:**
- **Tablas:** `schema.nombre_tabla` (snake_case)
- **PKs:** `id` o `nombre_id`
- **FKs:** `nombre_relacionado_id`
- **Timestamps:** Siempre con timezone (`TIMESTAMPTZ`)
- **Booleans:** `is_*`, `has_*`, `acknowledged`

### **Schemas:**
- `config`: Configuración y maestros
- `monitoring`: Datos operacionales en tiempo real
- `reporting`: Agregaciones y reportes

### **Índices:**
- Todos los campos de búsqueda frecuente
- Timestamps siempre indexados (DESC para queries recientes)
- Foreign keys indexadas

### **JSONB Usage:**
- `metadata`: Datos flexibles que varían por registro
- Indexados con GIN para búsquedas
- No usar para datos estructurados frecuentes

---

## 🔐 Seguridad

### **Grants:**
```sql
-- Usuario de aplicación (limitado)
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA monitoring TO ruido_user;
GRANT SELECT ON ALL TABLES IN SCHEMA config TO ruido_user;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO ruido_user;

-- Usuario admin (completo)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA config TO admin_user;
```

### **Passwords:**
- Almacenados con bcrypt (costo 12)
- Nunca en texto plano
- Salted por bcrypt

---

## 📊 Volumen de Datos Estimado

| Tabla | Registros/Día | Tamaño/Mes | Retención |
|-------|--------------|------------|-----------|
| monitoring.alerts | ~100-500 | ~5 MB | 90 días |
| monitoring.events | ~10-50 | ~1 MB | 1 año |
| reporting.daily_reports | 5 | <1 MB | Permanente |
| config.sensors | 5 (estático) | <1 KB | Permanente |

**Total estimado:** ~150 MB/año (PostgreSQL)

---

## 🔄 Mantenimiento

### **Vacuum regular:**
```sql
-- Ejecutar semanalmente
VACUUM ANALYZE monitoring.alerts;
VACUUM ANALYZE reporting.daily_reports;
```

### **Limpieza de datos antiguos:**
```sql
-- Eliminar alertas reconocidas > 90 días
SELECT cleanup_old_alerts(90);

-- Archivar reportes > 2 años
-- (implementar según necesidad)
```

---

## 📖 Queries de Ejemplo

### **Top 5 sensores con más violaciones:**
```sql
SELECT 
    sensor_id,
    zona,
    COUNT(*) as violations
FROM monitoring.alerts
WHERE alert_type = 'DS594_EXCEEDED'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY sensor_id, zona
ORDER BY violations DESC
LIMIT 5;
```

### **Tendencia de cumplimiento semanal:**
```sql
SELECT 
    date_trunc('week', report_date) as week,
    zona,
    AVG(avg_LAeq) as avg_level,
    SUM(ds594_violations_count) as total_violations
FROM reporting.daily_reports
WHERE report_date > CURRENT_DATE - INTERVAL '30 days'
GROUP BY week, zona
ORDER BY week DESC, zona;
```

### **Alertas por severidad (últimas 24h):**
```sql
SELECT 
    severity,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE acknowledged) as acknowledged_count
FROM monitoring.alerts
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY severity
ORDER BY 
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END;
```

---

## 🎯 Mejoras Futuras

- [ ] Particionamiento de `monitoring.alerts` por mes
- [ ] Tablas de auditoría con triggers
- [ ] Replicación para alta disponibilidad
- [ ] Búsqueda full-text en mensajes
- [ ] Materializar vistas para mejor performance
- [ ] Time-series específico para métricas de alta frecuencia

---

## 📞 Soporte

Para más información sobre el esquema:
- Ver: `init-db.sql` (código fuente)
- Ejecutar: `\d+ schema.table_name` en psql
- Documentación: Este archivo

---

**Última actualización:** 2024-11-04  
**Versión del esquema:** 1.0.0