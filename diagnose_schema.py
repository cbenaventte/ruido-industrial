"""
Script de Diagnóstico - Compatibilidad Schema SQL vs stream_processor_v2.py
============================================================================

Este script verifica que todas las tablas y columnas requeridas por
stream_processor_v2.py existan en la base de datos PostgreSQL.

Uso:
    python diagnose_schema.py
"""

import psycopg2
from psycopg2 import sql
from datetime import datetime

# Configuración
POSTGRES_CONFIG = {
    'host': 'localhost',
    'database': 'ruido_db',
    'user': 'ruido_user',
    'password': 'ruido_password'
}

# Estructura esperada por stream_processor_v2.py
REQUIRED_SCHEMA = {
    'monitoring.alerts': [
        'id', 'timestamp', 'sensor_id', 'zona', 'alert_type', 'severity',
        'level_db', 'peak_db', 'dose_percent', 'lex8h', 'message', 'actions',
        'acknowledged', 'acknowledged_by', 'acknowledged_at',
        'resolved', 'resolved_by', 'resolved_at', 'resolution_notes',
        'created_at'
    ],
    'analytics.dose_tracking': [
        'id', 'timestamp', 'sensor_id', 'zona', 'current_dose',
        'projected_dose', 'elapsed_hours', 'avg_laeq', 'lex8h',
        'samples_count', 'shift_type', 'created_at'
    ],
    'analytics.anomaly_history': [
        'id', 'timestamp', 'sensor_id', 'zona', 'anomaly_score',
        'confidence', 'features', 'laeq', 'lpeak',
        'context_before', 'context_after', 'validated',
        'false_positive', 'validation_notes', 'created_at'
    ],
    'reporting.shift_reports': [
        'id', 'report_date', 'shift_type', 'shift_start', 'shift_end',
        'sensor_id', 'zona', 'avg_LAeq', 'max_LAeq', 'max_LPeak',
        'dose_percent', 'lex8h', 'ds594_compliant',
        'violations_count', 'anomalies_count', 'workers_exposed',
        'samples_count', 'created_at'
    ],
    'config.sensors': [
        'sensor_id', 'zona', 'descripcion', 'lat', 'lon', 'floor',
        'building', 'baseline_db', 'alert_threshold_db', 'is_active',
        'status', 'installed_at', 'last_calibration', 'next_calibration',
        'metadata', 'created_at', 'updated_at'
    ]
}


def check_table_exists(cursor, schema, table):
    """Verifica si una tabla existe"""
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = %s
        );
    """
    cursor.execute(query, (schema, table))
    return cursor.fetchone()[0]


def check_column_exists(cursor, schema, table, column):
    """Verifica si una columna existe en una tabla"""
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = %s 
            AND column_name = %s
        );
    """
    cursor.execute(query, (schema, table, column))
    return cursor.fetchone()[0]


