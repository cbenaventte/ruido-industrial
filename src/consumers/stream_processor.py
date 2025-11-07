"""
Procesador de Stream para Análisis Acústico en Tiempo Real
Calcula métricas DS 594 y detecta anomalías
"""

import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import psycopg2
from sklearn.ensemble import IsolationForest


class DS594Calculator:
    """Calcula métricas según normativa chilena DS 594"""
    
    # Tabla de exposición permitida según DS 594
    EXPOSURE_LIMITS = {
        85: 8,    # 85 dB(A) → 8 horas
        88: 4,    # 88 dB(A) → 4 horas
        91: 2,    # 91 dB(A) → 2 horas
        94: 1,    # 94 dB(A) → 1 hora
        97: 0.5,  # 97 dB(A) → 30 minutos
        100: 0.25, # 100 dB(A) → 15 minutos
    }
    
    @staticmethod
    def calculate_dose(levels_db: List[float], durations_hours: List[float]) -> float:
        """
        Calcula dosis de ruido según DS 594
        Dosis = Σ(Ti / TPi) * 100
        donde Ti = tiempo exposición, TPi = tiempo permitido
        """
        total_dose = 0.0
        
        for level, duration in zip(levels_db, durations_hours):
            # Interpolar tiempo permitido
            permitted_time = DS594Calculator._get_permitted_time(level)
            
            if permitted_time > 0:
                dose = (duration / permitted_time) * 100
                total_dose += dose
        
        return round(total_dose, 2)
    
    @staticmethod
    def _get_permitted_time(level_db: float) -> float:
        """Obtiene tiempo permitido para un nivel de ruido (interpolación)"""
        if level_db < 85:
            return 8.0  # Sin límite práctico
        elif level_db >= 115:
            return 0.0  # No permitido
        
        # Interpolación lineal entre puntos de la tabla
        levels = sorted(DS594Calculator.EXPOSURE_LIMITS.keys())
        
        for i in range(len(levels) - 1):
            if levels[i] <= level_db < levels[i+1]:
                # Interpolación logarítmica (DS 594 usa factor de 3 dB)
                # Cada 3 dB duplica/reduce el tiempo
                delta_db = level_db - levels[i]
                time_factor = 2 ** (delta_db / 3)
                return DS594Calculator.EXPOSURE_LIMITS[levels[i]] / time_factor
        
        return 0.0
    
    @staticmethod
    def calculate_LAeq(levels_db: List[float]) -> float:
        """Calcula nivel equivalente LAeq"""
        if not levels_db:
            return 0.0
        
        # LAeq = 10 * log10(1/n * Σ(10^(Li/10)))
        sum_pressure = sum(10 ** (L / 10) for L in levels_db)
        LAeq = 10 * np.log10(sum_pressure / len(levels_db))
        return round(LAeq, 1)


class AnomalyDetector:
    """Detector de anomalías usando Isolation Forest"""
    
    def __init__(self, window_size: int = 100):
        self.model = IsolationForest(
            contamination=0.03,  # Reducido: solo 3% son anomalías
            random_state=42
        )
        self.window = deque(maxlen=window_size)
        self.is_trained = False
    
    def update(self, features: List[float]):
        """Actualiza ventana de datos y reentrena si necesario"""
        self.window.append(features)
        
        if len(self.window) >= 50 and not self.is_trained:
            self._train()
    
    def _train(self):
        """Entrena modelo con datos históricos"""
        X = np.array(list(self.window))
        self.model.fit(X)
        self.is_trained = True
    
    def detect(self, features: List[float]) -> Dict:
        """
        Detecta si los features son anómalos
        Retorna: {is_anomaly: bool, score: float, confidence: str}
        """
        if not self.is_trained or len(self.window) < 50:
            return {'is_anomaly': False, 'score': 0.0, 'confidence': 'insufficient_data'}
        
        X = np.array([features])
        prediction = self.model.predict(X)[0]
        score = self.model.score_samples(X)[0]
        
        # -1 = anomalía, 1 = normal
        is_anomaly = prediction == -1
        
        # Clasificar confianza
        if score < -0.7:       # Era -0.5, ahora -0.7
            confidence = 'high'
        elif score < -0.4:     # Era -0.2, ahora -0.4
            confidence = 'medium'
        else:
            confidence = 'low'
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(float(score), 3),
            'confidence': confidence
        }


