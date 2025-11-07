import psycopg2
import time

print("🔍 Probando conexión a PostgreSQL...")

for attempt in range(1, 6):
    try:
        print(f"\nIntento {attempt}/5...")
        
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='ruido_db',
            user='ruido_user',
            password='ruido_password',
            connect_timeout=5
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print(f"✅ Conectado exitosamente!")
        print(f"PostgreSQL version: {version[0][:50]}...")
        
        # Verificar tablas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema IN ('config', 'monitoring', 'reporting')
        """)
        
        table_count = cursor.fetchone()[0]
        print(f"✅ Tablas encontradas: {table_count}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 PostgreSQL está listo para usar!")
        break
        
    except psycopg2.OperationalError as e:
        print(f"❌ Error de conexión: {e}")
        
        if attempt < 5:
            print("⏳ Esperando 5 segundos antes de reintentar...")
            time.sleep(5)
        else:
            print("\n💡 Soluciones:")
            print("1. Verificar que PostgreSQL esté corriendo:")
            print("   docker-compose ps postgres")
            print("\n2. Reiniciar PostgreSQL:")
            print("   docker-compose restart postgres")
            print("\n3. Ver logs:")
            print("   docker-compose logs postgres")