def get_table_columns(cursor, schema, table):
    """Obtiene todas las columnas de una tabla"""
    query = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_schema = %s 
        AND table_name = %s
        ORDER BY ordinal_position;
    """
    cursor.execute(query, (schema, table))
    return cursor.fetchall()


def check_table_has_data(cursor, schema, table):
    """Verifica si una tabla tiene datos"""
    try:
        query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )
        cursor.execute(query)
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        return None


def main():
    print("="*80)
    print("DIAGNÓSTICO DE COMPATIBILIDAD - SCHEMA SQL vs stream_processor_v2.py")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Conectar a PostgreSQL
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        print("✅ Conexión a PostgreSQL exitosa\n")
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        return
    
    issues_found = 0
    tables_ok = 0
    columns_ok = 0
    columns_missing = 0
    
    # Verificar cada tabla
    for full_table, required_columns in REQUIRED_SCHEMA.items():
        schema, table = full_table.split('.')
        
        print(f"\n{'─'*80}")
        print(f"📋 Verificando: {full_table}")
        print(f"{'─'*80}")
        
        # 1. Verificar existencia de tabla
        if check_table_exists(cursor, schema, table):
            print(f"   ✅ Tabla existe")
            tables_ok += 1
            
            # 2. Obtener columnas actuales
            actual_columns = get_table_columns(cursor, schema, table)
            actual_column_names = [col[0] for col in actual_columns]
            
            print(f"   📊 Columnas actuales: {len(actual_column_names)}")
            print(f"   📊 Columnas requeridas: {len(required_columns)}")
            
            # 3. Verificar cada columna requerida
            missing_columns = []
            for col in required_columns:
                if check_column_exists(cursor, schema, table, col):
                    columns_ok += 1
                else:
                    missing_columns.append(col)
                    columns_missing += 1
                    issues_found += 1
            
            if missing_columns:
                print(f"\n   ❌ Columnas FALTANTES ({len(missing_columns)}):")
                for col in missing_columns:
                    print(f"      • {col}")
                    
                # Sugerir ALTER TABLE
                print(f"\n   🔧 SQL para agregar columnas faltantes:")
                for col in missing_columns:
                    # Determinar tipo de dato probable
                    if col in ['id', 'samples_count', 'violations_count', 'anomalies_count', 'workers_exposed']:
                        dtype = 'INTEGER'
                    elif col in ['dose_percent', 'lex8h', 'current_dose', 'projected_dose', 'elapsed_hours', 'avg_laeq', 'anomaly_score']:
                        dtype = 'NUMERIC(7,2)'
                    elif col in ['timestamp', 'shift_start', 'shift_end', 'created_at', 'acknowledged_at', 'resolved_at']:
                        dtype = 'TIMESTAMP WITH TIME ZONE'
                    elif col in ['report_date']:
                        dtype = 'DATE'
                    elif col in ['acknowledged', 'resolved', 'ds594_compliant', 'validated', 'false_positive']:
                        dtype = 'BOOLEAN'
                    elif col in ['actions', 'features', 'context_before', 'context_after', 'metadata']:
                        dtype = 'JSONB'
                    else:
                        dtype = 'VARCHAR(100)'
                    
                    print(f"      ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS {col} {dtype};")
            else:
                print(f"   ✅ Todas las columnas requeridas existen")
            
            # 4. Verificar si hay datos
            row_count = check_table_has_data(cursor, schema, table)
            if row_count is not None:
                if row_count > 0:
                    print(f"   📊 Datos: {row_count} filas")
                else:
                    print(f"   ⚠️  Tabla vacía (0 filas)")
                    print(f"      → Esto es normal si el sistema acaba de iniciarse")
            
            # 5. Mostrar columnas extra (no requeridas pero presentes)
            extra_columns = [col for col in actual_column_names if col not in required_columns]
            if extra_columns:
                print(f"\n   ℹ️  Columnas adicionales (no requeridas pero presentes):")
                for col in extra_columns:
                    print(f"      • {col}")
        
        else:
            print(f"   ❌ Tabla NO EXISTE")
            issues_found += 1
            
            # Sugerir CREATE TABLE
            print(f"\n   🔧 Esta tabla debe ser creada. Ejecutar fix_migration.sql")
    
    # Resumen final
    print(f"\n\n{'='*80}")
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print(f"{'='*80}")
    print(f"   Tablas verificadas: {len(REQUIRED_SCHEMA)}")
    print(f"   Tablas OK: {tables_ok}")
    print(f"   Tablas faltantes: {len(REQUIRED_SCHEMA) - tables_ok}")
    print(f"\n   Columnas OK: {columns_ok}")
    print(f"   Columnas faltantes: {columns_missing}")
    print(f"\n   Total de problemas: {issues_found}")
    
    if issues_found == 0:
        print(f"\n   ✅ ¡SCHEMA 100% COMPATIBLE!")
        print(f"   ✅ stream_processor_v2.py debería funcionar correctamente")
    else:
        print(f"\n   ⚠️  SE ENCONTRARON {issues_found} PROBLEMAS")
        print(f"   ⚠️  Ejecutar fix_migration.sql para corregir")
    
    print(f"{'='*80}\n")
    
    # Verificar conectividad InfluxDB (bonus)
    print("🔍 Verificación adicional: InfluxDB")
    print(f"{'─'*80}")
    try:
        from influxdb_client import InfluxDBClient
        client = InfluxDBClient(
            url='http://localhost:8086',
            token='my-super-secret-token-12345',
            org='ruido-industrial'
        )
        # Intentar listar buckets
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        
        acoustic_bucket = [b for b in buckets if b.name == 'acoustic-data']
        
        if acoustic_bucket:
            print("   ✅ InfluxDB conectado")
            print(f"   ✅ Bucket 'acoustic-data' existe")
        else:
            print("   ✅ InfluxDB conectado")
            print("   ⚠️  Bucket 'acoustic-data' NO existe")
            print("   🔧 Crear bucket: influx bucket create -n acoustic-data")
        
        client.close()
    except ImportError:
        print("   ⚠️  influxdb-client no instalado")
        print("   🔧 Instalar: pip install influxdb-client")
    except Exception as e:
        print(f"   ❌ Error conectando a InfluxDB: {e}")
    
    # Cerrar conexión
    cursor.close()
    conn.close()
    print(f"\n{'='*80}")
    print("DIAGNÓSTICO COMPLETADO")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()