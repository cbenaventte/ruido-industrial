# Guía de Instalación Detallada

## Requisitos Previos

- Docker Desktop 20+
- Python 3.10+
- 4GB RAM disponible
- 5GB espacio en disco

## Instalación Paso a Paso

### 1. Clonar Repositorio

```bash
git clone https://github.com/tu-usuario/ruido-industrial-ds594.git
cd ruido-industrial-ds594
```

### 2. Configurar Entorno Python

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus configuraciones
nano .env
```

### 4. Levantar Servicios Docker

```bash
# Iniciar todos los servicios
docker-compose up -d

# Verificar que estén corriendo
docker-compose ps

# Ver logs
docker-compose logs -f
```

### 5. Inicializar Base de Datos

```bash
# Esperar 30 segundos a que PostgreSQL inicie
sleep 30

# Verificar que la BD esté lista
docker-compose exec postgres psql -U ruido_user -d ruido_db -c "SELECT version();"
```

### 6. Configurar InfluxDB

```bash
# Acceder a http://localhost:8086
# User: admin
# Pass: adminpassword123
# Org: ruido-industrial
# Bucket: acoustic-data
```

### 7. Ejecutar Simulador

```bash
# Terminal 1: Simulador de sensores
python src/producers/sensor_simulator.py
```

### 8. Ejecutar Procesador

```bash
# Terminal 2: Procesador de stream
python src/consumers/stream_processor.py
```

## Verificación

### Kafka

```bash
# Ver topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Consumir mensajes (debugging)
docker-compose exec kafka kafka-console-consumer --topic acoustic-raw-data --from-beginning --bootstrap-server localhost:9092
```

### InfluxDB

```bash
# Query desde CLI
docker-compose exec influxdb influx query 'from(bucket:"acoustic-data") |> range(start:-1h)'
```

### PostgreSQL

```bash
# Conectar a BD
docker-compose exec postgres psql -U ruido_user -d ruido_db

# Ver alertas
SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 10;
```

## Solución de Problemas

### Puerto ya en uso

```bash
# Identificar proceso
lsof -i :9092  # Kafka
lsof -i :8086  # InfluxDB
lsof -i :5432  # PostgreSQL

# Detener servicios
docker-compose down
```

### Error de conexión a Kafka

```bash
# Reiniciar Kafka
docker-compose restart kafka zookeeper
```

### InfluxDB no responde

```bash
# Ver logs
docker-compose logs influxdb

# Reiniciar
docker-compose restart influxdb
```