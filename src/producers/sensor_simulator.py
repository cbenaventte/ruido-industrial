"""
Simulador de Sensores Acústicos para Monitoreo Industrial
Genera datos sintéticos realistas con anomalías según DS 594
"""

import json
import time
import random
from datetime import datetime
from typing import Dict, List
import numpy as np
from kafka import KafkaProducer
from dataclasses import dataclass, asdict


@dataclass
class SensorConfig:
    """Configuración de cada sensor industrial"""
    sensor_id: str
    zona: str
    baseline_db: float  # Nivel de ruido base
    variacion: float    # Desviación estándar
    lat: float
    lon: float


class AcousticSimulator:
    """Genera datos acústicos sintéticos con patrones realistas"""
    
    # Límites DS 594 Chile
    DS594_LIMITS = {
        'continuo_8h': 85,      # dB(A) para 8 horas
        'peak_max': 140,         # dB(C) peak máximo
        'accion': 82,            # Nivel de acción preventiva
    }
    
    # Configuración de sensores en planta industrial
    SENSORS = [
        SensorConfig('SENSOR_001', 'Sala_Compresores', 83, 3.5, -33.4489, -70.6693),    # Reducido de 88 → 83
        SensorConfig('SENSOR_002', 'Zona_Soldadura', 78, 4.0, -33.4490, -70.6695),      # Reducido de 82 → 78
        SensorConfig('SENSOR_003', 'Prensas_Hidraulicas', 85, 5.0, -33.4488, -70.6690), # Reducido de 91 → 84
        SensorConfig('SENSOR_004', 'Area_Ensamble', 72, 2.5, -33.4492, -70.6688),       # Reducido de 75 → 72
        SensorConfig('SENSOR_005', 'Molienda_Metales', 89, 6.0, -33.4487, -70.6692),    # Reducido de 95 → 86
    ]
    
    def __init__(self, kafka_bootstrap_servers: str = 'localhost:9092'):
        """Inicializa el simulador con conexión a Kafka"""
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type='gzip'
        )
        self.topic = 'acoustic-raw-data'
        
    def _generate_spectrum(self, base_level: float) -> List[float]:
        """Genera espectro de frecuencias realista (octavas)"""
        # Frecuencias centrales: 125, 250, 500, 1000, 2000, 4000, 8000 Hz
        # Curva típica industrial: pico en medias frecuencias
        octave_weights = [0.85, 0.90, 0.95, 1.0, 0.98, 0.92, 0.80]
        spectrum = []
        
        for weight in octave_weights:
            level = base_level * weight + np.random.normal(0, 1.5)
            spectrum.append(round(level, 1))
            
        return spectrum
    
    def _inject_anomaly(self, data: Dict, anomaly_type: str) -> Dict:
        """Inyecta anomalías para probar detección"""
        if anomaly_type == 'spike':
            # Pico súbito (impacto, caída de objeto)
            data['metrics']['LAeq'] += random.uniform(8, 15)  # Reducido: 8-15 dB en lugar de 15-30
            data['metrics']['LPeak'] = min(random.uniform(110, 130), 145) # Reducido
            data['anomaly'] = 'spike_detected'
            
        elif anomaly_type == 'drift':
            # Deriva gradual (maquinaria deteriorándose)
            data['metrics']['LAeq'] += random.uniform(3, 8) # Reducido: 3-8 dB en lugar de 5-12
            data['anomaly'] = 'gradual_drift'
            
        elif anomaly_type == 'night_activity':
            # Actividad fuera de horario
            current_hour = datetime.now().hour
            if 22 <= current_hour or current_hour <= 6:
                data['metrics']['LAeq'] += random.uniform(5, 12) # Reducido: 5-12 dB en lugar de 10-20
                data['anomaly'] = 'off_hours_activity'
                
        return data
    
    def generate_measurement(self, sensor: SensorConfig, 
                           inject_anomaly: bool = False) -> Dict:
        """Genera una medición acústica sintética"""
        
        # Nivel equivalente base con variación gaussiana
        LAeq = sensor.baseline_db + np.random.normal(0, sensor.variacion)
        
        # Nivel peak (10-20 dB sobre LAeq típicamente)
        LPeak = LAeq + random.uniform(10, 20)
        
        # Frecuencia dominante (simulada)
        dominant_freq = random.choice([500, 1000, 1250, 2000, 4000])
        
        # Espectro de frecuencias
        spectrum = self._generate_spectrum(LAeq)
        
        # Turno laboral
        current_hour = datetime.now().hour
        if 8 <= current_hour < 16:
            turno = 'diurno'
        elif 16 <= current_hour < 24:
            turno = 'vespertino'
        else:
            turno = 'nocturno'
        
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sensor_id': sensor.sensor_id,
            'zona': sensor.zona,
            'location': {
                'lat': sensor.lat,
                'lon': sensor.lon
            },
            'metrics': {
                'LAeq': round(LAeq, 1),
                'LPeak': round(LPeak, 1),
                'frecuencia_dominante': dominant_freq,
                'espectro_octavas': spectrum,
                'L10': round(LAeq + 3, 1),  # Nivel superado 10% del tiempo
                'L90': round(LAeq - 5, 1),  # Nivel superado 90% del tiempo
            },
            'metadata': {
                'turno': turno,
                'operadores_estimados': random.randint(1, 5),
                'temperatura_c': round(random.uniform(15, 30), 1),
                'humedad_pct': round(random.uniform(40, 70), 1)
            },
            'compliance': {
                'ds594_exceeded': LAeq > self.DS594_LIMITS['continuo_8h'],
                'peak_exceeded': LPeak > self.DS594_LIMITS['peak_max'],
                'action_level': LAeq > self.DS594_LIMITS['accion']
            }
        }
        
        # Inyectar anomalías aleatoriamente (5% probabilidad)
        if inject_anomaly or random.random() < 0.02:  # Reducido de 5% a 2%
            anomaly_types = ['spike', 'drift', 'night_activity']
            anomaly = random.choice(anomaly_types)
            data = self._inject_anomaly(data, anomaly)
        else:
            data['anomaly'] = None
            
        return data
    
    def run(self, interval_seconds: int = 5, duration_minutes: int = None):
        """
        Ejecuta el simulador continuamente
        
        Args:
            interval_seconds: Intervalo entre mediciones (default: 5s)
            duration_minutes: Duración total (None = infinito)
        """
        print(f"🎤 Iniciando simulador de {len(self.SENSORS)} sensores acústicos")
        print(f"📊 Publicando en topic: {self.topic}")
        print(f"⏱️  Intervalo: {interval_seconds}s\n")
        
        start_time = time.time()
        measurement_count = 0
        
        try:
            while True:
                # Generar mediciones para todos los sensores
                for sensor in self.SENSORS:
                    measurement = self.generate_measurement(sensor)
                    
                    # Publicar a Kafka
                    self.producer.send(self.topic, value=measurement)
                    
                    # Log si excede límites
                    if measurement['compliance']['ds594_exceeded']:
                        print(f"⚠️  {sensor.sensor_id}: {measurement['metrics']['LAeq']} dB(A) - EXCEDE DS 594")
                    
                    if measurement.get('anomaly'):
                        print(f"🚨 {sensor.sensor_id}: Anomalía detectada - {measurement['anomaly']}")
                    
                    measurement_count += 1
                
                self.producer.flush()
                
                # Log cada minuto
                if measurement_count % (12 * len(self.SENSORS)) == 0:
                    elapsed = (time.time() - start_time) / 60
                    print(f"✅ {measurement_count} mediciones enviadas ({elapsed:.1f} min)")
                
                # Verificar duración
                if duration_minutes:
                    if (time.time() - start_time) / 60 >= duration_minutes:
                        print(f"\n✅ Simulación completada: {duration_minutes} minutos")
                        break
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n⏹️  Simulación detenida por usuario")
        finally:
            self.producer.close()
            print(f"📊 Total mediciones: {measurement_count}")


if __name__ == '__main__':
    # Configuración
    KAFKA_SERVER = 'localhost:9092'
    MEASUREMENT_INTERVAL = 5  # segundos
    
    # Iniciar simulador
    simulator = AcousticSimulator(kafka_bootstrap_servers=KAFKA_SERVER)
    simulator.run(interval_seconds=MEASUREMENT_INTERVAL)