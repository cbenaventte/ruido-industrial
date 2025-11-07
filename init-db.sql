-- Inicialización de Base de Datos para Sistema de Monitoreo de Ruido
-- PostgreSQL 15+

-- ============================================
-- ESQUEMA POSTGRESQL CORREGIDO
-- Sistema de Monitoreo de Ruido Industrial DS 594
-- ============================================

-- Crear schemas
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS reporting;

-- ============================================
-- TABLA: config.sensors
-- ============================================

CREATE TABLE IF NOT EXISTS config.sensors (
    sensor_id VARCHAR(50) PRIMARY KEY,
    zona VARCHAR(100) NOT NULL,
    descripcion TEXT,
    lat NUMERIC(10, 8),
    lon NUMERIC(11, 8),
    floor INTEGER,
    building VARCHAR(50),
    baseline_db NUMERIC(5,1) NOT NULL,
    alert_threshold_db NUMERIC(5,1),
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'operational',
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_calibration TIMESTAMP WITH TIME ZONE,
    next_calibration TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sensors_zona ON config.sensors(zona);
CREATE INDEX IF NOT EXISTS idx_sensors_status ON config.sensors(status);
CREATE INDEX IF NOT EXISTS idx_sensors_active ON config.sensors(is_active);

-- ============================================
-- TABLA: config.zones
-- ============================================

CREATE TABLE IF NOT EXISTS config.zones (
    zone_id SERIAL PRIMARY KEY,
    zone_name VARCHAR(100) UNIQUE NOT NULL,
    zone_type VARCHAR(50),
    description TEXT,
    custom_limit_laeq NUMERIC(5,1),
    custom_limit_peak NUMERIC(5,1),
    max_workers INTEGER,
    shift_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zones_type ON config.zones(zone_type);

-- ============================================
-- TABLA: monitoring.alerts
-- ============================================

CREATE TABLE IF NOT EXISTS monitoring.alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    sensor_id VARCHAR(50) NOT NULL,
    zona VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    level_db NUMERIC(5,1),
    peak_db NUMERIC(5,1),
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON monitoring.alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_sensor_id ON monitoring.alerts(sensor_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON monitoring.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON monitoring.alerts(acknowledged);

-- ============================================
-- TABLA: monitoring.events
-- ============================================

CREATE TABLE IF NOT EXISTS monitoring.events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    sensor_id VARCHAR(50),
    zona VARCHAR(100),
    description TEXT NOT NULL,
    metadata JSONB,
    performed_by VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_type ON monitoring.events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON monitoring.events(timestamp);

-- ============================================
-- TABLA: monitoring.maintenance_events
-- ============================================

CREATE TABLE IF NOT EXISTS monitoring.maintenance_events (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50),
    event_type VARCHAR(50) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    performed_by VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_maintenance_scheduled ON monitoring.maintenance_events(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_maintenance_sensor ON monitoring.maintenance_events(sensor_id);

-- ============================================
-- TABLA: reporting.daily_reports
-- ============================================

CREATE TABLE IF NOT EXISTS reporting.daily_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    sensor_id VARCHAR(50) NOT NULL,
    zona VARCHAR(100) NOT NULL,
    avg_LAeq NUMERIC(5,1),
    max_LAeq NUMERIC(5,1),
    max_LPeak NUMERIC(5,1),
    total_dose_percent NUMERIC(7,2),
    ds594_violations_count INTEGER DEFAULT 0,
    anomalies_count INTEGER DEFAULT 0,
    operating_hours NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(report_date, sensor_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON reporting.daily_reports(report_date);
CREATE INDEX IF NOT EXISTS idx_daily_reports_sensor ON reporting.daily_reports(sensor_id);

-- ============================================
-- TABLA: config.ds594_limits
-- ============================================

CREATE TABLE IF NOT EXISTS config.ds594_limits (
    id SERIAL PRIMARY KEY,
    zona VARCHAR(100),
    limit_type VARCHAR(50) NOT NULL,
    limit_value NUMERIC(5,1) NOT NULL,
    duration_hours NUMERIC(5,2),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(zona, limit_type)
);

-- ============================================
-- TABLA: config.users
-- ============================================

CREATE TABLE IF NOT EXISTS config.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- VISTAS
-- ============================================

CREATE OR REPLACE VIEW monitoring.v_active_alerts AS
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

CREATE OR REPLACE VIEW reporting.v_daily_zone_summary AS
SELECT 
    report_date,
    zona,
    COUNT(DISTINCT sensor_id) as sensors_count,
    ROUND(AVG(avg_LAeq), 1) as avg_LAeq,
    ROUND(MAX(max_LAeq), 1) as max_LAeq,
    ROUND(MAX(max_LPeak), 1) as max_LPeak,
    ROUND(SUM(total_dose_percent), 2) as total_dose,
    SUM(ds594_violations_count) as total_violations,
    SUM(anomalies_count) as total_anomalies
FROM reporting.daily_reports
GROUP BY report_date, zona
ORDER BY report_date DESC, zona;

-- ============================================
-- FUNCIONES
-- ============================================

CREATE OR REPLACE FUNCTION cleanup_old_alerts(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM monitoring.alerts 
    WHERE timestamp < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL
    AND acknowledged = TRUE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- DATOS INICIALES
-- ============================================

-- Insertar sensores
INSERT INTO config.sensors (sensor_id, zona, descripcion, lat, lon, building, floor, baseline_db, alert_threshold_db, status) 
VALUES
    ('SENSOR_001', 'Sala_Compresores', 'Sala de compresores principales', -33.4489, -70.6693, 'Edificio A', 1, 88.0, 90.0, 'operational'),
    ('SENSOR_002', 'Zona_Soldadura', 'Área de soldadura industrial', -33.4490, -70.6695, 'Edificio A', 1, 82.0, 87.0, 'operational'),
    ('SENSOR_003', 'Prensas_Hidraulicas', 'Zona de prensas hidráulicas', -33.4488, -70.6690, 'Edificio B', 1, 91.0, 93.0, 'operational'),
    ('SENSOR_004', 'Area_Ensamble', 'Área de ensamblaje manual', -33.4492, -70.6688, 'Edificio A', 2, 75.0, 83.0, 'operational'),
    ('SENSOR_005', 'Molienda_Metales', 'Sección de molienda de metales', -33.4487, -70.6692, 'Edificio B', 1, 95.0, 97.0, 'operational')
ON CONFLICT (sensor_id) DO NOTHING;

-- Insertar límites DS 594
INSERT INTO config.ds594_limits (zona, limit_type, limit_value, duration_hours, description) 
VALUES
    (NULL, 'continuo_8h', 85.0, 8.0, 'Límite continuo para 8 horas según DS 594'),
    (NULL, 'peak_max', 140.0, NULL, 'Nivel peak máximo permitido'),
    (NULL, 'accion', 82.0, 8.0, 'Nivel de acción preventiva')
ON CONFLICT (zona, limit_type) DO NOTHING;

-- Insertar zonas
INSERT INTO config.zones (zone_name, zone_type, description, max_workers, shift_type) 
VALUES
    ('Sala_Compresores', 'produccion', 'Sala principal de compresores de aire', 3, 'continuo'),
    ('Zona_Soldadura', 'produccion', 'Área de soldadura y fabricación', 8, 'rotativo'),
    ('Prensas_Hidraulicas', 'produccion', 'Zona de prensado y conformado', 5, 'rotativo'),
    ('Area_Ensamble', 'produccion', 'Área de ensamblaje y montaje', 12, 'diurno'),
    ('Molienda_Metales', 'produccion', 'Sección de molienda y acabado', 4, 'rotativo')
ON CONFLICT (zone_name) DO NOTHING;

-- Usuario admin (password: admin123 - cambiar en producción)
INSERT INTO config.users (username, email, password_hash, role, is_active) 
VALUES
    ('admin', 'admin@ruido-industrial.cl', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ufWy1F2rGZOu', 'admin', true)
ON CONFLICT (username) DO NOTHING;

-- Grants
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA config TO ruido_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO ruido_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA reporting TO ruido_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA config TO ruido_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO ruido_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA reporting TO ruido_user;

-- Log de inicialización
DO $$ 
BEGIN 
    RAISE NOTICE '✅ Base de datos inicializada correctamente';
    RAISE NOTICE '📊 Tablas creadas en schemas: config, monitoring, reporting';
    RAISE NOTICE '🎤 5 sensores insertados';
END $$;