class StreamProcessor:
    """Procesa stream de Kafka y almacena en InfluxDB/PostgreSQL"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Kafka Consumer
        self.consumer = KafkaConsumer(
            'acoustic-raw-data',
            bootstrap_servers=config['kafka']['bootstrap_servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='stream-processor-group',
            auto_offset_reset='latest'
        )
        
        # InfluxDB Client
        self.influx_client = InfluxDBClient(
            url=config['influxdb']['url'],
            token=config['influxdb']['token'],
            org=config['influxdb']['org']
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        
        # PostgreSQL Connection
        self.pg_conn = psycopg2.connect(
            host=config['postgres']['host'],
            database=config['postgres']['database'],
            user=config['postgres']['user'],
            password=config['postgres']['password']
        )
        
        # Detectores de anomalías por sensor
        self.anomaly_detectors = defaultdict(lambda: AnomalyDetector())
        
        # Buffer para cálculo de ventanas temporales
        self.sensor_buffers = defaultdict(lambda: deque(maxlen=100))
        
        print("✅ StreamProcessor inicializado correctamente")
    
    def _extract_features(self, measurement: Dict) -> List[float]:
        """Extrae features para detección de anomalías"""
        metrics = measurement['metrics']
        return [
            metrics['LAeq'],
            metrics['LPeak'],
            metrics['L10'],
            metrics['L90'],
            max(metrics['espectro_octavas']),
            np.std(metrics['espectro_octavas'])
        ]
    
    def _write_to_influxdb(self, measurement: Dict, calculated_metrics: Dict):
        """Escribe métricas a InfluxDB"""
        point = Point("acoustic_measurements") \
            .tag("sensor_id", measurement['sensor_id']) \
            .tag("zona", measurement['zona']) \
            .tag("turno", measurement['metadata']['turno']) \
            .field("LAeq", measurement['metrics']['LAeq']) \
            .field("LPeak", measurement['metrics']['LPeak']) \
            .field("frecuencia_dominante", measurement['metrics']['frecuencia_dominante']) \
            .field("L10", measurement['metrics']['L10']) \
            .field("L90", measurement['metrics']['L90']) \
            .field("dose_percent", calculated_metrics['dose']) \
            .field("ds594_exceeded", int(measurement['compliance']['ds594_exceeded'])) \
            .field("is_anomaly", int(calculated_metrics['anomaly']['is_anomaly'])) \
            .time(measurement['timestamp'])
        
        self.write_api.write(bucket=self.config['influxdb']['bucket'], record=point)
    
    def _save_alert(self, measurement: Dict, alert_type: str, severity: str):
        """Guarda alerta en PostgreSQL"""
        cursor = self.pg_conn.cursor()
        
        query = """
            INSERT INTO monitoring.alerts (timestamp, sensor_id, zona, alert_type, severity, 
                               level_db, peak_db, message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        message = f"{alert_type}: {measurement['metrics']['LAeq']} dB(A)"
        
        cursor.execute(query, (
            measurement['timestamp'],
            measurement['sensor_id'],
            measurement['zona'],
            alert_type,
            severity,
            measurement['metrics']['LAeq'],
            measurement['metrics']['LPeak'],
            message
        ))
        
        self.pg_conn.commit()
        cursor.close()
    
    def process_message(self, measurement: Dict):
        """Procesa un mensaje individual"""
        sensor_id = measurement['sensor_id']
        
        # 1. Agregar a buffer del sensor
        self.sensor_buffers[sensor_id].append(measurement)
        
        # 2. Detectar anomalías
        features = self._extract_features(measurement)
        detector = self.anomaly_detectors[sensor_id]
        detector.update(features)
        anomaly_result = detector.detect(features)
        
        # 3. Calcular dosis de ruido (ventana de 1 hora)
        recent_levels = [m['metrics']['LAeq'] for m in list(self.sensor_buffers[sensor_id])[-12:]]
        dose = DS594Calculator.calculate_dose(recent_levels, [1/12] * len(recent_levels))
        
        # 4. Calcular LAeq de ventana
        window_LAeq = DS594Calculator.calculate_LAeq(recent_levels)
        
        calculated_metrics = {
            'dose': dose,
            'window_LAeq': window_LAeq,
            'anomaly': anomaly_result
        }
        
        # 5. Escribir a InfluxDB
        self._write_to_influxdb(measurement, calculated_metrics)
        
        # 6. Generar alertas si necesario
        if measurement['compliance']['ds594_exceeded']:
            self._save_alert(measurement, 'DS594_EXCEEDED', 'high')
            print(f"🚨 ALERTA: {sensor_id} excede DS 594 - {measurement['metrics']['LAeq']} dB(A)")
        
        if measurement['compliance']['peak_exceeded']:
            self._save_alert(measurement, 'PEAK_EXCEEDED', 'critical')
            print(f"⚠️  CRÍTICO: {sensor_id} peak excedido - {measurement['metrics']['LPeak']} dB(C)")
        
        if anomaly_result['is_anomaly'] and anomaly_result['confidence'] == 'high':
            self._save_alert(measurement, 'ANOMALY_DETECTED', 'medium')
            print(f"🔍 ANOMALÍA: {sensor_id} - score: {anomaly_result['score']}")
        
        # 7. Log periódico
        if sum(len(buf) for buf in self.sensor_buffers.values()) % 25 == 0:
            print(f"📊 Procesados: {sum(len(buf) for buf in self.sensor_buffers.values())} mensajes")
    
    def run(self):
        """Loop principal de procesamiento"""
        print("🚀 Iniciando procesamiento de stream...")
        print("⏳ Esperando mensajes de Kafka...\n")
        
        try:
            for message in self.consumer:
                measurement = message.value
                self.process_message(measurement)
                
        except KeyboardInterrupt:
            print("\n⏹️  Procesador detenido por usuario")
        finally:
            self.consumer.close()
            self.influx_client.close()
            self.pg_conn.close()
            print("✅ Recursos liberados correctamente")


if __name__ == '__main__':
    # Configuración
    config = {
        'kafka': {
            'bootstrap_servers': 'localhost:9092'
        },
        'influxdb': {
            'url': 'http://localhost:8086',
            'token': 'my-super-secret-token-12345',
            'org': 'ruido-industrial',
            'bucket': 'acoustic-data'
        },
        'postgres': {
            'host': 'localhost',
            'database': 'ruido_db',
            'user': 'ruido_user',
            'password': 'ruido_password'
        }
    }
    
    processor = StreamProcessor(config)
    processor.run()