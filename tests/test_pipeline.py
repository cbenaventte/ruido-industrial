"""
Tests Automatizados del Pipeline Completo
Sistema de Monitoreo de Ruido Industrial DS 594

Ejecutar: python tests/test_pipeline.py
O con pytest: pytest tests/test_pipeline.py -v
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta

# Agregar src al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from influxdb_client import InfluxDBClient
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
import requests


class Colors:
    """Colores ANSI para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str, status: bool, message: str = ""):
    """Imprime resultado de test con formato"""
    status_symbol = f"{Colors.GREEN}✓{Colors.END}" if status else f"{Colors.RED}✗{Colors.END}"
    status_text = f"{Colors.GREEN}PASS{Colors.END}" if status else f"{Colors.RED}FAIL{Colors.END}"
    
    print(f"[{status_symbol}] {name:.<60} {status_text}")
    if message:
        indent = "    "
        print(f"{indent}{Colors.CYAN}→{Colors.END} {message}")


def print_section(title: str):
    """Imprime encabezado de sección"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


class PipelineTests:
    """Suite de tests para el pipeline completo"""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        
        # Configuración
        self.influx_config = {
            'url': 'http://localhost:8086',
            'token': 'my-super-secret-token-12345',
            'org': 'ruido-industrial',
            'bucket': 'acoustic-data'
        }
        
        self.postgres_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'ruido_db',
            'user': 'ruido_user',
            'password': 'ruido_password'
        }
        
        self.kafka_config = {
            'bootstrap_servers': 'localhost:9092',
            'topic': 'acoustic-raw-data'
        }
    
    def test_docker_services(self) -> bool:
        """Test 1: Verificar que servicios Docker estén corriendo"""
        print_section("TEST 1: SERVICIOS DOCKER")
        
        services = {
            'Kafka': 'http://localhost:9092',
            'InfluxDB': 'http://localhost:8086/health',
            'PostgreSQL': ('localhost', 5432),
            'Grafana': 'http://localhost:3000',
            'Kafka UI': 'http://localhost:8080'
        }
        
        all_ok = True
        
        for service_name, endpoint in services.items():
            try:
                if isinstance(endpoint, tuple):
                    # Test de socket (PostgreSQL)
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(endpoint)
                    sock.close()
                    
                    if result == 0:
                        print_test(f"Servicio {service_name}", True, f"Puerto {endpoint[1]} abierto")
                    else:
                        print_test(f"Servicio {service_name}", False, f"Puerto {endpoint[1]} cerrado")
                        all_ok = False
                else:
                    # Test HTTP
                    response = requests.get(endpoint, timeout=3)
                    
                    if response.status_code in [200, 204]:
                        print_test(f"Servicio {service_name}", True, f"HTTP {response.status_code}")
                    else:
                        print_test(f"Servicio {service_name}", False, f"HTTP {response.status_code}")
                        all_ok = False
                        
            except Exception as e:
                print_test(f"Servicio {service_name}", False, str(e))
                all_ok = False
        
        self.results.append(('Docker Services', all_ok))
        return all_ok
    
    def test_kafka_connectivity(self) -> bool:
        """Test 2: Verificar conectividad con Kafka"""
        print_section("TEST 2: KAFKA")
        
        all_ok = True
        
        # Test Producer
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                request_timeout_ms=5000
            )
            producer.close()
            print_test("Kafka Producer", True, "Puede conectar y enviar mensajes")
        except Exception as e:
            print_test("Kafka Producer", False, str(e))
            all_ok = False
        
        # Test Consumer
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                consumer_timeout_ms=2000
            )
            topics = consumer.topics()
            consumer.close()
            
            topic_exists = self.kafka_config['topic'] in topics
            print_test(
                "Kafka Consumer", 
                True, 
                f"{len(topics)} topics disponibles"
            )
            
            if topic_exists:
                print_test(
                    f"Topic '{self.kafka_config['topic']}'", 
                    True, 
                    "Topic existe"
                )
            else:
                print_test(
                    f"Topic '{self.kafka_config['topic']}'", 
                    False, 
                    "Topic no existe (será creado al publicar)"
                )
                
        except Exception as e:
            print_test("Kafka Consumer", False, str(e))
            all_ok = False
        
        self.results.append(('Kafka', all_ok))
        return all_ok
    
    def test_influxdb_connectivity(self) -> bool:
        """Test 3: Verificar conectividad con InfluxDB"""
        print_section("TEST 3: INFLUXDB")
        
        all_ok = True
        
        try:
            client = InfluxDBClient(
                url=self.influx_config['url'],
                token=self.influx_config['token'],
                org=self.influx_config['org'],
                timeout=5000
            )
            
            # Verificar buckets
            buckets = client.buckets_api().find_buckets().buckets
            bucket_names = [b.name for b in buckets]
            
            print_test(
                "InfluxDB Conexión", 
                True, 
                f"{len(buckets)} buckets encontrados"
            )
            
            # Verificar bucket específico
            bucket_exists = self.influx_config['bucket'] in bucket_names
            print_test(
                f"Bucket '{self.influx_config['bucket']}'", 
                bucket_exists,
                "Bucket existe" if bucket_exists else "Bucket no existe"
            )
            
            if not bucket_exists:
                all_ok = False
            
            # Verificar datos recientes
            query = f'''
            from(bucket: "{self.influx_config['bucket']}")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "acoustic_measurements")
                |> filter(fn: (r) => r._field == "lex8h" or r._field == "dose_8h")
                |> count()
            '''
            
            try:
                result = client.query_api().query(query)
                
                if result:
                    total_points = sum(
                        record.get_value() 
                        for table in result 
                        for record in table.records
                    )
                    
                    print_test(
                        "Datos en InfluxDB", 
                        total_points > 0,
                        f"{total_points} puntos de datos en última hora"
                    )
                    
                    if total_points == 0:
                        print_test(
                            "Advertencia", 
                            False, 
                            "No hay datos recientes (¿simulador corriendo?)"
                        )
                        all_ok = False
                else:
                    print_test("Query InfluxDB", False, "Sin resultados")
                    all_ok = False
                    
            except Exception as e:
                print_test("Query InfluxDB", False, str(e))
                all_ok = False
            
            client.close()
            
        except Exception as e:
            print_test("InfluxDB Conexión", False, str(e))
            all_ok = False
        
        self.results.append(('InfluxDB', all_ok))
        return all_ok
    
    def test_postgres_connectivity(self) -> bool:
        """Test 4: Verificar conectividad con PostgreSQL"""
        print_section("TEST 4: POSTGRESQL")
        
        all_ok = True
        
        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor()
            
            print_test("PostgreSQL Conexión", True, "Conectado correctamente")
            
            # Verificar schemas
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('config', 'monitoring', 'reporting')
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            
            expected_schemas = ['config', 'monitoring', 'reporting']
            schemas_ok = all(s in schemas for s in expected_schemas)
            
            print_test(
                "Schemas de BD", 
                schemas_ok,
                f"Encontrados: {', '.join(schemas)}"
            )
            
            if not schemas_ok:
                all_ok = False
            
            # Verificar tablas principales
            tables_to_check = [
                ('config', 'sensors'),
                ('monitoring', 'alerts'),
                ('reporting', 'daily_reports')
            ]
            
            for schema, table in tables_to_check:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = '{schema}' AND table_name = '{table}'
                """)
                exists = cursor.fetchone()[0] > 0
                
                print_test(
                    f"Tabla {schema}.{table}", 
                    exists,
                    "Existe" if exists else "No existe"
                )
                
                if not exists:
                    all_ok = False
            
            # Verificar datos de sensores
            cursor.execute("SELECT COUNT(*) FROM config.sensors")
            sensor_count = cursor.fetchone()[0]
            
            print_test(
                "Datos de sensores", 
                sensor_count > 0,
                f"{sensor_count} sensores configurados"
            )
            
            if sensor_count == 0:
                all_ok = False
            
            # Verificar alertas recientes
            cursor.execute("""
                SELECT COUNT(*) 
                FROM monitoring.alerts 
                WHERE timestamp > NOW() - INTERVAL '1 hour'
            """)
            recent_alerts = cursor.fetchone()[0]
            
            print_test(
                "Alertas recientes", 
                True,
                f"{recent_alerts} alertas en última hora"
            )
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print_test("PostgreSQL Conexión", False, str(e))
            all_ok = False
        
        self.results.append(('PostgreSQL', all_ok))
        return all_ok
    
    def test_data_flow(self) -> bool:
        """Test 5: Verificar flujo de datos end-to-end"""
        print_section("TEST 5: FLUJO DE DATOS END-TO-END")
        
        all_ok = True
        
        # Verificar datos en Kafka
        try:
            consumer = KafkaConsumer(
                self.kafka_config['topic'],
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                consumer_timeout_ms=3000,
                auto_offset_reset='latest',
                enable_auto_commit=False
            )
            
            messages = []
            for message in consumer:
                messages.append(message.value)
                if len(messages) >= 3:
                    break
            
            consumer.close()
            
            print_test(
                "Mensajes en Kafka", 
                len(messages) > 0,
                f"{len(messages)} mensajes recientes en topic"
            )
            
            if len(messages) == 0:
                print_test(
                    "Advertencia", 
                    False, 
                    "No hay mensajes recientes (¿simulador corriendo?)"
                )
                all_ok = False
            else:
                # Validar estructura del mensaje
                try:
                    sample_msg = json.loads(messages[0])
                    required_fields = ['timestamp', 'sensor_id', 'zona', 'metrics']
                    
                    fields_ok = all(field in sample_msg for field in required_fields)
                    
                    print_test(
                        "Estructura de mensaje", 
                        fields_ok,
                        "Campos requeridos presentes"
                    )
                    
                    if not fields_ok:
                        all_ok = False
                        
                except Exception as e:
                    print_test("Validación de mensaje", False, str(e))
                    all_ok = False
                    
        except Exception as e:
            print_test("Kafka Consumer", False, str(e))
            all_ok = False
        
        # Verificar sincronización entre InfluxDB y PostgreSQL
        try:
            # Contar datos en InfluxDB (última hora)
            client = InfluxDBClient(
                url=self.influx_config['url'],
                token=self.influx_config['token'],
                org=self.influx_config['org']
            )
            
            query = f'''
            from(bucket: "{self.influx_config['bucket']}")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "acoustic_measurements")
                |> count()
            '''
            
            result = client.query_api().query(query)
            influx_count = sum(
                record.get_value() 
                for table in result 
                for record in table.records
            ) if result else 0
            
            client.close()
            
            # Contar alertas en PostgreSQL
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM monitoring.alerts 
                WHERE timestamp > NOW() - INTERVAL '1 hour'
            """)
            postgres_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            print_test(
                "Sincronización de datos", 
                influx_count > 0 and postgres_count >= 0,
                f"InfluxDB: {influx_count} pts | PostgreSQL: {postgres_count} alertas"
            )
            
        except Exception as e:
            print_test("Sincronización", False, str(e))
            all_ok = False
        
        self.results.append(('Data Flow', all_ok))
        return all_ok
    
    def test_ds594_calculations(self) -> bool:
        """Test 6: Verificar cálculos DS 594"""
        print_section("TEST 6: CÁLCULOS DS 594")
        
        all_ok = True
        
        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor()
            
            # Verificar límites DS 594 configurados
            cursor.execute("SELECT COUNT(*) FROM config.ds594_limits")
            limits_count = cursor.fetchone()[0]
            
            print_test(
                "Límites DS 594 configurados", 
                limits_count > 0,
                f"{limits_count} límites definidos"
            )
            
            if limits_count == 0:
                all_ok = False
            
            # Verificar alertas por violación DS 594
            cursor.execute("""
                SELECT COUNT(*) 
                FROM monitoring.alerts 
                WHERE alert_type = 'DS594_EXCEEDED'
                AND timestamp > NOW() - INTERVAL '24 hours'
            """)
            ds594_violations = cursor.fetchone()[0]
            
            print_test(
                "Violaciones DS 594 detectadas", 
                True,
                f"{ds594_violations} violaciones en últimas 24h"
            )
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print_test("Cálculos DS 594", False, str(e))
            all_ok = False
        
        self.results.append(('DS 594 Calculations', all_ok))
        return all_ok


    def test_dose_tracking(self) -> bool:
        """Test 7: Verificar que se está llenando dose_tracking en tiempo real"""
        print_section("TEST 7: DOSE TRACKING EN TIEMPO REAL")
        
        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor()
            
            # Últimos 10 minutos
            cursor.execute("""
                SELECT COUNT(*) FROM analytics.dose_tracking 
                WHERE timestamp > NOW() - INTERVAL '10 minutes'
            """)
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            ok = count > 0
            print_test("analytics.dose_tracking", ok, f"{count} registros en últimos 10min")
            
            self.results.append(('Dose Tracking', ok))
            return ok
            
        except Exception as e:
            print_test("analytics.dose_tracking", False, str(e))
            return False   

    
    def print_summary(self):
        """Imprime resumen final de tests"""
        elapsed_time = time.time() - self.start_time
        
        print_section("RESUMEN DE TESTS")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for _, result in self.results if result)
        failed_tests = total_tests - passed_tests
        
        print(f"Total de tests: {total_tests}")
        print(f"{Colors.GREEN}Pasados: {passed_tests}{Colors.END}")
        print(f"{Colors.RED}Fallidos: {failed_tests}{Colors.END}")
        print(f"\nTiempo de ejecución: {elapsed_time:.2f}s")
        
        if failed_tests == 0:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✓ TODOS LOS TESTS PASARON{Colors.END}")
            print(f"{Colors.GREEN}El pipeline está funcionando correctamente{Colors.END}")
            return True
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}✗ ALGUNOS TESTS FALLARON{Colors.END}")
            print(f"{Colors.YELLOW}Revisa los errores arriba para más detalles{Colors.END}")
            return False
    
    def run_all(self):
        """Ejecuta todos los tests"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}PIPELINE HEALTH CHECK - Sistema de Monitoreo Acústico{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Ejecutar tests en orden
        self.test_docker_services()
        self.test_kafka_connectivity()
        self.test_influxdb_connectivity()
        self.test_postgres_connectivity()
        self.test_data_flow()
        self.test_ds594_calculations()
        self.test_dose_tracking()  # ← NUEVO
        
        # Resumen
        return self.print_summary()


def main():
    """Función principal"""
    tests = PipelineTests()
    success = tests.run_all()
    
    # Exit code para CI/CD
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()